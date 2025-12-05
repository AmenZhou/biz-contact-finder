#!/usr/bin/env python3
"""
Universal Multi-Strategy Contact Enrichment for District 18 & District 9
Uses 5 different strategies to find phone numbers and emails for building management contacts
Works for any district via --district parameter
"""

import argparse
import csv
import json
import os
import re
import random
import requests
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
from openai import OpenAI

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Enrich building management contacts')
parser.add_argument('--district', required=True, choices=['district9', 'district18'],
                   help='Which district to enrich (district9 or district18)')
args = parser.parse_args()

# Configuration based on district
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "building_tenants"
EXPORTS_DIR = DATA_DIR / "exports"

DISTRICT = args.district
COMBINED_CSV = EXPORTS_DIR / f"{DISTRICT}_building_management_contacts.csv"
PROGRESS_FILE = DATA_DIR / "progress" / f"{DISTRICT}_universal_enrichment_progress.json"
REPORT_FILE = EXPORTS_DIR / f"{DISTRICT}_enrichment_report.json"

# Initialize clients
serper_api_key = os.getenv('SERPER_API_KEY')
openai_api_key = os.getenv('OPENAI_API_KEY')

if not serper_api_key or not openai_api_key:
    print("ERROR: SERPER_API_KEY and OPENAI_API_KEY required")
    sys.exit(1)

openai_client = OpenAI(api_key=openai_api_key)

# User agents for rotation (avoid blocking)
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0'
]

# Company-specific info
COMPANY_DOMAINS = {
    'CBRE': {'domain': 'cbre.com', 'email_pattern': '{first}.{last}@cbre.com'},
    'JLL': {'domain': 'jll.com', 'email_pattern': '{first}.{last}@jll.com'},
    'Cushman': {'domain': 'cushmanwakefield.com', 'email_pattern': '{first}.{last}@cushwake.com'},
    'Newmark': {'domain': 'nmrk.com', 'email_pattern': '{first}.{last}@nmrk.com'},
    'Tishman': {'domain': 'tishmanspeyer.com', 'email_pattern': '{first}.{last}@tishmanspeyer.com'},
}


class EnrichmentResult:
    def __init__(self):
        self.phone = ''
        self.email = ''
        self.linkedin = ''
        self.confidence = 0
        self.source = ''
        self.strategy = ''


def load_progress() -> Dict:
    """Load enrichment progress"""
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {
        'processed_contacts': [],
        'enriched_count': 0,
        'strategy_stats': {},
        'start_time': None
    }


def save_progress(progress: Dict):
    """Save enrichment progress"""
    progress['last_updated'] = datetime.now().isoformat()
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)


def get_random_user_agent() -> str:
    """Get random user agent to avoid blocking"""
    return random.choice(USER_AGENTS)


def scrape_url(url: str, max_retries: int = 2) -> Optional[str]:
    """Scrape URL with retry logic and user agent rotation"""
    for attempt in range(max_retries):
        try:
            headers = {'User-Agent': get_random_user_agent()}
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 403 and attempt < max_retries - 1:
                time.sleep(2)  # Wait before retry
                continue

            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            for script in soup(["script", "style"]):
                script.decompose()

            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)

            return text[:3000]

        except Exception as e:
            if attempt == max_retries - 1:
                return None
    return None


def extract_with_llm(text: str, contact_name: str, context: str) -> Dict:
    """Extract contact info using LLM"""
    prompt = f"""Extract contact information from this text.

Person: {contact_name}
Context: {context}

Text:
{text}

Return ONLY a JSON object:
{{
  "phone": "phone number or empty string",
  "email": "email address or empty string",
  "linkedin": "LinkedIn URL or empty string"
}}"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Extract contact info. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=200
        )

        result = response.choices[0].message.content.strip()
        result = re.sub(r'```json\s*|\s*```', '', result)
        return json.loads(result)

    except Exception:
        return {'phone': '', 'email': '', 'linkedin': ''}


def extract_company_from_title(title: str) -> Optional[str]:
    """Extract company name from title"""
    # Look for company names after comma or "at"
    for company in COMPANY_DOMAINS.keys():
        if company.lower() in title.lower():
            return company
    return None


def search_google(query: str) -> List[str]:
    """Search Google via Serper.dev"""
    try:
        response = requests.post(
            "https://google.serper.dev/search",
            headers={'X-API-KEY': serper_api_key, 'Content-Type': 'application/json'},
            json={'q': query, 'num': 5},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return [r.get('link') for r in data.get('organic', []) if r.get('link')]
    except Exception:
        return []


# ==================== STRATEGY 1: Company Website ====================
def strategy_company_website(contact: Dict) -> EnrichmentResult:
    """Try to find contact on company's website"""
    result = EnrichmentResult()
    result.strategy = 'company_website'

    title = contact.get('contact_title', '')
    name = contact.get('contact_name', '')

    company = extract_company_from_title(title)
    if not company or company not in COMPANY_DOMAINS:
        return result

    domain = COMPANY_DOMAINS[company]['domain']

    # Try company's people page
    search_query = f'site:{domain} "{name}" phone email'
    urls = search_google(search_query)

    for url in urls[:2]:
        if domain in url:
            text = scrape_url(url)
            if text:
                extracted = extract_with_llm(text, name, f"{company} agent profile")
                if extracted.get('phone') or extracted.get('email'):
                    result.phone = extracted.get('phone', '')
                    result.email = extracted.get('email', '')
                    result.linkedin = extracted.get('linkedin', '')
                    result.confidence = 90
                    result.source = url
                    return result

    return result


# ==================== STRATEGY 2: Building Leasing Page ====================
def strategy_building_leasing(contact: Dict) -> EnrichmentResult:
    """Search for building's leasing page"""
    result = EnrichmentResult()
    result.strategy = 'building_leasing'

    building = contact.get('building_name', '')
    address = contact.get('building_address', '')
    name = contact.get('contact_name', '')

    if not building or building == 'Unknown':
        return result

    # Search for leasing page
    query = f'"{building}" leasing office contact phone'
    urls = search_google(query)

    # Look for official building websites
    for url in urls[:3]:
        # Skip aggregator sites
        if any(x in url.lower() for x in ['loopnet', 'costar', 'zillow', 'trulia']):
            continue

        text = scrape_url(url)
        if text and name.lower() in text.lower():
            extracted = extract_with_llm(text, name, f"{building} leasing team")
            if extracted.get('phone') or extracted.get('email'):
                result.phone = extracted.get('phone', '')
                result.email = extracted.get('email', '')
                result.confidence = 85
                result.source = url
                return result

    return result


# ==================== STRATEGY 3: News Articles ====================
def strategy_news_articles(contact: Dict) -> EnrichmentResult:
    """Search real estate news sites"""
    result = EnrichmentResult()
    result.strategy = 'news_articles'

    name = contact.get('contact_name', '')
    building = contact.get('building_name', '')

    # Focus on sites that don't block
    good_sites = ['commercialobserver.com', 'therealdeal.com', 'bisnow.com', 'cretech.com']

    for site in good_sites:
        query = f'site:{site} "{name}" "{building}" broker contact'
        urls = search_google(query)

        for url in urls[:1]:  # Just try top result per site
            text = scrape_url(url)
            if text:
                extracted = extract_with_llm(text, name, f"commercial real estate news")
                if extracted.get('phone') or extracted.get('email'):
                    result.phone = extracted.get('phone', '')
                    result.email = extracted.get('email', '')
                    result.confidence = 75
                    result.source = url
                    return result

    return result


# ==================== STRATEGY 4: Phone Pattern Matching ====================
def strategy_phone_pattern(contact: Dict, all_contacts: List[Dict]) -> EnrichmentResult:
    """Use phone patterns from same company/building"""
    result = EnrichmentResult()
    result.strategy = 'phone_pattern'

    building = contact.get('building_address', '')
    title = contact.get('contact_title', '')
    company = extract_company_from_title(title)

    # Find other contacts at same building or company with phones
    for other in all_contacts:
        if other.get('contact_name') == contact.get('contact_name'):
            continue

        other_phone = other.get('phone', '')
        if not other_phone or other_phone in ['', 'N/A']:
            continue

        # Same building = likely same office phone
        if other.get('building_address') == building:
            result.phone = other_phone
            result.confidence = 60
            result.source = f"Same building as {other.get('contact_name')}"
            return result

        # Same company = possibly same office
        if company and extract_company_from_title(other.get('contact_title', '')) == company:
            result.phone = other_phone
            result.confidence = 50
            result.source = f"Same company ({company}) as {other.get('contact_name')}"
            return result

    return result


# ==================== STRATEGY 5: Email Pattern Generation ====================
def strategy_email_pattern(contact: Dict, all_contacts: List[Dict]) -> EnrichmentResult:
    """Generate email based on company pattern"""
    result = EnrichmentResult()
    result.strategy = 'email_pattern'

    name = contact.get('contact_name', '')
    title = contact.get('contact_title', '')

    if not name or name == 'Unknown':
        return result

    # Extract company
    company = extract_company_from_title(title)
    if not company or company not in COMPANY_DOMAINS:
        return result

    # Parse name
    parts = name.lower().strip().split()
    if len(parts) < 2:
        return result

    first = parts[0]
    last = parts[-1]

    # Generate email from pattern
    pattern = COMPANY_DOMAINS[company]['email_pattern']
    email = pattern.format(first=first, last=last)

    result.email = email
    result.confidence = 65
    result.source = f"Generated from {company} email pattern"

    return result


# ==================== Main Enrichment Logic ====================
def enrich_contact(contact: Dict, all_contacts: List[Dict]) -> Tuple[Dict, EnrichmentResult]:
    """Try all strategies to enrich a single contact"""

    strategies = [
        ('company_website', lambda: strategy_company_website(contact)),
        ('building_leasing', lambda: strategy_building_leasing(contact)),
        ('news_articles', lambda: strategy_news_articles(contact)),
        ('phone_pattern', lambda: strategy_phone_pattern(contact, all_contacts)),
        ('email_pattern', lambda: strategy_email_pattern(contact, all_contacts)),
    ]

    best_result = EnrichmentResult()

    for strategy_name, strategy_func in strategies:
        print(f"      Trying: {strategy_name}")
        result = strategy_func()

        # If this strategy found something and it's better than what we have
        if (result.phone or result.email) and result.confidence > best_result.confidence:
            best_result = result
            print(f"      ✅ {strategy_name}: phone={bool(result.phone)}, email={bool(result.email)}, confidence={result.confidence}%")

            # If high confidence, stop trying more strategies
            if result.confidence >= 85:
                break

        time.sleep(1)  # Rate limiting

    # Update contact with best result
    if best_result.phone:
        contact['phone'] = best_result.phone
    if best_result.email and not contact.get('email'):  # Don't overwrite existing emails
        contact['email'] = best_result.email
    if best_result.linkedin:
        contact['linkedin'] = best_result.linkedin

    return contact, best_result


def main():
    """Main enrichment workflow"""
    print("=" * 70)
    print(f"UNIVERSAL CONTACT ENRICHMENT - {DISTRICT.upper()}")
    print("=" * 70)
    print()

    # Load progress
    progress = load_progress()
    if not progress['start_time']:
        progress['start_time'] = datetime.now().isoformat()

    # Read CSV
    if not COMBINED_CSV.exists():
        print(f"❌ CSV not found: {COMBINED_CSV}")
        sys.exit(1)

    with open(COMBINED_CSV, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        all_contacts = list(reader)
        fieldnames = reader.fieldnames

    print(f"📊 Total contacts: {len(all_contacts)}")

    # Find contacts needing enrichment
    contacts_to_enrich = []
    for idx, contact in enumerate(all_contacts):
        contact_id = f"{contact.get('building_address')}|{contact.get('contact_name')}"

        if contact_id in progress['processed_contacts']:
            continue

        # Need phone
        has_phone = contact.get('phone') and contact['phone'] not in ['', 'N/A']
        if not has_phone:
            contacts_to_enrich.append((idx, contact_id, contact))

    print(f"📋 Contacts to enrich: {len(contacts_to_enrich)}")
    print(f"✅ Already processed: {len(progress['processed_contacts'])}")
    print()

    if not contacts_to_enrich:
        print("✨ All contacts enriched!")
        return

    # Enrich each contact
    enriched_count = 0

    for i, (idx, contact_id, contact) in enumerate(contacts_to_enrich, 1):
        print(f"\n[{i}/{len(contacts_to_enrich)}] {contact.get('contact_name', 'Unknown')} - {contact.get('building_name', 'Unknown')}")

        try:
            enriched, result = enrich_contact(contact, all_contacts)
            all_contacts[idx] = enriched

            # Track stats
            if result.phone or result.email:
                enriched_count += 1
                strategy = result.strategy
                progress['strategy_stats'][strategy] = progress['strategy_stats'].get(strategy, 0) + 1

            progress['processed_contacts'].append(contact_id)
            progress['enriched_count'] = enriched_count

            # Save progress every 5 contacts
            if i % 5 == 0:
                save_progress(progress)
                with open(COMBINED_CSV, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(all_contacts)
                print(f"    💾 Progress saved")

        except Exception as e:
            print(f"  ❌ Error: {e}")
            continue

    # Final save
    with open(COMBINED_CSV, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_contacts)

    save_progress(progress)

    # Generate report
    report = {
        'total_processed': len(contacts_to_enrich),
        'enriched_count': enriched_count,
        'success_rate': f"{enriched_count/len(contacts_to_enrich)*100:.1f}%",
        'strategy_stats': progress['strategy_stats'],
        'timestamp': datetime.now().isoformat()
    }

    with open(REPORT_FILE, 'w') as f:
        json.dump(report, f, indent=2)

    # Print summary
    print("\n" + "=" * 70)
    print("ENRICHMENT COMPLETE")
    print("=" * 70)
    print(f"Contacts processed: {len(contacts_to_enrich)}")
    print(f"Successfully enriched: {enriched_count} ({enriched_count/len(contacts_to_enrich)*100:.1f}%)")
    print(f"\nStrategy Performance:")
    for strategy, count in sorted(progress['strategy_stats'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {strategy}: {count} contacts")
    print(f"\n✅ Updated CSV: {COMBINED_CSV}")
    print(f"📊 Report saved: {REPORT_FILE}")
    print("=" * 70)


if __name__ == "__main__":
    main()
