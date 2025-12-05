#!/usr/bin/env python3
"""
Step 6: Targeted Building Management Contact Enrichment for District 18
Specifically enriches building management contacts missing phone numbers and emails
"""

import csv
import json
import os
import re
import requests
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from openai import OpenAI

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "building_tenants"
TENANTS_DIR = DATA_DIR / "tenants" / "district18"
EXPORTS_DIR = DATA_DIR / "exports"
COMBINED_CSV = EXPORTS_DIR / "district18_building_management_contacts.csv"
PROGRESS_FILE = DATA_DIR / "progress" / "building_mgmt_enrichment_progress.json"

# Initialize clients
serper_api_key = os.getenv('SERPER_API_KEY')
openai_api_key = os.getenv('OPENAI_API_KEY')

if not serper_api_key:
    print("ERROR: SERPER_API_KEY not found in environment")
    sys.exit(1)
if not openai_api_key:
    print("ERROR: OPENAI_API_KEY not found in environment")
    sys.exit(1)

openai_client = OpenAI(api_key=openai_api_key)


def load_progress() -> Dict:
    """Load enrichment progress"""
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {
        'processed_contacts': [],
        'enriched_count': 0,
        'start_time': None,
        'last_building': None
    }


def save_progress(progress: Dict):
    """Save enrichment progress"""
    progress['last_updated'] = datetime.now().isoformat()
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)


def needs_enrichment(contact: Dict) -> bool:
    """Check if contact needs enrichment"""
    # Missing phone is the primary issue
    has_phone = contact.get('phone') and contact['phone'] not in ['', 'N/A', 'Unknown']
    has_email = contact.get('email') and contact['email'] not in ['', 'N/A', 'Unknown']

    # Enrich if missing phone (email coverage is already good at 96%)
    return not has_phone


def search_for_contact(query: str) -> List[str]:
    """Search for contact information using Serper.dev"""
    print(f"    Searching: {query}")

    url = "https://google.serper.dev/search"
    headers = {
        'X-API-KEY': serper_api_key,
        'Content-Type': 'application/json'
    }
    payload = {
        'q': query,
        'num': 5  # Get top 5 results
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()

        urls = []
        # Extract URLs from organic results
        for result in data.get('organic', []):
            urls.append(result.get('link'))

        return [u for u in urls if u]

    except Exception as e:
        print(f"    ⚠️  Search error: {e}")
        return []


def scrape_webpage(url: str) -> Optional[str]:
    """Scrape webpage content"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)

        # Limit to first 3000 chars
        return text[:3000]

    except Exception as e:
        print(f"    ⚠️  Scraping error: {e}")
        return None


def extract_contact_with_llm(html_text: str, contact_name: str, building_name: str) -> Dict:
    """Extract contact information using OpenAI LLM"""
    prompt = f"""Extract contact information for the following person from the webpage text.

Person: {contact_name}
Building/Company: {building_name}

Webpage text:
{html_text}

Extract and return ONLY a JSON object with these fields (use empty string if not found):
{{
  "email": "email address",
  "phone": "phone number",
  "linkedin": "LinkedIn profile URL"
}}

IMPORTANT: Return ONLY valid JSON, no other text."""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a data extraction assistant. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=300
        )

        result_text = response.choices[0].message.content.strip()

        # Remove markdown code blocks if present
        result_text = re.sub(r'```json\s*|\s*```', '', result_text)

        # Parse JSON
        data = json.loads(result_text)

        return {
            'email': data.get('email', ''),
            'phone': data.get('phone', ''),
            'linkedin': data.get('linkedin', '')
        }

    except Exception as e:
        print(f"    ⚠️  LLM extraction error: {e}")
        return {'email': '', 'phone': '', 'linkedin': ''}


def enrich_contact(contact: Dict) -> Dict:
    """Enrich a single building management contact"""
    contact_name = contact.get('contact_name', '')
    building_name = contact.get('building_name', '')
    building_address = contact.get('building_address', '')
    contact_title = contact.get('contact_title', '')

    if not contact_name or contact_name == 'Unknown':
        print(f"    ⏭️  Skipping contact with no name")
        return contact

    # Build search queries (ordered by specificity)
    queries = []

    # Query 1: Contact name + building name + "phone email"
    if contact_name and building_name:
        queries.append(f'"{contact_name}" "{building_name}" phone email contact')

    # Query 2: Contact name + title + building address + "contact"
    if contact_name and contact_title and building_address:
        queries.append(f'"{contact_name}" {contact_title} "{building_address}" contact information')

    # Query 3: Building name + "leasing office phone"
    if building_name:
        queries.append(f'"{building_name}" leasing office phone contact')

    # Try each query until we find contact info
    found_data = {'email': '', 'phone': '', 'linkedin': ''}

    for query in queries[:2]:  # Try top 2 queries to save API costs
        urls = search_for_contact(query)

        if not urls:
            continue

        # Try scraping top 2 URLs
        for url in urls[:2]:
            print(f"    📄 Scraping: {url[:60]}...")
            html_text = scrape_webpage(url)

            if not html_text:
                continue

            # Extract contact info with LLM
            extracted = extract_contact_with_llm(html_text, contact_name, building_name)

            # Update found data (don't overwrite existing good data)
            if extracted.get('phone') and not found_data.get('phone'):
                found_data['phone'] = extracted['phone']
            if extracted.get('email') and not found_data.get('email'):
                found_data['email'] = extracted['email']
            if extracted.get('linkedin') and not found_data.get('linkedin'):
                found_data['linkedin'] = extracted['linkedin']

            # If we found phone (our primary goal), we can stop
            if found_data.get('phone'):
                break

        # If we found phone, no need to try more queries
        if found_data.get('phone'):
            break

        # Rate limiting between queries
        time.sleep(1)

    # Update contact with found data
    updated = False
    if found_data.get('phone') and not contact.get('phone'):
        contact['phone'] = found_data['phone']
        updated = True
    if found_data.get('email') and not contact.get('email'):
        contact['email'] = found_data['email']
        updated = True
    if found_data.get('linkedin') and not contact.get('linkedin'):
        contact['linkedin'] = found_data['linkedin']
        updated = True

    if updated:
        print(f"    ✅ Found: phone={bool(found_data.get('phone'))}, email={bool(found_data.get('email'))}, linkedin={bool(found_data.get('linkedin'))}")
    else:
        print(f"    ⚠️  No new contact info found")

    return contact


def update_building_csv(building_address: str, updated_contact: Dict):
    """Update the individual building's CSV file with enriched contact"""
    # Find the corresponding building CSV file
    # Format: building_address = "1114 6th Ave, New York, NY" or "1 Bryant Pk, New York, NY"
    # File: "1114 6th Ave New York NY_building_contacts.csv" or "1 Bryant Pk New York NY_building_contacts.csv"

    # Remove all commas and replace ", New York, NY" pattern
    filename_base = building_address.replace(', New York, NY', ' New York NY')
    contacts_file = TENANTS_DIR / f"{filename_base}_building_contacts.csv"

    if not contacts_file.exists():
        print(f"    ⚠️  Building contacts file not found: {contacts_file.name}")
        return

    # Read all contacts
    with open(contacts_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        contacts = list(reader)
        fieldnames = reader.fieldnames

    # Remove temporary fields from updated_contact
    clean_contact = {k: v for k, v in updated_contact.items() if k in fieldnames}

    # Find and update matching contact
    updated = False
    for i, contact in enumerate(contacts):
        if (contact.get('contact_name') == clean_contact.get('contact_name') and
            contact.get('building_name') == clean_contact.get('building_name')):
            # Update only the fields that exist in the original CSV
            for key in fieldnames:
                if key in clean_contact:
                    contacts[i][key] = clean_contact[key]
            updated = True
            break

    if not updated:
        print(f"    ⚠️  Contact not found in building CSV")
        return

    # Write back to file
    with open(contacts_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(contacts)

    print(f"    💾 Updated building CSV: {contacts_file.name}")


def main():
    """Main enrichment workflow"""
    print("=" * 70)
    print("DISTRICT 18 BUILDING MANAGEMENT CONTACT ENRICHMENT")
    print("=" * 70)
    print()

    # Load progress
    progress = load_progress()
    if not progress['start_time']:
        progress['start_time'] = datetime.now().isoformat()

    # Read combined contacts CSV
    if not COMBINED_CSV.exists():
        print(f"❌ Combined CSV not found: {COMBINED_CSV}")
        sys.exit(1)

    with open(COMBINED_CSV, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        all_contacts = list(reader)
        fieldnames = reader.fieldnames

    print(f"📊 Total building management contacts: {len(all_contacts)}")

    # Filter to contacts needing enrichment
    contacts_to_enrich_indices = []
    for idx, contact in enumerate(all_contacts):
        # Create unique ID for tracking
        contact_id = f"{contact.get('building_address')}|{contact.get('contact_name')}|{contact.get('building_name')}"

        if contact_id in progress['processed_contacts']:
            continue

        if needs_enrichment(contact):
            contacts_to_enrich_indices.append((idx, contact_id))

    print(f"📋 Contacts needing enrichment: {len(contacts_to_enrich_indices)}")
    print(f"✅ Already processed: {len(progress['processed_contacts'])}")
    print()

    if not contacts_to_enrich_indices:
        print("✨ All contacts are already enriched!")
        return

    # Enrich each contact
    enriched_count = 0
    for i, (idx, contact_id) in enumerate(contacts_to_enrich_indices, 1):
        contact = all_contacts[idx]
        print(f"\n[{i}/{len(contacts_to_enrich_indices)}] {contact.get('contact_name', 'Unknown')} - {contact.get('building_name', 'Unknown')}")
        print(f"  Building: {contact.get('building_address')}")

        try:
            # Enrich
            original_contact = contact.copy()
            enriched = enrich_contact(contact)

            # Update in all_contacts list
            all_contacts[idx] = enriched

            # Track progress
            progress['processed_contacts'].append(contact_id)
            if enriched != original_contact:
                enriched_count += 1
            progress['enriched_count'] = enriched_count
            progress['last_building'] = contact.get('building_address')

            # Save progress every 5 contacts
            if i % 5 == 0:
                save_progress(progress)
                # Also save intermediate results to CSV
                with open(COMBINED_CSV, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(all_contacts)
                print(f"    💾 Saved intermediate results to CSV")

            # Rate limiting
            time.sleep(2)

        except Exception as e:
            print(f"  ❌ Error enriching contact: {e}")
            import traceback
            traceback.print_exc()
            continue

    # Final save - write enriched data back to CSV
    with open(COMBINED_CSV, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_contacts)

    # Final progress save
    save_progress(progress)

    # Print summary
    print("\n" + "=" * 70)
    print("ENRICHMENT COMPLETE")
    print("=" * 70)
    print(f"Total contacts processed: {len(contacts_to_enrich_indices)}")
    print(f"Contacts enriched with new data: {enriched_count}")
    print(f"✅ Updated CSV: {COMBINED_CSV}")
    print(f"\n💡 You can now use the enriched contacts in your KMZ export!")
    print("=" * 70)


if __name__ == "__main__":
    main()
