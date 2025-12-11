#!/usr/bin/env python3
"""
Extract addresses from law office websites using LLM
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from typing import Dict, Optional
from bs4 import BeautifulSoup

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

import pandas as pd
from openai import OpenAI

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "law_offices"
INPUT_CSV = DATA_DIR / "queens_brooklyn_law_offices.csv"
OUTPUT_CSV = DATA_DIR / "queens_brooklyn_law_offices_with_addresses_llm.csv"

# API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    print("❌ Error: OPENAI_API_KEY environment variable not set")
    sys.exit(1)

# Initialize OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Test mode - set to number of records to test, or None for full run
TEST_MODE = None  # Full run on all records


def fetch_website_content(url: str, timeout: int = 30) -> Optional[str]:
    """Fetch website HTML content"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status()
        return response.text

    except Exception as e:
        print(f"    ⚠️  Failed to fetch: {e}")
        return None


def extract_text_from_html(html: str) -> str:
    """Extract clean text from HTML"""
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

        # Limit to first 3000 characters to save on API costs
        return text[:3000]

    except Exception as e:
        print(f"    ⚠️  Failed to parse HTML: {e}")
        return ""


def extract_address_with_llm(website_text: str, office_name: str) -> Dict:
    """Use OpenAI to extract address information from website text"""

    prompt = f"""You are extracting contact information from a law office website.

Office Name: {office_name}

Website Content:
{website_text}

Extract and return ONLY a JSON object with these fields:
- "address": Full street address (e.g., "123 Main St, Brooklyn, NY 11201"). Must be in Brooklyn or Queens, NY.
- "phone": Phone number in format (XXX) XXX-XXXX
- "suite": Suite or unit number if mentioned
- "business_hours": Operating hours if mentioned (e.g., "Mon-Fri 9am-5pm")
- "confidence": Your confidence level (high/medium/low)

Important:
- Only extract if you find a clear physical address in Brooklyn or Queens
- If no address found, return empty strings
- Return ONLY valid JSON, no explanation

Example:
{{"address": "25-20 30th Avenue, Astoria, NY 11102", "phone": "(718) 808-7777", "suite": "Suite 200", "business_hours": "Mon-Fri 9am-5pm, Sat 10am-2pm", "confidence": "high"}}
"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a precise data extraction assistant. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=250
        )

        result = response.choices[0].message.content.strip()

        # Try to parse JSON
        # Sometimes LLM returns with markdown code blocks
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]

        extracted = json.loads(result)

        # Handle case where OpenAI returns a list instead of dict
        if isinstance(extracted, list):
            print(f"    ⚠️  LLM returned list instead of dict, using first item")
            if len(extracted) > 0 and isinstance(extracted[0], dict):
                extracted = extracted[0]
            else:
                return {"address": "", "phone": "", "suite": "", "business_hours": "", "confidence": ""}

        # Ensure it's a dict
        if not isinstance(extracted, dict):
            print(f"    ⚠️  LLM returned unexpected type: {type(extracted)}")
            return {"address": "", "phone": "", "suite": "", "business_hours": "", "confidence": ""}

        return extracted

    except json.JSONDecodeError as e:
        print(f"    ⚠️  JSON parse error: {e}")
        print(f"    Response was: {result[:200]}")
        return {"address": "", "phone": "", "suite": "", "business_hours": "", "confidence": ""}

    except Exception as e:
        print(f"    ⚠️  LLM extraction error: {e}")
        return {"address": "", "phone": "", "suite": "", "business_hours": "", "confidence": ""}


def process_record(row: pd.Series, index: int, total: int) -> pd.Series:
    """Process a single law office record"""

    print(f"\n[{index + 1}/{total}] {row['name'][:60]}")

    # Skip if no website
    if pd.isna(row['website']) or not row['website']:
        print("    ⏭️  No website URL")
        return row

    # Skip if already has address
    if pd.notna(row.get('address')) and row.get('address'):
        print("    ✓ Already has address")
        return row

    website = row['website']
    print(f"    🌐 Fetching: {website[:60]}...")

    # Fetch website
    html = fetch_website_content(website)
    if not html:
        return row

    # Extract text
    text = extract_text_from_html(html)
    if not text:
        print("    ⚠️  No text extracted from HTML")
        return row

    print(f"    🤖 Extracting with LLM... ({len(text)} chars)")

    # Extract with LLM
    extracted = extract_address_with_llm(text, row['name'])

    # Update row
    if extracted.get('address'):
        row['address'] = extracted['address']
        print(f"    ✅ Address: {extracted['address']}")

    if extracted.get('phone') and not row.get('phone'):
        row['phone'] = extracted['phone']
        print(f"    ✅ Phone: {extracted['phone']}")

    if extracted.get('suite'):
        row['suite'] = extracted['suite']

    if extracted.get('business_hours'):
        row['business_hours'] = extracted['business_hours']
        print(f"    ✅ Hours: {extracted['business_hours']}")

    if extracted.get('confidence'):
        row['llm_confidence'] = extracted['confidence']

    if not extracted.get('address'):
        print("    ❌ No address found")

    return row


def main():
    """Main execution"""
    print("=" * 80)
    print("LLM-BASED ADDRESS EXTRACTION FROM LAW OFFICE WEBSITES")
    print("=" * 80)
    print()

    if TEST_MODE:
        print(f"🧪 TEST MODE: Processing first {TEST_MODE} records")
        print()

    # Load CSV
    if not INPUT_CSV.exists():
        print(f"❌ Error: CSV file not found at {INPUT_CSV}")
        sys.exit(1)

    print(f"📂 Loading data from {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV)

    # Add new columns if they don't exist
    if 'suite' not in df.columns:
        df['suite'] = ""
    if 'business_hours' not in df.columns:
        df['business_hours'] = ""
    if 'llm_confidence' not in df.columns:
        df['llm_confidence'] = ""

    # Filter to records with websites but no addresses
    needs_enrichment = df['website'].notna() & (df['website'] != '')
    missing_address = df['address'].isna() | (df['address'] == '')
    to_process = df[needs_enrichment & missing_address]

    print(f"   ✓ Loaded {len(df)} total records")
    print(f"   📊 Records needing enrichment: {len(to_process)}")
    print()

    if len(to_process) == 0:
        print("✅ All records already have addresses!")
        return

    # Test mode - only process first N
    if TEST_MODE:
        to_process = to_process.head(TEST_MODE)
        print(f"   🧪 Testing on {len(to_process)} records")
        print()

    # Process each record
    success_count = 0
    start_time = time.time()

    for idx, (df_idx, row) in enumerate(to_process.iterrows()):
        processed_row = process_record(row, idx, len(to_process))

        # Update main dataframe
        for col in processed_row.index:
            df.at[df_idx, col] = processed_row[col]

        # Track success
        if processed_row.get('address') and pd.notna(processed_row['address']):
            success_count += 1

        # Rate limiting
        time.sleep(1)

        # Save progress every 10 records
        if (idx + 1) % 10 == 0:
            df.to_csv(OUTPUT_CSV, index=False)
            print(f"\n    💾 Progress saved ({success_count}/{idx + 1} successful)")

    # Final save
    df.to_csv(OUTPUT_CSV, index=False)

    elapsed = time.time() - start_time

    print()
    print("=" * 80)
    print("✅ EXTRACTION COMPLETE")
    print("=" * 80)
    print(f"Output File: {OUTPUT_CSV}")
    print()
    print(f"Records processed: {len(to_process)}")
    print(f"Addresses found: {success_count} ({success_count/len(to_process)*100:.1f}%)")
    print(f"Time elapsed: {elapsed:.1f} seconds ({elapsed/len(to_process):.1f}s per record)")
    print()

    if TEST_MODE:
        # Calculate estimates for full run
        total_to_process = len(df[needs_enrichment & missing_address])
        est_time = (elapsed / len(to_process)) * total_to_process
        est_cost = (total_to_process * 0.0005)  # Rough estimate: $0.0005 per record

        print("📊 ESTIMATES FOR FULL RUN:")
        print(f"   Total records to process: {total_to_process}")
        print(f"   Estimated time: {est_time/60:.1f} minutes")
        print(f"   Estimated cost: ${est_cost:.2f}")
        print()
        print("💡 To run on all records, edit the script and set TEST_MODE = None")

    print("=" * 80)


if __name__ == "__main__":
    main()
