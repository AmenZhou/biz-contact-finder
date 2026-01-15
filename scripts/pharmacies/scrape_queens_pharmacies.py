#!/usr/bin/env python3
"""
Scrape pharmacies in Queens, NY using Google Places API.

This script searches for pharmacies across Queens using a grid-based approach
to ensure comprehensive coverage. It uses Queens neighborhood centers as
search points and combines nearby search with text search for major chains.
"""

import csv
import json
import sys
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scrapers.pharmacy_scraper import PharmacyScraper
from config.settings import GOOGLE_PLACES_API_KEY
from utils.logger import setup_logger

logger = setup_logger('queens_pharmacies')

# Queens neighborhood centers for comprehensive coverage
QUEENS_SEARCH_AREAS = [
    # Western Queens
    {"name": "Astoria", "lat": 40.7644, "lng": -73.9235},
    {"name": "Long Island City", "lat": 40.7447, "lng": -73.9485},
    {"name": "Sunnyside", "lat": 40.7433, "lng": -73.9196},
    {"name": "Woodside", "lat": 40.7456, "lng": -73.9054},
    {"name": "Jackson Heights", "lat": 40.7557, "lng": -73.8831},
    {"name": "Elmhurst", "lat": 40.7362, "lng": -73.8778},
    {"name": "Corona", "lat": 40.7470, "lng": -73.8620},
    {"name": "Rego Park", "lat": 40.7264, "lng": -73.8610},
    {"name": "Forest Hills", "lat": 40.7185, "lng": -73.8448},
    {"name": "Middle Village", "lat": 40.7177, "lng": -73.8819},
    {"name": "Glendale", "lat": 40.7019, "lng": -73.8827},
    {"name": "Ridgewood", "lat": 40.7006, "lng": -73.9066},
    {"name": "Maspeth", "lat": 40.7226, "lng": -73.9122},

    # Central Queens
    {"name": "Flushing", "lat": 40.7631, "lng": -73.8333},
    {"name": "Murray Hill", "lat": 40.7640, "lng": -73.8187},
    {"name": "Whitestone", "lat": 40.7947, "lng": -73.8153},
    {"name": "College Point", "lat": 40.7865, "lng": -73.8465},
    {"name": "Fresh Meadows", "lat": 40.7333, "lng": -73.7944},
    {"name": "Kew Gardens", "lat": 40.7069, "lng": -73.8309},
    {"name": "Kew Gardens Hills", "lat": 40.7278, "lng": -73.8226},
    {"name": "Briarwood", "lat": 40.7091, "lng": -73.8177},
    {"name": "Jamaica", "lat": 40.6917, "lng": -73.8073},
    {"name": "Jamaica Estates", "lat": 40.7194, "lng": -73.7839},
    {"name": "Hollis", "lat": 40.7119, "lng": -73.7626},
    {"name": "Queens Village", "lat": 40.7269, "lng": -73.7415},
    {"name": "Bayside", "lat": 40.7682, "lng": -73.7772},
    {"name": "Douglaston", "lat": 40.7644, "lng": -73.7475},
    {"name": "Little Neck", "lat": 40.7631, "lng": -73.7312},

    # Southern Queens
    {"name": "Richmond Hill", "lat": 40.7003, "lng": -73.8312},
    {"name": "South Ozone Park", "lat": 40.6747, "lng": -73.8117},
    {"name": "Ozone Park", "lat": 40.6789, "lng": -73.8496},
    {"name": "Woodhaven", "lat": 40.6896, "lng": -73.8580},
    {"name": "Howard Beach", "lat": 40.6586, "lng": -73.8419},
    {"name": "South Richmond Hill", "lat": 40.6893, "lng": -73.8196},
    {"name": "St. Albans", "lat": 40.6895, "lng": -73.7608},
    {"name": "Springfield Gardens", "lat": 40.6642, "lng": -73.7616},
    {"name": "Rosedale", "lat": 40.6627, "lng": -73.7357},
    {"name": "Laurelton", "lat": 40.6695, "lng": -73.7449},

    # Rockaways
    {"name": "Far Rockaway", "lat": 40.6056, "lng": -73.7556},
    {"name": "Rockaway Park", "lat": 40.5808, "lng": -73.8375},
    {"name": "Arverne", "lat": 40.5911, "lng": -73.7941},
    {"name": "Belle Harbor", "lat": 40.5747, "lng": -73.8494},
]

# Major pharmacy chains to search for
PHARMACY_CHAINS = [
    "CVS",
    "Walgreens",
    "Duane Reade",
    "Rite Aid",
    "Costco Pharmacy",
]

# Queens approximate bounds
QUEENS_BOUNDS = {
    'north': 40.8,
    'south': 40.54,
    'east': -73.70,
    'west': -73.96,
}

def load_progress(progress_file):
    """Load scraping progress from JSON file."""
    if progress_file.exists():
        with open(progress_file, 'r') as f:
            return json.load(f)
    return {'completed_areas': [], 'completed_chains': [], 'last_updated': None}

def save_progress(progress_file, progress):
    """Save scraping progress to JSON file."""
    progress['last_updated'] = datetime.now().isoformat()
    with open(progress_file, 'w') as f:
        json.dump(progress, f, indent=2)

def main():
    # Setup paths
    project_root = Path(__file__).parent.parent.parent
    data_dir = project_root / "data" / "pharmacies"
    data_dir.mkdir(parents=True, exist_ok=True)

    output_file = data_dir / "queens_pharmacies.csv"
    progress_file = data_dir / "queens_scraping_progress.json"

    logger.info("=" * 70)
    logger.info("QUEENS PHARMACY SCRAPER")
    logger.info("=" * 70)
    logger.info(f"Output file: {output_file}")
    logger.info(f"Progress file: {progress_file}")

    # Initialize scraper
    scraper = PharmacyScraper(GOOGLE_PLACES_API_KEY)
    if not scraper.client:
        logger.error("Failed to initialize Google Places client. Check API key.")
        sys.exit(1)

    # Load progress
    progress = load_progress(progress_file)
    logger.info(f"Loaded progress: {len(progress['completed_areas'])} areas, {len(progress['completed_chains'])} chains completed")

    # Track all pharmacies by place_id to avoid duplicates
    all_pharmacies = {}

    # Load existing data if present
    if output_file.exists():
        logger.info(f"Loading existing data from {output_file}")
        with open(output_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                place_id = row.get('place_id')
                if place_id:
                    all_pharmacies[place_id] = row
        logger.info(f"Loaded {len(all_pharmacies)} existing pharmacies")

    # Phase 1: Nearby search for each neighborhood
    logger.info("\n" + "=" * 70)
    logger.info("PHASE 1: Neighborhood-based search")
    logger.info("=" * 70)

    for area in QUEENS_SEARCH_AREAS:
        area_key = f"area_{area['name']}"
        if area_key in progress['completed_areas']:
            logger.info(f"✓ Skipping {area['name']} (already completed)")
            continue

        logger.info(f"\nSearching {area['name']}...")

        # Search with 2km radius to cover the neighborhood
        results = scraper.search_pharmacies_in_area(
            center_lat=area['lat'],
            center_lng=area['lng'],
            radius_meters=2000,
            keyword="pharmacy",
            bounds=QUEENS_BOUNDS
        )

        logger.info(f"  Found {len(results)} pharmacies in {area['name']}")

        # Add to collection
        for pharmacy in results:
            place_id = pharmacy.get('place_id')
            if place_id and place_id not in all_pharmacies:
                pharmacy['search_area'] = area['name']
                pharmacy['search_method'] = 'nearby'
                all_pharmacies[place_id] = pharmacy

        # Mark as completed
        progress['completed_areas'].append(area_key)
        save_progress(progress_file, progress)

        # Rate limiting
        time.sleep(1)

    # Phase 2: Text search for major chains
    logger.info("\n" + "=" * 70)
    logger.info("PHASE 2: Chain pharmacy search")
    logger.info("=" * 70)

    for chain in PHARMACY_CHAINS:
        chain_key = f"chain_{chain}"
        if chain_key in progress['completed_chains']:
            logger.info(f"✓ Skipping {chain} (already completed)")
            continue

        logger.info(f"\nSearching for {chain} in Queens...")

        # Use the center of Queens for text search
        queens_center_lat = 40.7282
        queens_center_lng = -73.7949

        results = scraper.search_pharmacies_text(
            query=f"{chain} pharmacy Queens NY",
            location_bias=(queens_center_lat, queens_center_lng),
            bounds=QUEENS_BOUNDS
        )

        logger.info(f"  Found {len(results)} {chain} locations")

        # Add to collection
        new_count = 0
        for pharmacy in results:
            place_id = pharmacy.get('place_id')
            if place_id and place_id not in all_pharmacies:
                pharmacy['search_area'] = 'Queens (chain search)'
                pharmacy['search_method'] = f'text_search_{chain}'
                all_pharmacies[place_id] = pharmacy
                new_count += 1

        logger.info(f"  Added {new_count} new {chain} locations")

        # Mark as completed
        progress['completed_chains'].append(chain_key)
        save_progress(progress_file, progress)

        # Rate limiting
        time.sleep(1)

    # Export to CSV
    logger.info("\n" + "=" * 70)
    logger.info("EXPORT RESULTS")
    logger.info("=" * 70)

    if all_pharmacies:
        fieldnames = [
            'search_area', 'search_method', 'name', 'address', 'phone',
            'website', 'google_maps_url', 'business_status', 'is_open_now',
            'hours', 'latitude', 'longitude', 'place_id', 'types'
        ]

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            # Sort by name for better readability
            sorted_pharmacies = sorted(all_pharmacies.values(), key=lambda x: x.get('name', ''))
            writer.writerows(sorted_pharmacies)

        logger.info(f"✓ Exported {len(all_pharmacies)} unique pharmacies to {output_file}")
    else:
        logger.warning("No pharmacies found!")

    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("SCRAPING COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Total unique pharmacies: {len(all_pharmacies)}")
    logger.info(f"Search areas completed: {len(progress['completed_areas'])}/{len(QUEENS_SEARCH_AREAS)}")
    logger.info(f"Chain searches completed: {len(progress['completed_chains'])}/{len(PHARMACY_CHAINS)}")
    logger.info("=" * 70)

if __name__ == "__main__":
    main()
