#!/usr/bin/env python3
"""
Enrich Queens/Brooklyn facilities with addresses using HERE Geocoding & Search API
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
DATA_DIR = PROJECT_ROOT / "data" / "queens_brooklyn_facilities"
INPUT_CSV = DATA_DIR / "queens_brooklyn_facilities.csv"
OUTPUT_CSV = DATA_DIR / "queens_brooklyn_facilities_with_addresses.csv"

# API Configuration
HERE_API_KEY = os.getenv("HERE_API_KEY")

if not HERE_API_KEY:
    print("❌ Error: HERE_API_KEY environment variable not set")
    print("   Get your API key from: https://platform.here.com/")
    sys.exit(1)


def search_here_places(query: str, location: str = "New York, NY") -> List[Dict]:
    """
    Search using HERE Geocoding & Search API
    Returns place results with addresses
    """
    url = "https://discover.search.hereapi.com/v1/discover"

    # Use 'in' parameter for area-based search (NYC area)
    # Queens/Brooklyn coordinates roughly centered
    params = {
        "q": query,
        "in": "circle:40.7128,-73.9;r=20000",  # 20km radius around NYC
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
    Returns True for:
    - Completely missing addresses
    - Search snippets/garbage
    - Partial addresses (city-only, no street number, etc.)

    Returns False for:
    - Valid street addresses (starts with number, has street name)
    """
    if pd.isna(addr) or addr == '':
        return True  # Completely missing - needs enrichment

    addr_str = str(addr).strip()

    # Check if it's a valid street address
    if is_valid_street_address(addr):
        return False  # Valid address - skip enrichment

    # Everything else needs enrichment:
    # - Search snippets (long text with keywords)
    # - Partial addresses (city-only, no street number)
    # - Garbage data
    return True


def enrich_with_address(row: pd.Series) -> pd.Series:
    """Enrich a facility record with address from HERE API"""

    # Skip if address is already valid
    if not needs_enrichment(row['address']):
        return row

    # Build search query
    name = row['name']
    location_search = row.get('location', 'New York, NY')

    query = f"{name} {location_search}"

    print(f"  Searching HERE for: {name[:50]}...")
    if not pd.isna(row['address']) and row['address']:
        print(f"    Old: {str(row['address'])[:60]}...")

    # Search HERE API
    items = search_here_places(query, location_search)

    if items and len(items) > 0:
        # Take first result and parse it
        parsed = parse_here_result(items[0])

        if parsed:
            # Update fields
            if parsed.get('address'):
                row['address'] = parsed['address']
                print(f"    ✓ New: {parsed['address'][:60]}")

            if parsed.get('phone') and not row['phone']:
                row['phone'] = parsed['phone']

            if parsed.get('latitude'):
                row['latitude'] = parsed['latitude']

            if parsed.get('longitude'):
                row['longitude'] = parsed['longitude']
        else:
            print(f"    ❌ No valid result found")
    else:
        print(f"    ❌ No results from API")

    return row


def main():
    """Main execution"""
    print("=" * 80)
    print("ENRICHING QUEENS/BROOKLYN FACILITIES WITH ADDRESSES (HERE API)")
    print("=" * 80)
    print()

    # Load CSV
    if not INPUT_CSV.exists():
        print(f"❌ Error: CSV file not found at {INPUT_CSV}")
        sys.exit(1)

    print(f"📂 Loading data from {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV)
    print(f"   ✓ Loaded {len(df)} facilities")

    # Analyze address quality
    valid_addresses = df['address'].apply(lambda x: is_valid_street_address(x) if pd.notna(x) else False)
    invalid_addresses = df['address'].apply(needs_enrichment)

    print()
    print("📊 Address Quality:")
    print(f"   ✅ Valid street addresses: {valid_addresses.sum()}")
    print(f"   ❌ Invalid/missing addresses: {invalid_addresses.sum()}")
    print()

    # Enrich each record
    print(f"🔍 Enriching {invalid_addresses.sum()} invalid addresses with HERE API...")
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

    # Final statistics
    final_valid = df['address'].apply(lambda x: is_valid_street_address(x) if pd.notna(x) else False)
    final_invalid = df['address'].apply(needs_enrichment)

    print()
    print("=" * 80)
    print("✅ ENRICHMENT COMPLETE")
    print("=" * 80)
    print(f"Output File: {OUTPUT_CSV}")
    print()
    print("📊 Final Results:")
    print(f"   Total records: {len(df)}")
    print(f"   ✅ Valid addresses: {final_valid.sum()} ({final_valid.sum()/len(df)*100:.1f}%)")
    print(f"   ❌ Still invalid: {final_invalid.sum()} ({final_invalid.sum()/len(df)*100:.1f}%)")
    print(f"   📞 With phone: {df['phone'].astype(bool).sum()}")
    print(f"   📍 With coordinates: {df['latitude'].astype(bool).sum()}")
    print()
    print("Improvement:")
    print(f"   Before: {valid_addresses.sum()} valid addresses")
    print(f"   After:  {final_valid.sum()} valid addresses")
    print(f"   Fixed:  {final_valid.sum() - valid_addresses.sum()} addresses")
    print("=" * 80)


if __name__ == "__main__":
    main()
