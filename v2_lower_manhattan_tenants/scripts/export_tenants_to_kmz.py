#!/usr/bin/env python3
"""
Export Lower Manhattan Office Building Tenants to KMZ
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
PROJECT_ROOT = Path(__file__).parent.parent
V2_DATA_DIR = PROJECT_ROOT / "data"
# CSV files are saved in parent data directory by scraper
MAIN_DATA_DIR = PROJECT_ROOT.parent / "data"
BUILDINGS_CSV = V2_DATA_DIR / "lower_manhattan_office_buildings.csv"
OUTPUT_KML = V2_DATA_DIR / "lower_manhattan_tenants.kml"
OUTPUT_KMZ = V2_DATA_DIR / "lower_manhattan_tenants.kmz"


def load_building_data() -> List[Dict]:
    """Load all building coordinates from CSV"""
    buildings = []
    with open(BUILDINGS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Load all buildings - scraper already filtered for commercial/office
            buildings.append({
                'address': row['address'],
                'lat': float(row['latitude']),
                'lon': float(row['longitude']),
                'levels': row.get('building_levels', 'N/A')
            })
    return buildings


def load_tenant_data(building_address: str) -> Dict:
    """
    Load all tenant data for a building from CSV files
    Returns dict with merchants, lawyers, building_contacts
    """
    # Sanitize filename - match scraper's naming convention
    # Scraper creates files like: "28 Liberty Street New York NY_merchants.csv"
    filename_base = building_address.replace(', ', ' ').replace(',', '')

    result = {
        'merchants': [],
        'lawyers': [],
        'building_contacts': []
    }

    # Try to load merchants (from main data directory where scraper saves them)
    merchants_file = MAIN_DATA_DIR / f"{filename_base}_merchants.csv"
    if merchants_file.exists():
        with open(merchants_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            result['merchants'] = list(reader)

    # Try to load lawyers
    lawyers_file = MAIN_DATA_DIR / f"{filename_base}_lawyers.csv"
    if lawyers_file.exists():
        with open(lawyers_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            result['lawyers'] = list(reader)

    # Try to load building contacts
    contacts_file = MAIN_DATA_DIR / f"{filename_base}_building_contacts.csv"
    if contacts_file.exists():
        with open(contacts_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            result['building_contacts'] = list(reader)

    return result


def create_html_popup(building: Dict, tenants: Dict) -> str:
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
        for merchant in tenants['merchants'][:20]:  # Limit to 20 to avoid popup overflow
            name = merchant.get('name', 'Unknown')
            website = merchant.get('website', '')
            email = merchant.get('email', '')
            phone = merchant.get('phone', '')
            contact_person = merchant.get('contact_person', '')
            contact_title = merchant.get('contact_title', '')

            html += f'''
    <div style="margin-bottom: 12px; padding: 8px; background: #f8f9fa; border-radius: 4px;">
      <p style="margin: 2px 0; font-weight: bold;">{name}</p>
'''
            if website:
                html += f'      <p style="margin: 2px 0; font-size: 12px;">🌐 <a href="{website}" target="_blank">Website</a></p>\n'
            if email:
                html += f'      <p style="margin: 2px 0; font-size: 12px;">📧 {email}</p>\n'
            if phone:
                html += f'      <p style="margin: 2px 0; font-size: 12px;">📞 {phone}</p>\n'
            if contact_person:
                title_str = f" - {contact_title}" if contact_title else ""
                html += f'      <p style="margin: 2px 0; font-size: 11px; color: #666;">👤 {contact_person}{title_str}</p>\n'

            html += '    </div>\n'

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
            html += f'    <div style="margin-bottom: 10px;">\n'
            html += f'      <p style="margin: 2px 0; font-weight: bold;">{company}</p>\n'
            html += '      <ul style="margin: 5px 0; padding-left: 20px; font-size: 12px;">\n'

            for lawyer in lawyers[:5]:  # Max 5 lawyers per firm
                lawyer_name = lawyer.get('lawyer_name', '')
                lawyer_title = lawyer.get('lawyer_title', '')
                lawyer_email = lawyer.get('lawyer_email', '')
                lawyer_phone = lawyer.get('lawyer_phone', '')

                if lawyer_name:
                    title_str = f" - {lawyer_title}" if lawyer_title else ""
                    html += f'        <li>{lawyer_name}{title_str}'
                    if lawyer_email or lawyer_phone:
                        html += '<br/>'
                        if lawyer_email:
                            html += f'📧 {lawyer_email} '
                        if lawyer_phone:
                            html += f'📞 {lawyer_phone}'
                    html += '</li>\n'

            if len(lawyers) > 5:
                html += f'        <li style="color: #666; font-style: italic;">...and {len(lawyers) - 5} more attorneys</li>\n'

            html += '      </ul>\n'
            html += '    </div>\n'

        if len(lawyers_by_company) > 10:
            html += f'    <p style="color: #666; font-style: italic; font-size: 12px;">...and {len(lawyers_by_company) - 10} more law firms</p>\n'

        html += '  </div>\n'

    # Building Management Section
    if total_contacts > 0:
        html += f'''
  <h4 style="color: #333; border-bottom: 2px solid #f9a825; padding-bottom: 5px; margin-top: 15px; font-size: 14px;">
    🏗️ Building Management
  </h4>
  <div style="margin-left: 10px;">
'''
        for contact in tenants['building_contacts'][:3]:  # Max 3 contacts
            company = contact.get('name', 'Unknown')
            contact_person = contact.get('contact_person', '')
            contact_title = contact.get('contact_title', '')
            email = contact.get('email', '')
            phone = contact.get('phone', '')
            website = contact.get('website', '')

            html += f'    <div style="margin-bottom: 10px;">\n'
            html += f'      <p style="margin: 2px 0; font-weight: bold;">{company}</p>\n'

            if contact_person:
                title_str = f" - {contact_title}" if contact_title else ""
                html += f'      <p style="margin: 2px 0; font-size: 12px;">👤 {contact_person}{title_str}</p>\n'
            if email:
                html += f'      <p style="margin: 2px 0; font-size: 12px;">📧 {email}</p>\n'
            if phone:
                html += f'      <p style="margin: 2px 0; font-size: 12px;">📞 {phone}</p>\n'
            if website:
                html += f'      <p style="margin: 2px 0; font-size: 12px;">🌐 <a href="{website}" target="_blank">Website</a></p>\n'

            html += '    </div>\n'

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
    Data scraped: {datetime.now().strftime('%Y-%m-%d')}<br/>
    Generated by Phase 1 Web Scraping
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
    styles = [
        ("high-density", "http://maps.google.com/mapfiles/kml/paddle/grn-circle.png"),
        ("medium-density", "http://maps.google.com/mapfiles/kml/paddle/ylw-circle.png"),
        ("low-density", "http://maps.google.com/mapfiles/kml/paddle/orange-circle.png"),
        ("minimal-data", "http://maps.google.com/mapfiles/kml/paddle/wht-circle.png"),
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

    # Create placemark
    placemark = SubElement(doc, "Placemark")

    # Name
    name = SubElement(placemark, "name")
    name.text = address

    # Description (HTML popup)
    description = SubElement(placemark, "description")
    html_content = create_html_popup(building, tenants)
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
    print("EXPORTING TO KMZ")
    print("=" * 60)

    # Load buildings
    print("\n1. Loading building data...")
    buildings = load_building_data()
    print(f"   Loaded {len(buildings)} buildings")

    # Create KML document
    print("\n2. Creating KML document...")
    kml = Element("kml", xmlns="http://www.opengis.net/kml/2.2")
    document = SubElement(kml, "Document")

    # Document info
    doc_name = SubElement(document, "name")
    doc_name.text = "Lower Manhattan Office Building Tenants"

    doc_desc = SubElement(document, "description")
    doc_desc.text = f"324 buildings with tenant directories - Scraped {datetime.now().strftime('%Y-%m-%d')}"

    # Create styles
    print("   Creating marker styles...")
    create_kml_styles(document)

    # Create placemarks
    print("\n3. Creating placemarks for buildings...")
    buildings_with_data = 0
    buildings_without_data = 0
    total_tenants = 0

    for i, building in enumerate(buildings, 1):
        if i % 50 == 0:
            print(f"   Progress: {i}/{len(buildings)} buildings processed")

        # Load tenant data
        tenants = load_tenant_data(building['address'])
        tenant_count = len(tenants['merchants']) + len(tenants['lawyers'])

        # Skip buildings with no tenants (only show buildings with actual merchants/lawyers)
        if tenant_count == 0:
            buildings_without_data += 1
            continue

        # Only create placemark for buildings with tenant data
        buildings_with_data += 1
        total_tenants += tenant_count
        create_building_placemark(document, building, tenants)

    print(f"   Complete: {buildings_with_data} placemarks created (skipped {buildings_without_data} buildings with no data)")

    # Save KML
    print("\n4. Saving KML file...")
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
    print(f"Average Tenants per Building: {total_tenants / max(buildings_with_data, 1):.1f}")
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
