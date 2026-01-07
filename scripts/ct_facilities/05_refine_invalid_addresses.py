#!/usr/bin/env python3
"""
Refine invalid addresses in CT facilities CSV using Serper Google Maps API
"""

import os
import sys
import re
import time
import requests
from pathlib import Path
from typing import Dict, List

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

import pandas as pd

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "ct_facilities"
INPUT_CSV = DATA_DIR / "ct_facilities_with_addresses.csv"
OUTPUT_CSV = DATA_DIR / "ct_facilities_with_addresses_refined.csv"

# API Configuration
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

if not SERPER_API_KEY:
    print("❌ Error: SERPER_API_KEY environment variable not set")
    sys.exit(1)


def is_valid_address(address: str) -> bool:
    """
    Check if address is valid (starts with number and is reasonable length)
    """
    if not address or pd.isna(address):
        return False

    address = str(address).strip()

    # Address is too long (likely description text)
    if len(address) > 200:
        return False

    # Valid address should start with a number
    if not re.match(r'^\d', address):
        return False

    return True


def search_google_maps(query: str, location: str = "Connecticut") -> List[Dict]:
    """
    Search using Serper Google Maps API
    Returns place results with addresses
    """
    url = "https://google.serper.dev/maps"

    payload = {
        "q": query,
        "location": location,
        "gl": "us",
        "hl": "en"
    }

    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Google Maps API returns 'places' array
        return data.get("places", [])
    except Exception as e:
        print(f"   ⚠️  Serper Maps API error: {e}")
        return []


def refine_address(row: pd.Series) -> pd.Series:
    """Refine a facility record with proper address from Google Maps"""

    # Skip if already has valid address
    if is_valid_address(row['address']):
        return row

    # Build search query
    name = row['name']
    location_search = row.get('location', 'Connecticut')

    query = f"{name} {location_search}"

    print(f"  Searching Maps for: {name[:50]}...")
    print(f"    Current invalid address: {str(row['address'])[:80]}...")

    # Search Google Maps
    places = search_google_maps(query, location_search)

    if places and len(places) > 0:
        # Take first result
        place = places[0]

        # Update address if found
        if place.get('address'):
            row['address'] = place['address']
            print(f"    ✓ Refined address: {place['address'][:60]}")

        # Update other fields if missing
        if place.get('phoneNumber') and (not row['phone'] or pd.isna(row['phone'])):
            row['phone'] = place['phoneNumber']

        if place.get('latitude'):
            row['latitude'] = place['latitude']

        if place.get('longitude'):
            row['longitude'] = place['longitude']

        if place.get('rating') and (not row['rating'] or pd.isna(row['rating'])):
            row['rating'] = place['rating']

        if place.get('ratingCount') and (not row['reviews'] or pd.isna(row['reviews'])):
            row['reviews'] = place['ratingCount']
    else:
        print(f"    ✗ No results found")

    return row


def main():
    """Main execution"""
    print("=" * 80)
    print("REFINING CT FACILITIES WITH VALID ADDRESSES")
    print("=" * 80)
    print()

    # Load CSV
    if not INPUT_CSV.exists():
        print(f"❌ Error: CSV file not found at {INPUT_CSV}")
        sys.exit(1)

    print(f"📂 Loading data from {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV)
    print(f"   ✓ Loaded {len(df)} facilities")

    # Count invalid addresses
    invalid_addresses = df['address'].apply(lambda x: not is_valid_address(x))
    print(f"   Invalid addresses to refine: {invalid_addresses.sum()}")
    print()

    # Refine each record with invalid address
    print("🔍 Refining records with invalid addresses...")
    print()

    refined_count = 0
    for idx in range(len(df)):
        # Only process rows with invalid addresses
        if not is_valid_address(df.loc[idx, 'address']):
            if refined_count % 10 == 0 and refined_count > 0:
                print(f"[{refined_count} refined so far]")

            df.loc[idx] = refine_address(df.loc[idx])

            # Check if address was refined
            if is_valid_address(df.loc[idx, 'address']):
                refined_count += 1

            # Rate limiting - be nice to the API
            time.sleep(0.5)

            # Save progress every 50 records
            if (refined_count + 1) % 50 == 0:
                df.to_csv(OUTPUT_CSV, index=False)
                print(f"  💾 Progress saved ({refined_count} addresses refined)")

    # Final save
    df.to_csv(OUTPUT_CSV, index=False)

    # Count final stats
    final_valid = df['address'].apply(is_valid_address).sum()
    final_invalid = len(df) - final_valid

    print()
    print("=" * 80)
    print("✅ REFINEMENT COMPLETE")
    print("=" * 80)
    print(f"Output File: {OUTPUT_CSV}")
    print()
    print(f"Total records: {len(df)}")
    print(f"Addresses refined: {refined_count}")
    print(f"Valid addresses: {final_valid}")
    print(f"Still invalid: {final_invalid}")
    print(f"With phone: {df['phone'].astype(bool).sum()}")
    print(f"With coordinates: {df['latitude'].astype(bool).sum()}")
    print("=" * 80)


if __name__ == "__main__":
    main()
