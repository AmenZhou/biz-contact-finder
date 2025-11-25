#!/usr/bin/env python3
"""
Export pharmacy data to KMZ format for Google Maps import.
Creates placemarks for each pharmacy with detailed information.
"""

import csv
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element, SubElement
from xml.dom import minidom


# Configuration
DATA_DIR = Path('data')
INPUT_CSV = DATA_DIR / 'all_districts_pharmacies.csv'
OUTPUT_KMZ = DATA_DIR / 'all_districts_pharmacies.kmz'
OUTPUT_KML = DATA_DIR / 'doc.kml'


def create_kml_styles(kml_doc: Element) -> dict:
    """Create KML styles for different rating tiers."""
    # Define color schemes for rating tiers
    rating_styles = {
        'excellent': {  # 4.5+
            'color': 'ff00ff00',  # Green
            'icon': 'http://maps.google.com/mapfiles/kml/paddle/grn-circle.png'
        },
        'good': {  # 4.0-4.5
            'color': 'ff00ffff',  # Yellow
            'icon': 'http://maps.google.com/mapfiles/kml/paddle/ylw-circle.png'
        },
        'average': {  # 3.0-4.0
            'color': 'ff0080ff',  # Orange
            'icon': 'http://maps.google.com/mapfiles/kml/paddle/orange-circle.png'
        },
        'poor': {  # <3.0
            'color': 'ff0000ff',  # Red
            'icon': 'http://maps.google.com/mapfiles/kml/paddle/red-circle.png'
        },
        'no_rating': {  # No rating
            'color': 'ff808080',  # Gray
            'icon': 'http://maps.google.com/mapfiles/kml/paddle/wht-circle.png'
        }
    }

    style_ids = {}

    for tier, style_config in rating_styles.items():
        style_id = f'pharmacy-{tier}'
        style_ids[tier] = style_id

        # Create style
        style = SubElement(kml_doc, 'Style', id=style_id)

        # Icon style
        icon_style = SubElement(style, 'IconStyle')
        SubElement(icon_style, 'scale').text = '1.1'
        SubElement(icon_style, 'color').text = style_config['color']
        icon = SubElement(icon_style, 'Icon')
        SubElement(icon, 'href').text = style_config['icon']

        # Label style
        label_style = SubElement(style, 'LabelStyle')
        SubElement(label_style, 'scale').text = '0.9'

        # Balloon style (popup)
        balloon_style = SubElement(style, 'BalloonStyle')
        SubElement(balloon_style, 'text').text = '<![CDATA[$[description]]]>'

    return style_ids


def get_rating_tier(rating: str) -> str:
    """Determine rating tier for styling."""
    try:
        rating_float = float(rating)
        if rating_float >= 4.5:
            return 'excellent'
        elif rating_float >= 4.0:
            return 'good'
        elif rating_float >= 3.0:
            return 'average'
        else:
            return 'poor'
    except (ValueError, TypeError):
        return 'no_rating'


def create_description_html(pharmacy: dict) -> str:
    """Create HTML description for pharmacy popup."""
    html_parts = []

    html_parts.append(f"<h3>{pharmacy['name']}</h3>")

    # Rating
    rating = pharmacy.get('rating', 'N/A')
    total_ratings = pharmacy.get('total_ratings', 'N/A')
    if rating and rating != 'N/A':
        stars = '⭐' * int(float(rating))
        html_parts.append(f"<p><b>Rating:</b> {rating} {stars} ({total_ratings} reviews)</p>")

    # Address
    if pharmacy.get('address'):
        html_parts.append(f"<p><b>Address:</b> {pharmacy['address']}</p>")

    # Phone
    if pharmacy.get('phone'):
        html_parts.append(f"<p><b>Phone:</b> <a href='tel:{pharmacy['phone']}'>{pharmacy['phone']}</a></p>")

    # Website
    if pharmacy.get('website'):
        html_parts.append(f"<p><b>Website:</b> <a href='{pharmacy['website']}' target='_blank'>Visit Website</a></p>")

    # Google Maps link
    if pharmacy.get('google_maps_url'):
        html_parts.append(f"<p><a href='{pharmacy['google_maps_url']}' target='_blank'>View on Google Maps</a></p>")

    # Hours
    if pharmacy.get('hours'):
        html_parts.append(f"<p><b>Hours:</b><br/>{pharmacy['hours'].replace(' | ', '<br/>')}</p>")

    # Business status
    if pharmacy.get('business_status'):
        status = pharmacy['business_status']
        status_color = 'green' if status == 'OPERATIONAL' else 'red'
        html_parts.append(f"<p><b>Status:</b> <span style='color:{status_color}'>{status}</span></p>")

    # District info
    if pharmacy.get('district_num'):
        html_parts.append(f"<p><b>District:</b> {pharmacy['district_num']} - {pharmacy.get('district_name', '')}</p>")

    return '\n'.join(html_parts)


def create_pharmacy_placemark(folder: Element, pharmacy: dict, style_ids: dict):
    """Create a KML placemark for a single pharmacy."""
    placemark = SubElement(folder, 'Placemark')

    # Name
    SubElement(placemark, 'name').text = pharmacy['name']

    # Description (HTML for popup)
    description = create_description_html(pharmacy)
    desc_elem = SubElement(placemark, 'description')
    desc_elem.text = f'<![CDATA[{description}]]>'

    # Style
    rating_tier = get_rating_tier(pharmacy.get('rating'))
    SubElement(placemark, 'styleUrl').text = f"#{style_ids[rating_tier]}"

    # Point location
    point = SubElement(placemark, 'Point')
    coordinates = f"{pharmacy['longitude']},{pharmacy['latitude']},0"
    SubElement(point, 'coordinates').text = coordinates


def export_to_kml(input_csv: Path, output_kml: Path) -> int:
    """Export CSV data to KML format."""
    print(f"Reading pharmacy data from: {input_csv}")

    # Read CSV data
    pharmacies = []
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        pharmacies = list(reader)

    if not pharmacies:
        print("✗ No pharmacy data found in CSV")
        return 0

    print(f"✓ Loaded {len(pharmacies)} pharmacies")

    # Create KML structure
    kml = Element('kml', xmlns='http://www.opengis.net/kml/2.2')
    document = SubElement(kml, 'Document')

    # Document metadata
    SubElement(document, 'name').text = 'NYC Pharmacies - All Districts'
    SubElement(document, 'description').text = f'Pharmacy locations across {len(set(p["district_num"] for p in pharmacies))} NYC districts'

    # Create styles
    print("Creating KML styles...")
    style_ids = create_kml_styles(document)

    # Group pharmacies by district
    districts = {}
    for pharmacy in pharmacies:
        district_num = pharmacy['district_num']
        if district_num not in districts:
            districts[district_num] = []
        districts[district_num].append(pharmacy)

    # Create folders for each district
    print(f"Creating placemarks for {len(pharmacies)} pharmacies across {len(districts)} districts...")

    for district_num in sorted(districts.keys(), key=lambda x: int(x) if x.isdigit() else 999):
        district_pharmacies = districts[district_num]
        district_name = district_pharmacies[0].get('district_name', f'District {district_num}')

        # Create folder for district
        folder = SubElement(document, 'Folder')
        SubElement(folder, 'name').text = f'{district_name} ({len(district_pharmacies)} pharmacies)'

        # Add pharmacies
        for pharmacy in district_pharmacies:
            try:
                create_pharmacy_placemark(folder, pharmacy, style_ids)
            except Exception as e:
                print(f"  ⚠ Failed to create placemark for {pharmacy.get('name', 'Unknown')}: {e}")

        print(f"  ✓ District {district_num}: {len(district_pharmacies)} pharmacies")

    # Write KML file with pretty formatting
    print(f"\nWriting KML file to: {output_kml}")

    # Convert to string with pretty print
    rough_string = ET.tostring(kml, encoding='utf-8')
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent='  ', encoding='utf-8')

    with open(output_kml, 'wb') as f:
        f.write(pretty_xml)

    print(f"✓ KML file created: {output_kml}")

    return len(pharmacies)


def create_kmz(kml_file: Path, output_kmz: Path):
    """Create KMZ file (zipped KML)."""
    print(f"\nCreating KMZ archive: {output_kmz}")

    with zipfile.ZipFile(output_kmz, 'w', zipfile.ZIP_DEFLATED) as kmz:
        # Add KML file as 'doc.kml' (required name for KMZ)
        kmz.write(kml_file, 'doc.kml')

    print(f"✓ KMZ file created: {output_kmz}")
    print(f"  Size: {output_kmz.stat().st_size / 1024:.2f} KB")


def main():
    """Main function to export pharmacy data to KMZ."""
    print(f"{'='*60}")
    print("PHARMACY DATA TO KMZ EXPORTER")
    print(f"{'='*60}\n")

    # Check if input CSV exists
    if not INPUT_CSV.exists():
        print(f"✗ Input CSV not found: {INPUT_CSV}")
        print("  Please run scrape_all_pharmacies.py first to generate the data")
        return

    # Export to KML
    pharmacy_count = export_to_kml(INPUT_CSV, OUTPUT_KML)

    if pharmacy_count == 0:
        print("\n✗ Export failed - no pharmacies processed")
        return

    # Create KMZ
    create_kmz(OUTPUT_KML, OUTPUT_KMZ)

    # Summary
    print(f"\n{'='*60}")
    print("EXPORT COMPLETED!")
    print(f"{'='*60}")
    print(f"Total pharmacies exported: {pharmacy_count}")
    print(f"\nOutput files:")
    print(f"  - KML: {OUTPUT_KML}")
    print(f"  - KMZ: {OUTPUT_KMZ}")
    print(f"\nTo import into Google My Maps:")
    print(f"  1. Go to https://mymaps.google.com")
    print(f"  2. Click 'Create a New Map'")
    print(f"  3. Click 'Import' and upload {OUTPUT_KMZ.name}")
    print(f"  4. View your pharmacy locations on the map!")


if __name__ == '__main__':
    main()
