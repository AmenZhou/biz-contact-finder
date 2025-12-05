#!/usr/bin/env python3
"""
Step 1: Convert District 9 Excel file to building CSV
Reads data/district_9/9.xlsx and extracts building addresses,
then geocodes them to get coordinates.
"""

import csv
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import googlemaps
import pandas as pd

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
EXCEL_FILE = DATA_DIR / "district_9" / "9.xlsx"
OUTPUT_CSV = DATA_DIR / "building_tenants" / "buildings" / "district9_buildings.csv"

# Google Places API
GOOGLE_PLACES_API_KEY = os.getenv('GOOGLE_PLACES_API_KEY')
gmaps = googlemaps.Client(key=GOOGLE_PLACES_API_KEY) if GOOGLE_PLACES_API_KEY else None


def read_excel_file() -> pd.DataFrame:
    """Read the Excel file and extract building data"""
    print(f"Reading Excel file: {EXCEL_FILE}")
    df = pd.read_excel(EXCEL_FILE)
    print(f"  Shape: {df.shape}")
    print(f"  Columns: {df.columns.tolist()}")
    return df


def extract_buildings(df: pd.DataFrame) -> List[Dict]:
    """Extract unique building addresses from DataFrame"""
    buildings = []
    seen_addresses = set()

    print(f"\nExtracting buildings from Excel...")
    print(f"  Found {len(df)} rows")

    for idx, row in df.iterrows():
        address = str(row['Address']).strip()
        building_name = str(row.get('Building Name', '')).strip()

        # Skip invalid addresses
        if not address or address.lower() in ['nan', 'none', '']:
            continue

        # Normalize address - add "New York, NY" if not present
        if 'new york' not in address.lower() and 'ny' not in address.lower():
            address = f"{address}, New York, NY"

        # Skip duplicates
        if address in seen_addresses:
            continue
        seen_addresses.add(address)

        buildings.append({
            'address': address,
            'building_name': building_name,
            'estimated_tenants': 5,  # Default estimate
            'building_levels': '',
            'building_type': 'office',
            'zip_code': '',
            'latitude': '',
            'longitude': ''
        })

    print(f"  Extracted {len(buildings)} unique buildings")
    return buildings


def geocode_address(address: str) -> Optional[tuple]:
    """Geocode an address using Google Places API"""
    if not gmaps:
        return None

    try:
        time.sleep(0.1)  # Rate limiting
        result = gmaps.geocode(address)
        if result:
            location = result[0]['geometry']['location']
            return (location['lat'], location['lng'])
    except Exception as e:
        print(f"    Geocoding error for {address}: {e}")

    return None


def geocode_buildings(buildings: List[Dict]) -> List[Dict]:
    """Geocode all building addresses"""
    if not gmaps:
        print("\n⚠️  GOOGLE_PLACES_API_KEY not set, skipping geocoding")
        print("   Buildings will be saved without coordinates")
        return buildings

    print(f"\nGeocoding {len(buildings)} addresses...")
    geocoded = 0

    for i, building in enumerate(buildings, 1):
        address = building['address']
        if building['latitude'] and building['longitude']:
            continue  # Already has coordinates

        print(f"  [{i}/{len(buildings)}] {address}")
        coords = geocode_address(address)

        if coords:
            building['latitude'] = coords[0]
            building['longitude'] = coords[1]
            geocoded += 1
            print(f"    ✓ {coords[0]:.6f}, {coords[1]:.6f}")
        else:
            print(f"    ✗ Failed to geocode")

    print(f"\n✓ Geocoded {geocoded}/{len(buildings)} addresses")
    return buildings


def save_buildings_csv(buildings: List[Dict]):
    """Save buildings to CSV file"""
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        'address', 'building_name', 'estimated_tenants',
        'building_levels', 'building_type', 'zip_code',
        'latitude', 'longitude'
    ]

    with open(OUTPUT_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for building in buildings:
            writer.writerow({
                'address': building['address'],
                'building_name': building.get('building_name', ''),
                'estimated_tenants': building.get('estimated_tenants', 5),
                'building_levels': building.get('building_levels', ''),
                'building_type': building.get('building_type', 'office'),
                'zip_code': building.get('zip_code', ''),
                'latitude': building.get('latitude', ''),
                'longitude': building.get('longitude', '')
            })

    print(f"\n✓ Saved {len(buildings)} buildings to: {OUTPUT_CSV}")


def main():
    """Main function"""
    print("=" * 60)
    print("DISTRICT 9: CONVERT EXCEL TO BUILDING CSV")
    print("=" * 60)
    print()

    # Check if Excel file exists
    if not EXCEL_FILE.exists():
        print(f"❌ Error: Excel file not found: {EXCEL_FILE}")
        sys.exit(1)

    # Read Excel file
    try:
        df = read_excel_file()

        if 'Address' not in df.columns:
            print("\n❌ Error: Could not find 'Address' column in Excel file")
            print("   Columns found:", df.columns.tolist())
            sys.exit(1)

        print(f"\n✓ Successfully read Excel file")
        print(f"   Total rows: {len(df)}")

    except Exception as e:
        print(f"\n❌ Error reading Excel file: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Extract buildings
    try:
        buildings = extract_buildings(df)
    except Exception as e:
        print(f"\n❌ Error extracting buildings: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    if not buildings:
        print("\n❌ No buildings found in Excel file")
        sys.exit(1)

    # Geocode addresses
    buildings = geocode_buildings(buildings)

    # Save to CSV
    save_buildings_csv(buildings)

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total buildings: {len(buildings)}")
    geocoded_count = sum(1 for b in buildings if b.get('latitude') and b.get('longitude'))
    print(f"Geocoded: {geocoded_count}/{len(buildings)}")
    print(f"Output file: {OUTPUT_CSV}")
    print()
    print("Next step: Run 02_scrape_building_management.py")
    print("=" * 60)


if __name__ == '__main__':
    main()
