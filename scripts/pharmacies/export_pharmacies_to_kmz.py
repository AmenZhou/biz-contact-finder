#!/usr/bin/env python3
"""
Convert pharmacy CSV data to KML/KMZ format for Google My Maps import
"""
import sys
import os
import csv
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Default CSV file path
DEFAULT_CSV = 'data/area9_pharmacies.csv'


def escape_xml(text):
    """Escape XML special characters"""
    if text is None:
        return ""
    text = str(text)
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&apos;"))


def format_description(row):
    """Format pharmacy information as HTML description"""
    desc_parts = []
    
    if row.get('address'):
        desc_parts.append(f"<b>Address:</b> {escape_xml(row['address'])}")
    
    if row.get('phone'):
        desc_parts.append(f"<b>Phone:</b> {escape_xml(row['phone'])}")
    
    if row.get('website'):
        website = escape_xml(row['website'])
        desc_parts.append(f"<b>Website:</b> <a href='{website}' target='_blank'>{website}</a>")
    
    if row.get('rating'):
        try:
            rating = float(row['rating'])
            total_ratings = row.get('total_ratings', 0)
            if total_ratings:
                try:
                    total_int = int(float(total_ratings))
                    desc_parts.append(f"<b>Rating:</b> {rating:.1f} ⭐ ({total_int} reviews)")
                except (ValueError, TypeError):
                    desc_parts.append(f"<b>Rating:</b> {rating:.1f} ⭐")
            else:
                desc_parts.append(f"<b>Rating:</b> {rating:.1f} ⭐")
        except (ValueError, TypeError):
            desc_parts.append(f"<b>Rating:</b> {escape_xml(row['rating'])}")
    
    if row.get('hours'):
        hours = escape_xml(row['hours']).replace(' | ', '<br>')
        desc_parts.append(f"<b>Hours:</b><br>{hours}")
    
    if row.get('is_open_now') is not None:
        status = "🟢 Open Now" if row['is_open_now'] else "🔴 Closed"
        desc_parts.append(f"<b>Status:</b> {status}")
    
    if row.get('google_maps_url'):
        maps_url = escape_xml(row['google_maps_url'])
        desc_parts.append(f"<br><a href='{maps_url}' target='_blank'>View on Google Maps</a>")
    
    return "<br>".join(desc_parts) if desc_parts else ""


def get_icon_style(rating):
    """Get icon style based on rating"""
    if rating is None or rating == "":
        return "http://maps.google.com/mapfiles/ms/icons/blue-dot.png"
    
    try:
        rating_float = float(rating)
        if rating_float >= 4.5:
            return "http://maps.google.com/mapfiles/ms/icons/green-dot.png"
        elif rating_float >= 4.0:
            return "http://maps.google.com/mapfiles/ms/icons/yellow-dot.png"
        elif rating_float >= 3.0:
            return "http://maps.google.com/mapfiles/ms/icons/orange-dot.png"
        else:
            return "http://maps.google.com/mapfiles/ms/icons/red-dot.png"
    except (ValueError, TypeError):
        return "http://maps.google.com/mapfiles/ms/icons/blue-dot.png"


def csv_to_kml(csv_file, kml_file):
    """Convert CSV to KML format"""
    # Create KML root element
    kml = ET.Element("kml", xmlns="http://www.opengis.net/kml/2.2")
    document = ET.SubElement(kml, "Document")
    
    # Add document metadata
    name = ET.SubElement(document, "name")
    name.text = "Area #9 Pharmacies (Chelsea/NoMad)"
    
    description = ET.SubElement(document, "description")
    description.text = f"Pharmacies in District #9 (Chelsea/NoMad) - Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    # Read CSV and create placemarks
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            # Skip rows without coordinates
            if not row.get('latitude') or not row.get('longitude'):
                continue
            
            try:
                lat = float(row['latitude'])
                lng = float(row['longitude'])
            except (ValueError, TypeError):
                continue
            
            # Create placemark
            placemark = ET.SubElement(document, "Placemark")
            
            # Name
            name_elem = ET.SubElement(placemark, "name")
            name_elem.text = escape_xml(row.get('name', 'Unknown Pharmacy'))
            
            # Description
            desc_elem = ET.SubElement(placemark, "description")
            desc_elem.text = format_description(row)
            
            # Style
            style = ET.SubElement(placemark, "Style")
            icon_style = ET.SubElement(style, "IconStyle")
            icon = ET.SubElement(icon_style, "Icon")
            href = ET.SubElement(icon, "href")
            href.text = get_icon_style(row.get('rating'))
            
            # Point coordinates
            point = ET.SubElement(placemark, "Point")
            coordinates = ET.SubElement(point, "coordinates")
            coordinates.text = f"{lng},{lat},0"  # KML format: longitude,latitude,altitude
            
            # Extended data for additional info
            extended_data = ET.SubElement(placemark, "ExtendedData")
            
            # Add custom data fields
            data_fields = ['address', 'phone', 'website', 'rating', 'total_ratings', 
                          'business_status', 'is_open_now', 'hours', 'place_id']
            for field in data_fields:
                if row.get(field):
                    data = ET.SubElement(extended_data, "Data", name=field)
                    value = ET.SubElement(data, "value")
                    value.text = escape_xml(str(row[field]))
    
    # Write KML file
    tree = ET.ElementTree(kml)
    ET.indent(tree, space="  ")  # Pretty print
    tree.write(kml_file, encoding='utf-8', xml_declaration=True)
    
    print(f"✓ KML file created: {kml_file}")
    return kml_file


def kml_to_kmz(kml_file, kmz_file):
    """Compress KML to KMZ format"""
    with ZipFile(kmz_file, 'w') as kmz:
        kmz.write(kml_file, os.path.basename(kml_file))
    
    print(f"✓ KMZ file created: {kmz_file}")
    return kmz_file


def main():
    """Main function"""
    # Allow CSV file to be passed as argument, or use default
    if len(sys.argv) > 1:
        csv_file = Path(sys.argv[1])
    else:
        # Get script directory and find CSV relative to project root
        script_dir = Path(__file__).parent
        project_root = script_dir.parent
        csv_file = project_root / DEFAULT_CSV
    
    if not csv_file.exists():
        print(f"Error: CSV file not found: {csv_file}")
        return
    
    # Output files
    output_dir = csv_file.parent
    kml_file = output_dir / "area9_pharmacies.kml"
    kmz_file = output_dir / "area9_pharmacies.kmz"
    
    print(f"Converting {csv_file} to KML/KMZ...")
    print(f"Input: {csv_file}")
    
    # Convert to KML
    csv_to_kml(csv_file, kml_file)
    
    # Convert to KMZ
    kml_to_kmz(kml_file, kmz_file)
    
    print(f"\n{'='*60}")
    print("Conversion complete!")
    print(f"{'='*60}")
    print(f"\nFiles created:")
    print(f"  • KML: {kml_file}")
    print(f"  • KMZ: {kmz_file}")
    print(f"\nTo import into Google My Maps:")
    print(f"  1. Go to https://www.google.com/maps/d/")
    print(f"  2. Open your map or create a new one")
    print(f"  3. Click 'Import' → Select '{kmz_file.name}'")
    print(f"  4. The pharmacies will be added as markers with all details")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()

