#!/usr/bin/env python3
"""
Enrich Queens pharmacies with business hours using Serper Google Maps API
"""

import os
import sys
import time
import requests
from pathlib import Path
from typing import Dict, List

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

import pandas as pd

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "pharmacies"
INPUT_CSV = DATA_DIR / "queens_pharmacies_with_addresses.csv"
OUTPUT_CSV = DATA_DIR / "queens_pharmacies_enriched.csv"

# API Configuration
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

if not SERPER_API_KEY:
    print("❌ Error: SERPER_API_KEY environment variable not set")
    print("   Set it in your .env file or export SERPER_API_KEY=your_key")
    sys.exit(1)


def format_business_hours(hours_data) -> str:
    """
    Format business hours into a human-readable string.
    Input can be dict, list, or string.
    """
    if isinstance(hours_data, str):
        return hours_data

    if isinstance(hours_data, dict):
        # Format as: "Mon: 8 AM–10 PM, Tue: 8 AM–10 PM, ..."
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        formatted_parts = []

        for day in day_order:
            if day in hours_data:
                # Shorten day name and clean up special characters
                day_short = day[:3]
                hours = hours_data[day].replace('\u202f', ' ')  # Replace narrow no-break space
                formatted_parts.append(f"{day_short}: {hours}")

        return "; ".join(formatted_parts)

    # Fallback: convert to string
    return str(hours_data)


def search_google_maps(query: str, location: str = "Queens, NY") -> List[Dict]:
    """
    Search using Serper Google Maps API
    Returns place results with business hours
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


def enrich_with_hours(row: pd.Series) -> pd.Series:
    """
    Enrich a pharmacy record with business hours from Google Maps
    """
    # Skip if already has hours
    if pd.notna(row.get('business_hours')) and str(row.get('business_hours')).strip():
        return row

    # Build search query
    name = row['name']
    location_search = row.get('location', 'Queens, NY')

    # Try to use address if available for more accurate search
    if pd.notna(row.get('address')) and str(row.get('address')).strip():
        address = str(row['address']).strip()
        # Use just the street address part for search
        address_parts = address.split(',')
        if len(address_parts) > 0:
            query = f"{name} {address_parts[0]}"
        else:
            query = f"{name} pharmacy {location_search}"
    else:
        query = f"{name} pharmacy {location_search}"

    print(f"  🔍 Searching: {name[:50]}...")

    # Search Google Maps
    places = search_google_maps(query, location_search)

    if places and len(places) > 0:
        # Take first result
        place = places[0]

        # Extract business hours
        if place.get('openingHours'):
            hours = place['openingHours']
            # Format hours into human-readable string
            formatted_hours = format_business_hours(hours)
            row['business_hours'] = formatted_hours
            print(f"    ✓ Hours: {formatted_hours[:70]}...")

        # Also update other fields if missing
        if place.get('address') and (pd.isna(row.get('address')) or str(row.get('address')).strip() == ''):
            row['address'] = place['address']
            print(f"    ✓ Address: {place['address'][:60]}")

        if place.get('phoneNumber') and (pd.isna(row.get('phone')) or str(row.get('phone')).strip() == ''):
            row['phone'] = place['phoneNumber']
            print(f"    ✓ Phone: {place['phoneNumber']}")

        if place.get('rating'):
            row['rating'] = place['rating']

        if place.get('ratingCount'):
            row['reviews'] = place['ratingCount']

        if place.get('latitude'):
            row['latitude'] = place['latitude']

        if place.get('longitude'):
            row['longitude'] = place['longitude']
    else:
        print(f"    ⚠️  No results found")

    # Rate limiting
    time.sleep(0.5)

    return row


def main():
    print("=" * 70)
    print("QUEENS PHARMACIES - BUSINESS HOURS ENRICHMENT (SERPER API)")
    print("=" * 70)
    print(f"Input: {INPUT_CSV}")
    print(f"Output: {OUTPUT_CSV}")
    print()

    # Load data
    if not INPUT_CSV.exists():
        print(f"❌ Error: Input file not found: {INPUT_CSV}")
        print(f"   Make sure you've run 02_enrich_with_addresses.py first")
        sys.exit(1)

    df = pd.read_csv(INPUT_CSV)
    print(f"📊 Loaded {len(df)} pharmacies")

    # Add business_hours column if it doesn't exist
    if 'business_hours' not in df.columns:
        df['business_hours'] = None

    # Add other columns if they don't exist
    if 'latitude' not in df.columns:
        df['latitude'] = None
    if 'longitude' not in df.columns:
        df['longitude'] = None

    # Count how many need enrichment
    needs_hours = df['business_hours'].isna().sum()
    print(f"🎯 Pharmacies needing business hours: {needs_hours}")
    print()

    # Enrich each record
    print("=" * 70)
    print("ENRICHING BUSINESS HOURS")
    print("=" * 70)

    enriched_count = 0

    for idx in range(len(df)):
        # Only enrich if missing hours
        if pd.isna(df.loc[idx, 'business_hours']) or str(df.loc[idx, 'business_hours']).strip() == '':
            print(f"[{idx + 1}/{len(df)}]", end=" ")
            df.loc[idx] = enrich_with_hours(df.loc[idx])
            enriched_count += 1

            # Save progress every 50 records
            if enriched_count % 50 == 0:
                df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8')
                print(f"\n💾 Progress saved ({enriched_count} processed)")

    # Final save
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8')

    # Summary
    print("\n" + "=" * 70)
    print("ENRICHMENT COMPLETE")
    print("=" * 70)

    # Count results
    still_missing = df['business_hours'].isna().sum()
    successfully_enriched = needs_hours - still_missing

    print(f"✅ Successfully enriched: {successfully_enriched}/{needs_hours}")
    print(f"⚠️  Still missing hours: {still_missing}")
    print(f"📁 Output saved to: {OUTPUT_CSV}")
    print("=" * 70)


if __name__ == "__main__":
    main()
