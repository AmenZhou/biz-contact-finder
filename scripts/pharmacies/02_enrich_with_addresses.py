#!/usr/bin/env python3
"""
Enrich Queens pharmacies with addresses using HERE Discover API
"""

import os
import sys
import time
import requests
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

import pandas as pd

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "pharmacies"
INPUT_CSV = DATA_DIR / "queens_pharmacies.csv"
OUTPUT_CSV = DATA_DIR / "queens_pharmacies_with_addresses.csv"

# API Configuration
HERE_API_KEY = os.getenv("HERE_API_KEY")

if not HERE_API_KEY:
    print("❌ Error: HERE_API_KEY environment variable not set")
    print("   Set it in your .env file or export HERE_API_KEY=your_key")
    sys.exit(1)


def search_here_places(query: str, location: str = "Queens, NY") -> List[Dict]:
    """
    Search using HERE Discover API
    Returns place results with addresses
    """
    url = "https://discover.search.hereapi.com/v1/discover"

    # Queens area - centered around Flushing
    params = {
        "q": query,
        "in": "circle:40.7282,-73.7949;r=25000",  # 25km radius covering all of Queens
        "limit": 5,
        "apiKey": HERE_API_KEY
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        # HERE API returns 'items' array
        return data.get("items", [])
    except Exception as e:
        print(f"   ⚠️  HERE API error: {e}")
        return []


def parse_here_result(item: Dict) -> Optional[Dict]:
    """
    Parse HERE API result into standard format
    """
    if not item:
        return None

    result = {}

    # Extract address
    if "address" in item:
        addr = item["address"]
        # Build full address
        address_parts = []
        if addr.get("houseNumber"):
            address_parts.append(addr["houseNumber"])
        if addr.get("street"):
            address_parts.append(addr["street"])
        if addr.get("city"):
            address_parts.append(addr["city"])
        if addr.get("stateCode"):
            address_parts.append(addr["stateCode"])
        if addr.get("postalCode"):
            address_parts.append(addr["postalCode"])

        result["address"] = ", ".join(address_parts) if address_parts else None

    # Extract coordinates
    if "position" in item:
        result["latitude"] = item["position"].get("lat")
        result["longitude"] = item["position"].get("lng")

    # Extract contact info
    if "contacts" in item:
        contacts = item["contacts"]
        if contacts and len(contacts) > 0:
            contact = contacts[0]
            if "phone" in contact:
                phone_list = contact["phone"]
                if phone_list and len(phone_list) > 0:
                    result["phone"] = phone_list[0].get("value")

    # Extract title (name)
    if "title" in item:
        result["name"] = item["title"]

    return result


def is_valid_street_address(addr: str) -> bool:
    """Check if address is a valid street address"""
    if pd.isna(addr) or addr == '':
        return False

    addr_str = str(addr).strip()

    # Must start with a number for valid street address
    if not addr_str[0].isdigit():
        return False

    # Should have comma (street, city format)
    if ',' not in addr_str:
        return False

    # Should not be too long (likely a snippet)
    if len(addr_str) > 150:
        return False

    return True


def needs_enrichment(addr: str) -> bool:
    """
    Check if address needs enrichment (invalid or missing).
    """
    if pd.isna(addr) or addr == '':
        return True  # Completely missing - needs enrichment

    addr_str = str(addr).strip()

    # Check if it's a valid street address
    if is_valid_street_address(addr):
        return False  # Valid address - skip enrichment

    return True  # Invalid address - needs enrichment


def enrich_with_address(row: pd.Series) -> pd.Series:
    """
    Enrich a single pharmacy record with address data from HERE API
    """
    # Skip if address is already valid
    if not needs_enrichment(row['address']):
        return row

    name = row['name']
    location_search = row.get('location', 'Queens, NY')

    # Build search query
    query = f"{name} pharmacy {location_search}"

    print(f"  🔍 Searching: {name[:50]}...")

    # Search HERE API
    items = search_here_places(query, location_search)

    if items and len(items) > 0:
        # Parse first result
        parsed = parse_here_result(items[0])

        if parsed:
            # Update address if found
            if parsed.get('address'):
                row['address'] = parsed['address']
                print(f"    ✓ Address: {parsed['address'][:70]}")

            # Update phone if missing and found
            if parsed.get('phone') and (pd.isna(row['phone']) or row['phone'] == ''):
                row['phone'] = parsed['phone']
                print(f"    ✓ Phone: {parsed['phone']}")

            # Add coordinates if not present
            if parsed.get('latitude'):
                row['latitude'] = parsed['latitude']

            if parsed.get('longitude'):
                row['longitude'] = parsed['longitude']
    else:
        print(f"    ⚠️  No results found")

    # Rate limiting
    time.sleep(0.5)

    return row


def main():
    print("=" * 70)
    print("QUEENS PHARMACIES - ADDRESS ENRICHMENT (HERE API)")
    print("=" * 70)
    print(f"Input: {INPUT_CSV}")
    print(f"Output: {OUTPUT_CSV}")
    print()

    # Load data
    if not INPUT_CSV.exists():
        print(f"❌ Error: Input file not found: {INPUT_CSV}")
        sys.exit(1)

    df = pd.read_csv(INPUT_CSV)
    print(f"📊 Loaded {len(df)} pharmacies")

    # Add lat/lng columns if they don't exist
    if 'latitude' not in df.columns:
        df['latitude'] = None
    if 'longitude' not in df.columns:
        df['longitude'] = None

    # Count how many need enrichment
    needs_update = df['address'].apply(needs_enrichment).sum()
    print(f"🎯 Pharmacies needing address enrichment: {needs_update}")
    print()

    # Enrich each record
    print("=" * 70)
    print("ENRICHING ADDRESSES")
    print("=" * 70)

    enriched_count = 0

    for idx in range(len(df)):
        if needs_enrichment(df.loc[idx, 'address']):
            print(f"[{idx + 1}/{len(df)}]", end=" ")
            df.loc[idx] = enrich_with_address(df.loc[idx])
            enriched_count += 1

            # Save progress every 50 records
            if enriched_count % 50 == 0:
                df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8')
                print(f"\n💾 Progress saved ({enriched_count} enriched)")

    # Final save
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8')

    # Summary
    print("\n" + "=" * 70)
    print("ENRICHMENT COMPLETE")
    print("=" * 70)

    # Count results
    still_missing = df['address'].apply(needs_enrichment).sum()
    successfully_enriched = needs_update - still_missing

    print(f"✅ Successfully enriched: {successfully_enriched}/{needs_update}")
    print(f"⚠️  Still missing: {still_missing}")
    print(f"📁 Output saved to: {OUTPUT_CSV}")
    print("=" * 70)


if __name__ == "__main__":
    main()
