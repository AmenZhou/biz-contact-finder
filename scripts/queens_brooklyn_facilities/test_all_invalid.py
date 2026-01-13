#!/usr/bin/env python3
"""
Test enrichment on sample of ALL invalid address types
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

import pandas as pd
import os
import time
import requests
from typing import Dict, List, Optional

# Import functions from main script
exec(open('scripts/queens_brooklyn_facilities/03_enrich_with_addresses.py').read(), globals())

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "queens_brooklyn_facilities"
INPUT_CSV = DATA_DIR / "queens_brooklyn_facilities.csv"

# API Configuration
HERE_API_KEY = os.getenv("HERE_API_KEY")

if not HERE_API_KEY:
    print("❌ Error: HERE_API_KEY environment variable not set")
    sys.exit(1)

def main():
    """Test on all types of invalid addresses"""
    print("=" * 80)
    print("TESTING ALL INVALID ADDRESS TYPES")
    print("=" * 80)
    print()

    # Load data
    df = pd.read_csv(INPUT_CSV)
    print(f"Loaded {len(df)} records")
    print()

    # Find all invalid addresses
    invalid_mask = df['address'].apply(needs_enrichment)
    invalid_df = df[invalid_mask]

    print(f"Found {len(invalid_df)} invalid addresses")
    print()

    # Sample different types
    print("Selecting sample addresses...")

    # Get samples of each type
    missing = invalid_df[df['address'].isna() | (df['address'] == '')]
    snippets = invalid_df[df['address'].apply(lambda x: len(str(x)) > 100 if pd.notna(x) else False)]
    partial = invalid_df[~invalid_df.index.isin(missing.index) & ~invalid_df.index.isin(snippets.index)]

    samples = pd.concat([
        missing.head(2),
        partial.head(4),
        snippets.head(4)
    ])

    print(f"Testing with {len(samples)} samples:")
    print(f"  - {len(missing.head(2))} missing addresses")
    print(f"  - {len(partial.head(4))} partial addresses")
    print(f"  - {len(snippets.head(4))} search snippets")
    print()

    # Test each
    success_count = 0
    for idx, row in samples.iterrows():
        print(f"[{success_count + 1}/{len(samples)}] {row['name'][:50]}")
        print(f"  Type: {'MISSING' if pd.isna(row['address']) or not row['address'] else ('SNIPPET' if len(str(row['address'])) > 100 else 'PARTIAL')}")
        print(f"  Before: {row['address'] if pd.notna(row['address']) else '(none)'}".replace('\n', ' ')[:80])

        # Enrich
        enriched = enrich_with_address(row.copy())

        if is_valid_street_address(enriched['address']):
            success_count += 1
            print(f"  ✅ SUCCESS")
        else:
            print(f"  ⚠️  Still invalid")

        print()
        time.sleep(1)

    print("=" * 80)
    print(f"Results: {success_count}/{len(samples)} successfully enriched")
    print(f"Success rate: {success_count/len(samples)*100:.1f}%")
    print("=" * 80)

if __name__ == "__main__":
    main()
