#!/usr/bin/env python3
"""
Test HERE API enrichment on a small sample of addresses
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

# API Configuration
HERE_API_KEY = os.getenv("HERE_API_KEY")

if not HERE_API_KEY:
    print("❌ Error: HERE_API_KEY environment variable not set")
    print("   Set it with: export HERE_API_KEY='your_key'")
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
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_details = e.response.json()
                print(f"   Error details: {error_details}")
            except:
                pass
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


def is_city_only_address(addr: str) -> bool:
    """Check if address is just city/state (needs enrichment)"""
    if pd.isna(addr) or addr == '':
        return True  # Completely missing

    addr_str = str(addr).strip()

    # Valid street address (starts with number) - skip
    if addr_str[0].isdigit():
        return False

    # Search result snippets/garbage (long or has keywords) - skip for now
    if len(addr_str) > 100 or any(word in addr_str.lower() for word in
                                    ['best', 'top 10', 'yelp', 'http', 'www',
                                     'provide', 'offer', 'activities', 'services']):
        return False

    # City/state only or short partial addresses - ENRICH
    if len(addr_str) < 100 and any(state in addr_str for state in ['NY ', 'NY,', 'New York']):
        return True

    return False


def main():
    """Test enrichment on sample records"""
    print("=" * 80)
    print("TESTING HERE API ENRICHMENT ON SAMPLE")
    print("=" * 80)
    print()

    # Load CSV
    if not INPUT_CSV.exists():
        print(f"❌ Error: CSV file not found at {INPUT_CSV}")
        sys.exit(1)

    print(f"📂 Loading data from {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV)
    print(f"   ✓ Loaded {len(df)} facilities")
    print()

    # Find records that need enrichment
    need_enrichment = df[df['address'].apply(is_city_only_address)]
    print(f"📊 Found {len(need_enrichment)} addresses needing enrichment")
    print()

    # Take first 10 samples
    sample_size = min(10, len(need_enrichment))
    samples = need_enrichment.head(sample_size).copy()

    print(f"🧪 Testing with {sample_size} sample records...")
    print()

    # Process each sample
    results = []
    success_count = 0

    for idx, row in samples.iterrows():
        print(f"[{len(results) + 1}/{sample_size}] {row['name'][:50]}")
        print(f"  Before: {row['address']}")

        # Build search query
        query = f"{row['name']} {row.get('location', 'New York, NY')}"

        # Search HERE API
        items = search_here_places(query, row.get('location', 'New York, NY'))

        new_address = row['address']
        new_coords = (row.get('latitude'), row.get('longitude'))

        if items and len(items) > 0:
            parsed = parse_here_result(items[0])

            if parsed and parsed.get('address'):
                new_address = parsed['address']
                new_coords = (parsed.get('latitude'), parsed.get('longitude'))
                success_count += 1
                print(f"  ✓ After:  {new_address}")
            else:
                print(f"  ❌ No address found")
        else:
            print(f"  ❌ No results from API")

        results.append({
            'name': row['name'],
            'before': row['address'],
            'after': new_address,
            'coords': new_coords,
            'success': new_address != row['address']
        })

        print()

        # Rate limiting
        time.sleep(1)

    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print()
    print(f"Total tested: {sample_size}")
    print(f"Successfully enriched: {success_count}")
    print(f"Failed: {sample_size - success_count}")
    print(f"Success rate: {success_count/sample_size*100:.1f}%")
    print()

    # Show results table
    print("DETAILED RESULTS:")
    print("-" * 80)
    for i, result in enumerate(results, 1):
        status = "✅" if result['success'] else "❌"
        print(f"{status} {i}. {result['name'][:50]}")
        print(f"     Before: {result['before']}")
        print(f"     After:  {result['after']}")
        if result['coords'][0]:
            print(f"     Coords: {result['coords']}")
        print()

    print("=" * 80)

    if success_count > 0:
        print(f"✅ HERE API is working! Successfully enriched {success_count}/{sample_size} addresses.")
        print("   You can now run the full enrichment script.")
    else:
        print("⚠️  No addresses were enriched. Please check:")
        print("   1. HERE_API_KEY is set correctly")
        print("   2. API key is valid and active")
        print("   3. Network connection is working")


if __name__ == "__main__":
    main()
