#!/usr/bin/env python3
"""
Enrich law offices with practice areas using LLM and name parsing
"""

import os
import sys
import time
import requests
import re
import logging
from pathlib import Path
from typing import Optional, List
from bs4 import BeautifulSoup

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

import pandas as pd
from openai import OpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "law_offices"
INPUT_CSV = DATA_DIR / "queens_brooklyn_law_offices_final.csv"
OUTPUT_CSV = DATA_DIR / "queens_brooklyn_law_offices_with_practice_areas.csv"

# API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    print("❌ Error: OPENAI_API_KEY environment variable not set")
    sys.exit(1)

# Initialize OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Common legal practice areas keywords
PRACTICE_AREA_KEYWORDS = {
    "Immigration": ["immigration", "visa", "green card", "asylum", "deportation", "citizenship"],
    "Personal Injury": ["personal injury", "accident", "slip and fall", "car accident", "workers comp"],
    "Family Law": ["family law", "divorce", "custody", "child support", "matrimonial"],
    "Criminal Defense": ["criminal", "defense", "dui", "dwi", "felony", "misdemeanor"],
    "Real Estate": ["real estate", "property", "landlord", "tenant", "foreclosure"],
    "Estate Planning": ["estate", "will", "trust", "probate", "elder law"],
    "Bankruptcy": ["bankruptcy", "debt", "chapter 7", "chapter 11", "chapter 13"],
    "Employment Law": ["employment", "labor", "discrimination", "wrongful termination", "harassment"],
    "Business Law": ["business", "corporate", "contract", "llc", "incorporation"],
    "Civil Rights": ["civil rights", "discrimination", "constitutional"],
    "Medical Malpractice": ["medical malpractice", "hospital negligence"],
    "Social Security": ["social security", "disability", "ssi", "ssdi"],
    "Tax Law": ["tax", "irs", "tax planning"],
    "Intellectual Property": ["intellectual property", "patent", "trademark", "copyright"],
    "Consumer Protection": ["consumer", "fraud", "scam"],
}

# Practice area normalization map
PRACTICE_AREA_NORMALIZATION = {
    "divorce lawyer": "Family Law",
    "divorce attorney": "Family Law",
    "accident lawyer": "Personal Injury",
    "injury lawyer": "Personal Injury",
    "dui lawyer": "Criminal Defense",
    "dwi lawyer": "Criminal Defense",
    "immigration lawyer": "Immigration",
    "immigration attorney": "Immigration",
    "bankruptcy lawyer": "Bankruptcy",
    "bankruptcy attorney": "Bankruptcy",
}

# Patterns to identify aggregator/directory listings (not actual law offices)
AGGREGATOR_PATTERNS = [
    r"^best\s+.*\s+near",
    r"^top\s+\d+\s+best",
    r"^the\s+best\s+\d+",
    r"near\s+me\s+in\s+",
    r"^\d+\s+of\s+the\s+best",
    r"^find\s+.*\s+near",
    r"^book\s+\d+.*\s+near",
    r"(lawyer|attorney|legal)s?\s+near\s+me\s+in",
]


def fetch_website_content(url: str, timeout: int = 10, max_retries: int = 2) -> Optional[str]:
    """Fetch website HTML content with retry logic"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            response.raise_for_status()
            return response.text

        except requests.Timeout:
            logging.warning(f"Timeout fetching {url} (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(1)
        except requests.RequestException as e:
            logging.warning(f"Error fetching {url}: {str(e)[:100]}")
            break
        except Exception as e:
            logging.error(f"Unexpected error fetching {url}: {str(e)[:100]}")
            break

    return None


def extract_text_from_html(html: str) -> str:
    """Extract clean text from HTML, prioritizing practice area content"""
    try:
        soup = BeautifulSoup(html, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()

        # Get text
        text = soup.get_text()

        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)

        # Limit to first 3000 characters
        return text[:3000]

    except Exception as e:
        logging.error(f"Error extracting text from HTML: {str(e)[:100]}")
        return ""


def extract_practice_areas_from_name(name: str) -> List[str]:
    """Extract practice areas from office name using keyword matching"""
    practice_areas = []
    name_lower = name.lower()

    for area, keywords in PRACTICE_AREA_KEYWORDS.items():
        for keyword in keywords:
            if keyword in name_lower:
                practice_areas.append(area)
                break

    return list(set(practice_areas))  # Remove duplicates


def is_aggregator_listing(name: str) -> bool:
    """Check if the office name matches aggregator/directory listing patterns"""
    name_lower = name.lower()

    for pattern in AGGREGATOR_PATTERNS:
        if re.search(pattern, name_lower, re.IGNORECASE):
            return True

    return False


def normalize_practice_areas(practice_areas: List[str]) -> List[str]:
    """Normalize and deduplicate practice area names"""
    normalized = []
    seen = set()

    for area in practice_areas:
        area_lower = area.lower().strip()

        # Check if it needs normalization
        normalized_area = PRACTICE_AREA_NORMALIZATION.get(area_lower, area.strip())

        # Avoid duplicates
        if normalized_area not in seen:
            normalized.append(normalized_area)
            seen.add(normalized_area)

    return normalized


def extract_practice_areas_with_llm(website_text: str, office_name: str) -> List[str]:
    """Use OpenAI to extract practice areas from website text"""

    prompt = f"""You are extracting legal practice areas from a law office website.

Office Name: {office_name}

Website Content:
{website_text}

Extract and return legal practice areas offered at this law office.

Common practice areas include:
- Immigration Law
- Personal Injury
- Family Law / Divorce
- Criminal Defense
- Real Estate Law
- Estate Planning / Wills & Trusts
- Bankruptcy
- Employment Law
- Business Law / Corporate Law
- Civil Rights
- Medical Malpractice
- Social Security Disability
- Tax Law
- Intellectual Property
- Consumer Protection
- And other legal practice areas

Return your response as a JSON object with a "practice_areas" array.
Example: {{"practice_areas": ["Immigration", "Family Law"]}}
If no specific practice areas are found, return: {{"practice_areas": ["General Practice"]}}
"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a legal practice area extraction assistant. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=150
        )

        result = response.choices[0].message.content.strip()

        import json
        data = json.loads(result)

        if isinstance(data.get('practice_areas'), list):
            return data['practice_areas']
        return []

    except Exception as e:
        logging.error(f"Error extracting practice areas with LLM: {str(e)[:100]}")
        return []


def enrich_with_practice_areas(row: pd.Series, index: int, total: int) -> pd.Series:
    """Enrich a single record with practice areas"""

    print(f"\n[{index + 1}/{total}] {row['name'][:60]}")

    # Skip if already has practice areas
    if pd.notna(row.get('practice_areas')) and row.get('practice_areas'):
        print("    ✓ Already has practice areas")
        return row

    practice_areas = []
    made_api_call = False

    # 1. Extract from name
    name_practice_areas = extract_practice_areas_from_name(row['name'])
    if name_practice_areas:
        practice_areas.extend(name_practice_areas)
        print(f"    📝 From name: {', '.join(name_practice_areas)}")

    # 2. Extract from website if available
    if row.get('website') and pd.notna(row['website']):
        print(f"    🌐 Fetching website...")
        html = fetch_website_content(row['website'])
        if html:
            text = extract_text_from_html(html)
            if text:
                print(f"    🤖 Extracting practice areas with LLM...")
                llm_practice_areas = extract_practice_areas_with_llm(text, row['name'])
                made_api_call = True
                if llm_practice_areas:
                    practice_areas.extend(llm_practice_areas)
                    print(f"    ✅ From website: {', '.join(llm_practice_areas)}")

    # Normalize and remove duplicates
    practice_areas = normalize_practice_areas(practice_areas)

    # If no practice areas found, use search query as hint
    if not practice_areas:
        search_query = row.get('search_query', '').lower()
        if 'immigration' in search_query:
            practice_areas = ["Immigration"]
        elif 'personal injury' in search_query or 'accident' in search_query:
            practice_areas = ["Personal Injury"]
        elif 'divorce' in search_query or 'family' in search_query:
            practice_areas = ["Family Law"]
        elif 'criminal' in search_query or 'defense' in search_query:
            practice_areas = ["Criminal Defense"]
        else:
            practice_areas = ["General Practice"]

        print(f"    💡 Inferred: {', '.join(practice_areas)}")

    # Update row
    row['practice_areas'] = ", ".join(practice_areas)

    if not practice_areas:
        print("    ❌ No practice areas found")
    else:
        print(f"    ✅ Final: {row['practice_areas']}")

    # Rate limiting - only sleep if we made an API call
    if made_api_call:
        time.sleep(0.5)

    return row


def main():
    """Main execution"""
    print("=" * 80)
    print("ENRICHING LAW OFFICES WITH PRACTICE AREAS")
    print("=" * 80)
    print()

    # Load CSV
    if not INPUT_CSV.exists():
        print(f"❌ Error: CSV file not found at {INPUT_CSV}")
        sys.exit(1)

    print(f"📂 Loading data from {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV)

    print(f"   ✓ Loaded {len(df)} total records")

    # Filter out aggregator/directory listings
    aggregator_mask = df['name'].apply(is_aggregator_listing)
    num_aggregators = aggregator_mask.sum()

    if num_aggregators > 0:
        print(f"   🗑️  Filtering out {num_aggregators} aggregator/directory listings")
        df = df[~aggregator_mask].reset_index(drop=True)
        print(f"   ✓ {len(df)} records remaining after filtering")

    # Add practice_areas column if it doesn't exist
    if 'practice_areas' not in df.columns:
        df['practice_areas'] = ""

    print()

    # Count records needing enrichment
    needs_practice_areas = df['practice_areas'].isna() | (df['practice_areas'] == '')
    to_process = df[needs_practice_areas]

    print(f"   📊 Records needing practice areas: {len(to_process)}")
    print()

    if len(to_process) == 0:
        print("✅ All records already have practice areas!")
        return

    # Process each record
    success_count = 0
    start_time = time.time()

    for idx, (df_idx, row) in enumerate(to_process.iterrows()):
        enriched_row = enrich_with_practice_areas(row, idx, len(to_process))

        # Update main dataframe
        for col in enriched_row.index:
            df.at[df_idx, col] = enriched_row[col]

        # Track success
        if enriched_row.get('practice_areas') and pd.notna(enriched_row['practice_areas']):
            success_count += 1

        # Save progress every 50 records
        if (idx + 1) % 50 == 0:
            df.to_csv(OUTPUT_CSV, index=False)
            print(f"\n    💾 Progress saved ({success_count}/{idx + 1} successful)")

    # Final save
    df.to_csv(OUTPUT_CSV, index=False)

    elapsed = time.time() - start_time

    print()
    print("=" * 80)
    print("✅ PRACTICE AREA ENRICHMENT COMPLETE")
    print("=" * 80)
    print(f"Output File: {OUTPUT_CSV}")
    print()
    print(f"Records processed: {len(to_process)}")
    print(f"Practice areas found: {success_count} ({success_count/len(to_process)*100:.1f}%)")
    print(f"Time elapsed: {elapsed:.1f} seconds ({elapsed/len(to_process):.1f}s per record)")
    print()

    # Show practice area distribution
    print("📊 PRACTICE AREA DISTRIBUTION:")
    all_practice_areas = []
    for areas in df['practice_areas'].dropna():
        if areas:
            all_practice_areas.extend([s.strip() for s in areas.split(',')])

    from collections import Counter
    area_counts = Counter(all_practice_areas)
    for area, count in area_counts.most_common(15):
        print(f"   {area}: {count}")

    print("=" * 80)


if __name__ == "__main__":
    main()
