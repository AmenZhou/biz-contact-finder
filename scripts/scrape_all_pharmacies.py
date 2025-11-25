#!/usr/bin/env python3
"""
Master script to scrape pharmacies across all NYC districts.
Features:
- Scrapes all 49 districts with grid + text search
- Progress tracking with checkpoint file
- Resume capability
- Individual and consolidated outputs
"""

import json
import os
import sys
import time
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.pharmacy_scraper import PharmacyScraper
from config.districts import DISTRICTS
from config.settings import GOOGLE_PLACES_API_KEY


# Configuration
DATA_DIR = Path('data')
PROGRESS_FILE = DATA_DIR / 'scraping_progress.json'
CONSOLIDATED_CSV = DATA_DIR / 'all_districts_pharmacies.csv'
MAJOR_CHAINS = ['CVS', 'Walgreens', 'Duane Reade', 'Rite Aid', 'Walmart Pharmacy']


def load_progress() -> Dict:
    """Load progress from checkpoint file."""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {
        'completed_districts': [],
        'failed_districts': [],
        'start_time': None,
        'last_updated': None
    }


def save_progress(progress: Dict):
    """Save progress to checkpoint file."""
    progress['last_updated'] = datetime.now().isoformat()
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)


def save_district_results(district_num: int, pharmacies: List[Dict], district_name: str):
    """Save pharmacy results for a single district to CSV."""
    output_file = DATA_DIR / f'district_{district_num:02d}_pharmacies.csv'

    if not pharmacies:
        print(f"  ⚠ No pharmacies found for district {district_num}")
        # Create empty file to mark as processed
        output_file.touch()
        return

    # Sort by name (alphabetically) since rating field removed for cost optimization
    pharmacies_sorted = sorted(
        pharmacies,
        key=lambda x: (x.get('name') or '').lower()
    )

    # Write to CSV (removed rating/total_ratings fields for cost optimization)
    fieldnames = [
        'district_num', 'district_name', 'name', 'address', 'phone', 'website',
        'google_maps_url', 'business_status',
        'is_open_now', 'hours', 'latitude', 'longitude', 'place_id', 'types'
    ]

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for pharmacy in pharmacies_sorted:
            row = {
                'district_num': district_num,
                'district_name': district_name,
                **pharmacy
            }
            writer.writerow(row)

    print(f"  ✓ Saved {len(pharmacies)} pharmacies to: {output_file}")


def scrape_district(district_num: int, district_info: Dict, scraper: PharmacyScraper) -> List[Dict]:
    """Scrape pharmacies for a single district using grid + text search."""
    print(f"\n{'='*60}")
    print(f"DISTRICT {district_num}: {district_info['name']}")
    print(f"{'='*60}")

    bounds = district_info['bounds']
    center = district_info['center']
    grid_size = district_info['grid_size']

    print(f"  Bounds: Lat [{bounds['south']:.6f}, {bounds['north']:.6f}], "
          f"Lng [{bounds['west']:.6f}, {bounds['east']:.6f}]")
    print(f"  Center: ({center['lat']:.6f}, {center['lng']:.6f})")
    print(f"  Grid: {grid_size}x{grid_size}")

    all_pharmacies = {}

    # Method 1: Grid search
    print(f"\n  [1/2] Running grid search...")
    try:
        pharmacies_grid = scraper.search_area_grid(
            bounds=bounds,
            grid_size=grid_size,
            keyword="pharmacy"
        )
        print(f"    ✓ Found {len(pharmacies_grid)} pharmacies via grid search")

        for pharmacy in pharmacies_grid:
            place_id = pharmacy.get('place_id')
            if place_id and place_id not in all_pharmacies:
                all_pharmacies[place_id] = pharmacy

    except Exception as e:
        print(f"    ✗ Grid search failed: {e}")

    # Method 2: Text search for major chains
    print(f"\n  [2/2] Running text search for major chains...")
    # Optimized text searches (reduced from 6 to 2 for cost savings)
    # Grid search already provides comprehensive coverage
    text_search_queries = [
        f"pharmacy near {center['lat']},{center['lng']}",  # Generic search
        f"CVS Duane Reade near {center['lat']},{center['lng']}",  # Major chain (CVS owns Duane Reade)
    ]

    text_results_count = 0
    for query in text_search_queries:
        try:
            time.sleep(0.5)  # Rate limiting
            pharmacies_text = scraper.search_pharmacies_text(
                query=query,
                location_bias=(center['lat'], center['lng']),
                bounds=bounds
            )

            for pharmacy in pharmacies_text:
                place_id = pharmacy.get('place_id')
                if place_id and place_id not in all_pharmacies:
                    all_pharmacies[place_id] = pharmacy
                    text_results_count += 1

        except Exception as e:
            print(f"    ⚠ Text search failed for '{query}': {e}")
            continue

    print(f"    ✓ Found {text_results_count} additional pharmacies via text search")

    # Final deduplication and return
    unique_pharmacies = list(all_pharmacies.values())
    print(f"\n  📊 TOTAL: {len(unique_pharmacies)} unique pharmacies")

    return unique_pharmacies


def consolidate_results():
    """Consolidate all district CSV files into one master file."""
    print(f"\n{'='*60}")
    print("CONSOLIDATING RESULTS")
    print(f"{'='*60}")

    all_pharmacies = []

    # Read all district files
    for district_file in sorted(DATA_DIR.glob('district_*_pharmacies.csv')):
        try:
            with open(district_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                pharmacies = list(reader)
                all_pharmacies.extend(pharmacies)
                print(f"  ✓ Loaded {len(pharmacies)} pharmacies from {district_file.name}")
        except Exception as e:
            print(f"  ✗ Failed to read {district_file.name}: {e}")

    if not all_pharmacies:
        print("  ⚠ No pharmacy data to consolidate")
        return

    # Deduplicate by place_id (in case of overlapping boundaries)
    unique_pharmacies = {}
    for pharmacy in all_pharmacies:
        place_id = pharmacy.get('place_id')
        if place_id and place_id not in unique_pharmacies:
            unique_pharmacies[place_id] = pharmacy

    pharmacies_list = list(unique_pharmacies.values())

    # Sort by district number, then rating
    # Sort by district number, then name (rating removed for cost optimization)
    pharmacies_sorted = sorted(
        pharmacies_list,
        key=lambda x: (int(x.get('district_num', 999)), (x.get('name') or '').lower())
    )

    # Write consolidated CSV (removed rating/total_ratings for cost optimization)
    fieldnames = [
        'district_num', 'district_name', 'name', 'address', 'phone', 'website',
        'google_maps_url', 'business_status',
        'is_open_now', 'hours', 'latitude', 'longitude', 'place_id', 'types'
    ]

    with open(CONSOLIDATED_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(pharmacies_sorted)

    print(f"\n  ✓ Consolidated {len(pharmacies_sorted)} unique pharmacies")
    print(f"  ✓ Saved to: {CONSOLIDATED_CSV}")

    # Print statistics by district
    district_counts = {}
    for pharmacy in pharmacies_sorted:
        district_num = pharmacy.get('district_num', 'Unknown')
        district_counts[district_num] = district_counts.get(district_num, 0) + 1

    print(f"\n  📊 Pharmacies per district:")
    for district_num in sorted(district_counts.keys(), key=lambda x: int(x) if str(x).isdigit() else 999):
        count = district_counts[district_num]
        print(f"    District {district_num}: {count} pharmacies")


def main():
    """Main function to orchestrate the scraping process."""
    print(f"{'='*60}")
    print("NYC PHARMACY SCRAPER - ALL DISTRICTS")
    print(f"{'='*60}")
    print(f"Total districts to scrape: {len(DISTRICTS)}")
    print(f"Data directory: {DATA_DIR}")

    # Create data directory if it doesn't exist
    DATA_DIR.mkdir(exist_ok=True)

    # Initialize scraper
    if not GOOGLE_PLACES_API_KEY:
        print("\n✗ ERROR: GOOGLE_PLACES_API_KEY not found in environment")
        print("  Please set the API key in your .env file")
        sys.exit(1)

    scraper = PharmacyScraper(api_key=GOOGLE_PLACES_API_KEY)
    print(f"✓ Initialized PharmacyScraper")

    # Load progress
    progress = load_progress()
    if progress['start_time'] is None:
        progress['start_time'] = datetime.now().isoformat()
        save_progress(progress)
    else:
        print(f"\n✓ Resuming from previous session")
        print(f"  Started: {progress['start_time']}")
        print(f"  Completed: {len(progress['completed_districts'])} districts")
        print(f"  Failed: {len(progress['failed_districts'])} districts")

    # Determine which districts to scrape
    completed = set(progress['completed_districts'])
    failed = set(progress['failed_districts'])
    all_districts = set(DISTRICTS.keys())
    remaining = all_districts - completed - failed

    if not remaining:
        print("\n✓ All districts already processed!")
        print("  Proceeding to consolidation...")
    else:
        print(f"\n📋 Districts remaining: {len(remaining)}")
        print(f"   {sorted(remaining)}")

        # Scrape remaining districts
        for i, district_num in enumerate(sorted(remaining), 1):
            district_info = DISTRICTS[district_num]

            print(f"\n[{i}/{len(remaining)}] Processing District {district_num}...")

            try:
                # Scrape district
                pharmacies = scrape_district(district_num, district_info, scraper)

                # Save results
                save_district_results(district_num, pharmacies, district_info['name'])

                # Update progress
                progress['completed_districts'].append(district_num)
                save_progress(progress)

                print(f"  ✓ District {district_num} completed successfully")

            except KeyboardInterrupt:
                print(f"\n\n⚠ Interrupted by user")
                print(f"  Progress saved. Run again to resume from District {district_num}")
                save_progress(progress)
                sys.exit(0)

            except Exception as e:
                print(f"  ✗ District {district_num} failed: {e}")
                progress['failed_districts'].append(district_num)
                save_progress(progress)
                continue

            # Rate limiting between districts
            if i < len(remaining):
                time.sleep(1)

    # Consolidate all results
    consolidate_results()

    # Final summary
    print(f"\n{'='*60}")
    print("SCRAPING COMPLETED!")
    print(f"{'='*60}")
    print(f"Completed: {len(progress['completed_districts'])} districts")
    print(f"Failed: {len(progress['failed_districts'])} districts")
    if progress['failed_districts']:
        print(f"Failed districts: {sorted(progress['failed_districts'])}")
    print(f"\nOutput files:")
    print(f"  - Individual CSVs: {DATA_DIR}/district_XX_pharmacies.csv")
    print(f"  - Consolidated: {CONSOLIDATED_CSV}")
    print(f"  - Progress: {PROGRESS_FILE}")


if __name__ == '__main__':
    main()
