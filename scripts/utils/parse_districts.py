#!/usr/bin/env python3
"""
Parse district boundaries from Google Maps KML file.
Extracts all 55 districts and calculates bounding boxes for each.
"""

import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple
import json


def parse_coordinates(coord_string: str) -> List[Tuple[float, float]]:
    """Parse KML coordinate string into list of (lng, lat) tuples."""
    coords = []
    for line in coord_string.strip().split('\n'):
        line = line.strip()
        if line:
            parts = line.split(',')
            if len(parts) >= 2:
                lng = float(parts[0])
                lat = float(parts[1])
                coords.append((lng, lat))
    return coords


def calculate_bounds(coordinates: List[Tuple[float, float]]) -> Dict[str, float]:
    """Calculate bounding box from polygon coordinates."""
    lngs = [coord[0] for coord in coordinates]
    lats = [coord[1] for coord in coordinates]

    return {
        'north': max(lats),
        'south': min(lats),
        'east': max(lngs),
        'west': min(lngs)
    }


def parse_districts_from_kml(kml_file: str) -> Dict[int, Dict]:
    """Parse all districts from KML file."""
    # Parse XML with namespace
    tree = ET.parse(kml_file)
    root = tree.getroot()

    # Define namespace
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}

    districts = {}

    # Find the "分区" folder
    for folder in root.findall('.//kml:Folder', ns):
        folder_name_elem = folder.find('kml:name', ns)
        if folder_name_elem is not None and folder_name_elem.text == '分区':
            print(f"Found '分区' (Districts) folder")

            # Parse each placemark (district)
            for placemark in folder.findall('.//kml:Placemark', ns):
                # Get district name/number
                name_elem = placemark.find('kml:name', ns)
                if name_elem is None or not name_elem.text:
                    continue

                try:
                    district_num = int(name_elem.text.strip())
                except (ValueError, AttributeError):
                    print(f"  Warning: Skipping placemark with invalid name: {name_elem.text}")
                    continue

                # Get coordinates
                coord_elem = placemark.find('.//kml:coordinates', ns)
                if coord_elem is None:
                    print(f"  Warning: District {district_num} has no coordinates")
                    continue

                # Parse coordinates
                coordinates = parse_coordinates(coord_elem.text)

                if not coordinates:
                    print(f"  Warning: District {district_num} has empty coordinates")
                    continue

                # Calculate bounds
                bounds = calculate_bounds(coordinates)

                # Calculate center point
                center_lat = (bounds['north'] + bounds['south']) / 2
                center_lng = (bounds['east'] + bounds['west']) / 2

                # Store district info
                districts[district_num] = {
                    'name': f'District {district_num}',
                    'bounds': bounds,
                    'center': {
                        'lat': center_lat,
                        'lng': center_lng
                    },
                    'polygon': coordinates,
                    'grid_size': 3  # Default grid size
                }

                print(f"  ✓ District {district_num}: "
                      f"Lat [{bounds['south']:.6f} to {bounds['north']:.6f}], "
                      f"Lng [{bounds['west']:.6f} to {bounds['east']:.6f}]")

            break

    return districts


def main():
    """Main function to parse and save district data."""
    kml_file = '/tmp/doc.kml'

    print("Parsing KML file...")
    districts = parse_districts_from_kml(kml_file)

    print(f"\n✓ Successfully parsed {len(districts)} districts")

    # Verify we have all 55 districts
    expected_districts = set(range(1, 56))
    found_districts = set(districts.keys())

    if found_districts == expected_districts:
        print("✓ All 55 districts found!")
    else:
        missing = expected_districts - found_districts
        extra = found_districts - expected_districts
        if missing:
            print(f"⚠ Missing districts: {sorted(missing)}")
        if extra:
            print(f"⚠ Extra districts: {sorted(extra)}")

    # Save to JSON file
    output_file = 'config/districts.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(districts, f, indent=2, ensure_ascii=False)

    print(f"\n✓ District data saved to: {output_file}")

    # Also create a Python config file
    py_output_file = 'config/districts.py'
    with open(py_output_file, 'w', encoding='utf-8') as f:
        f.write('"""District boundaries for NYC pharmacy scraping."""\n\n')
        f.write('# Generated from Google Maps KML data\n')
        f.write('# Total districts: 55\n\n')
        f.write('DISTRICTS = {\n')

        for district_num in sorted(districts.keys()):
            district = districts[district_num]
            f.write(f'    {district_num}: {{\n')
            f.write(f"        'name': '{district['name']}',\n")
            f.write(f"        'bounds': {{\n")
            f.write(f"            'north': {district['bounds']['north']},\n")
            f.write(f"            'south': {district['bounds']['south']},\n")
            f.write(f"            'east': {district['bounds']['east']},\n")
            f.write(f"            'west': {district['bounds']['west']},\n")
            f.write(f"        }},\n")
            f.write(f"        'center': {{\n")
            f.write(f"            'lat': {district['center']['lat']},\n")
            f.write(f"            'lng': {district['center']['lng']},\n")
            f.write(f"        }},\n")
            f.write(f"        'grid_size': {district['grid_size']},\n")
            f.write(f'    }},\n')

        f.write('}\n')

    print(f"✓ Python config saved to: {py_output_file}")

    # Print summary statistics
    print("\n" + "="*60)
    print("DISTRICT SUMMARY")
    print("="*60)

    # Calculate area sizes (rough approximation)
    for district_num in sorted(districts.keys())[:5]:  # Show first 5 as examples
        district = districts[district_num]
        bounds = district['bounds']
        lat_range = bounds['north'] - bounds['south']
        lng_range = bounds['east'] - bounds['west']
        # Rough area in square degrees
        area = lat_range * lng_range
        print(f"District {district_num:2d}: "
              f"~{area*100:.4f} sq° "
              f"({lat_range:.4f}° lat x {lng_range:.4f}° lng)")

    print("... (50 more districts)")


if __name__ == '__main__':
    main()
