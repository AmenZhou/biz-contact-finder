#!/usr/bin/env python3
"""
Enrich doctor offices with ratings and reviews using Serper Google Maps API
"""

import os
import sys
import time
import requests
from pathlib import Path
from typing import Optional, Dict

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

import pandas as pd

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "medical_offices"
INPUT_CSV = DATA_DIR / "queens_brooklyn_doctors_with_addresses_llm.csv"
OUTPUT_CSV = DATA_DIR / "queens_brooklyn_doctors_final.csv"

# API Configuration
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

if not SERPER_API_KEY:
    print("❌ Error: SERPER_API_KEY environment variable not set")
    sys.exit(1)


def search_google_maps(name: str, address: str = None) -> Optional[Dict]:
    """
    Search Google Maps using Serper API to get ratings and reviews
    """
    url = "https://google.serper.dev/maps"

    # Build search query
    if address:
        query = f"{name} {address}"
    else:
        query = f"{name} Queens Brooklyn NY"

    payload = {
        "q": query,
        "location": "New York, NY",
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

        # Return first place result if available
        places = data.get("places", [])
        if places and len(places) > 0:
            return places[0]
        return None

    except Exception as e:
        print(f"   ⚠️  API error: {e}")
        return None


def enrich_record(row: pd.Series, index: int, total: int) -> pd.Series:
    """Enrich a single doctor office record with rating and reviews"""

    print(f"\n[{index + 1}/{total}] {row['name'][:60]}")

    # Skip if already has rating and reviews
    if pd.notna(row.get('rating')) and row.get('rating') and \
       pd.notna(row.get('reviews')) and row.get('reviews'):
        print("    ✓ Already has rating and reviews")
        return row

    # Search Google Maps
    print(f"    🔍 Searching Google Maps...")
    place = search_google_maps(row['name'], row.get('address'))

    if not place:
        print("    ❌ No results found")
        return row

    # Update rating and reviews
    if place.get('rating'):
        row['rating'] = place['rating']
        print(f"    ✅ Rating: {place['rating']}")

    if place.get('ratingCount'):
        row['reviews'] = place['ratingCount']
        print(f"    ✅ Reviews: {place['ratingCount']}")

    # Also update other fields if missing
    if place.get('phoneNumber') and not row.get('phone'):
        row['phone'] = place['phoneNumber']
        print(f"    ✅ Phone: {place['phoneNumber']}")

    if place.get('address') and not row.get('address'):
        row['address'] = place['address']
        print(f"    ✅ Address: {place['address']}")

    if place.get('latitude') and not row.get('latitude'):
        row['latitude'] = place['latitude']

    if place.get('longitude') and not row.get('longitude'):
        row['longitude'] = place['longitude']

    return row


def main():
    """Main execution"""
    print("=" * 80)
    print("ENRICHING DOCTOR OFFICES WITH RATINGS AND REVIEWS")
    print("=" * 80)
    print()

    # Load CSV
    if not INPUT_CSV.exists():
        print(f"❌ Error: CSV file not found at {INPUT_CSV}")
        sys.exit(1)

    print(f"📂 Loading data from {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV)

    print(f"   ✓ Loaded {len(df)} total records")
    print()

    # Count records needing enrichment
    needs_rating = df['rating'].isna() | (df['rating'] == '')
    needs_reviews = df['reviews'].isna() | (df['reviews'] == '')
    to_process = df[needs_rating | needs_reviews]

    print(f"   📊 Records missing rating: {needs_rating.sum()}")
    print(f"   📊 Records missing reviews: {needs_reviews.sum()}")
    print(f"   📊 Records to process: {len(to_process)}")
    print()

    if len(to_process) == 0:
        print("✅ All records already have ratings and reviews!")
        return

    # Process each record
    success_count = 0
    start_time = time.time()

    for idx, (df_idx, row) in enumerate(to_process.iterrows()):
        enriched_row = enrich_record(row, idx, len(to_process))

        # Update main dataframe
        for col in enriched_row.index:
            df.at[df_idx, col] = enriched_row[col]

        # Track success
        if enriched_row.get('rating') and pd.notna(enriched_row['rating']):
            success_count += 1

        # Rate limiting - be respectful to the API
        time.sleep(1)

        # Save progress every 50 records
        if (idx + 1) % 50 == 0:
            df.to_csv(OUTPUT_CSV, index=False)
            print(f"\n    💾 Progress saved ({success_count}/{idx + 1} successful)")

    # Final save
    df.to_csv(OUTPUT_CSV, index=False)

    elapsed = time.time() - start_time

    print()
    print("=" * 80)
    print("✅ ENRICHMENT COMPLETE")
    print("=" * 80)
    print(f"Output File: {OUTPUT_CSV}")
    print()
    print(f"Records processed: {len(to_process)}")
    print(f"Ratings found: {success_count} ({success_count/len(to_process)*100:.1f}%)")
    print(f"Time elapsed: {elapsed:.1f} seconds ({elapsed/len(to_process):.1f}s per record)")
    print()

    # Final statistics
    print("📊 FINAL STATISTICS:")
    print(f"   Total records: {len(df)}")
    print(f"   With addresses: {df['address'].astype(bool).sum()}")
    print(f"   With phone: {df['phone'].astype(bool).sum()}")
    print(f"   With rating: {df['rating'].astype(bool).sum()}")
    print(f"   With reviews: {df['reviews'].astype(bool).sum()}")
    print(f"   With business hours: {df['business_hours'].astype(bool).sum()}")
    print("=" * 80)


if __name__ == "__main__":
    main()
