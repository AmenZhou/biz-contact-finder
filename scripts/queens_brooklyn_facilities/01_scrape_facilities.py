#!/usr/bin/env python3
"""
Scrape Community Facilities in Queens and Brooklyn
Searches for: Senior Centers, Libraries, City Halls, Community Centers,
Colleges, Clubs (Golf, Yacht, etc.)
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
DATA_DIR = PROJECT_ROOT / "data" / "queens_brooklyn_facilities"
OUTPUT_CSV = DATA_DIR / "queens_brooklyn_facilities.csv"
PROGRESS_FILE = DATA_DIR / "scraping_progress.json"

# API Configuration
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

if not SERPER_API_KEY:
    print("❌ Error: SERPER_API_KEY environment variable not set")
    sys.exit(1)

# Queens and Brooklyn neighborhoods/areas
LOCATIONS = [
    # Queens
    "Queens, NY",
    "Astoria, Queens, NY",
    "Long Island City, Queens, NY",
    "Flushing, Queens, NY",
    "Jamaica, Queens, NY",
    "Forest Hills, Queens, NY",
    "Rego Park, Queens, NY",
    "Elmhurst, Queens, NY",
    "Corona, Queens, NY",
    "Jackson Heights, Queens, NY",
    "Woodside, Queens, NY",
    "Sunnyside, Queens, NY",
    "Bayside, Queens, NY",
    "Whitestone, Queens, NY",
    "Fresh Meadows, Queens, NY",
    "Kew Gardens, Queens, NY",
    "Richmond Hill, Queens, NY",
    "Ozone Park, Queens, NY",
    "Howard Beach, Queens, NY",
    "Rockaway, Queens, NY",

    # Brooklyn
    "Brooklyn, NY",
    "Williamsburg, Brooklyn, NY",
    "Greenpoint, Brooklyn, NY",
    "Bushwick, Brooklyn, NY",
    "Bedford-Stuyvesant, Brooklyn, NY",
    "Crown Heights, Brooklyn, NY",
    "Park Slope, Brooklyn, NY",
    "Prospect Heights, Brooklyn, NY",
    "Downtown Brooklyn, NY",
    "Brooklyn Heights, NY",
    "DUMBO, Brooklyn, NY",
    "Fort Greene, Brooklyn, NY",
    "Clinton Hill, Brooklyn, NY",
    "Sunset Park, Brooklyn, NY",
    "Bay Ridge, Brooklyn, NY",
    "Bensonhurst, Brooklyn, NY",
    "Borough Park, Brooklyn, NY",
    "Flatbush, Brooklyn, NY",
    "East Flatbush, Brooklyn, NY",
    "Canarsie, Brooklyn, NY",
    "Sheepshead Bay, Brooklyn, NY",
    "Brighton Beach, Brooklyn, NY",
    "Coney Island, Brooklyn, NY"
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
    "library": {
        "search_terms": [
            "public library",
            "library branch",
            "community library"
        ]
    },
    "city_hall": {
        "search_terms": [
            "city hall",
            "borough hall",
            "community board",
            "municipal building"
        ]
    },
    "community_center": {
        "search_terms": [
            "community center",
            "recreation center",
            "civic center",
            "youth center"
        ]
    },
    "college": {
        "search_terms": [
            "college",
            "university",
            "community college",
            "technical college"
        ]
    },
    "golf_club": {
        "search_terms": [
            "golf club",
            "golf course",
            "country club golf"
        ]
    },
    "yacht_club": {
        "search_terms": [
            "yacht club",
            "boat club",
            "sailing club",
            "marina club"
        ]
    },
    "social_club": {
        "search_terms": [
            "social club",
            "private club",
            "members club"
        ]
    }
}


def search_serper(query: str, location: str = "New York, NY") -> List[Dict]:
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


def load_progress() -> Dict:
    """Load scraping progress from file"""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {
        'completed_searches': [],
        'last_location': '',
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
    print("SCRAPING QUEENS & BROOKLYN COMMUNITY FACILITIES")
    print("=" * 80)
    print()

    # Create output directory
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Load progress
    progress = load_progress()
    print(f"📊 Loaded progress: {len(progress['completed_searches'])} searches completed")
    print()

    all_facilities = []

    # Load existing data if available
    if OUTPUT_CSV.exists():
        existing_df = pd.read_csv(OUTPUT_CSV)
        all_facilities = existing_df.to_dict('records')
        print(f"📂 Loaded {len(all_facilities)} existing facilities from {OUTPUT_CSV}")
        print()

    # Iterate through facility types and locations
    total_searches = len(FACILITY_TYPES) * len(LOCATIONS)
    current_search = 0

    for facility_type, config in FACILITY_TYPES.items():
        print(f"\n{'='*80}")
        print(f"🏢 Searching for: {facility_type.upper().replace('_', ' ')}")
        print(f"{'='*80}\n")

        for location in LOCATIONS:
            for search_term in config['search_terms']:
                current_search += 1
                search_key = f"{facility_type}|{location}|{search_term}"

                # Skip if already completed
                if search_key in progress['completed_searches']:
                    continue

                query = f"{search_term} {location}"
                print(f"[{current_search}/{total_searches * len(config['search_terms'])}] Searching: {query}")

                # Search
                results = search_serper(query, location)

                if results:
                    print(f"   ✓ Found {len(results)} results")
                    # Add facility type to each result
                    for result in results:
                        result['facility_type'] = facility_type
                    all_facilities.extend(results)
                else:
                    print(f"   ○ No results")

                # Mark as completed
                progress['completed_searches'].append(search_key)
                progress['last_location'] = location
                progress['last_facility_type'] = facility_type
                progress['total_found'] = len(all_facilities)

                # Save progress every 10 searches
                if current_search % 10 == 0:
                    # Deduplicate before saving
                    unique_facilities = deduplicate_facilities(all_facilities)
                    df = pd.DataFrame(unique_facilities)
                    df.to_csv(OUTPUT_CSV, index=False)
                    save_progress(progress)
                    print(f"\n  💾 Progress saved: {len(unique_facilities)} unique facilities")
                    print()

                # Rate limiting
                time.sleep(1)

    # Final save with deduplication
    print("\n" + "="*80)
    print("🔄 Deduplicating facilities...")
    unique_facilities = deduplicate_facilities(all_facilities)

    df = pd.DataFrame(unique_facilities)
    df.to_csv(OUTPUT_CSV, index=False)
    save_progress(progress)

    print()
    print("="*80)
    print("✅ SCRAPING COMPLETE")
    print("="*80)
    print(f"Output File: {OUTPUT_CSV}")
    print()
    print(f"Total facilities found: {len(all_facilities)}")
    print(f"Unique facilities: {len(unique_facilities)}")
    print()

    # Breakdown by facility type
    print("Breakdown by facility type:")
    type_counts = df['facility_type'].value_counts()
    for facility_type, count in type_counts.items():
        print(f"  {facility_type}: {count}")
    print("="*80)


if __name__ == "__main__":
    main()
