#!/usr/bin/env python3
"""
Step 1: Convert District 18 Excel file to building CSV
Reads data/district_18/18.xlsx and extracts building addresses,
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
EXCEL_FILE = DATA_DIR / "district_18" / "18.xlsx"
OUTPUT_CSV = DATA_DIR / "building_tenants" / "buildings" / "district18_buildings.csv"

# Google Places API (optional, for geocoding)
GOOGLE_PLACES_API_KEY = os.getenv('GOOGLE_PLACES_API_KEY')
gmaps = googlemaps.Client(key=GOOGLE_PLACES_API_KEY) if GOOGLE_PLACES_API_KEY else None


def read_excel_file() -> pd.DataFrame:
    """Read the Excel file and extract building data"""
    print(f"Reading Excel file: {EXCEL_FILE}")
    
    # Try reading with different header rows
    for header_row in [0, 1, 2]:
        try:
            df = pd.read_excel(EXCEL_FILE, header=header_row)
            print(f"  Tried header row {header_row}, shape: {df.shape}")
            
            # Look for address column
            address_cols = [col for col in df.columns if 'address' in str(col).lower() or 'addr' in str(col).lower()]
            if address_cols:
                print(f"  Found address column: {address_cols}")
                return df, header_row, address_cols[0]
            
            # Check if any row contains "Address" header
            for idx, row in df.iterrows():
                for col in df.columns:
                    if pd.notna(row[col]) and 'address' in str(row[col]).lower():
                        print(f"  Found 'Address' in row {idx}, column {col}")
                        # Use this row as header
                        df_new = pd.read_excel(EXCEL_FILE, header=idx)
                        return df_new, idx, col
        except Exception as e:
            continue
    
    # Fallback: read raw and search
    df = pd.read_excel(EXCEL_FILE, header=None)
    print(f"  Reading without header, shape: {df.shape}")
    
    # Find row with "Address" header
    for idx, row in df.iterrows():
        row_str = ' '.join([str(x) for x in row.values if pd.notna(x)])
        if 'address' in row_str.lower() and 'bldg' in row_str.lower():
            print(f"  Found header row at index {idx}")
            df_header = pd.read_excel(EXCEL_FILE, header=idx)
            # Find address column
            for col in df_header.columns:
                if 'address' in str(col).lower():
                    return df_header, idx, col
    
    return df, 0, None


def extract_buildings(df: pd.DataFrame, address_col: str) -> List[Dict]:
    """Extract unique building addresses from DataFrame"""
    buildings = []
    seen_addresses = set()
    
    print(f"\nExtracting buildings from column: {address_col}")
    
    # Get all non-null addresses
    addresses = df[address_col].dropna().unique()
    print(f"  Found {len(addresses)} unique addresses")
    
    for address in addresses:
        address_str = str(address).strip()
        if not address_str or address_str.lower() in ['nan', 'none', '', 'address']:
            continue
        
        # Normalize address - add "New York, NY" if not present
        if 'new york' not in address_str.lower() and 'ny' not in address_str.lower():
            address_str = f"{address_str}, New York, NY"
        
        # Skip if already seen
        if address_str in seen_addresses:
            continue
        seen_addresses.add(address_str)
        
        # Try to extract building number/name from other columns
        building_name = ""
        building_num = ""
        
        # Look for building number column
        for col in df.columns:
            if 'bldg' in str(col).lower() or 'building' in str(col).lower():
                matching_rows = df[df[address_col] == address]
                if not matching_rows.empty:
                    bldg_val = matching_rows.iloc[0][col]
                    if pd.notna(bldg_val):
                        building_num = str(bldg_val).strip()
                break
        
        buildings.append({
            'address': address_str,
            'building_name': building_name,
            'building_num': building_num,
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
    print("DISTRICT 18: CONVERT EXCEL TO BUILDING CSV")
    print("=" * 60)
    print()
    
    # Check if Excel file exists
    if not EXCEL_FILE.exists():
        print(f"❌ Error: Excel file not found: {EXCEL_FILE}")
        sys.exit(1)
    
    # Read Excel file
    try:
        df, header_row, address_col = read_excel_file()
        
        if address_col is None:
            print("\n❌ Error: Could not find 'Address' column in Excel file")
            print("   Columns found:", df.columns.tolist())
            sys.exit(1)
        
        print(f"\n✓ Successfully read Excel file")
        print(f"   Header row: {header_row}")
        print(f"   Address column: {address_col}")
        print(f"   Total rows: {len(df)}")
        
    except Exception as e:
        print(f"\n❌ Error reading Excel file: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Extract buildings
    try:
        buildings = extract_buildings(df, address_col)
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
    print("Next step: Run 02_scrape_tenant_directories.py")
    print("=" * 60)


if __name__ == '__main__':
    main()

