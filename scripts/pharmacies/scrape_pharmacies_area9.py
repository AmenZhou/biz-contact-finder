#!/usr/bin/env python3
"""
Script to scrape all pharmacies in Area #9 (Chelsea/NoMad)

Area #9 Boundaries:
- North: W 33rd-34th Street (near Penn Station)
- South: W 23rd-24th Street
- West: 7th Avenue
- East: Broadway

Geographic coordinates (approximate):
- North: 40.7505
- South: 40.7425
- West: -73.9950
- East: -73.9875
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from pathlib import Path
from datetime import datetime
import logging

from utils.logger import setup_logger
from scrapers.pharmacy_scraper import PharmacyScraper

# Setup logging
logger = setup_logger()

# Area #9 boundaries (Chelsea/NoMad)
AREA_9_BOUNDS = {
    'north': 40.7505,   # ~34th Street
    'south': 40.7425,   # ~23rd Street
    'west': -73.9950,   # ~7th Avenue
    'east': -73.9875    # ~Broadway
}

# Center point of Area #9
AREA_9_CENTER = (
    (AREA_9_BOUNDS['north'] + AREA_9_BOUNDS['south']) / 2,
    (AREA_9_BOUNDS['east'] + AREA_9_BOUNDS['west']) / 2
)

# Output file
OUTPUT_FILE = 'data/area9_pharmacies.csv'


def main():
    """Main function to scrape pharmacies in Area #9"""
    logger.info("=" * 60)
    logger.info("PHARMACY SCRAPER - AREA #9 (Chelsea/NoMad)")
    logger.info("=" * 60)
    logger.info(f"Boundaries:")
    logger.info(f"  North: {AREA_9_BOUNDS['north']} (~34th St)")
    logger.info(f"  South: {AREA_9_BOUNDS['south']} (~23rd St)")
    logger.info(f"  West: {AREA_9_BOUNDS['west']} (~7th Ave)")
    logger.info(f"  East: {AREA_9_BOUNDS['east']} (~Broadway)")
    logger.info(f"  Center: {AREA_9_CENTER}")
    logger.info("=" * 60)

    # Initialize scraper
    scraper = PharmacyScraper()

    if not scraper.client:
        logger.error("Failed to initialize scraper. Check GOOGLE_PLACES_API_KEY.")
        return

    # Method 1: Grid search for comprehensive coverage
    logger.info("\nMethod 1: Grid search for comprehensive coverage...")
    pharmacies_grid = scraper.search_area_grid(
        bounds=AREA_9_BOUNDS,
        grid_size=3,  # 3x3 grid
        keyword="pharmacy"
    )

    # Method 2: Text search for additional coverage
    logger.info("\nMethod 2: Text search for additional matches...")
    search_queries = [
        "pharmacy Chelsea Manhattan NYC",
        "pharmacy NoMad Manhattan NYC",
        "drugstore 28th Street Manhattan",
        "CVS pharmacy Chelsea",
        "Walgreens Chelsea Manhattan",
        "Duane Reade Chelsea Manhattan",
        "Rite Aid Chelsea Manhattan"
    ]

    pharmacies_text = []
    for query in search_queries:
        results = scraper.search_pharmacies_text(
            query=query,
            location_bias=AREA_9_CENTER,
            bounds=AREA_9_BOUNDS  # Pass bounds to filter results early
        )
        pharmacies_text.extend(results)

    # Combine and deduplicate results (both methods already filter by bounds)
    all_pharmacies = {}

    # Add grid results (already filtered by bounds)
    for pharmacy in pharmacies_grid:
        place_id = pharmacy.get('place_id')
        if place_id:
            all_pharmacies[place_id] = pharmacy

    # Add text search results (already filtered by bounds)
    for pharmacy in pharmacies_text:
        place_id = pharmacy.get('place_id')
        if place_id and place_id not in all_pharmacies:
            all_pharmacies[place_id] = pharmacy

    # All results are already filtered by bounds in the scraper methods
    filtered_pharmacies = list(all_pharmacies.values())

    logger.info(f"\n{'=' * 60}")
    logger.info(f"RESULTS: Found {len(filtered_pharmacies)} unique pharmacies in Area #9")
    logger.info(f"{'=' * 60}")

    if not filtered_pharmacies:
        logger.warning("No pharmacies found. Check API key and search parameters.")
        return

    # Create DataFrame
    df = pd.DataFrame(filtered_pharmacies)

    # Reorder columns
    column_order = [
        'name', 'address', 'phone', 'website', 'google_maps_url',
        'rating', 'total_ratings', 'business_status',
        'is_open_now', 'hours',
        'latitude', 'longitude', 'place_id', 'types'
    ]
    column_order = [col for col in column_order if col in df.columns]
    df = df[column_order]

    # Sort by rating (descending)
    if 'rating' in df.columns:
        df = df.sort_values('rating', ascending=False, na_position='last')

    # Save to CSV
    try:
        Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(OUTPUT_FILE, index=False)
        logger.info(f"\n✓ Results saved to: {OUTPUT_FILE}")
    except Exception as e:
        logger.error(f"Failed to save CSV: {e}")
        return

    # Print summary
    logger.info(f"\n📊 SUMMARY")
    logger.info(f"{'=' * 60}")
    logger.info(f"Total pharmacies: {len(df)}")

    if 'rating' in df.columns:
        avg_rating = df['rating'].mean()
        logger.info(f"Average rating: {avg_rating:.2f}")

    if 'phone' in df.columns:
        with_phone = df['phone'].notna().sum()
        logger.info(f"With phone: {with_phone}/{len(df)}")

    if 'website' in df.columns:
        with_website = df['website'].notna().sum()
        logger.info(f"With website: {with_website}/{len(df)}")

    logger.info(f"{'=' * 60}")

    # List all pharmacies found
    logger.info(f"\nPharmacies found:")
    for idx, row in df.iterrows():
        name = row.get('name', 'Unknown')
        address = row.get('address', 'N/A')
        rating = row.get('rating', 'N/A')
        logger.info(f"  • {name}")
        logger.info(f"    Address: {address}")
        logger.info(f"    Rating: {rating}")
        logger.info("")


if __name__ == '__main__':
    main()
