#!/usr/bin/env python3
"""
Step 2: District 18 Office Building Tenant Scraper - Web Scraping + OpenAI Only
No Google API usage - generates coverage report to assess gaps.

Outputs per-building CSV files matching existing format:
- {building_address}_merchants.csv
- {building_address}_building_contacts.csv
- {building_address}_lawyers.csv
"""

import csv
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup
from openai import OpenAI


# Configuration
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "building_tenants"
INPUT_CSV = DATA_DIR / "buildings" / "district18_buildings.csv"
TENANTS_DIR = DATA_DIR / "tenants" / "district18"
COVERAGE_REPORT = DATA_DIR / "scraping_coverage_report_district18.csv"

# OpenAI API (set OPENAI_API_KEY environment variable)
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Serper.dev API (set SERPER_API_KEY environment variable)
SERPER_API_KEY = os.getenv('SERPER_API_KEY')

# User agent for web requests
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}


def load_buildings() -> List[Dict]:
    """
    Load office buildings from CSV.

    Returns:
        List of building dictionaries
    """
    print("Loading office buildings...")

    TENANTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(INPUT_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        all_buildings = list(reader)

    print(f"  Total buildings: {len(all_buildings)}")

    return all_buildings


def search_building_directory(building_address: str) -> List[str]:
    """
    Search for building tenant directory pages using Serper.dev API.

    Args:
        building_address: Full building address

    Returns:
        List of URLs to scrape
    """
    urls = []

    if not SERPER_API_KEY:
        print(f"    Warning: SERPER_API_KEY not set, skipping search")
        return urls

    # Search query
    query = f'"{building_address}" tenant directory OR tenants OR "office space"'

    try:
        response = requests.post(
            'https://google.serper.dev/search',
            headers={
                'X-API-KEY': SERPER_API_KEY,
                'Content-Type': 'application/json'
            },
            json={'q': query, 'num': 10},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        # Extract organic search results
        for result in data.get('organic', [])[:5]:  # Top 5 results
            link = result.get('link')
            if link:
                urls.append(link)

    except Exception as e:
        print(f"    Search error: {e}")

    return urls


def scrape_webpage(url: str) -> Optional[str]:
    """
    Scrape content from a webpage.

    Args:
        url: URL to scrape

    Returns:
        Extracted text content or None
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()

        # Get text
        text = soup.get_text(separator='\n', strip=True)

        # Clean up whitespace
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        content = '\n'.join(lines)

        # Limit content size (for LLM token limits)
        if len(content) > 15000:
            content = content[:15000]

        return content

    except Exception as e:
        print(f"    Scrape error ({url}): {e}")
        return None


def extract_tenants_with_llm(building_address: str, scraped_content: str) -> Dict:
    """
    Use OpenAI to extract structured tenant data from scraped content.

    Args:
        building_address: Building address
        scraped_content: Raw text from scraped pages

    Returns:
        Dictionary with merchants, building_contacts, and lawyers
    """
    prompt = f"""Extract tenant/business information from this building directory or webpage.

Building Address: {building_address}

Content:
{scraped_content}

Extract the following information for each tenant/business:
1. Business/tenant name
2. Website URL
3. Email addresses
4. Phone numbers
5. Contact person names and titles
6. Suite/floor numbers
7. Social media links (LinkedIn, Twitter, Facebook, Instagram)
8. Type of business
9. Identify if it's a law firm

Also identify building management contacts separately.

Return a JSON object with this structure:
{{
  "merchants": [
    {{
      "name": "Company Name",
      "type": "business type",
      "is_law_firm": true/false,
      "website": "url",
      "email": "email",
      "email_secondary": "email2",
      "phone": "phone",
      "phone_secondary": "phone2",
      "suite": "suite/floor",
      "linkedin": "url",
      "twitter": "url",
      "facebook": "url",
      "instagram": "url",
      "contact_person": "name",
      "contact_title": "title"
    }}
  ],
  "building_contacts": [
    {{
      "building_name": "name",
      "contact_name": "name",
      "contact_title": "title",
      "email": "email",
      "phone": "phone",
      "website": "url",
      "linkedin": "url"
    }}
  ],
  "lawyers": [
    {{
      "company_name": "law firm name",
      "lawyer_name": "name",
      "lawyer_title": "title",
      "lawyer_email": "email",
      "lawyer_phone": "phone",
      "lawyer_linkedin": "url"
    }}
  ]
}}

Only include data that is clearly present in the content. Return empty arrays if no data found."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a data extraction expert. Extract structured business information from text. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        return result

    except Exception as e:
        print(f"    LLM extraction error: {e}")
        return {"merchants": [], "building_contacts": [], "lawyers": []}


def save_merchants_csv(building_address: str, merchants: List[Dict]):
    """Save merchants CSV in existing format."""
    if not merchants:
        return

    # Sanitize filename
    filename = re.sub(r'[^\w\s-]', '', building_address.replace(',', ''))
    filename = re.sub(r'\s+', ' ', filename).strip()
    output_file = TENANTS_DIR / f"{filename}_merchants.csv"

    fieldnames = [
        'name', 'type', 'is_law_firm', 'website', 'email', 'email_contact_name',
        'email_contact_title', 'email_secondary', 'phone', 'phone_contact_name',
        'phone_contact_title', 'phone_secondary', 'address', 'linkedin', 'twitter',
        'facebook', 'instagram', 'contact_person', 'contact_title', 'stars',
        'reviews', 'quality_score', 'data_source', 'last_updated'
    ]

    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for merchant in merchants:
            # Calculate quality score
            quality_score = 0
            if merchant.get('website'): quality_score += 20
            if merchant.get('email'): quality_score += 15
            if merchant.get('phone'): quality_score += 10
            if merchant.get('contact_person'): quality_score += 10
            if merchant.get('linkedin'): quality_score += 15
            if merchant.get('twitter') or merchant.get('facebook') or merchant.get('instagram'):
                quality_score += 10

            writer.writerow({
                'name': merchant.get('name', ''),
                'type': merchant.get('type', ''),
                'is_law_firm': merchant.get('is_law_firm', False),
                'website': merchant.get('website', ''),
                'email': merchant.get('email', ''),
                'email_contact_name': '',
                'email_contact_title': '',
                'email_secondary': merchant.get('email_secondary', ''),
                'phone': merchant.get('phone', ''),
                'phone_contact_name': '',
                'phone_contact_title': '',
                'phone_secondary': merchant.get('phone_secondary', ''),
                'address': building_address,
                'linkedin': merchant.get('linkedin', ''),
                'twitter': merchant.get('twitter', ''),
                'facebook': merchant.get('facebook', ''),
                'instagram': merchant.get('instagram', ''),
                'contact_person': merchant.get('contact_person', ''),
                'contact_title': merchant.get('contact_title', ''),
                'stars': '',
                'reviews': '',
                'quality_score': quality_score,
                'data_source': "['web_scraping', 'llm_parser']",
                'last_updated': datetime.now().isoformat()
            })


def save_building_contacts_csv(building_address: str, contacts: List[Dict]):
    """Save building contacts CSV in existing format."""
    if not contacts:
        return

    filename = re.sub(r'[^\w\s-]', '', building_address.replace(',', ''))
    filename = re.sub(r'\s+', ' ', filename).strip()
    output_file = TENANTS_DIR / f"{filename}_building_contacts.csv"

    fieldnames = [
        'building_name', 'contact_name', 'contact_title', 'email',
        'email_secondary', 'phone', 'phone_secondary', 'linkedin',
        'instagram', 'website', 'address'
    ]

    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for contact in contacts:
            writer.writerow({
                'building_name': contact.get('building_name', ''),
                'contact_name': contact.get('contact_name', ''),
                'contact_title': contact.get('contact_title', ''),
                'email': contact.get('email', ''),
                'email_secondary': '',
                'phone': contact.get('phone', ''),
                'phone_secondary': '',
                'linkedin': contact.get('linkedin', ''),
                'instagram': '',
                'website': contact.get('website', ''),
                'address': building_address
            })


def save_lawyers_csv(building_address: str, lawyers: List[Dict]):
    """Save lawyers CSV in existing format."""
    if not lawyers:
        return

    filename = re.sub(r'[^\w\s-]', '', building_address.replace(',', ''))
    filename = re.sub(r'\s+', ' ', filename).strip()
    output_file = TENANTS_DIR / f"{filename}_lawyers.csv"

    fieldnames = [
        'company_name', 'lawyer_name', 'lawyer_title',
        'lawyer_email', 'lawyer_phone', 'lawyer_linkedin'
    ]

    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for lawyer in lawyers:
            writer.writerow({
                'company_name': lawyer.get('company_name', ''),
                'lawyer_name': lawyer.get('lawyer_name', ''),
                'lawyer_title': lawyer.get('lawyer_title', ''),
                'lawyer_email': lawyer.get('lawyer_email', ''),
                'lawyer_phone': lawyer.get('lawyer_phone', ''),
                'lawyer_linkedin': lawyer.get('lawyer_linkedin', '')
            })


def process_building(building: Dict) -> Dict:
    """
    Process a single building - scrape and extract tenant data.

    Args:
        building: Building dictionary

    Returns:
        Coverage report dictionary for this building
    """
    address = building['address']
    print(f"\nProcessing: {address}")

    # Search for directory pages
    print("  Searching for tenant directory...")
    urls = search_building_directory(address)
    print(f"  Found {len(urls)} potential pages")

    if not urls:
        return {
            'building_address': address,
            'scraping_success': False,
            'tenants_found': 0,
            'data_completeness_score': 0,
            'missing_fields': 'No directory found',
            'needs_google_api': True
        }

    # Scrape pages
    all_content = []
    for url in urls[:3]:  # Limit to top 3 URLs
        print(f"  Scraping: {url[:60]}...")
        content = scrape_webpage(url)
        if content:
            all_content.append(content)
        time.sleep(1)  # Be respectful

    if not all_content:
        return {
            'building_address': address,
            'scraping_success': False,
            'tenants_found': 0,
            'data_completeness_score': 0,
            'missing_fields': 'Failed to scrape content',
            'needs_google_api': True
        }

    # Extract data with LLM
    print("  Extracting data with OpenAI...")
    combined_content = '\n\n---\n\n'.join(all_content)
    extracted_data = extract_tenants_with_llm(address, combined_content)

    # Save CSVs
    merchants = extracted_data.get('merchants', [])
    building_contacts = extracted_data.get('building_contacts', [])
    lawyers = extracted_data.get('lawyers', [])

    if merchants:
        save_merchants_csv(address, merchants)
        print(f"  ✓ Saved {len(merchants)} merchants")

    if building_contacts:
        save_building_contacts_csv(address, building_contacts)
        print(f"  ✓ Saved {len(building_contacts)} building contacts")

    if lawyers:
        save_lawyers_csv(address, lawyers)
        print(f"  ✓ Saved {len(lawyers)} lawyers")

    # Calculate completeness
    total_records = len(merchants) + len(building_contacts) + len(lawyers)
    success = total_records > 0
    completeness = min(100, total_records * 10) if success else 0

    return {
        'building_address': address,
        'scraping_success': success,
        'tenants_found': len(merchants),
        'data_completeness_score': completeness,
        'missing_fields': '' if success else 'No tenant data extracted',
        'needs_google_api': not success
    }


def generate_coverage_report(coverage_data: List[Dict]):
    """Generate and save coverage report."""
    print(f"\n{'='*60}")
    print("COVERAGE REPORT")
    print(f"{'='*60}")

    total = len(coverage_data)
    successful = sum(1 for d in coverage_data if d['scraping_success'])
    failed = total - successful

    total_tenants = sum(d['tenants_found'] for d in coverage_data)
    avg_completeness = sum(d['data_completeness_score'] for d in coverage_data) / total if total > 0 else 0

    need_api = sum(1 for d in coverage_data if d['needs_google_api'])

    print(f"Total buildings processed: {total}")
    print(f"Successful scrapes: {successful} ({successful/total*100:.1f}%)")
    print(f"Failed/No data: {failed} ({failed/total*100:.1f}%)")
    print(f"Total tenants extracted: {total_tenants}")
    print(f"Average completeness: {avg_completeness:.1f}%")
    print(f"\nBuildings needing Google API: {need_api}")
    print(f"Estimated Google API cost: ${need_api * 0.30:.2f} - ${need_api * 0.50:.2f}")

    # Save report
    COVERAGE_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(COVERAGE_REPORT, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=coverage_data[0].keys())
        writer.writeheader()
        writer.writerows(coverage_data)

    print(f"\nCoverage report saved: {COVERAGE_REPORT}")


def main():
    """Main function."""
    print("="*60)
    print("DISTRICT 18: TENANT SCRAPER - WEB SCRAPING + OPENAI")
    print("="*60)
    print("No Google API usage - Will generate coverage report")
    print("="*60 + "\n")

    # Check API keys
    if not os.getenv('OPENAI_API_KEY'):
        print("ERROR: OPENAI_API_KEY environment variable not set")
        print("Set it with: export OPENAI_API_KEY='your-key-here'")
        return

    if not SERPER_API_KEY:
        print("ERROR: SERPER_API_KEY environment variable not set")
        print("Set it with: export SERPER_API_KEY='your-key-here'")
        return

    # Load buildings
    buildings = load_buildings()

    # Filter out invalid addresses (like "Address, New York, NY")
    valid_buildings = []
    for building in buildings:
        address = building.get('address', '')
        # Skip generic/invalid addresses
        if address and address.lower() not in ['address', 'address, new york, ny']:
            valid_buildings.append(building)
    
    buildings = valid_buildings
    print(f"\n🚀 Processing {len(buildings)} buildings\n")

    # Process each building
    coverage_data = []
    for i, building in enumerate(buildings, 1):
        print(f"\n[{i}/{len(buildings)}]")
        report = process_building(building)
        coverage_data.append(report)
        time.sleep(2)  # Rate limiting

    # Generate report
    generate_coverage_report(coverage_data)

    print(f"\n{'='*60}")
    print("STEP 2 COMPLETED!")
    print(f"{'='*60}")
    print("Review the coverage report to decide if you want to run Step 3")
    print("(Step 3 = Enrich contacts with additional data)")
    print("=" * 60)


if __name__ == '__main__':
    main()

