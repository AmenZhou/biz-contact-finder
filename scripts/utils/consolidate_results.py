#!/usr/bin/env python3
"""
Consolidate all district pharmacy CSV files into a single master file.
Can be run standalone or as part of the scraping pipeline.
"""

import csv
import sys
from pathlib import Path
from typing import List, Dict


# Configuration
DATA_DIR = Path('data')
DISTRICT_PATTERN = 'district_*_pharmacies.csv'
CONSOLIDATED_CSV = DATA_DIR / 'all_districts_pharmacies.csv'

# CSV field names (without rating fields - cost optimized)
FIELDNAMES = [
    'district_num', 'district_name', 'name', 'address', 'phone', 'website',
    'google_maps_url', 'business_status',
    'is_open_now', 'hours', 'latitude', 'longitude', 'place_id', 'types'
]


def load_district_files() -> List[Dict]:
    """Load all district CSV files."""
    all_pharmacies = []

    district_files = sorted(DATA_DIR.glob(DISTRICT_PATTERN))

    if not district_files:
        print(f"  ⚠ No district files found matching: {DISTRICT_PATTERN}")
        return []

    print(f"  Found {len(district_files)} district files")

    for district_file in district_files:
        try:
            with open(district_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                pharmacies = list(reader)
                all_pharmacies.extend(pharmacies)
                print(f"  ✓ Loaded {len(pharmacies):3d} pharmacies from {district_file.name}")
        except Exception as e:
            print(f"  ✗ Failed to read {district_file.name}: {e}")

    return all_pharmacies


def deduplicate_pharmacies(pharmacies: List[Dict]) -> List[Dict]:
    """Remove duplicate pharmacies by place_id."""
    unique_pharmacies = {}

    for pharmacy in pharmacies:
        place_id = pharmacy.get('place_id')
        if place_id:
            if place_id not in unique_pharmacies:
                unique_pharmacies[place_id] = pharmacy
            # If duplicate, keep the one with more data
            elif len(pharmacy) > len(unique_pharmacies[place_id]):
                unique_pharmacies[place_id] = pharmacy

    duplicates_removed = len(pharmacies) - len(unique_pharmacies)
    if duplicates_removed > 0:
        print(f"  ℹ Removed {duplicates_removed} duplicate pharmacies")

    return list(unique_pharmacies.values())


def sort_pharmacies(pharmacies: List[Dict]) -> List[Dict]:
    """Sort pharmacies by district number, then alphabetically by name."""
    return sorted(
        pharmacies,
        key=lambda x: (
            int(x.get('district_num', 999)),
            (x.get('name') or '').lower()
        )
    )


def write_consolidated_csv(pharmacies: List[Dict]) -> None:
    """Write consolidated CSV file."""
    with open(CONSOLIDATED_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(pharmacies)

    print(f"\n  ✓ Saved {len(pharmacies)} pharmacies to: {CONSOLIDATED_CSV}")
    print(f"  File size: {CONSOLIDATED_CSV.stat().st_size / 1024:.2f} KB")


def print_statistics(pharmacies: List[Dict]) -> None:
    """Print statistics by district."""
    district_counts = {}

    for pharmacy in pharmacies:
        district_num = pharmacy.get('district_num', 'Unknown')
        district_counts[district_num] = district_counts.get(district_num, 0) + 1

    print(f"\n  📊 Pharmacies by district:")
    print("  " + "-" * 40)

    total = 0
    for district_num in sorted(district_counts.keys(), key=lambda x: int(x) if str(x).isdigit() else 999):
        count = district_counts[district_num]
        total += count
        print(f"    District {district_num:>2s}: {count:3d} pharmacies")

    print("  " + "-" * 40)
    print(f"    TOTAL: {total} pharmacies across {len(district_counts)} districts")

    # Calculate averages
    if district_counts:
        avg_per_district = total / len(district_counts)
        print(f"    Average per district: {avg_per_district:.1f}")

    # Find districts with most/least pharmacies
    if district_counts:
        max_district = max(district_counts.items(), key=lambda x: x[1])
        min_district = min(district_counts.items(), key=lambda x: x[1])
        print(f"\n  Highest: District {max_district[0]} ({max_district[1]} pharmacies)")
        print(f"  Lowest: District {min_district[0]} ({min_district[1]} pharmacies)")


def main():
    """Main consolidation function."""
    print("="*60)
    print("PHARMACY DATA CONSOLIDATION")
    print("="*60)

    # Create data directory if it doesn't exist
    DATA_DIR.mkdir(exist_ok=True)

    # Load all district files
    print("\n[1/4] Loading district CSV files...")
    all_pharmacies = load_district_files()

    if not all_pharmacies:
        print("\n✗ No pharmacy data found to consolidate")
        sys.exit(1)

    print(f"\n  Loaded {len(all_pharmacies)} total pharmacy records")

    # Deduplicate
    print("\n[2/4] Removing duplicates...")
    unique_pharmacies = deduplicate_pharmacies(all_pharmacies)

    # Sort
    print("\n[3/4] Sorting pharmacies...")
    sorted_pharmacies = sort_pharmacies(unique_pharmacies)

    # Write consolidated file
    print("\n[4/4] Writing consolidated CSV...")
    write_consolidated_csv(sorted_pharmacies)

    # Print statistics
    print_statistics(sorted_pharmacies)

    print("\n" + "="*60)
    print("✅ CONSOLIDATION COMPLETED SUCCESSFULLY!")
    print("="*60)
    print(f"\nOutput file: {CONSOLIDATED_CSV}")
    print(f"Total unique pharmacies: {len(sorted_pharmacies)}")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Consolidation interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
