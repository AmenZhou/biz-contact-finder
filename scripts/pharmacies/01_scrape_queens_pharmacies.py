#!/usr/bin/env python3
"""
Queens Pharmacy Scraper
Uses Serper.dev API to find all pharmacies in Queens
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import re

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

import pandas as pd

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "pharmacies"
OUTPUT_CSV = DATA_DIR / "queens_pharmacies.csv"
PROGRESS_FILE = DATA_DIR / "queens_scraping_progress.json"

# API Configuration
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

if not SERPER_API_KEY:
    print("❌ Error: SERPER_API_KEY environment variable not set")
    sys.exit(1)

# Queens neighborhoods
QUEENS_AREAS = [
    "Astoria", "Long Island City", "Flushing", "Jamaica", "Forest Hills",
    "Rego Park", "Elmhurst", "Jackson Heights", "Corona", "Woodside",
    "Sunnyside", "Bayside", "Whitestone", "College Point", "Fresh Meadows",
    "Kew Gardens", "Richmond Hill", "Ozone Park", "Howard Beach", "Rockaway",
    "Far Rockaway", "Ridgewood", "Middle Village", "Glendale", "Maspeth",
    "Briarwood", "Hollis", "Queens Village", "Douglaston", "Little Neck",
    "Bellerose", "Floral Park", "Glen Oaks", "St. Albans", "Springfield Gardens",
    "Rosedale", "Laurelton", "Cambria Heights", "Arverne", "Belle Harbor"
]

# Search terms for pharmacies
SEARCH_TERMS = [
    "pharmacy",
    "drugstore",
    "CVS pharmacy",
    "Walgreens pharmacy",
    "Duane Reade pharmacy",
    "Rite Aid pharmacy",
]


def load_progress() -> Dict:
    """Load progress from previous runs"""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {
        "completed_searches": [],
        "found_pharmacies": {},
        "last_updated": None
    }


def save_progress(progress: Dict):
    """Save progress to resume later"""
    progress["last_updated"] = datetime.now().isoformat()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)


def search_serper(query: str, location: str = "Queens, NY") -> Dict:
    """
    Search using Serper.dev API
    Returns organic + local pack results
    """
    url = "https://google.serper.dev/search"

    payload = {
        "q": f"{query} in {location}",
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
        return response.json()
    except Exception as e:
        print(f"   ⚠️  Serper API error: {e}")
        return {}


def extract_phone_from_text(text: str) -> Optional[str]:
    """Extract phone number from text"""
    if not text:
        return None

    # Common US phone patterns
    patterns = [
        r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # (123) 456-7890 or 123-456-7890
        r'\d{3}[-.\s]\d{3}[-.\s]\d{4}',          # 123-456-7890
        r'\d{10}'                                 # 1234567890
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            # Clean up the phone number
            phone = re.sub(r'[^\d]', '', match.group())
            if len(phone) == 10:
                return f"({phone[:3]}) {phone[3:6]}-{phone[6:]}"
            elif len(phone) == 11 and phone[0] == '1':
                return f"({phone[1:4]}) {phone[4:7]}-{phone[7:]}"

    return None


def extract_address_from_snippet(snippet: str, title: str) -> Optional[str]:
    """Extract address from search result snippet"""
    # Look for patterns like "123 Main St, Queens, NY 11201"
    address_pattern = r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct|Place|Pl)[,\s]+(?:Queens|Astoria|Flushing|Jamaica)[,\s]+NY\s+\d{5}'

    match = re.search(address_pattern, snippet, re.IGNORECASE)
    if match:
        return match.group()

    # Try simpler pattern without street type
    simple_pattern = r'\d+\s+[A-Za-z\s,]+Queens[,\s]+NY\s+\d{5}'
    match = re.search(simple_pattern, snippet, re.IGNORECASE)
    if match:
        return match.group()

    return None


def is_aggregator_listing(title: str, snippet: str) -> bool:
    """Check if result is an aggregator/directory listing rather than a real pharmacy"""
    aggregator_patterns = [
        r'best\s+\d+',  # "Best 10 Pharmacies"
        r'top\s+\d+',   # "Top 10 Pharmacies"
        r'list of',     # "List of pharmacies"
        r'directory',   # "Pharmacy Directory"
        r'find a',      # "Find a pharmacy"
        r'yelp',
        r'yellowpages',
    ]

    combined_text = f"{title} {snippet}".lower()

    for pattern in aggregator_patterns:
        if re.search(pattern, combined_text):
            return True

    return False


def parse_serper_results(results: Dict, search_query: str, location: str) -> List[Dict]:
    """Parse Serper results and extract pharmacy information"""
    pharmacies = []

    # Parse "places" results (Google Maps local pack)
    places = results.get("places", [])
    for place in places:
        name = place.get("title", "")
        address = place.get("address", "")
        phone = place.get("phoneNumber", "")
        rating = place.get("rating")
        reviews = place.get("reviews")

        # Only include if we have at least a name and address
        if name and address:
            pharmacies.append({
                "name": name,
                "address": address,
                "phone": phone,
                "website": "",  # Not provided in places results
                "email": "",
                "contact_name": "",
                "rating": rating,
                "reviews": reviews,
                "source": "serper_places",
                "search_query": search_query,
                "location": location,
                "found_date": datetime.now().strftime("%Y-%m-%d")
            })

    # Parse organic results
    organic = results.get("organic", [])
    for result in organic:
        title = result.get("title", "")
        snippet = result.get("snippet", "")
        link = result.get("link", "")

        # Skip aggregator listings
        if is_aggregator_listing(title, snippet):
            continue

        # Extract information
        address = extract_address_from_snippet(snippet, title)
        phone = extract_phone_from_text(snippet)

        # Only include if we have at least a name
        if title and ("pharmacy" in title.lower() or "drugstore" in title.lower()):
            pharmacies.append({
                "name": title,
                "address": address or "",
                "phone": phone or "",
                "website": link,
                "email": "",
                "contact_name": "",
                "rating": "",
                "reviews": "",
                "source": "serper_organic",
                "search_query": search_query,
                "location": location,
                "found_date": datetime.now().strftime("%Y-%m-%d")
            })

    return pharmacies


def main():
    print("=" * 70)
    print("QUEENS PHARMACY SCRAPER")
    print("=" * 70)
    print(f"Output: {OUTPUT_CSV}")
    print(f"Progress: {PROGRESS_FILE}")
    print()

    # Load progress
    progress = load_progress()
    print(f"📊 Loaded progress: {len(progress['completed_searches'])} searches completed")
    print()

    # Track all pharmacies by unique key (name|address)
    all_pharmacies = progress.get("found_pharmacies", {})

    # Generate all search combinations
    total_searches = len(QUEENS_AREAS) * len(SEARCH_TERMS)
    completed = len(progress['completed_searches'])

    print(f"🎯 Total searches: {total_searches}")
    print(f"✅ Completed: {completed}")
    print(f"⏳ Remaining: {total_searches - completed}")
    print()

    try:
        for i, area in enumerate(QUEENS_AREAS, 1):
            print(f"\n{'=' * 70}")
            print(f"Area {i}/{len(QUEENS_AREAS)}: {area}")
            print(f"{'=' * 70}")

            for j, search_term in enumerate(SEARCH_TERMS, 1):
                search_key = f"{area}|{search_term}"

                # Skip if already completed
                if search_key in progress['completed_searches']:
                    print(f"   ✓ [{j}/{len(SEARCH_TERMS)}] {search_term} (already completed)")
                    continue

                print(f"   🔍 [{j}/{len(SEARCH_TERMS)}] Searching: {search_term}...", end=" ", flush=True)

                # Search using Serper
                results = search_serper(search_term, f"{area}, Queens, NY")

                if results:
                    # Parse results
                    pharmacies = parse_serper_results(results, search_term, area)

                    # Add to collection (deduplicate by name|address)
                    new_count = 0
                    for pharmacy in pharmacies:
                        key = f"{pharmacy['name']}|{pharmacy['address']}".lower()
                        if key not in all_pharmacies:
                            all_pharmacies[key] = pharmacy
                            new_count += 1

                    print(f"Found {len(pharmacies)} results ({new_count} new)")
                else:
                    print("No results")

                # Mark as completed
                progress['completed_searches'].append(search_key)
                progress['found_pharmacies'] = all_pharmacies

                # Save progress every 5 searches
                if len(progress['completed_searches']) % 5 == 0:
                    save_progress(progress)

                # Rate limiting (1 request per second)
                time.sleep(1)

        # Final save
        save_progress(progress)

        # Export to CSV
        print("\n" + "=" * 70)
        print("EXPORTING RESULTS")
        print("=" * 70)

        if all_pharmacies:
            # Convert to DataFrame
            df = pd.DataFrame(list(all_pharmacies.values()))

            # Reorder columns
            columns = [
                'name', 'address', 'phone', 'email', 'website',
                'contact_name', 'rating', 'reviews', 'source',
                'search_query', 'location', 'found_date'
            ]

            df = df[columns]

            # Sort by name
            df = df.sort_values('name')

            # Save to CSV
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8')

            print(f"✅ Saved {len(df)} unique pharmacies to {OUTPUT_CSV}")
        else:
            print("⚠️  No pharmacies found!")

        # Summary
        print("\n" + "=" * 70)
        print("SCRAPING COMPLETE")
        print("=" * 70)
        print(f"Total unique pharmacies: {len(all_pharmacies)}")
        print(f"Total searches completed: {len(progress['completed_searches'])}/{total_searches}")
        print("=" * 70)

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user. Saving progress...")
        save_progress(progress)
        print(f"Progress saved. Run again to resume from {len(progress['completed_searches'])} completed searches.")
        sys.exit(0)


if __name__ == "__main__":
    main()
