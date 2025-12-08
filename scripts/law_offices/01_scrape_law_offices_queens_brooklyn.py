#!/usr/bin/env python3
"""
Queens & Brooklyn Law Office Scraper
Uses Serper.dev API to find all law offices and enrich contact information
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime
import re

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

import pandas as pd
from openai import OpenAI

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "law_offices"
OUTPUT_CSV = DATA_DIR / "queens_brooklyn_law_offices.csv"
PROGRESS_FILE = DATA_DIR / "scraping_progress.json"

# API Configuration
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not SERPER_API_KEY:
    print("❌ Error: SERPER_API_KEY environment variable not set")
    sys.exit(1)

if not OPENAI_API_KEY:
    print("❌ Warning: OPENAI_API_KEY not set. Contact enrichment will be limited.")

# Initialize OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Queens neighborhoods and ZIP codes
QUEENS_AREAS = [
    "Astoria", "Long Island City", "Flushing", "Jamaica", "Forest Hills",
    "Rego Park", "Elmhurst", "Jackson Heights", "Corona", "Woodside",
    "Sunnyside", "Bayside", "Whitestone", "College Point", "Fresh Meadows",
    "Kew Gardens", "Richmond Hill", "Ozone Park", "Howard Beach", "Rockaway"
]

# Brooklyn neighborhoods and ZIP codes
BROOKLYN_AREAS = [
    "Williamsburg", "Greenpoint", "Bushwick", "Bedford-Stuyvesant", "Crown Heights",
    "Park Slope", "Prospect Heights", "Carroll Gardens", "Cobble Hill", "Brooklyn Heights",
    "Downtown Brooklyn", "Fort Greene", "Clinton Hill", "Boerum Hill", "Red Hook",
    "Sunset Park", "Bay Ridge", "Bensonhurst", "Dyker Heights", "Borough Park",
    "Flatbush", "Midwood", "Sheepshead Bay", "Brighton Beach", "Coney Island",
    "Canarsie", "East New York", "Brownsville", "East Flatbush", "Flatlands"
]

# Search terms for law offices
SEARCH_TERMS = [
    "law office",
    "attorney",
    "lawyer",
    "legal services",
    "immigration lawyer",
    "family law attorney",
    "personal injury attorney",
    "criminal defense lawyer",
    "real estate lawyer"
]


def load_progress() -> Dict:
    """Load progress from previous runs"""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {
        "completed_searches": [],
        "found_law_offices": {},
        "last_updated": None
    }


def save_progress(progress: Dict):
    """Save progress to resume later"""
    progress["last_updated"] = datetime.now().isoformat()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)


def search_serper(query: str, location: str = "New York, NY") -> Dict:
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
    # Look for patterns like "123 Main St, Brooklyn, NY 11201"
    address_pattern = r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct|Place|Pl)[,\s]+(?:Brooklyn|Queens)[,\s]+NY\s+\d{5}'

    match = re.search(address_pattern, snippet + " " + title, re.IGNORECASE)
    if match:
        return match.group().strip()

    return None


def parse_serper_results(results: Dict, search_query: str, location: str) -> List[Dict]:
    """
    Parse Serper results to extract law office information
    """
    law_offices = []
    seen_names = set()

    # Parse local pack results (Google Maps results)
    if "places" in results:
        for place in results["places"]:
            name = place.get("title", "").strip()

            # Skip if already seen
            if name.lower() in seen_names:
                continue

            # Filter for law firms
            title_lower = name.lower()
            if not any(keyword in title_lower for keyword in [
                "law", "attorney", "lawyer", "legal", "esq", "counselor",
                "advocate", "firm", "llc", "pllc", "pc"
            ]):
                continue

            seen_names.add(name.lower())

            law_office = {
                "name": name,
                "address": place.get("address", ""),
                "phone": place.get("phoneNumber", ""),
                "website": place.get("website", ""),
                "rating": place.get("rating", ""),
                "reviews": place.get("ratingCount", ""),
                "latitude": place.get("latitude", ""),
                "longitude": place.get("longitude", ""),
                "source": "serper_places",
                "search_query": search_query,
                "location": location,
                "found_date": datetime.now().isoformat()
            }
            law_offices.append(law_office)

    # Parse organic search results
    if "organic" in results:
        for result in results["organic"]:
            name = result.get("title", "").strip()

            # Skip if already seen
            if name.lower() in seen_names:
                continue

            # Filter for law firms
            title_lower = name.lower()
            snippet = result.get("snippet", "").lower()

            if not any(keyword in title_lower or keyword in snippet for keyword in [
                "law", "attorney", "lawyer", "legal", "esq", "counselor",
                "advocate", "firm", "llc", "pllc", "pc"
            ]):
                continue

            seen_names.add(name.lower())

            # Try to extract phone and address from snippet
            phone = extract_phone_from_text(result.get("snippet", ""))
            address = extract_address_from_snippet(
                result.get("snippet", ""),
                result.get("title", "")
            )

            law_office = {
                "name": name,
                "address": address or "",
                "phone": phone or "",
                "website": result.get("link", ""),
                "rating": "",
                "reviews": "",
                "latitude": "",
                "longitude": "",
                "source": "serper_organic",
                "search_query": search_query,
                "location": location,
                "found_date": datetime.now().isoformat()
            }
            law_offices.append(law_office)

    return law_offices


def enrich_contact_with_serper(law_office: Dict) -> Dict:
    """
    Enrich law office contact info using Serper + OpenAI
    """
    if not law_office.get("website"):
        return law_office

    # Search for contact information
    contact_query = f"{law_office['name']} contact email phone"
    results = search_serper(contact_query)

    # Extract additional contact info from search results
    if "organic" in results:
        for result in results["organic"][:3]:  # Check top 3 results
            snippet = result.get("snippet", "")

            # Try to extract email
            if not law_office.get("email"):
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                email_match = re.search(email_pattern, snippet)
                if email_match:
                    law_office["email"] = email_match.group()

            # Try to extract phone if missing
            if not law_office.get("phone"):
                phone = extract_phone_from_text(snippet)
                if phone:
                    law_office["phone"] = phone

    # Use OpenAI to extract structured contact info
    if openai_client and "organic" in results:
        try:
            context = "\n".join([
                f"Title: {r.get('title', '')}\nSnippet: {r.get('snippet', '')}"
                for r in results["organic"][:3]
            ])

            prompt = f"""Extract contact information for this law office:
Name: {law_office['name']}
Website: {law_office.get('website', '')}

Search Results:
{context}

Extract and return JSON with:
- email (if found, otherwise empty string)
- phone (if found, otherwise empty string)
- contact_name (office manager, administrator, or contact person name if found, otherwise empty string)

Return only valid JSON, no explanation."""

            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )

            extracted = json.loads(response.choices[0].message.content)

            if extracted.get("email") and not law_office.get("email"):
                law_office["email"] = extracted["email"]
            if extracted.get("phone") and not law_office.get("phone"):
                law_office["phone"] = extracted["phone"]
            if extracted.get("contact_name"):
                law_office["contact_name"] = extracted["contact_name"]

        except Exception as e:
            print(f"   ⚠️  OpenAI enrichment error: {e}")

    return law_office


def scrape_law_offices():
    """Main scraping function"""
    print("=" * 80)
    print("QUEENS & BROOKLYN LAW OFFICE SCRAPER")
    print("=" * 80)
    print()

    # Load progress
    progress = load_progress()
    all_law_offices = progress.get("found_law_offices", {})
    completed = set(progress.get("completed_searches", []))

    print(f"📊 Progress: {len(completed)} searches completed, {len(all_law_offices)} law_offices found")
    print()

    # Generate all search combinations
    searches = []
    for area in QUEENS_AREAS:
        for term in SEARCH_TERMS:
            searches.append((term, f"{area}, Queens, NY"))

    for area in BROOKLYN_AREAS:
        for term in SEARCH_TERMS:
            searches.append((term, f"{area}, Brooklyn, NY"))

    total_searches = len(searches)
    remaining = [s for s in searches if f"{s[0]}|{s[1]}" not in completed]

    print(f"🔍 Total searches: {total_searches}")
    print(f"⏳ Remaining: {len(remaining)}")
    print()

    # Perform searches
    for idx, (search_term, location) in enumerate(remaining, 1):
        search_key = f"{search_term}|{location}"

        print(f"[{idx}/{len(remaining)}] Searching: '{search_term}' in {location}")

        # Search with Serper
        results = search_serper(search_term, location)

        if not results:
            print("   ⚠️  No results")
            completed.add(search_key)
            continue

        # Parse results
        law_offices = parse_serper_results(results, search_term, location)
        print(f"   ✓ Found {len(law_offices)} law offices")

        # Add to collection (deduplicate by name + address)
        for law_office in law_offices:
            key = f"{law_office['name']}|{law_office['address']}".lower()
            if key not in all_law_offices:
                all_law_offices[key] = law_office

        # Mark search as completed
        completed.add(search_key)

        # Save progress every 10 searches
        if idx % 10 == 0:
            progress["completed_searches"] = list(completed)
            progress["found_law_offices"] = all_law_offices
            save_progress(progress)
            print(f"   💾 Progress saved ({len(all_law_offices)} total law_offices)")

        # Rate limiting
        time.sleep(1)  # Be respectful to Serper API

    # Final save
    progress["completed_searches"] = list(completed)
    progress["found_law_offices"] = all_law_offices
    save_progress(progress)

    print()
    print("=" * 80)
    print(f"✅ Scraping complete! Found {len(all_law_offices)} unique law offices")
    print("=" * 80)
    print()

    return list(all_law_offices.values())


def enrich_contacts(law_offices: List[Dict]) -> List[Dict]:
    """Enrich contact information for all law_offices"""
    print()
    print("=" * 80)
    print("ENRICHING CONTACT INFORMATION")
    print("=" * 80)
    print()

    enriched = []
    total = len(law_offices)

    for idx, law_office in enumerate(law_offices, 1):
        print(f"[{idx}/{total}] Enriching: {law_office['name']}")

        # Skip if already has good contact info
        has_email = bool(law_office.get("email"))
        has_phone = bool(law_office.get("phone"))

        if has_email and has_phone:
            print("   ✓ Already has email and phone")
            enriched.append(law_office)
            continue

        # Enrich using Serper + OpenAI
        enriched_law_office = enrich_contact_with_serper(law_office)
        enriched.append(enriched_law_office)

        # Show what was found
        if enriched_law_office.get("email") and not has_email:
            print(f"   ✓ Found email: {enriched_law_office['email']}")
        if enriched_law_office.get("phone") and not has_phone:
            print(f"   ✓ Found phone: {enriched_law_office['phone']}")

        # Rate limiting
        if idx % 10 == 0:
            time.sleep(2)
        else:
            time.sleep(1)

    print()
    print(f"✅ Enrichment complete!")
    print()

    return enriched


def export_to_csv(law_offices: List[Dict]):
    """Export law_offices to CSV"""
    df = pd.DataFrame(law_offices)

    # Reorder columns
    columns = [
        "name", "address", "phone", "email", "website",
        "contact_name", "rating", "reviews",
        "latitude", "longitude",
        "source", "search_query", "location", "found_date"
    ]

    # Add missing columns
    for col in columns:
        if col not in df.columns:
            df[col] = ""

    df = df[columns]

    # Save CSV
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False)

    print(f"📄 CSV saved: {OUTPUT_CSV}")
    print(f"   Total records: {len(df)}")
    print(f"   With phone: {df['phone'].astype(bool).sum()}")
    print(f"   With email: {df['email'].astype(bool).sum()}")
    print(f"   With address: {df['address'].astype(bool).sum()}")


def main():
    """Main execution"""
    try:
        # Step 1: Scrape law_offices
        law_offices = scrape_law_offices()

        if not law_offices:
            print("❌ No law_offices found!")
            return

        # Step 2: Enrich contacts
        enriched_law_offices = enrich_contacts(law_offices)

        # Step 3: Export to CSV
        export_to_csv(enriched_law_offices)

        print()
        print("=" * 80)
        print("🎉 ALL DONE!")
        print("=" * 80)

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user. Progress has been saved.")
        print("   Run the script again to resume from where you left off.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
