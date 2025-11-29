#!/usr/bin/env python3
"""
Step 4: Export District 18 Office Building Tenants to KMZ
Creates interactive Google Maps KMZ file with clickable building markers
"""

import csv
import os
from pathlib import Path
from typing import Dict, List, Optional
from xml.etree.ElementTree import Element, SubElement, ElementTree
import zipfile
from datetime import datetime


# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "building_tenants"
BUILDINGS_CSV = DATA_DIR / "buildings" / "district18_buildings.csv"
TENANTS_DIR = DATA_DIR / "tenants" / "district18"
OUTPUT_KML = DATA_DIR / "exports" / "district18_tenants.kml"
OUTPUT_KMZ = DATA_DIR / "exports" / "district18_tenants.kmz"


def load_building_data() -> List[Dict]:
    """Load all building coordinates from CSV"""
    buildings = []
    with open(BUILDINGS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Only include buildings with coordinates
            if row.get('latitude') and row.get('longitude'):
                try:
                    buildings.append({
                        'address': row['address'],
                        'lat': float(row['latitude']),
                        'lon': float(row['longitude']),
                        'levels': row.get('building_levels', 'N/A')
                    })
                except (ValueError, KeyError):
                    continue
    return buildings


def load_tenant_data(building_address: str) -> Dict:
    """
    Load all tenant data for a building from CSV files
    Returns dict with merchants, lawyers, building_contacts
    """
    # Sanitize filename - match scraper's naming convention
    # Scraper creates files like: "500 5th Ave New York NY_merchants.csv"
    filename_base = building_address.replace(', ', ' ').replace(',', '')

    result = {
        'merchants': [],
        'lawyers': [],
        'building_contacts': []
    }

    # Try to load merchants (from tenants directory)
    merchants_file = TENANTS_DIR / f"{filename_base}_merchants.csv"
    if merchants_file.exists():
        with open(merchants_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            result['merchants'] = list(reader)

    # Try to load lawyers
    lawyers_file = TENANTS_DIR / f"{filename_base}_lawyers.csv"
    if lawyers_file.exists():
        with open(lawyers_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            result['lawyers'] = list(reader)

    # Try to load building contacts
    contacts_file = TENANTS_DIR / f"{filename_base}_building_contacts.csv"
    if contacts_file.exists():
        with open(contacts_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            result['building_contacts'] = list(reader)

    return result


def create_html_popup(building: Dict, tenants: Dict, has_building_contacts: int = 0) -> str:
    """Generate HTML popup content for a building"""
    address = building['address']
    levels = building['levels']

    # Count totals
    total_merchants = len(tenants['merchants'])
    total_lawyers = len(tenants['lawyers'])
    total_contacts = len(tenants['building_contacts'])
    total_tenants = total_merchants + total_lawyers

    # Start HTML
    html = f'''<div style="font-family: Arial, sans-serif; max-width: 500px; font-size: 13px;">
  <h3 style="color: #1a73e8; margin: 0 0 5px 0; font-size: 16px;">
    🏢 {address}
  </h3>
  <p style="color: #666; margin: 5px 0; font-size: 12px;">
    📍 {address}
  </p>
  <hr style="border: 1px solid #ddd; margin: 10px 0;"/>

  <p style="margin: 5px 0;"><b>Total Tenants:</b> {total_tenants}</p>
  <p style="margin: 5px 0;"><b>Building Levels:</b> {levels}</p>
'''

    # Merchants Section
    if total_merchants > 0:
        html += f'''
  <h4 style="color: #333; border-bottom: 2px solid #1a73e8; padding-bottom: 5px; margin-top: 15px; font-size: 14px;">
    📋 Tenants ({total_merchants})
  </h4>
  <div style="margin-left: 10px;">
'''
        for i, merchant in enumerate(tenants['merchants'][:20]):  # Limit to 20 to avoid popup overflow
            name = merchant.get('name', 'Unknown')
            website = merchant.get('website', '')
            email = merchant.get('email', '')
            phone = merchant.get('phone', '')
            contact_person = merchant.get('contact_person', '')
            contact_title = merchant.get('contact_title', '')

            # Merchant info
            html += f'      <p style="margin: 8px 0 2px 0; font-weight: bold; font-size: 13px;">{name}</p>\n'

            if website:
                html += f'      <p style="margin: 2px 0; font-size: 12px;">🌐 <a href="{website}" target="_blank">Website</a></p>\n'
            if email:
                html += f'      <p style="margin: 2px 0; font-size: 12px;">📧 {email}</p>\n'
            if phone:
                html += f'      <p style="margin: 2px 0; font-size: 12px;">📞 {phone}</p>\n'
            if contact_person:
                title_str = f" - {contact_title}" if contact_title else ""
                html += f'      <p style="margin: 2px 0 8px 0; font-size: 11px; color: #666;">👤 {contact_person}{title_str}</p>\n'

            # Add divider line after each merchant (including the last one if building management follows)
            if i < min(len(tenants['merchants']), 20) - 1:
                html += '      <p style="margin: 10px 0; color: #999;">──────────────────────</p>\n'

        if total_merchants > 20:
            html += f'    <p style="color: #666; font-style: italic; font-size: 12px;">...and {total_merchants - 20} more tenants</p>\n'

        html += '  </div>\n'

    # Law Firms Section
    if total_lawyers > 0:
        html += f'''
  <h4 style="color: #333; border-bottom: 2px solid #d32f2f; padding-bottom: 5px; margin-top: 15px; font-size: 14px;">
    ⚖️ Law Firms ({total_lawyers})
  </h4>
  <div style="margin-left: 10px;">
'''
        # Group by company
        lawyers_by_company = {}
        for lawyer in tenants['lawyers']:
            company = lawyer.get('company_name', 'Unknown Firm')
            if company not in lawyers_by_company:
                lawyers_by_company[company] = []
            lawyers_by_company[company].append(lawyer)

        for company, lawyers in list(lawyers_by_company.items())[:10]:  # Limit to 10 firms
            # Add gray box for each law firm
            html += f'    <div style="margin-bottom: 10px; padding: 10px; background: #f8f9fa; border-radius: 4px;">\n'
            html += f'      <p style="margin: 0 0 8px 0; font-weight: bold; font-size: 13px;">{company}</p>\n'

            for lawyer in lawyers[:5]:  # Max 5 lawyers per firm
                lawyer_name = lawyer.get('lawyer_name', '')
                lawyer_title = lawyer.get('lawyer_title', '')
                lawyer_email = lawyer.get('lawyer_email', '')
                lawyer_phone = lawyer.get('lawyer_phone', '')

                if lawyer_name:
                    title_str = f" - {lawyer_title}" if lawyer_title else ""
                    html += f'      <div style="margin-left: 15px; margin-bottom: 6px;">\n'
                    html += f'        <p style="margin: 2px 0; font-size: 12px;">• {lawyer_name}{title_str}</p>\n'
                    if lawyer_email:
                        html += f'        <p style="margin: 2px 0 2px 18px; font-size: 11px;">📧 {lawyer_email}</p>\n'
                    if lawyer_phone:
                        html += f'        <p style="margin: 2px 0 2px 18px; font-size: 11px;">📞 {lawyer_phone}</p>\n'
                    html += '      </div>\n'

            if len(lawyers) > 5:
                html += f'      <p style="margin-left: 15px; color: #666; font-style: italic; font-size: 11px;">...and {len(lawyers) - 5} more attorneys</p>\n'

            html += '    </div>\n'

        if len(lawyers_by_company) > 10:
            html += f'    <p style="color: #666; font-style: italic; font-size: 12px;">...and {len(lawyers_by_company) - 10} more law firms</p>\n'

        html += '  </div>\n'

    # Building Management Section
    if total_contacts > 0:
        # Add divider before Building Management if there were merchants or lawyers before it
        if total_merchants > 0 or total_lawyers > 0:
            html += '  <p style="margin: 15px 0 5px 0; color: #999;">──────────────────────</p>\n'
            html += '  <br/>\n'

        html += f'''
  <h4 style="color: #333; border-bottom: 2px solid #f9a825; padding-bottom: 5px; margin-top: 10px; font-size: 14px;">
    🏗️ Building Management
  </h4>
  <div style="margin-left: 10px;">
'''
        # Group contacts by company name
        contacts_by_company = {}
        for contact in tenants['building_contacts']:
            company = contact.get('building_name', contact.get('name', 'Unknown'))
            if company not in contacts_by_company:
                contacts_by_company[company] = []
            contacts_by_company[company].append(contact)

        # Display grouped contacts (max 3 companies, max 5 contacts per company)
        for company, contacts in list(contacts_by_company.items())[:3]:
            # Add gray box for each company
            html += f'    <div style="margin-bottom: 8px; margin-top: 5px; padding: 10px; background: #f8f9fa; border-radius: 4px;">\n'
            html += f'      <p style="margin: 0 0 4px 0; font-weight: bold; font-size: 13px;">{company}</p>\n'

            for contact in contacts[:5]:  # Max 5 contacts per company
                contact_person = contact.get('contact_name', contact.get('contact_person', ''))
                contact_title = contact.get('contact_title', '')
                email = contact.get('email', '')
                phone = contact.get('phone', '')
                website = contact.get('website', '')

                if contact_person:
                    title_str = f" - {contact_title}" if contact_title else ""
                    html += f'      <div style="margin-left: 15px; margin-bottom: 6px;">\n'
                    html += f'        <p style="margin: 2px 0; font-size: 12px;">• {contact_person}{title_str}</p>\n'
                    if email:
                        html += f'        <p style="margin: 2px 0 2px 18px; font-size: 11px;">📧 {email}</p>\n'
                    if phone:
                        html += f'        <p style="margin: 2px 0 2px 18px; font-size: 11px;">📞 {phone}</p>\n'
                    if website:
                        html += f'        <p style="margin: 2px 0 2px 18px; font-size: 11px;">🌐 <a href="{website}" target="_blank">Website</a></p>\n'
                    html += '      </div>\n'

            if len(contacts) > 5:
                html += f'      <p style="margin-left: 15px; color: #666; font-style: italic; font-size: 11px;">...and {len(contacts) - 5} more contacts</p>\n'

            html += '    </div>\n'

        if len(contacts_by_company) > 3:
            html += f'    <p style="color: #666; font-style: italic; font-size: 12px;">...and {len(contacts_by_company) - 3} more management companies</p>\n'

        html += '  </div>\n'

    # No data message
    if total_tenants == 0 and total_contacts == 0:
        html += '''
  <p style="color: #999; font-style: italic; margin-top: 15px;">
    No tenant data available for this building.
  </p>
'''

    # Footer
    html += f'''
  <hr style="border: 1px solid #ddd; margin-top: 15px;"/>
  <p style="font-size: 11px; color: #999; text-align: center; margin: 5px 0;">
    Data scraped: {datetime.now().strftime('%Y-%m-%d')}
  </p>
</div>'''

    return html


def determine_marker_style(tenant_count: int) -> str:
    """Return style ID based on tenant count"""
    if tenant_count >= 20:
        return "high-density"
    elif tenant_count >= 10:
        return "medium-density"
    elif tenant_count >= 5:
        return "low-density"
    else:
        return "minimal-data"


def create_kml_styles(doc: Element) -> None:
    """Create color-coded marker styles"""
    # Using standard Google Maps colored dots - most reliable across platforms
    styles = [
        ("high-density", "http://maps.google.com/mapfiles/ms/icons/green-dot.png"),  # Green
        ("medium-density", "http://maps.google.com/mapfiles/ms/icons/yellow-dot.png"),  # Yellow
        ("low-density", "http://maps.google.com/mapfiles/ms/icons/orange-dot.png"),  # Orange
        ("minimal-data", "http://maps.google.com/mapfiles/ms/icons/blue-dot.png"),  # Blue
    ]

    for style_id, icon_url in styles:
        style = SubElement(doc, "Style", id=style_id)
        icon_style = SubElement(style, "IconStyle")
        icon = SubElement(icon_style, "Icon")
        href = SubElement(icon, "href")
        href.text = icon_url


def create_building_placemark(doc: Element, building: Dict, tenants: Dict) -> None:
    """Create KML placemark for a building"""
    address = building['address']
    lat = building['lat']
    lon = building['lon']

    # Count tenants
    tenant_count = len(tenants['merchants']) + len(tenants['lawyers'])
    contact_count = len(tenants['building_contacts'])

    # Create placemark
    placemark = SubElement(doc, "Placemark")

    # Name
    name = SubElement(placemark, "name")
    name.text = address

    # Description (HTML popup)
    description = SubElement(placemark, "description")
    html_content = create_html_popup(building, tenants, contact_count)
    description.text = f"<![CDATA[{html_content}]]>"

    # Style
    style_url = SubElement(placemark, "styleUrl")
    style_url.text = f"#{determine_marker_style(tenant_count)}"

    # Coordinates
    point = SubElement(placemark, "Point")
    coordinates = SubElement(point, "coordinates")
    coordinates.text = f"{lon},{lat},0"


def export_to_kmz() -> None:
    """Main export function"""
    print("=" * 60)
    print("DISTRICT 18: EXPORTING TO KMZ")
    print("=" * 60)

    # Load buildings
    print("\n1. Loading building data...")
    buildings = load_building_data()
    print(f"   Loaded {len(buildings)} buildings with coordinates")

    # Create KML document
    print("\n2. Creating KML document...")
    kml = Element("kml", xmlns="http://www.opengis.net/kml/2.2")
    document = SubElement(kml, "Document")

    # Document info
    doc_name = SubElement(document, "name")
    doc_name.text = "District 18 Office Building Tenants"

    doc_desc = SubElement(document, "description")
    doc_desc.text = f"""District 18 office buildings with tenant directories

📍 Color Legend (by tenant count):
🟢 Green = High Density (20+ tenants)
🟡 Yellow = Medium Density (10-19 tenants)
🟠 Orange = Low Density (5-9 tenants)
🔵 Blue = Minimal Data (1-4 tenants)

Data scraped: {datetime.now().strftime('%Y-%m-%d')}
Total buildings: {len(buildings)}"""

    # Create styles
    print("   Creating marker styles...")
    create_kml_styles(document)

    # Create placemarks
    print("\n3. Creating placemarks for buildings...")
    buildings_with_data = 0
    buildings_without_data = 0
    total_tenants = 0

    for i, building in enumerate(buildings, 1):
        if i % 20 == 0:
            print(f"   Progress: {i}/{len(buildings)} buildings processed")

        # Load tenant data
        tenants = load_tenant_data(building['address'])
        tenant_count = len(tenants['merchants']) + len(tenants['lawyers'])
        contact_count = len(tenants['building_contacts'])

        # Skip buildings with no data at all (no tenants AND no building contacts)
        if tenant_count == 0 and contact_count == 0:
            buildings_without_data += 1
            continue

        # Create placemark for buildings with tenant data OR building management contacts
        buildings_with_data += 1
        total_tenants += tenant_count
        create_building_placemark(document, building, tenants)

    print(f"   Complete: {buildings_with_data} placemarks created (skipped {buildings_without_data} buildings with no data)")

    # Save KML
    print("\n4. Saving KML file...")
    OUTPUT_KML.parent.mkdir(parents=True, exist_ok=True)
    tree = ElementTree(kml)
    tree.write(OUTPUT_KML, encoding='utf-8', xml_declaration=True)
    print(f"   ✓ KML saved: {OUTPUT_KML}")

    # Create KMZ (zipped KML)
    print("\n5. Creating KMZ package...")
    with zipfile.ZipFile(OUTPUT_KMZ, 'w', zipfile.ZIP_DEFLATED) as kmz:
        kmz.write(OUTPUT_KML, arcname='doc.kml')
    print(f"   ✓ KMZ saved: {OUTPUT_KMZ}")

    # Print summary
    print("\n" + "=" * 60)
    print("EXPORT SUMMARY")
    print("=" * 60)
    print(f"Total Buildings: {len(buildings)}")
    print(f"Buildings with Data: {buildings_with_data}")
    print(f"Buildings without Data: {buildings_without_data}")
    print(f"Total Tenants: {total_tenants}")
    if buildings_with_data > 0:
        print(f"Average Tenants per Building: {total_tenants / buildings_with_data:.1f}")
    print()
    print(f"Output File: {OUTPUT_KMZ}")
    print(f"File Size: {OUTPUT_KMZ.stat().st_size / 1024:.1f} KB")
    print()
    print("✅ Ready to import into Google My Maps!")
    print("   → Go to https://mymaps.google.com")
    print("   → Click 'Create a New Map'")
    print("   → Click 'Import'")
    print("   → Upload the .kmz file")
    print("=" * 60)


def main():
    """Entry point"""
    try:
        export_to_kmz()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()

