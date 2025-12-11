#!/usr/bin/env python3
"""
Step 3: Contact Enrichment Script for District 18 Buildings
Enriches merchant, lawyer, and building contact data with emails, phones, and contact info
"""

import argparse
import csv
import json
import os
import re
import requests
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from openai import OpenAI

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "building_tenants"
TENANTS_DIR = DATA_DIR / "tenants" / "district18"
PROGRESS_FILE = DATA_DIR / "progress" / "district18_enrichment_progress.json"
TOP_N_BUILDINGS = 25

# Initialize clients from environment variables
serper_api_key = os.getenv('SERPER_API_KEY')
openai_api_key = os.getenv('OPENAI_API_KEY')

if not serper_api_key:
    print("ERROR: SERPER_API_KEY not found")
    sys.exit(1)
if not openai_api_key:
    print("ERROR: OPENAI_API_KEY not found")
    sys.exit(1)

openai_client = OpenAI(api_key=openai_api_key)


def load_top_buildings(n: int = TOP_N_BUILDINGS) -> List[str]:
    """Load top N buildings by tenant count"""
    buildings = {}

    for file in TENANTS_DIR.glob("*_merchants.csv"):
        building = file.stem.replace('_merchants', '')
        with open(file, 'r', encoding='utf-8') as f:
            count = len(list(csv.DictReader(f)))
            buildings[building] = count

    # Sort by count and return top N
    sorted_buildings = sorted(buildings.items(), key=lambda x: x[1], reverse=True)
    top_buildings = [b[0] for b in sorted_buildings[:n]]

    print(f"Top {n} buildings:")
    for i, (building, count) in enumerate(sorted_buildings[:n], 1):
        print(f"  {i}. {building}: {count} tenants")
    print()

    return top_buildings


def load_buildings_from_file(file_path: str) -> List[str]:
    """Load building names from a text file (one per line)"""
    buildings = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if line and not line.startswith('#'):
                buildings.append(line)

    print(f"Loaded {len(buildings)} buildings from {file_path}")
    return buildings


def load_progress() -> Dict:
    """Load enrichment progress"""
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {
        'completed_buildings': [],
        'current_building': None,
        'enriched_count': 0,
        'start_time': None
    }


def save_progress(progress: Dict):
    """Save enrichment progress"""
    progress['last_updated'] = datetime.now().isoformat()
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)


def search_for_contact_info(query: str) -> List[str]:
    """Search for contact information using Serper.dev"""
    try:
        response = requests.post(
            'https://google.serper.dev/search',
            headers={
                'X-API-KEY': serper_api_key,
                'Content-Type': 'application/json'
            },
            json={'q': query, 'num': 5},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        urls = []
        for result in data.get('organic', [])[:3]:  # Top 3 results
            link = result.get('link')
            if link and 'linkedin.com' not in link:  # Skip LinkedIn for now
                urls.append(link)

        return urls
    except Exception as e:
        print(f"    Search error: {e}")
        return []


def scrape_webpage(url: str) -> str:
    """Scrape webpage content"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Get text and clean it
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)

        # Limit to first 3000 characters to save on LLM costs
        return text[:3000]
    except Exception as e:
        print(f"    Scrape error ({url}): {e}")
        return ""


def extract_contact_with_llm(company_name: str, scraped_content: str) -> Optional[Dict]:
    """Use OpenAI to extract contact information"""
    if not scraped_content:
        return None

    prompt = f"""Extract contact information for "{company_name}" from the following text.

Text:
{scraped_content}

Return a JSON object with these fields (use empty string if not found):
{{
  "email": "primary email address",
  "email_secondary": "secondary email if found",
  "phone": "primary phone number",
  "phone_secondary": "secondary phone if found",
  "contact_person": "contact person name",
  "contact_title": "their job title",
  "linkedin": "LinkedIn profile URL if found"
}}

Rules:
- Only extract information that clearly belongs to {company_name}
- For email: prefer general contact emails (info@, contact@, hello@) over personal emails
- For phone: use US format if possible
- For contact_person: prefer executives, partners, or main contacts
- Return empty strings if information is not found"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a data extraction expert. Extract contact information accurately."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        print(f"    LLM error: {e}")
        return None


def needs_enrichment(entry: Dict) -> bool:
    """Check if entry needs contact enrichment"""
    # Needs enrichment if missing email AND phone
    has_email = bool(entry.get('email') or entry.get('lawyer_email'))
    has_phone = bool(entry.get('phone') or entry.get('lawyer_phone'))

    return not (has_email and has_phone)


def enrich_entry(entry: Dict, entry_type: str) -> Dict:
    """Enrich a single entry with contact information"""
    # Determine search query based on type
    if entry_type == 'merchant':
        name = entry.get('name', '')
        address = entry.get('address', '')
        query = f'"{name}" {address} contact email phone'
    elif entry_type == 'lawyer':
        lawyer_name = entry.get('lawyer_name', '')
        company = entry.get('company_name', '')
        query = f'"{lawyer_name}" {company} contact email'
    elif entry_type == 'building_contact':
        building_name = entry.get('building_name', '')
        address = entry.get('address', '')
        query = f'"{building_name}" {address} management contact'
    else:
        return entry

    if not query.strip() or query.count('"') < 2:
        return entry  # Skip if no valid query

    print(f"    Searching: {query}")

    # Search for contact pages
    urls = search_for_contact_info(query)
    if not urls:
        return entry

    # Scrape and extract
    all_content = ""
    for url in urls[:2]:  # Limit to 2 URLs to save time
        content = scrape_webpage(url)
        if content:
            all_content += content + "\n\n"

    if not all_content:
        return entry

    # Extract with LLM
    name = entry.get('name') or entry.get('lawyer_name') or entry.get('building_name')
    extracted = extract_contact_with_llm(name, all_content)

    if not extracted:
        return entry

    # Update entry with extracted data (only if field is empty)
    updated = False

    if entry_type == 'merchant':
        if not entry.get('email') and extracted.get('email'):
            entry['email'] = extracted['email']
            updated = True
        if not entry.get('phone') and extracted.get('phone'):
            entry['phone'] = extracted['phone']
            updated = True
        if not entry.get('contact_person') and extracted.get('contact_person'):
            entry['contact_person'] = extracted['contact_person']
            updated = True
        if not entry.get('contact_title') and extracted.get('contact_title'):
            entry['contact_title'] = extracted['contact_title']
            updated = True
        if not entry.get('linkedin') and extracted.get('linkedin'):
            entry['linkedin'] = extracted['linkedin']
            updated = True

    elif entry_type == 'lawyer':
        if not entry.get('lawyer_email') and extracted.get('email'):
            entry['lawyer_email'] = extracted['email']
            updated = True
        if not entry.get('lawyer_phone') and extracted.get('phone'):
            entry['lawyer_phone'] = extracted['phone']
            updated = True
        if not entry.get('lawyer_linkedin') and extracted.get('linkedin'):
            entry['lawyer_linkedin'] = extracted['linkedin']
            updated = True

    elif entry_type == 'building_contact':
        if not entry.get('email') and extracted.get('email'):
            entry['email'] = extracted['email']
            updated = True
        if not entry.get('phone') and extracted.get('phone'):
            entry['phone'] = extracted['phone']
            updated = True
        if not entry.get('contact_name') and extracted.get('contact_person'):
            entry['contact_name'] = extracted['contact_person']
            updated = True
        if not entry.get('contact_title') and extracted.get('contact_title'):
            entry['contact_title'] = extracted['contact_title']
            updated = True

    if updated:
        print(f"    ✓ Enriched with new contact info")

    return entry


def enrich_building(building_name: str) -> Dict:
    """Enrich all data for a single building"""
    print(f"\n{'='*60}")
    print(f"ENRICHING: {building_name}")
    print(f"{'='*60}")

    stats = {
        'merchants_enriched': 0,
        'lawyers_enriched': 0,
        'building_contacts_enriched': 0
    }

    # Enrich merchants
    merchants_file = TENANTS_DIR / f"{building_name}_merchants.csv"
    if merchants_file.exists():
        print(f"\n📋 Processing merchants...")
        with open(merchants_file, 'r', encoding='utf-8') as f:
            merchants = list(csv.DictReader(f))

        enriched_merchants = []
        for i, merchant in enumerate(merchants, 1):
            if needs_enrichment(merchant):
                print(f"  [{i}/{len(merchants)}] {merchant.get('name', 'Unknown')}")
                enriched = enrich_entry(merchant, 'merchant')
                if enriched != merchant:
                    stats['merchants_enriched'] += 1
                enriched_merchants.append(enriched)
            else:
                enriched_merchants.append(merchant)

        # Save enriched merchants
        with open(merchants_file, 'w', encoding='utf-8', newline='') as f:
            if enriched_merchants:
                writer = csv.DictWriter(f, fieldnames=enriched_merchants[0].keys())
                writer.writeheader()
                writer.writerows(enriched_merchants)

        print(f"  ✓ Enriched {stats['merchants_enriched']}/{len(merchants)} merchants")

    # Enrich lawyers
    lawyers_file = TENANTS_DIR / f"{building_name}_lawyers.csv"
    if lawyers_file.exists():
        print(f"\n⚖️  Processing lawyers...")
        with open(lawyers_file, 'r', encoding='utf-8') as f:
            lawyers = list(csv.DictReader(f))

        enriched_lawyers = []
        for i, lawyer in enumerate(lawyers, 1):
            if needs_enrichment(lawyer):
                print(f"  [{i}/{len(lawyers)}] {lawyer.get('lawyer_name', 'Unknown')}")
                enriched = enrich_entry(lawyer, 'lawyer')
                if enriched != lawyer:
                    stats['lawyers_enriched'] += 1
                enriched_lawyers.append(enriched)
            else:
                enriched_lawyers.append(lawyer)

        # Save enriched lawyers
        with open(lawyers_file, 'w', encoding='utf-8', newline='') as f:
            if enriched_lawyers:
                writer = csv.DictWriter(f, fieldnames=enriched_lawyers[0].keys())
                writer.writeheader()
                writer.writerows(enriched_lawyers)

        print(f"  ✓ Enriched {stats['lawyers_enriched']}/{len(lawyers)} lawyers")

    # Enrich building contacts
    contacts_file = TENANTS_DIR / f"{building_name}_building_contacts.csv"
    if contacts_file.exists():
        print(f"\n🏗️  Processing building contacts...")
        with open(contacts_file, 'r', encoding='utf-8') as f:
            contacts = list(csv.DictReader(f))

        enriched_contacts = []
        for i, contact in enumerate(contacts, 1):
            if needs_enrichment(contact):
                print(f"  [{i}/{len(contacts)}] {contact.get('building_name', 'Unknown')}")
                enriched = enrich_entry(contact, 'building_contact')
                if enriched != contact:
                    stats['building_contacts_enriched'] += 1
                enriched_contacts.append(enriched)
            else:
                enriched_contacts.append(contact)

        # Save enriched contacts
        with open(contacts_file, 'w', encoding='utf-8', newline='') as f:
            if enriched_contacts:
                writer = csv.DictWriter(f, fieldnames=enriched_contacts[0].keys())
                writer.writeheader()
                writer.writerows(enriched_contacts)

        print(f"  ✓ Enriched {stats['building_contacts_enriched']}/{len(contacts)} building contacts")

    return stats


def main():
    """Main enrichment process"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Enrich District 18 building tenant contact data')
    parser.add_argument('--buildings-file', help='File containing building names to enrich (one per line)')
    parser.add_argument('--top-n', type=int, default=TOP_N_BUILDINGS, help=f'Number of top buildings to enrich (default: {TOP_N_BUILDINGS})')
    args = parser.parse_args()

    print("="*60)
    print("DISTRICT 18: CONTACT ENRICHMENT")
    print("="*60)
    print()

    # Load buildings (either from file or top N)
    if args.buildings_file:
        top_buildings = load_buildings_from_file(args.buildings_file)
    else:
        top_buildings = load_top_buildings(args.top_n)

    print(f"Will enrich {len(top_buildings)} buildings\n")

    # Load progress
    progress = load_progress()
    if not progress['start_time']:
        progress['start_time'] = datetime.now().isoformat()

    # Process each building
    total_stats = {
        'merchants_enriched': 0,
        'lawyers_enriched': 0,
        'building_contacts_enriched': 0
    }

    for i, building in enumerate(top_buildings, 1):
        if building in progress['completed_buildings']:
            print(f"\n[{i}/{len(top_buildings)}] Skipping {building} (already completed)")
            continue

        print(f"\n[{i}/{len(top_buildings)}] Processing {building}")
        progress['current_building'] = building
        save_progress(progress)

        try:
            stats = enrich_building(building)
            total_stats['merchants_enriched'] += stats['merchants_enriched']
            total_stats['lawyers_enriched'] += stats['lawyers_enriched']
            total_stats['building_contacts_enriched'] += stats['building_contacts_enriched']

            progress['completed_buildings'].append(building)
            progress['enriched_count'] = sum(total_stats.values())
            save_progress(progress)

        except Exception as e:
            print(f"\n❌ Error processing {building}: {e}")
            import traceback
            traceback.print_exc()
            continue

    # Final summary
    print("\n" + "="*60)
    print("ENRICHMENT COMPLETE")
    print("="*60)
    print(f"Buildings processed: {len(progress['completed_buildings'])}/{len(top_buildings)}")
    print(f"Merchants enriched: {total_stats['merchants_enriched']}")
    print(f"Lawyers enriched: {total_stats['lawyers_enriched']}")
    print(f"Building contacts enriched: {total_stats['building_contacts_enriched']}")
    print(f"Total enriched: {sum(total_stats.values())}")
    print()
    print("Next step: Run 04_export_to_kmz.py to generate KMZ file")
    print("="*60)


if __name__ == "__main__":
    main()




