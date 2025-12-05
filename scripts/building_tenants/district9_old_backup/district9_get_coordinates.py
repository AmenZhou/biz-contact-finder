#!/usr/bin/env python3
"""
Get coordinates for District 9 buildings using Google Geocoding API
Creates district9_buildings.csv with building coordinates
"""

import csv
import json
import os
import sys
import urllib.request
import urllib.parse
from pathlib import Path

# Building addresses to geocode
DISTRICT9_BUILDINGS = [
    {
        'name': '330 Madison Avenue',
        'address': '330 Madison Ave, New York, NY 10017, USA'
    },
    {
        'name': '1221 Avenue of the Americas',
        'address': '1221 6th Ave, New York, NY 10020, USA'
    },
    {
        'name': '477 Madison Avenue',
        'address': '477 Madison Ave, New York, NY 10022, USA'
    },
    {
        'name': '485 Madison Avenue',
        'address': '485 Madison Ave, New York, NY 10022, USA'
    },
    {
        'name': '488 Madison Avenue',
        'address': '488 Madison Ave, New York, NY 10022, USA'
    },
    {
        'name': '499 Park Avenue',
        'address': '499 Park Ave, New York, NY 10022, USA'
    }
]

# Output path
OUTPUT_DIR = Path(__file__).parent.parent / 'data'
OUTPUT_FILE = OUTPUT_DIR / 'district9_buildings.csv'


def geocode_address(address: str, api_key: str) -> dict:
    """
    Geocode an address using Google Geocoding API

    Args:
        address: Full address string
        api_key: Google API key

    Returns:
        Dictionary with lat, lng, formatted_address
    """
    base_url = 'https://maps.googleapis.com/maps/api/geocode/json'
    params = urllib.parse.urlencode({
        'address': address,
        'key': api_key
    })
    url = f"{base_url}?{params}"

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

        if data['status'] == 'OK' and data['results']:
            result = data['results'][0]
            location = result['geometry']['location']

            return {
                'latitude': location['lat'],
                'longitude': location['lng'],
                'formatted_address': result['formatted_address']
            }
        else:
            print(f"  ⚠️  Geocoding failed: {data.get('status', 'Unknown error')}")
            return None

    except Exception as e:
        print(f"  ❌ Error geocoding: {e}")
        return None


def main():
    """Main function to geocode buildings and create CSV"""
    print("="*60)
    print("DISTRICT 9 BUILDINGS - COORDINATE EXTRACTION")
    print("="*60)
    print()

    # Get API key from environment
    api_key = os.getenv('GOOGLE_MAPS_API_KEY') or os.getenv('GOOGLE_PLACES_API_KEY')

    if not api_key:
        print("❌ Error: GOOGLE_MAPS_API_KEY or GOOGLE_PLACES_API_KEY not found in environment")
        print("   Please set one of these environment variables")
        sys.exit(1)

    print(f"Processing {len(DISTRICT9_BUILDINGS)} buildings...")
    print()

    # Geocode each building
    buildings_with_coords = []

    for i, building in enumerate(DISTRICT9_BUILDINGS, 1):
        print(f"[{i}/{len(DISTRICT9_BUILDINGS)}] {building['name']}")
        print(f"  Address: {building['address']}")

        coords = geocode_address(building['address'], api_key)

        if coords:
            print(f"  ✓ Latitude: {coords['latitude']}")
            print(f"  ✓ Longitude: {coords['longitude']}")

            buildings_with_coords.append({
                'building_name': building['name'],
                'address': building['address'],
                'latitude': coords['latitude'],
                'longitude': coords['longitude'],
                'formatted_address': coords['formatted_address']
            })
        else:
            print(f"  ❌ Failed to geocode")

        print()

    # Create output directory if needed
    OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

    # Write to CSV
    if buildings_with_coords:
        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['building_name', 'address', 'latitude', 'longitude', 'formatted_address']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(buildings_with_coords)

        print("="*60)
        print("SUCCESS")
        print("="*60)
        print(f"✓ Geocoded {len(buildings_with_coords)}/{len(DISTRICT9_BUILDINGS)} buildings")
        print(f"✓ Output saved to: {OUTPUT_FILE}")
        print()
        print("Next step: Create export_district9_to_kmz.py script")
        print("="*60)
    else:
        print("❌ No buildings were successfully geocoded")
        sys.exit(1)


if __name__ == '__main__':
    main()
