#!/usr/bin/env python3
"""
Scrape Community Facilities in Massachusetts using HERE API with Category Filtering
Searches for: Town Halls, Schools, Supermarkets, Building Offices, Law Offices,
Clinical Offices, Universities, Senior Centers, Libraries

Uses HERE category codes to ensure accurate facility type classification.
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

import pandas as pd

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "ma_facilities"
OUTPUT_CSV = DATA_DIR / "ma_facilities.csv"
PROGRESS_FILE = DATA_DIR / "scraping_progress.json"

# API Configuration
HERE_API_KEY = os.getenv("HERE_API_KEY")

if not HERE_API_KEY:
    print("Error: HERE_API_KEY environment variable not set")
    print("   Get your API key from: https://platform.here.com/")
    sys.exit(1)

# Massachusetts zip codes (with leading 0)
ZIP_CODES = [
    "02048", "02330", "02346", "02347", "02532", "02538", "02558",
    "02571", "02576", "02702", "02703", "02715", "02717", "02725",
    "02726", "02743", "02760", "02764", "02767", "02769", "02777",
    "02779", "02771"
]

# Facility type configurations with HERE category codes
# Category codes are used to filter and validate results
FACILITY_TYPES = {
    "town_hall": {
        "search_terms": ["town hall", "city hall"],
        "category_filter": "800-8100",  # Government/Civic
        "valid_categories": {"800-8100-0163", "800-8100-0171", "800-8100-0000"},  # City Hall, Government Office
        "valid_keywords": {"town hall", "city hall", "municipal", "borough hall", "government"}
    },
    "school": {
        "search_terms": ["elementary school", "middle school", "high school", "public school"],
        "category_filter": "800-8200",  # Education
        "valid_categories": {"800-8200-0000", "800-8250-0287", "800-8250-0288", "800-8250-0289", "800-8250-0000"},
        "valid_keywords": {"school", "elementary", "middle school", "high school", "academy", "preparatory"}
    },
    "supermarket": {
        "search_terms": ["supermarket", "grocery store"],
        "category_filter": "600-6300",  # Food/Grocery
        "valid_categories": {"600-6300-0066", "600-6300-0067", "600-6300-0064", "600-6300-0000"},  # Grocery, Supermarket
        "valid_keywords": {"supermarket", "grocery", "market", "food mart", "stop & shop", "shaw", "market basket", "trader joe", "whole foods", "aldi", "walmart", "target"}
    },
    "building_office": {
        "search_terms": ["office building", "business center"],
        "category_filter": "700-7400",  # Business Services
        "valid_categories": {"700-7400-0000", "700-7400-0285", "700-7450-0000"},
        "valid_keywords": {"office", "business center", "corporate", "commercial", "plaza"}
    },
    "law_office": {
        "search_terms": ["law office", "attorney", "law firm"],
        "category_filter": "700-7400-0138",  # Attorney
        "valid_categories": {"700-7400-0138", "700-7400-0327"},  # Attorney, Legal Services
        "valid_keywords": {"law", "attorney", "lawyer", "legal", "firm", "esq", "llp", "pllc"}
    },
    "clinical_office": {
        "search_terms": ["medical clinic", "doctor office", "healthcare center", "physician"],
        "category_filter": "800-8000",  # Health/Medical
        "valid_categories": {"800-8000-0158", "800-8000-0159", "800-8000-0000", "800-8000-0154", "800-8000-0156"},
        "valid_keywords": {"clinic", "medical", "doctor", "physician", "healthcare", "health center", "urgent care", "family practice", "pediatric"}
    },
    "university": {
        "search_terms": ["university", "college"],
        "category_filter": "800-8200-0173",  # Higher Education
        "valid_categories": {"800-8200-0173", "800-8200-0174"},  # Higher Education, College
        "valid_keywords": {"university", "college", "community college", "institute", "school of"}
    },
    "senior_center": {
        "search_terms": ["senior center", "council on aging"],
        "category_filter": "700-7400-0147",  # Social Services
        "valid_categories": {"700-7400-0147", "800-8100-0000"},
        "valid_keywords": {"senior", "elderly", "aging", "older adult", "retirement"}
    },
    "library": {
        "search_terms": ["public library", "library"],
        "category_filter": "800-8300-0175",  # Library
        "valid_categories": {"800-8300-0175", "800-8300-0000"},
        "valid_keywords": {"library", "public library"}
    }
}


def geocode_zipcode(zipcode: str) -> tuple:
    """
    Get coordinates for a zip code using HERE Geocoding API
    Returns (latitude, longitude) or (None, None) if not found
    """
    url = "https://geocode.search.hereapi.com/v1/geocode"
    params = {
        "q": f"{zipcode}, Massachusetts, USA",
        "apiKey": HERE_API_KEY
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if "items" in data and len(data["items"]) > 0:
            position = data["items"][0].get("position", {})
            return position.get("lat"), position.get("lng")
    except Exception as e:
        print(f"   Warning: Geocoding error for {zipcode}: {e}")

    return None, None


def is_valid_facility(item: Dict, facility_config: Dict) -> bool:
    """
    Validate if the returned item matches the expected facility type
    Uses category codes and keyword matching
    """
    # Check categories
    item_categories = set()
    if "categories" in item:
        for cat in item["categories"]:
            cat_id = cat.get("id", "")
            item_categories.add(cat_id)
            # Also add parent category (first 7 chars)
            if len(cat_id) >= 7:
                item_categories.add(cat_id[:7])
            if len(cat_id) >= 3:
                item_categories.add(cat_id[:3])

    valid_cats = facility_config.get("valid_categories", set())

    # Check if any category matches
    if item_categories & valid_cats:
        return True

    # Fallback: Check keywords in name
    name = item.get("title", "").lower()
    valid_keywords = facility_config.get("valid_keywords", set())

    for keyword in valid_keywords:
        if keyword in name:
            return True

    return False


def search_here_discover(query: str, lat: float, lng: float, facility_config: Dict, radius: int = 15000) -> List[Dict]:
    """
    Search using HERE Discover API with category filtering
    Returns list of validated places found
    """
    url = "https://discover.search.hereapi.com/v1/discover"

    # Build params with category filter if available
    params = {
        "q": query,
        "in": f"circle:{lat},{lng};r={radius}",
        "limit": 20,
        "apiKey": HERE_API_KEY
    }

    facilities = []

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if "items" in data:
            for item in data["items"]:
                # Validate facility type
                if not is_valid_facility(item, facility_config):
                    continue

                # Parse address
                addr_parts = []
                if "address" in item:
                    addr = item["address"]
                    if addr.get("houseNumber"):
                        addr_parts.append(addr["houseNumber"])
                    if addr.get("street"):
                        addr_parts.append(addr["street"])
                    if addr.get("city"):
                        addr_parts.append(addr["city"])
                    if addr.get("stateCode"):
                        addr_parts.append(addr["stateCode"])
                    if addr.get("postalCode"):
                        addr_parts.append(addr["postalCode"])

                address = ", ".join(addr_parts) if addr_parts else ""

                # Parse phone
                phone = ""
                if "contacts" in item:
                    contacts = item["contacts"]
                    if contacts and len(contacts) > 0:
                        contact = contacts[0]
                        if "phone" in contact and len(contact["phone"]) > 0:
                            phone = contact["phone"][0].get("value", "")

                # Parse website
                website = ""
                if "contacts" in item:
                    contacts = item["contacts"]
                    if contacts and len(contacts) > 0:
                        contact = contacts[0]
                        if "www" in contact and len(contact["www"]) > 0:
                            website = contact["www"][0].get("value", "")

                # Get coordinates
                position = item.get("position", {})

                # Get opening hours if available
                hours = ""
                if "openingHours" in item:
                    opening_hours = item["openingHours"]
                    if opening_hours and len(opening_hours) > 0:
                        hours_text = opening_hours[0].get("text", [])
                        if hours_text:
                            hours = "; ".join(hours_text)

                # Get primary category name
                category_name = ""
                if "categories" in item and len(item["categories"]) > 0:
                    category_name = item["categories"][0].get("name", "")

                facility = {
                    "name": item.get("title", ""),
                    "address": address,
                    "phone": phone,
                    "email": "",
                    "website": website,
                    "rating": "",
                    "reviews": "",
                    "latitude": position.get("lat", ""),
                    "longitude": position.get("lng", ""),
                    "business_hours": hours,
                    "here_category": category_name,
                    "source": "here_discover",
                    "search_query": query,
                    "found_date": datetime.now().isoformat()
                }
                facilities.append(facility)

    except Exception as e:
        print(f"   Warning: HERE API error: {e}")

    return facilities


def load_progress() -> Dict:
    """Load scraping progress from file"""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {
        'completed_searches': [],
        'zip_coords': {},
        'last_zip': '',
        'last_facility_type': '',
        'total_found': 0
    }


def save_progress(progress: Dict):
    """Save scraping progress to file"""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)


def deduplicate_facilities(facilities: List[Dict]) -> List[Dict]:
    """Remove duplicate facilities based on name and location"""
    seen = set()
    unique_facilities = []

    for facility in facilities:
        # Create a key from name and rough location
        name = facility['name'].lower().strip()
        # Use first part of address or location for deduplication
        location_key = facility.get('address', facility.get('location', '')).lower()[:50]
        key = f"{name}|{location_key}"

        if key not in seen:
            seen.add(key)
            unique_facilities.append(facility)

    return unique_facilities


def main():
    """Main execution"""
    print("=" * 80)
    print("SCRAPING MASSACHUSETTS FACILITIES (HERE API + CATEGORY FILTERING)")
    print("=" * 80)
    print()
    print(f"Target zip codes: {len(ZIP_CODES)}")
    print(f"Facility types: {len(FACILITY_TYPES)}")
    print()

    # Create output directory
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Load progress
    progress = load_progress()
    print(f"Loaded progress: {len(progress['completed_searches'])} searches completed")
    print()

    all_facilities = []

    # Load existing data if available
    if OUTPUT_CSV.exists():
        existing_df = pd.read_csv(OUTPUT_CSV)
        all_facilities = existing_df.to_dict('records')
        print(f"Loaded {len(all_facilities)} existing facilities from {OUTPUT_CSV}")
        print()

    # First, geocode all zip codes if not already cached
    print("Geocoding zip codes...")
    zip_coords = progress.get('zip_coords', {})
    for zipcode in ZIP_CODES:
        if zipcode not in zip_coords:
            lat, lng = geocode_zipcode(zipcode)
            if lat and lng:
                zip_coords[zipcode] = {"lat": lat, "lng": lng}
                print(f"  {zipcode}: {lat}, {lng}")
            else:
                print(f"  {zipcode}: Could not geocode")
            time.sleep(0.3)

    progress['zip_coords'] = zip_coords
    save_progress(progress)
    print()

    # Calculate total searches
    total_search_terms = sum(len(config['search_terms']) for config in FACILITY_TYPES.values())
    total_searches = total_search_terms * len(ZIP_CODES)
    current_search = 0

    # Iterate through facility types and zip codes
    for facility_type, config in FACILITY_TYPES.items():
        print(f"\n{'='*80}")
        print(f"Searching for: {facility_type.upper().replace('_', ' ')}")
        print(f"Category filter: {config.get('category_filter', 'none')}")
        print(f"{'='*80}\n")

        for zipcode in ZIP_CODES:
            # Get coordinates for this zip code
            coords = zip_coords.get(zipcode)
            if not coords:
                print(f"  Skipping {zipcode}: no coordinates available")
                continue

            lat, lng = coords["lat"], coords["lng"]

            for search_term in config['search_terms']:
                current_search += 1
                search_key = f"{facility_type}|{zipcode}|{search_term}"

                # Skip if already completed
                if search_key in progress['completed_searches']:
                    continue

                print(f"[{current_search}/{total_searches}] Searching: {search_term} in {zipcode}")

                # Search using HERE Discover API with validation
                results = search_here_discover(search_term, lat, lng, config)

                if results:
                    print(f"   Found {len(results)} validated results")
                    # Add facility type and zip code to each result
                    for result in results:
                        result['facility_type'] = facility_type
                        result['zip_code'] = zipcode
                        result['location'] = f"{zipcode}, MA"
                    all_facilities.extend(results)
                else:
                    print(f"   No validated results")

                # Mark as completed
                progress['completed_searches'].append(search_key)
                progress['last_zip'] = zipcode
                progress['last_facility_type'] = facility_type
                progress['total_found'] = len(all_facilities)

                # Save progress every 10 searches
                if current_search % 10 == 0:
                    unique_facilities = deduplicate_facilities(all_facilities)
                    df = pd.DataFrame(unique_facilities)
                    df.to_csv(OUTPUT_CSV, index=False)
                    save_progress(progress)
                    print(f"\n  Progress saved: {len(unique_facilities)} unique facilities")
                    print()

                # Rate limiting
                time.sleep(0.5)

    # Final save with deduplication
    print("\n" + "="*80)
    print("Deduplicating facilities...")
    unique_facilities = deduplicate_facilities(all_facilities)

    # Fix zip codes to have leading zeros
    for facility in unique_facilities:
        if 'zip_code' in facility:
            facility['zip_code'] = str(facility['zip_code']).zfill(5)

    df = pd.DataFrame(unique_facilities)
    df.to_csv(OUTPUT_CSV, index=False)
    save_progress(progress)

    print()
    print("="*80)
    print("SCRAPING COMPLETE (WITH CATEGORY VALIDATION)")
    print("="*80)
    print(f"Output File: {OUTPUT_CSV}")
    print()
    print(f"Total facilities found: {len(all_facilities)}")
    print(f"Unique facilities: {len(unique_facilities)}")
    print()

    # Breakdown by facility type
    print("Breakdown by facility type:")
    if len(unique_facilities) > 0:
        type_counts = df['facility_type'].value_counts()
        for facility_type, count in type_counts.items():
            print(f"  {facility_type}: {count}")

    # Breakdown by zip code
    print()
    print("Breakdown by zip code:")
    if len(unique_facilities) > 0:
        zip_counts = df['zip_code'].value_counts().head(10)
        for zipcode, count in zip_counts.items():
            print(f"  {zipcode}: {count}")
        if len(df['zip_code'].unique()) > 10:
            print(f"  ... and {len(df['zip_code'].unique()) - 10} more zip codes")

    print("="*80)


if __name__ == "__main__":
    main()
