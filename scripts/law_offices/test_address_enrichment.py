#!/usr/bin/env python3
"""
Test script to verify address enrichment fix on a few sample records
"""

import os
import sys
import json
import time
import requests
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

import pandas as pd

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "law_offices"
INPUT_CSV = DATA_DIR / "queens_brooklyn_law_offices.csv"

# API Configuration
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

if not SERPER_API_KEY:
    print("❌ Error: SERPER_API_KEY environment variable not set")
    sys.exit(1)


def search_google_maps(query: str, location: str = "New York, NY"):
    """Search using Serper Google Maps API"""
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
        return data.get("places", [])
    except Exception as e:
        print(f"   ⚠️  API error: {e}")
        return []


def enrich_with_address(row: pd.Series) -> pd.Series:
    """Enrich a law office record with address from Google Maps"""

    # Build search query
    name = row['name']
    location_search = row.get('location', 'Queens, NY')
    query = f"{name} {location_search}"

    print(f"\n  🔍 Searching: {name[:60]}")

    # Search Google Maps
    places = search_google_maps(query)

    if places and len(places) > 0:
        place = places[0]

        # Update fields - WITH THE FIX (no "and not row['address']")
        if place.get('address'):
            row['address'] = place['address']
            print(f"    ✓ Found address: {place['address']}")

        if place.get('phoneNumber'):
            row['phone'] = place['phoneNumber']
            print(f"    ✓ Found phone: {place['phoneNumber']}")

        if place.get('latitude') and place.get('longitude'):
            row['latitude'] = place['latitude']
            row['longitude'] = place['longitude']
            print(f"    ✓ Found coords: ({place['latitude']}, {place['longitude']})")

        if place.get('rating'):
            row['rating'] = place['rating']
            print(f"    ✓ Found rating: {place['rating']} ({place.get('ratingCount', 0)} reviews)")
    else:
        print(f"    ❌ No results found")

    return row


def main():
    """Test on sample records"""
    print("=" * 80)
    print("TESTING ADDRESS ENRICHMENT FIX")
    print("=" * 80)
    print()

    # Load CSV
    if not INPUT_CSV.exists():
        print(f"❌ Error: CSV file not found at {INPUT_CSV}")
        sys.exit(1)

    print(f"📂 Loading data from {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV)
    print(f"   ✓ Loaded {len(df)} law offices")

    # Find records missing addresses
    missing_mask = df['address'].isna() | (df['address'] == '')
    missing_df = df[missing_mask]

    print(f"   📊 Total missing addresses: {len(missing_df)}")
    print()

    # Select 10 sample records
    sample_size = min(10, len(missing_df))
    samples = missing_df.head(sample_size).copy()

    print(f"🧪 Testing with {sample_size} sample records...")
    print()

    # Show before state
    print("BEFORE ENRICHMENT:")
    print("-" * 80)
    for idx, row in samples.iterrows():
        print(f"{row['name'][:60]}")
        print(f"  Address: {row['address'] if pd.notna(row['address']) else 'MISSING'}")
        print()

    print("=" * 80)
    print("ENRICHING SAMPLES...")
    print("=" * 80)

    # Enrich samples
    results = []
    success_count = 0

    for idx, row in samples.iterrows():
        enriched_row = enrich_with_address(row.copy())

        # Check if address was added
        before_has_address = pd.notna(row['address']) and row['address'].strip()
        after_has_address = pd.notna(enriched_row['address']) and enriched_row['address'].strip()

        if not before_has_address and after_has_address:
            success_count += 1

        results.append({
            'name': row['name'],
            'before_address': row['address'] if pd.notna(row['address']) else 'MISSING',
            'after_address': enriched_row['address'] if pd.notna(enriched_row['address']) else 'MISSING',
            'success': not before_has_address and after_has_address
        })

        # Rate limiting
        time.sleep(0.5)

    # Show results
    print()
    print("=" * 80)
    print("TEST RESULTS")
    print("=" * 80)
    print()

    for result in results:
        status = "✅" if result['success'] else "❌"
        print(f"{status} {result['name'][:60]}")
        print(f"   Before: {result['before_address']}")
        print(f"   After:  {result['after_address']}")
        print()

    print("=" * 80)
    print(f"Success Rate: {success_count}/{sample_size} ({success_count/sample_size*100:.1f}%)")
    print("=" * 80)
    print()

    if success_count > 0:
        print("✅ The fix is working! Addresses are being successfully enriched.")
    else:
        print("⚠️  No addresses were enriched. There may be an issue with the API or queries.")


if __name__ == "__main__":
    main()
