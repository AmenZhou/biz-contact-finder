#!/usr/bin/env python3
"""
Export District 9 Office Building Tenants to KMZ
Creates interactive Google Maps KMZ file with building management info prominently displayed
"""

import csv
import os
from pathlib import Path
from typing import Dict, List, Optional
from xml.etree.ElementTree import Element, SubElement, ElementTree
import zipfile
from datetime import datetime


# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "building_tenants"
DISTRICT9_DATA_DIR = DATA_DIR / "tenants" / "district9"
BUILDINGS_CSV = DATA_DIR / "buildings" / "district9_buildings.csv"
OUTPUT_KML = DATA_DIR / "exports" / "district9_tenants.kml"
OUTPUT_KMZ = DATA_DIR / "exports" / "district9_tenants.kmz"


def load_building_data() -> List[Dict]:
    """Load all District 9 building coordinates from CSV"""
    buildings = []
    with open(BUILDINGS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            buildings.append({
                'name': row['building_name'],
                'address': row['address'],
                'lat': float(row['latitude']),
                'lon': float(row['longitude'])
            })
    return buildings


def load_tenant_data(building_name: str) -> Dict:
    """
    Load all tenant data for a building from District 9 CSV files
    Returns dict with merchants, lawyers, building_contacts
    """
    # Mapping of building names to their actual CSV filename prefixes
    filename_map = {
        '330 Madison Avenue': '330Madison',
        '1221 Avenue of the Americas': '1221_6th',
        '477 Madison Avenue': '477 Madison Ave',
        '485 Madison Avenue': '485_Madison_Ave',
        '488 Madison Avenue': '488_Madison_Ave',
        '499 Park Avenue': '499 Park Ave'
    }

    # Get the filename prefix for this building
    filename_prefix = filename_map.get(building_name)

    result = {
        'merchants': [],
        'lawyers': [],
        'building_contacts': []
    }

    if not filename_prefix:
        return result

    # Try to load merchants
    merchants_file = DISTRICT9_DATA_DIR / f"{filename_prefix}_merchants.csv"
    if merchants_file.exists():
        with open(merchants_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            result['merchants'] = list(reader)

    # Try to load lawyers
    lawyers_file = DISTRICT9_DATA_DIR / f"{filename_prefix}_lawyers.csv"
    if lawyers_file.exists():
        with open(lawyers_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            result['lawyers'] = list(reader)

    # Try to load building contacts
    contacts_file = DISTRICT9_DATA_DIR / f"{filename_prefix}_building_contacts.csv"
    if contacts_file.exists():
        with open(contacts_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            result['building_contacts'] = list(reader)

    return result


def create_html_popup(building: Dict, tenants: Dict) -> str:
    """Generate HTML popup content for a building with building management prominently displayed"""
    name = building['name']
    address = building['address']

    # Count totals
    total_merchants = len(tenants['merchants'])
    total_lawyers = len(tenants['lawyers'])
    total_contacts = len(tenants['building_contacts'])
    total_tenants = total_merchants + total_lawyers

    # Start HTML with building header
    html = f'''<div style="font-family: Arial, sans-serif; max-width: 600px; font-size: 13px;">
  <h2 style="color: #1a73e8; margin: 0 0 8px 0; font-size: 18px;">
    🏢 {name}
  </h2>
  <p style="color: #666; margin: 5px 0 10px 0; font-size: 12px;">
    📍 {address}
  </p>
'''

    # ===========================
    # BUILDING MANAGEMENT SECTION - PROMINENTLY DISPLAYED FIRST
    # ===========================
    if total_contacts > 0:
        html += f'''
  <div style="background: linear-gradient(135deg, #fff9e6 0%, #fff3cd 100%); border: 2px solid #f9a825; border-radius: 8px; padding: 15px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(249,168,37,0.2);">
    <h3 style="color: #d68000; margin: 0 0 12px 0; font-size: 17px; border-bottom: 2px solid #f9a825; padding-bottom: 8px;">
      🏗️ BUILDING MANAGEMENT
    </h3>
'''
        for contact in tenants['building_contacts']:
            building_name_field = contact.get('building_name', '')
            building_type = contact.get('building_type', '')
            mgmt_company = contact.get('management_company', '')
            contact_name = contact.get('contact_name', '')
            contact_title = contact.get('contact_title', '')
            contact_email = contact.get('contact_email', '')
            contact_phone = contact.get('contact_phone', '')
            tenant_email = contact.get('tenant_engagement_email', '')
            main_phone = contact.get('main_phone', '')
            website = contact.get('website', '')
            portal = contact.get('tenant_portal', '')

            # Management company section
            if mgmt_company:
                html += f'    <p style="margin: 5px 0; font-size: 15px; font-weight: bold; color: #d68000;">🏢 {mgmt_company}</p>\n'

            if building_type:
                html += f'    <p style="margin: 3px 0; font-size: 13px; color: #555;">Type: {building_type}</p>\n'

            # Primary contact
            if contact_name:
                title_str = f" - {contact_title}" if contact_title else ""
                html += f'    <p style="margin: 8px 0 3px 0; font-size: 14px; font-weight: bold; color: #333;">👤 {contact_name}{title_str}</p>\n'

            # Contact information
            if contact_email:
                html += f'    <p style="margin: 3px 0; font-size: 13px;">📧 <a href="mailto:{contact_email}" style="color: #1a73e8; text-decoration: none;">{contact_email}</a></p>\n'
            if contact_phone:
                html += f'    <p style="margin: 3px 0; font-size: 13px;">📞 {contact_phone}</p>\n'

            # Additional contact info
            if tenant_email and tenant_email != contact_email:
                html += f'    <p style="margin: 3px 0; font-size: 12px; color: #555;">📬 Tenant Engagement: <a href="mailto:{tenant_email}" style="color: #1a73e8;">{tenant_email}</a></p>\n'
            if main_phone and main_phone != contact_phone:
                html += f'    <p style="margin: 3px 0; font-size: 12px; color: #555;">☎️ Main Phone: {main_phone}</p>\n'

            # Links
            if website:
                html += f'    <p style="margin: 5px 0 3px 0; font-size: 13px;">🌐 <a href="{website}" target="_blank" style="color: #1a73e8; font-weight: 500;">Building Website</a></p>\n'
            if portal:
                html += f'    <p style="margin: 3px 0; font-size: 13px;">🔐 <a href="{portal}" target="_blank" style="color: #1a73e8; font-weight: 500;">Tenant Portal</a></p>\n'

        html += '  </div>\n'

    # Add separator and tenant summary
    html += f'''
  <hr style="border: 1px solid #ddd; margin: 15px 0;"/>
  <p style="margin: 10px 0; font-size: 14px; color: #333;"><b>Total Tenants:</b> {total_tenants}</p>
'''

    # ===========================
    # MERCHANTS SECTION
    # ===========================
    if total_merchants > 0:
        html += f'''
  <h4 style="color: #333; border-bottom: 2px solid #1a73e8; padding-bottom: 5px; margin-top: 15px; font-size: 14px;">
    📋 Tenants ({total_merchants})
  </h4>
  <div style="margin-left: 10px;">
'''
        for merchant in tenants['merchants'][:20]:  # Limit to 20
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

    # ===========================
    # LAW FIRMS SECTION
    # ===========================
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

    # No data message
    if total_tenants == 0 and total_contacts == 0:
        html += '''
  <p style="color: #999; font-style: italic; margin-top: 15px;">
    No data available for this building.
  </p>
'''

    # Footer
    html += f'''
  <hr style="border: 1px solid #ddd; margin-top: 15px;"/>
  <p style="font-size: 11px; color: #999; text-align: center; margin: 5px 0;">
    District 9 Buildings - Data scraped: {datetime.now().strftime('%Y-%m-%d')}
  </p>
</div>'''

    return html


def determine_marker_style(tenant_count: int) -> str:
    """Return style ID based on tenant count"""
    if tenant_count >= 50:
        return "high-density"
    elif tenant_count >= 20:
        return "medium-density"
    elif tenant_count >= 10:
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
    name = building['name']
    lat = building['lat']
    lon = building['lon']

    # Count tenants
    tenant_count = len(tenants['merchants']) + len(tenants['lawyers'])

    # Create placemark
    placemark = SubElement(doc, "Placemark")

    # Name
    name_elem = SubElement(placemark, "name")
    name_elem.text = name

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
    print("DISTRICT 9 - EXPORTING TO KMZ")
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
    doc_name.text = "District 9 Office Building Tenants"

    doc_desc = SubElement(document, "description")
    doc_desc.text = f"District 9 buildings with tenant directories and building management - Scraped {datetime.now().strftime('%Y-%m-%d')}"

    # Create styles
    print("   Creating marker styles...")
    create_kml_styles(document)

    # Create placemarks
    print("\n3. Creating placemarks for buildings...")
    buildings_with_data = 0
    buildings_without_data = 0
    total_tenants = 0

    for i, building in enumerate(buildings, 1):
        print(f"   Processing: {building['name']}")

        # Load tenant data
        tenants = load_tenant_data(building['name'])
        tenant_count = len(tenants['merchants']) + len(tenants['lawyers'])
        contact_count = len(tenants['building_contacts'])

        # Create placemark for all buildings (even without tenants, if they have building management)
        if tenant_count > 0 or contact_count > 0:
            buildings_with_data += 1
            total_tenants += tenant_count
            create_building_placemark(document, building, tenants)
            print(f"     ✓ {tenant_count} tenants, {contact_count} management contacts")
        else:
            buildings_without_data += 1
            print(f"     ⚠ No data found")

    print(f"   Complete: {buildings_with_data} placemarks created")

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
