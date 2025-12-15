#!/usr/bin/env python3
"""
Queens & Brooklyn Accountants/CPAs Scraper
Uses Serper.dev API to find all accountants and CPAs and enrich contact information
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
DATA_DIR = PROJECT_ROOT / "data" / "accountants"
OUTPUT_CSV = DATA_DIR / "queens_brooklyn_accountants.csv"
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

# Search terms for accountants
SEARCH_TERMS = [
    "accountant",
    "CPA",
    "certified public accountant",
    "accounting firm",
    "tax accountant",
    "bookkeeper",
    "accounting services",
    "tax preparation",
    "tax services"
]

# Patterns to identify aggregator/directory listings (not actual accountants)
AGGREGATOR_PATTERNS = [
    r"^best\s+.*\s+near",
    r"^top\s+\d+\s+best",
    r"^the\s+best\s+\d+",
    r"near\s+me\s+in\s+",
    r"^\d+\s+of\s+the\s+best",
    r"^find\s+.*\s+near",
    r"^book\s+\d+.*\s+near",
    r"(accountant|cpa|tax)s?\s+near\s+me\s+in",
]


def load_progress() -> Dict:
    """Load progress from previous runs"""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {
        "completed_searches": [],
        "found_accountants": {},
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


def is_aggregator_listing(name: str) -> bool:
    """Check if the office name matches aggregator/directory listing patterns"""
    name_lower = name.lower()

    for pattern in AGGREGATOR_PATTERNS:
        if re.search(pattern, name_lower, re.IGNORECASE):
            return True

    return False


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
    Parse Serper results to extract accountant information
    """
    accountants = []
    seen_names = set()

    # Parse local pack results (Google Maps results)
    if "places" in results:
        for place in results["places"]:
            name = place.get("title", "").strip()

            # Skip if already seen
            if name.lower() in seen_names:
                continue

            # Skip aggregator/directory listings
            if is_aggregator_listing(name):
                continue

            # Filter for accountants/CPAs
            title_lower = name.lower()
            if not any(keyword in title_lower for keyword in [
                "account", "cpa", "tax", "bookkeep", "audit", "payroll",
                "financial", "consulting", "certified", "llp", "pllc", "pc", "llc"
            ]):
                continue

            seen_names.add(name.lower())

            accountant = {
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
            accountants.append(accountant)

    # Parse organic search results
    if "organic" in results:
        for result in results["organic"]:
            name = result.get("title", "").strip()

            # Skip if already seen
            if name.lower() in seen_names:
                continue

            # Skip aggregator/directory listings
            if is_aggregator_listing(name):
                continue

            # Filter for accountants/CPAs
            title_lower = name.lower()
            snippet = result.get("snippet", "").lower()

            if not any(keyword in title_lower or keyword in snippet for keyword in [
                "account", "cpa", "tax", "bookkeep", "audit", "payroll",
                "financial", "consulting", "certified", "llp", "pllc", "pc", "llc"
            ]):
                continue

            seen_names.add(name.lower())

            # Try to extract phone and address from snippet
            phone = extract_phone_from_text(result.get("snippet", ""))
            address = extract_address_from_snippet(
                result.get("snippet", ""),
                result.get("title", "")
            )

            accountant = {
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
            accountants.append(accountant)

    return accountants


def enrich_contact_with_serper(accountant: Dict) -> Dict:
    """
    Enrich accountant contact info using Serper + OpenAI
    """
    if not accountant.get("website"):
        return accountant

    # Search for contact information
    contact_query = f"{accountant['name']} contact email phone"
    results = search_serper(contact_query)

    # Extract additional contact info from search results
    if "organic" in results:
        for result in results["organic"][:3]:  # Check top 3 results
            snippet = result.get("snippet", "")

            # Try to extract email
            if not accountant.get("email"):
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                email_match = re.search(email_pattern, snippet)
                if email_match:
                    accountant["email"] = email_match.group()

            # Try to extract phone if missing
            if not accountant.get("phone"):
                phone = extract_phone_from_text(snippet)
                if phone:
                    accountant["phone"] = phone

    # Use OpenAI to extract structured contact info
    if openai_client and "organic" in results:
        try:
            context = "\n".join([
                f"Title: {r.get('title', '')}\nSnippet: {r.get('snippet', '')}"
                for r in results["organic"][:3]
            ])

            prompt = f"""Extract contact information for this accounting firm:
Name: {accountant['name']}
Website: {accountant.get('website', '')}

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

            if extracted.get("email") and not accountant.get("email"):
                accountant["email"] = extracted["email"]
            if extracted.get("phone") and not accountant.get("phone"):
                accountant["phone"] = extracted["phone"]
            if extracted.get("contact_name"):
                accountant["contact_name"] = extracted["contact_name"]

        except Exception as e:
            print(f"   ⚠️  OpenAI enrichment error: {e}")

    return accountant


def scrape_accountants():
    """Main scraping function"""
    print("=" * 80)
    print("QUEENS & BROOKLYN ACCOUNTANTS/CPAs SCRAPER")
    print("=" * 80)
    print()

    # Load progress
    progress = load_progress()
    all_accountants = progress.get("found_accountants", {})
    completed = set(progress.get("completed_searches", []))

    print(f"📊 Progress: {len(completed)} searches completed, {len(all_accountants)} accountants found")
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
        accountants = parse_serper_results(results, search_term, location)
        print(f"   ✓ Found {len(accountants)} accountants")

        # Add to collection (deduplicate by name + address)
        for accountant in accountants:
            key = f"{accountant['name']}|{accountant['address']}".lower()
            if key not in all_accountants:
                all_accountants[key] = accountant

        # Mark search as completed
        completed.add(search_key)

        # Save progress every 10 searches
        if idx % 10 == 0:
            progress["completed_searches"] = list(completed)
            progress["found_accountants"] = all_accountants
            save_progress(progress)
            print(f"   💾 Progress saved ({len(all_accountants)} total accountants)")

        # Rate limiting
        time.sleep(1)  # Be respectful to Serper API

    # Final save
    progress["completed_searches"] = list(completed)
    progress["found_accountants"] = all_accountants
    save_progress(progress)

    print()
    print("=" * 80)
    print(f"✅ Scraping complete! Found {len(all_accountants)} unique accountants")
    print("=" * 80)
    print()

    return list(all_accountants.values())


def enrich_contacts(accountants: List[Dict]) -> List[Dict]:
    """Enrich contact information for all accountants"""
    print()
    print("=" * 80)
    print("ENRICHING CONTACT INFORMATION")
    print("=" * 80)
    print()

    enriched = []
    total = len(accountants)

    for idx, accountant in enumerate(accountants, 1):
        print(f"[{idx}/{total}] Enriching: {accountant['name']}")

        # Skip if already has good contact info
        has_email = bool(accountant.get("email"))
        has_phone = bool(accountant.get("phone"))

        if has_email and has_phone:
            print("   ✓ Already has email and phone")
            enriched.append(accountant)
            continue

        # Enrich using Serper + OpenAI
        enriched_accountant = enrich_contact_with_serper(accountant)
        enriched.append(enriched_accountant)

        # Show what was found
        if enriched_accountant.get("email") and not has_email:
            print(f"   ✓ Found email: {enriched_accountant['email']}")
        if enriched_accountant.get("phone") and not has_phone:
            print(f"   ✓ Found phone: {enriched_accountant['phone']}")

        # Rate limiting
        if idx % 10 == 0:
            time.sleep(2)
        else:
            time.sleep(1)

    print()
    print(f"✅ Enrichment complete!")
    print()

    return enriched


def export_to_csv(accountants: List[Dict]):
    """Export accountants to CSV"""
    df = pd.DataFrame(accountants)

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
        # Step 1: Scrape accountants
        accountants = scrape_accountants()

        if not accountants:
            print("❌ No accountants found!")
            return

        # Step 2: Enrich contacts
        enriched_accountants = enrich_contacts(accountants)

        # Step 3: Export to CSV
        export_to_csv(enriched_accountants)

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
