#!/usr/bin/env python3
"""
Clean and enrich Queens/Brooklyn facilities data:
1. Remove duplicates
2. Remove junk records (web snippets, non-facilities)
3. Enrich invalid addresses with HERE API
"""

import os
import sys
import time
import json
import requests
from pathlib import Path
from typing import Dict, List, Optional
import csv
from collections import defaultdict

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "queens_brooklyn_facilities"
QUEENS_INPUT = DATA_DIR / "queens_facilities.csv"
BROOKLYN_INPUT = DATA_DIR / "brooklyn_facilities.csv"
QUEENS_OUTPUT = DATA_DIR / "queens_facilities_cleaned.csv"
BROOKLYN_OUTPUT = DATA_DIR / "brooklyn_facilities_cleaned.csv"
PROGRESS_FILE = DATA_DIR / "cleaning_progress.json"

# API Configuration
HERE_API_KEY = os.getenv("HERE_API_KEY")

if not HERE_API_KEY:
    print("❌ Error: HERE_API_KEY environment variable not set")
    sys.exit(1)


def is_valid_street_address(addr: str) -> bool:
    """Check if address is a valid street address"""
    if not addr or addr.strip() == '':
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
    """Check if address needs enrichment"""
    return not is_valid_street_address(addr)


def is_junk_record(row: Dict) -> bool:
    """Identify junk records that should be removed"""
    name = row.get('name', '').lower()

    # Web page titles and search snippets
    junk_patterns = [
        'the best 10',
        'top 10 best',
        'best nursing homes',
        'elder care in',
        'senior care in',
        'geriatric medicine in',
        'nursing homes near',
        'senior centers near',
        'older adult center - nyc aging',
        'locations - queens public library',
        'locations | brooklyn public library',
        'community boards',
        'united states postal service',
        'puregym',
        'blink fitness',
        'brooklyn borough hall',
    ]

    for pattern in junk_patterns:
        if pattern in name:
            return True

    # Generic location names only (without actual facility name)
    generic_names = [
        'whitestone', 'howard beach', 'jamaica', 'flushing',
        'astoria', 'queens', 'brooklyn', 'williamsburg',
        'bay ridge', 'bushwick', 'crown heights'
    ]

    # Only mark as junk if it's ONLY the location name
    if name.strip() in generic_names:
        return True

    return False


def remove_duplicates(rows: List[Dict]) -> List[Dict]:
    """Remove exact duplicates based on name + address"""
    seen = set()
    unique_rows = []

    for row in rows:
        # Create key from name + address
        key = (row.get('name', '').strip().lower(), row.get('address', '').strip().lower())

        if key not in seen:
            seen.add(key)
            unique_rows.append(row)

    return unique_rows


def search_here_places(query: str, location: str = "New York, NY") -> List[Dict]:
    """Search using HERE Geocoding & Search API"""
    url = "https://discover.search.hereapi.com/v1/discover"

    # Use 'in' parameter for area-based search (NYC area)
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
        return data.get("items", [])
    except Exception as e:
        print(f"   ⚠️  HERE API error: {e}")
        return []


def parse_here_result(item: Dict) -> Optional[Dict]:
    """Parse HERE API result into standard format"""
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

    return result


def enrich_with_address(row: Dict) -> Dict:
    """Enrich a facility record with address from HERE API"""

    # Skip if address is already valid
    if not needs_enrichment(row['address']):
        return row

    # Build search query
    name = row['name']
    location_search = row.get('location', 'New York, NY')

    query = f"{name} {location_search}"

    print(f"  Searching HERE for: {name[:50]}...")
    if row['address']:
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

            if parsed.get('phone') and not row.get('phone'):
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


def load_progress() -> Dict:
    """Load progress from file"""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {"queens_processed": 0, "brooklyn_processed": 0}


def save_progress(progress: Dict):
    """Save progress to file"""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)


def process_file(input_file: Path, output_file: Path, borough: str, progress_key: str):
    """Process a single CSV file"""
    print(f"\n{'='*80}")
    print(f"PROCESSING {borough.upper()} FACILITIES")
    print(f"{'='*80}\n")

    # Load progress
    progress = load_progress()
    start_idx = progress.get(progress_key, 0)

    # Load CSV
    print(f"📂 Loading data from {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    print(f"   ✓ Loaded {len(rows)} facilities")

    # Step 1: Remove junk records
    print(f"\n🗑️  Removing junk records...")
    clean_rows = [row for row in rows if not is_junk_record(row)]
    print(f"   Removed {len(rows) - len(clean_rows)} junk records")

    # Step 2: Remove duplicates
    print(f"\n🔄 Removing duplicates...")
    unique_rows = remove_duplicates(clean_rows)
    print(f"   Removed {len(clean_rows) - len(unique_rows)} duplicates")
    print(f"   Remaining: {len(unique_rows)} unique facilities")

    # Step 3: Analyze address quality
    valid_count = sum(1 for row in unique_rows if is_valid_street_address(row.get('address', '')))
    invalid_count = len(unique_rows) - valid_count

    print(f"\n📊 Address Quality:")
    print(f"   ✅ Valid: {valid_count} ({valid_count/len(unique_rows)*100:.1f}%)")
    print(f"   ❌ Invalid: {invalid_count} ({invalid_count/len(unique_rows)*100:.1f}%)")

    # Step 4: Enrich invalid addresses
    if invalid_count > 0:
        print(f"\n🔍 Enriching {invalid_count} invalid addresses with HERE API...")
        print(f"   Starting from record {start_idx + 1}")
        print()

        enriched = 0
        for idx in range(start_idx, len(unique_rows)):
            if idx % 10 == 0:
                print(f"[{idx + 1}/{len(unique_rows)}]")

            unique_rows[idx] = enrich_with_address(unique_rows[idx])

            # Track enriched
            if is_valid_street_address(unique_rows[idx].get('address', '')):
                enriched += 1

            # Rate limiting
            time.sleep(0.5)

            # Save progress every 50 records
            if (idx + 1) % 50 == 0:
                progress[progress_key] = idx + 1
                save_progress(progress)

                # Save intermediate results
                with open(output_file, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(unique_rows)

                print(f"  💾 Progress saved ({enriched} enriched so far)")

    # Final save
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(unique_rows)

    # Final statistics
    final_valid = sum(1 for row in unique_rows if is_valid_street_address(row.get('address', '')))
    final_invalid = len(unique_rows) - final_valid

    print(f"\n{'='*80}")
    print(f"✅ {borough.upper()} PROCESSING COMPLETE")
    print(f"{'='*80}")
    print(f"Output: {output_file}")
    print()
    print(f"📊 Final Results:")
    print(f"   Total records: {len(unique_rows)}")
    print(f"   ✅ Valid addresses: {final_valid} ({final_valid/len(unique_rows)*100:.1f}%)")
    print(f"   ❌ Still invalid: {final_invalid} ({final_invalid/len(unique_rows)*100:.1f}%)")
    print()
    print(f"Improvements:")
    print(f"   Before: {len(rows)} records, {valid_count} valid addresses")
    print(f"   After:  {len(unique_rows)} records, {final_valid} valid addresses")
    print(f"   Removed: {len(rows) - len(unique_rows)} duplicates/junk")
    print(f"   Fixed: {final_valid - valid_count} addresses")
    print(f"{'='*80}")

    # Reset progress for this file
    progress[progress_key] = 0
    save_progress(progress)


def main():
    """Main execution"""
    print("=" * 80)
    print("CLEANING AND ENRICHING QUEENS/BROOKLYN FACILITIES")
    print("=" * 80)

    # Process Queens
    if QUEENS_INPUT.exists():
        process_file(QUEENS_INPUT, QUEENS_OUTPUT, "Queens", "queens_processed")
    else:
        print(f"❌ Queens file not found: {QUEENS_INPUT}")

    # Process Brooklyn
    if BROOKLYN_INPUT.exists():
        process_file(BROOKLYN_INPUT, BROOKLYN_OUTPUT, "Brooklyn", "brooklyn_processed")
    else:
        print(f"❌ Brooklyn file not found: {BROOKLYN_INPUT}")

    print("\n" + "=" * 80)
    print("🎉 ALL PROCESSING COMPLETE!")
    print("=" * 80)
    print(f"\nOutput files:")
    print(f"  - {QUEENS_OUTPUT}")
    print(f"  - {BROOKLYN_OUTPUT}")
    print("=" * 80)


if __name__ == "__main__":
    main()
