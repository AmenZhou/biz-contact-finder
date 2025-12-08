#!/usr/bin/env python3
"""
Enrich medical offices with addresses using Serper Google Maps API
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from typing import Dict, List

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

import pandas as pd

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "medical_offices"
INPUT_CSV = DATA_DIR / "queens_brooklyn_doctors.csv"
OUTPUT_CSV = DATA_DIR / "queens_brooklyn_doctors_with_addresses.csv"

# API Configuration
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

if not SERPER_API_KEY:
    print("❌ Error: SERPER_API_KEY environment variable not set")
    sys.exit(1)


def search_google_maps(query: str, location: str = "New York, NY") -> List[Dict]:
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


def enrich_with_address(row: pd.Series) -> pd.Series:
    """Enrich a doctor office record with address from Google Maps"""

    # Skip if already has address
    if pd.notna(row['address']) and row['address'].strip():
        return row

    # Build search query
    name = row['name']
    location_search = row.get('location', 'Queens, NY')

    query = f"{name} {location_search}"

    print(f"  Searching Maps for: {name[:50]}...")

    # Search Google Maps
    places = search_google_maps(query)

    if places and len(places) > 0:
        # Take first result
        place = places[0]

        # Update fields
        if place.get('address') and not row['address']:
            row['address'] = place['address']
            print(f"    ✓ Found address: {place['address'][:60]}")

        if place.get('phoneNumber') and not row['phone']:
            row['phone'] = place['phoneNumber']

        if place.get('latitude'):
            row['latitude'] = place['latitude']

        if place.get('longitude'):
            row['longitude'] = place['longitude']

        if place.get('rating'):
            row['rating'] = place['rating']

        if place.get('ratingCount'):
            row['reviews'] = place['ratingCount']

    return row


def main():
    """Main execution"""
    print("=" * 80)
    print("ENRICHING DOCTOR OFFICES WITH ADDRESSES")
    print("=" * 80)
    print()

    # Load CSV
    if not INPUT_CSV.exists():
        print(f"❌ Error: CSV file not found at {INPUT_CSV}")
        sys.exit(1)

    print(f"📂 Loading data from {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV)
    print(f"   ✓ Loaded {len(df)} doctor offices")

    # Count missing addresses
    missing_addresses = df['address'].isna() | (df['address'] == '')
    print(f"   Missing addresses: {missing_addresses.sum()}")
    print()

    # Enrich each record
    print("🔍 Enriching records with Google Maps data...")
    print()

    enriched_count = 0
    for idx in range(len(df)):
        if idx % 10 == 0:
            print(f"[{idx + 1}/{len(df)}]")

        df.loc[idx] = enrich_with_address(df.loc[idx])

        # Track progress
        if df.loc[idx, 'address'] and pd.notna(df.loc[idx, 'address']):
            enriched_count += 1

        # Rate limiting - be nice to the API
        time.sleep(0.5)

        # Save progress every 50 records
        if (idx + 1) % 50 == 0:
            df.to_csv(OUTPUT_CSV, index=False)
            print(f"  💾 Progress saved ({enriched_count} with addresses)")

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
    print("=" * 80)


if __name__ == "__main__":
    main()
