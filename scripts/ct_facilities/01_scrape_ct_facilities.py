#!/usr/bin/env python3
"""
Scrape Community Facilities in Connecticut Target Area
Searches for: Senior Centers, City Halls, Community Centers, and Colleges
"""

import os
import sys
import json
import time
import requests
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

import pandas as pd

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "ct_facilities"
BOUNDARY_FILE = PROJECT_ROOT / "data" / "ct_target_area_boundary.json"
OUTPUT_CSV = DATA_DIR / "ct_facilities.csv"
PROGRESS_FILE = DATA_DIR / "scraping_progress.json"

# API Configuration
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

if not SERPER_API_KEY:
    print("❌ Error: SERPER_API_KEY environment variable not set")
    sys.exit(1)

# Connecticut towns in the Hartford area (Central CT)
CT_TOWNS = [
    # Hartford County
    "Hartford, CT", "West Hartford, CT", "East Hartford, CT",
    "Manchester, CT", "Glastonbury, CT", "Newington, CT",
    "Wethersfield, CT", "Windsor, CT", "Bloomfield, CT",
    "South Windsor, CT", "Rocky Hill, CT", "Cromwell, CT",
    "Berlin, CT", "Farmington, CT", "Avon, CT",
    "Simsbury, CT", "Canton, CT", "Granby, CT",
    "Enfield, CT", "Suffield, CT", "East Windsor, CT",
    "Windsor Locks, CT", "Plainville, CT", "Bristol, CT"
]

# Facility type configurations
FACILITY_TYPES = {
    "senior_center": {
        "search_terms": [
            "senior center",
            "senior citizens center",
            "elderly care center",
            "senior services"
        ]
    },
    "city_hall": {
        "search_terms": [
            "city hall",
            "town hall",
            "municipal building",
            "town office"
        ]
    },
    "community_center": {
        "search_terms": [
            "community center",
            "recreation center",
            "civic center",
            "community recreation"
        ]
    },
    "college": {
        "search_terms": [
            "college",
            "university",
            "community college",
            "technical college"
        ]
    }
}


def search_serper(query: str, location: str = "Connecticut") -> List[Dict]:
    """
    Search using Serper API
    Returns both Maps and Organic results
    """
    facilities = []

    # Try Maps API first
    url = "https://google.serper.dev/maps"
    payload = {
        "q": query,
        "location": location,
        "gl": "us",
        "hl": "en"
    }
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Process places from Maps API
        if "places" in data:
            for place in data["places"]:
                facility = {
                    "name": place.get("title", ""),
                    "address": place.get("address", ""),
                    "phone": place.get("phoneNumber", ""),
                    "email": "",
                    "website": place.get("website", ""),
                    "rating": place.get("rating", ""),
                    "reviews": place.get("ratingCount", ""),
                    "latitude": place.get("latitude", ""),
                    "longitude": place.get("longitude", ""),
                    "business_hours": place.get("openingHours", ""),
                    "source": "serper_maps",
                    "search_query": query,
                    "location": location,
                    "found_date": datetime.now().isoformat()
                }
                facilities.append(facility)

        # Also try organic search for more results
        time.sleep(0.5)
        url = "https://google.serper.dev/search"
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        if "organic" in data:
            for result in data["organic"][:5]:  # Limit organic results
                facility = {
                    "name": result.get("title", ""),
                    "address": result.get("snippet", ""),
                    "phone": "",
                    "email": "",
                    "website": result.get("link", ""),
                    "rating": "",
                    "reviews": "",
                    "latitude": "",
                    "longitude": "",
                    "business_hours": "",
                    "source": "serper_organic",
                    "search_query": query,
                    "location": location,
                    "found_date": datetime.now().isoformat()
                }
                facilities.append(facility)

    except Exception as e:
        print(f"   ⚠️  Serper API error: {e}")

    return facilities


def is_relevant_facility(name: str, facility_type: str) -> bool:
    """Check if facility name is relevant and not an aggregator"""
    name_lower = name.lower()

    # Filter out aggregator keywords
    aggregator_keywords = [
        'yelp', 'yellow pages', 'find', 'directory', 'list of',
        'best', 'top', 'reviews', 'comparison', 'guide',
        'indeed', 'linkedin', 'facebook', 'twitter',
        'mapquest', 'google maps'
    ]

    for keyword in aggregator_keywords:
        if keyword in name_lower:
            return False

    # Type-specific validation
    if facility_type == "senior_center":
        relevant = any(kw in name_lower for kw in ['senior', 'elderly', 'aging'])
    elif facility_type == "city_hall":
        relevant = any(kw in name_lower for kw in ['hall', 'municipal', 'town', 'city'])
    elif facility_type == "community_center":
        relevant = any(kw in name_lower for kw in ['community', 'recreation', 'civic', 'center'])
    elif facility_type == "college":
        relevant = any(kw in name_lower for kw in ['college', 'university', 'institute', 'school'])
    else:
        relevant = True

    return relevant


def deduplicate_facilities(facilities: List[Dict]) -> List[Dict]:
    """Remove duplicate facilities based on name and address"""
    seen = set()
    unique_facilities = []

    for facility in facilities:
        # Create a key from name and first part of address
        name = facility.get('name', '').strip().lower()
        address = facility.get('address', '').strip().lower()
        key = f"{name}|{address[:50]}"

        if key not in seen and name:
            seen.add(key)
            unique_facilities.append(facility)

    return unique_facilities


def load_progress() -> Dict:
    """Load scraping progress from JSON file"""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_progress(progress: Dict):
    """Save scraping progress to JSON file"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)


def main():
    """Main scraping execution"""
    print("=" * 80)
    print("CONNECTICUT COMMUNITY FACILITIES SCRAPER")
    print("=" * 80)
    print()

    # Load existing progress
    progress = load_progress()
    completed_searches = set(progress.get('completed_searches', []))
    all_facilities = progress.get('facilities', {})

    if all_facilities:
        print(f"📊 Progress: {len(completed_searches)} searches completed, {len(all_facilities)} facilities found")
        print()

    # Generate all search combinations
    searches = []
    for town in CT_TOWNS:
        for facility_type, config in FACILITY_TYPES.items():
            for search_term in config["search_terms"]:
                query = f"{search_term} {town}"
                if query not in completed_searches:
                    searches.append((query, town, facility_type, search_term))

    total_searches = len(searches) + len(completed_searches)
    print(f"🔍 Total searches: {total_searches}")
    print(f"⏳ Remaining: {len(searches)}")
    print()

    # Perform searches
    for idx, (query, town, facility_type, search_term) in enumerate(searches, 1):
        print(f"[{idx}/{len(searches)}] Searching: '{search_term}' in {town}")

        facilities = search_serper(query, town)

        # Filter relevant facilities
        relevant_count = 0
        for facility in facilities:
            if is_relevant_facility(facility['name'], facility_type):
                # Add facility type
                facility['facility_type'] = facility_type

                # Use name|address as unique key
                key = f"{facility['name']}|{facility.get('address', '')}"
                all_facilities[key] = facility
                relevant_count += 1

        print(f"   ✓ Found {relevant_count} relevant facilities")

        # Mark search as completed
        completed_searches.add(query)

        # Rate limiting
        time.sleep(0.5)

        # Save progress every 10 searches
        if idx % 10 == 0:
            progress['completed_searches'] = list(completed_searches)
            progress['facilities'] = all_facilities
            progress['last_updated'] = datetime.now().isoformat()
            save_progress(progress)
            print(f"   💾 Progress saved ({len(all_facilities)} total facilities)")

    # Final save
    progress['completed_searches'] = list(completed_searches)
    progress['facilities'] = all_facilities
    progress['last_updated'] = datetime.now().isoformat()
    save_progress(progress)

    print()
    print("=" * 80)
    print("CONVERTING TO CSV")
    print("=" * 80)
    print()

    # Convert to DataFrame
    facilities_list = list(all_facilities.values())
    df = pd.DataFrame(facilities_list)

    # Deduplicate
    initial_count = len(df)
    facilities_list = deduplicate_facilities(facilities_list)
    df = pd.DataFrame(facilities_list)
    print(f"   Removed {initial_count - len(df)} duplicates")

    # Reorder columns
    columns = [
        'name', 'facility_type', 'address', 'phone', 'email', 'website',
        'business_hours', 'rating', 'reviews', 'latitude', 'longitude',
        'source', 'search_query', 'location', 'found_date'
    ]
    df = df[columns]

    # Save to CSV
    df.to_csv(OUTPUT_CSV, index=False)

    print()
    print("=" * 80)
    print("✅ SCRAPING COMPLETE")
    print("=" * 80)
    print(f"Output File: {OUTPUT_CSV}")
    print()
    print(f"Total facilities: {len(df)}")
    print("\nBy facility type:")
    for facility_type in df['facility_type'].unique():
        count = len(df[df['facility_type'] == facility_type])
        print(f"  {facility_type}: {count}")
    print()
    print(f"With phone: {df['phone'].astype(bool).sum()}")
    print(f"With address: {df['address'].astype(bool).sum()}")
    print(f"With coordinates: {df['latitude'].astype(bool).sum()}")
    print(f"With business hours: {df['business_hours'].astype(bool).sum()}")
    print("=" * 80)


if __name__ == "__main__":
    main()
