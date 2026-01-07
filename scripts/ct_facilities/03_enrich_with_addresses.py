#!/usr/bin/env python3
"""
Enrich CT facilities with addresses and business hours using Serper Google Maps API
"""

import os
import sys
import time
import requests
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

import pandas as pd

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "ct_facilities"
INPUT_CSV = DATA_DIR / "ct_facilities.csv"
OUTPUT_CSV = DATA_DIR / "ct_facilities_with_addresses.csv"

# API Configuration
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

if not SERPER_API_KEY:
    print("❌ Error: SERPER_API_KEY environment variable not set")
    sys.exit(1)


def search_google_maps(query: str, location: str = "Connecticut") -> dict:
    """
    Search using Serper Google Maps API
    Returns place details with addresses and business hours
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
        places = data.get("places", [])
        if places:
            return places[0]  # Return first result
        return {}
    except Exception as e:
        print(f"   ⚠️  Serper Maps API error: {e}")
        return {}


def enrich_facility(row: pd.Series) -> pd.Series:
    """Enrich a facility record with address and business hours from Google Maps"""

    # Skip if already has complete data
    has_address = pd.notna(row['address']) and row['address'].strip()
    has_coords = pd.notna(row['latitude']) and pd.notna(row['longitude'])
    has_hours = pd.notna(row['business_hours']) and row['business_hours'].strip()

    if has_address and has_coords and has_hours:
        return row

    # Build search query
    name = row['name']
    location_search = row.get('location', 'Connecticut')

    query = f"{name} {location_search}"

    print(f"  Searching Maps for: {name[:60]}...")

    # Search Google Maps
    place = search_google_maps(query, location_search)

    if place:
        # Update fields if missing
        if not has_address and place.get('address'):
            row['address'] = place['address']
            print(f"    ✓ Found address: {place['address'][:60]}")

        if not row.get('phone') and place.get('phoneNumber'):
            row['phone'] = place['phoneNumber']

        if not has_coords:
            if place.get('latitude'):
                row['latitude'] = place['latitude']
            if place.get('longitude'):
                row['longitude'] = place['longitude']

        if place.get('rating'):
            row['rating'] = place['rating']

        if place.get('ratingCount'):
            row['reviews'] = place['ratingCount']

        if not has_hours and place.get('openingHours'):
            row['business_hours'] = place['openingHours']
            print(f"    ✓ Found business hours")

    return row


def main():
    """Main execution"""
    print("=" * 80)
    print("ENRICHING CT FACILITIES WITH ADDRESSES AND HOURS")
    print("=" * 80)
    print()

    # Load CSV
    if not INPUT_CSV.exists():
        print(f"❌ Error: CSV file not found at {INPUT_CSV}")
        sys.exit(1)

    print(f"📂 Loading data from {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV)
    print(f"   ✓ Loaded {len(df)} facilities")

    # Count missing data
    missing_addresses = df['address'].isna() | (df['address'] == '')
    missing_coords = df['latitude'].isna() | (df['latitude'] == '')
    missing_hours = df['business_hours'].isna() | (df['business_hours'] == '')

    print(f"   Missing addresses: {missing_addresses.sum()}")
    print(f"   Missing coordinates: {missing_coords.sum()}")
    print(f"   Missing business hours: {missing_hours.sum()}")
    print()

    # Enrich each record
    print("🔍 Enriching records with Google Maps data...")
    print()

    enriched_count = 0
    for idx in range(len(df)):
        if idx % 10 == 0:
            print(f"[{idx + 1}/{len(df)}]")

        original_address = df.loc[idx, 'address']
        original_hours = df.loc[idx, 'business_hours']

        df.loc[idx] = enrich_facility(df.loc[idx])

        # Track progress
        if pd.notna(df.loc[idx, 'address']) and (pd.isna(original_address) or original_address == ''):
            enriched_count += 1

        # Rate limiting - be nice to the API
        time.sleep(0.5)

        # Save progress every 50 records
        if (idx + 1) % 50 == 0:
            df.to_csv(OUTPUT_CSV, index=False)
            print(f"  💾 Progress saved ({enriched_count} enriched)")

    # Final save
    df.to_csv(OUTPUT_CSV, index=False)

    print()
    print("=" * 80)
    print("✅ ENRICHMENT COMPLETE")
    print("=" * 80)
    print(f"Output File: {OUTPUT_CSV}")
    print()
    print(f"Total records: {len(df)}")
    print(f"With addresses: {df['address'].astype(bool).sum()}")
    print(f"With phone: {df['phone'].astype(bool).sum()}")
    print(f"With coordinates: {df['latitude'].astype(bool).sum()}")
    print(f"With business hours: {df['business_hours'].astype(bool).sum()}")
    print("=" * 80)


if __name__ == "__main__":
    main()
