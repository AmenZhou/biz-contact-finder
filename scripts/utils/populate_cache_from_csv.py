#!/usr/bin/env python3
"""
Populate the pharmacy cache with data from existing CSV files.
This allows future scraping runs to use cached data for 30 days.
"""

import csv
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.pharmacy_cache import PharmacyCache


DATA_DIR = Path('data')


def main():
    """Main function to populate cache from CSV files."""
    print("="*60)
    print("POPULATE CACHE FROM CSV FILES")
    print("="*60)

    # Initialize cache
    cache = PharmacyCache()

    print("\nBefore population:")
    cache.print_stats()

    # Find all district CSV files
    district_files = sorted(DATA_DIR.glob('district_*_pharmacies.csv'))

    if not district_files:
        print("\n✗ No district CSV files found")
        sys.exit(1)

    print(f"\nFound {len(district_files)} district files")
    print("\nPopulating cache...")

    total_pharmacies = 0

    for district_file in district_files:
        # Extract district number from filename
        filename = district_file.stem  # e.g., "district_01_pharmacies"
        parts = filename.split('_')
        if len(parts) >= 2:
            try:
                district_num = int(parts[1])
            except ValueError:
                print(f"  ⚠ Skipping {district_file.name} - invalid district number")
                continue
        else:
            print(f"  ⚠ Skipping {district_file.name} - unexpected filename format")
            continue

        # Read pharmacies from CSV
        try:
            with open(district_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                pharmacies = list(reader)

            if pharmacies:
                # Cache the district data
                cache.cache_district(district_num, pharmacies)
                total_pharmacies += len(pharmacies)
                print(f"  ✓ District {district_num:2d}: Cached {len(pharmacies):3d} pharmacies")
            else:
                print(f"  ⚠ District {district_num:2d}: No pharmacies found")

        except Exception as e:
            print(f"  ✗ District {district_num:2d}: Failed to read - {e}")

    print(f"\n✓ Successfully cached {total_pharmacies} pharmacies from {len(district_files)} districts")

    print("\nAfter population:")
    cache.print_stats()

    print("\n" + "="*60)
    print("CACHE POPULATION COMPLETED!")
    print("="*60)
    print("\nBenefits:")
    print("  - Future scraping runs will check cache first")
    print("  - Cached data is valid for 30 days")
    print("  - Estimated savings: ~$40-50 per re-run (within 30 days)")
    print("\nUsage:")
    print("  - Run scraper normally - it will automatically use cache")
    print("  - Force refresh: delete data/pharmacy_cache.json")
    print("  - Manage cache: python scripts/manage_cache.py stats")


if __name__ == '__main__':
    main()
