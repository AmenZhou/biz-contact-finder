#!/usr/bin/env python3
"""
Enrich doctor offices with medical specialties using LLM and name parsing
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
DATA_DIR = PROJECT_ROOT / "data" / "medical_offices"
INPUT_CSV = DATA_DIR / "queens_brooklyn_doctors_final.csv"
OUTPUT_CSV = DATA_DIR / "queens_brooklyn_doctors_with_specialties.csv"

# API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    print("❌ Error: OPENAI_API_KEY environment variable not set")
    sys.exit(1)

# Initialize OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Common medical specialties keywords
SPECIALTY_KEYWORDS = {
    "Primary Care": ["primary care", "general practice", "family practice", "family medicine", "family doctor"],
    "Internal Medicine": ["internal medicine", "internist"],
    "Pediatrics": ["pediatric", "pediatrician", "children", "kids"],
    "Cardiology": ["cardio", "heart"],
    "Dermatology": ["derma", "skin"],
    "Orthopedics": ["orthopedic", "ortho", "bone", "sports medicine"],
    "OB/GYN": ["obgyn", "ob/gyn", "obstetrics", "gynecology", "women"],
    "Psychiatry": ["psychiatr", "mental health"],
    "Ophthalmology": ["ophthal", "eye", "vision"],
    "ENT": ["ent", "ear nose throat", "otolaryngology"],
    "Urgent Care": ["urgent care", "walk-in", "immediate care"],
    "Gastroenterology": ["gastro", "digestive"],
    "Neurology": ["neuro", "brain"],
    "Pulmonology": ["pulmo", "lung", "respiratory"],
    "Nephrology": ["nephr", "kidney"],
    "Endocrinology": ["endo", "diabetes", "hormone"],
    "Rheumatology": ["rheumat", "arthritis"],
    "Oncology": ["onco", "cancer"],
    "Urology": ["uro", "urolog"],
    "Allergy": ["allergy", "allergist"],
}

# Specialty normalization map
SPECIALTY_NORMALIZATION = {
    "general practice": "Primary Care",
    "family practice": "Primary Care",
    "family medicine": "Primary Care",
    "family doctor": "Primary Care",
    "general medicine": "Primary Care",
    "internist": "Internal Medicine",
}


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
    """Extract clean text from HTML, prioritizing specialty-related content"""
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


def extract_specialties_from_name(name: str) -> List[str]:
    """Extract specialties from office name using keyword matching"""
    specialties = []
    name_lower = name.lower()

    for specialty, keywords in SPECIALTY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in name_lower:
                specialties.append(specialty)
                break

    return list(set(specialties))  # Remove duplicates


def normalize_specialties(specialties: List[str]) -> List[str]:
    """Normalize and deduplicate specialty names"""
    normalized = []
    seen = set()

    for spec in specialties:
        spec_lower = spec.lower().strip()

        # Check if it needs normalization
        normalized_spec = SPECIALTY_NORMALIZATION.get(spec_lower, spec.strip())

        # Avoid duplicates
        if normalized_spec not in seen:
            normalized.append(normalized_spec)
            seen.add(normalized_spec)

    return normalized


def extract_specialties_with_llm(website_text: str, office_name: str) -> List[str]:
    """Use OpenAI to extract medical specialties from website text"""

    prompt = f"""You are extracting medical specialties from a doctor's office website.

Office Name: {office_name}

Website Content:
{website_text}

Extract and return medical specialties offered at this office.

Common specialties include:
- Primary Care / Family Medicine / General Practice
- Internal Medicine
- Pediatrics
- Cardiology
- Dermatology
- Orthopedics
- OB/GYN
- Psychiatry
- Ophthalmology
- ENT
- Urgent Care
- Gastroenterology
- Neurology
- And other medical specialties

Return your response as a JSON object with a "specialties" array.
Example: {{"specialties": ["Primary Care", "Internal Medicine"]}}
If no specific specialties are found, return: {{"specialties": ["General Practice"]}}
"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a medical specialty extraction assistant. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=150
        )

        result = response.choices[0].message.content.strip()

        import json
        data = json.loads(result)

        if isinstance(data.get('specialties'), list):
            return data['specialties']
        return []

    except Exception as e:
        logging.error(f"Error extracting specialties with LLM: {str(e)[:100]}")
        return []


def enrich_with_specialties(row: pd.Series, index: int, total: int) -> pd.Series:
    """Enrich a single record with medical specialties"""

    print(f"\n[{index + 1}/{total}] {row['name'][:60]}")

    # Skip if already has specialties
    if pd.notna(row.get('specialties')) and row.get('specialties'):
        print("    ✓ Already has specialties")
        return row

    specialties = []
    made_api_call = False

    # 1. Extract from name
    name_specialties = extract_specialties_from_name(row['name'])
    if name_specialties:
        specialties.extend(name_specialties)
        print(f"    📝 From name: {', '.join(name_specialties)}")

    # 2. Extract from website if available
    if row.get('website') and pd.notna(row['website']):
        print(f"    🌐 Fetching website...")
        html = fetch_website_content(row['website'])
        if html:
            text = extract_text_from_html(html)
            if text:
                print(f"    🤖 Extracting specialties with LLM...")
                llm_specialties = extract_specialties_with_llm(text, row['name'])
                made_api_call = True
                if llm_specialties:
                    specialties.extend(llm_specialties)
                    print(f"    ✅ From website: {', '.join(llm_specialties)}")

    # Normalize and remove duplicates
    specialties = normalize_specialties(specialties)

    # If no specialties found, use search query as hint
    if not specialties:
        search_query = row.get('search_query', '').lower()
        if 'urgent' in search_query or 'walk-in' in search_query:
            specialties = ["Urgent Care"]
        elif 'primary' in search_query or 'family' in search_query:
            specialties = ["Primary Care"]
        elif 'internal' in search_query:
            specialties = ["Internal Medicine"]
        else:
            specialties = ["General Practice"]

        print(f"    💡 Inferred: {', '.join(specialties)}")

    # Update row
    row['specialties'] = ", ".join(specialties)

    if not specialties:
        print("    ❌ No specialties found")
    else:
        print(f"    ✅ Final: {row['specialties']}")

    # Rate limiting - only sleep if we made an API call
    if made_api_call:
        time.sleep(0.5)

    return row


def main():
    """Main execution"""
    print("=" * 80)
    print("ENRICHING DOCTOR OFFICES WITH MEDICAL SPECIALTIES")
    print("=" * 80)
    print()

    # Load CSV
    if not INPUT_CSV.exists():
        print(f"❌ Error: CSV file not found at {INPUT_CSV}")
        sys.exit(1)

    print(f"📂 Loading data from {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV)

    # Add specialties column if it doesn't exist
    if 'specialties' not in df.columns:
        df['specialties'] = ""

    print(f"   ✓ Loaded {len(df)} total records")
    print()

    # Count records needing enrichment
    needs_specialties = df['specialties'].isna() | (df['specialties'] == '')
    to_process = df[needs_specialties]

    print(f"   📊 Records needing specialties: {len(to_process)}")
    print()

    if len(to_process) == 0:
        print("✅ All records already have specialties!")
        return

    # Process each record
    success_count = 0
    start_time = time.time()

    for idx, (df_idx, row) in enumerate(to_process.iterrows()):
        enriched_row = enrich_with_specialties(row, idx, len(to_process))

        # Update main dataframe
        for col in enriched_row.index:
            df.at[df_idx, col] = enriched_row[col]

        # Track success
        if enriched_row.get('specialties') and pd.notna(enriched_row['specialties']):
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
    print("✅ SPECIALTY ENRICHMENT COMPLETE")
    print("=" * 80)
    print(f"Output File: {OUTPUT_CSV}")
    print()
    print(f"Records processed: {len(to_process)}")
    print(f"Specialties found: {success_count} ({success_count/len(to_process)*100:.1f}%)")
    print(f"Time elapsed: {elapsed:.1f} seconds ({elapsed/len(to_process):.1f}s per record)")
    print()

    # Show specialty distribution
    print("📊 SPECIALTY DISTRIBUTION:")
    all_specialties = []
    for specs in df['specialties'].dropna():
        if specs:
            all_specialties.extend([s.strip() for s in specs.split(',')])

    from collections import Counter
    spec_counts = Counter(all_specialties)
    for spec, count in spec_counts.most_common(15):
        print(f"   {spec}: {count}")

    print("=" * 80)


if __name__ == "__main__":
    main()
