#!/usr/bin/env python3
"""
Analyze address quality in the dataset
"""

import pandas as pd
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "queens_brooklyn_facilities"
INPUT_CSV = DATA_DIR / "queens_brooklyn_facilities.csv"

def is_valid_street_address(addr):
    """Check if address is a valid street address"""
    if pd.isna(addr) or addr == '':
        return False

    addr_str = str(addr).strip()

    # Must start with a number
    if not addr_str[0].isdigit():
        return False

    # Should have street name
    if ',' not in addr_str:
        return False

    return True

def is_search_snippet(addr):
    """Check if address is actually a search snippet/description"""
    if pd.isna(addr) or addr == '':
        return False

    addr_str = str(addr).strip().lower()

    # Long text is usually a snippet
    if len(addr_str) > 150:
        return True

    # Contains snippet keywords
    snippet_words = ['best', 'top 10', 'yelp', 'http', 'www', 'provide',
                     'offer', 'activities', 'services', 'reviews', 'website',
                     'located', 'serving', 'specializing']

    if any(word in addr_str for word in snippet_words):
        return True

    return False

def is_partial_address(addr):
    """Check if address is partial (has some info but not complete)"""
    if pd.isna(addr) or addr == '':
        return False

    addr_str = str(addr).strip()

    # Search snippets are not partial addresses
    if is_search_snippet(addr):
        return False

    # Valid street addresses are not partial
    if is_valid_street_address(addr):
        return False

    # Has NY but not a proper street address
    if any(state in addr_str for state in ['NY ', 'NY,', 'New York']):
        return True

    return False

def is_missing(addr):
    """Check if address is completely missing"""
    return pd.isna(addr) or addr == ''

# Load data
print("Loading data...")
df = pd.read_csv(INPUT_CSV)

print(f"\nTotal records: {len(df)}")
print("=" * 80)

# Categorize addresses
valid = df['address'].apply(is_valid_street_address)
snippets = df['address'].apply(is_search_snippet)
partial = df['address'].apply(is_partial_address)
missing = df['address'].apply(is_missing)

print("\nADDRESS QUALITY BREAKDOWN:")
print("-" * 80)
print(f"✅ Valid street addresses:     {valid.sum():5d}  ({valid.sum()/len(df)*100:.1f}%)")
print(f"⚠️  Partial addresses:          {partial.sum():5d}  ({partial.sum()/len(df)*100:.1f}%)")
print(f"❌ Search snippets (invalid):  {snippets.sum():5d}  ({snippets.sum()/len(df)*100:.1f}%)")
print(f"❌ Completely missing:         {missing.sum():5d}  ({missing.sum()/len(df)*100:.1f}%)")
print("-" * 80)
print(f"TOTAL INVALID (need fixing):   {(snippets.sum() + partial.sum() + missing.sum()):5d}")
print("=" * 80)

# Show examples
print("\n📋 EXAMPLES OF EACH CATEGORY:")
print("=" * 80)

print("\n✅ VALID STREET ADDRESSES (sample):")
print("-" * 80)
for i, row in df[valid].head(5).iterrows():
    print(f"{row['name'][:50]}")
    print(f"  → {row['address'][:80]}")
    print()

print("\n⚠️  PARTIAL ADDRESSES (sample):")
print("-" * 80)
for i, row in df[partial].head(5).iterrows():
    print(f"{row['name'][:50]}")
    print(f"  → {row['address'][:80]}")
    print()

print("\n❌ SEARCH SNIPPETS / GARBAGE (sample):")
print("-" * 80)
for i, row in df[snippets].head(5).iterrows():
    print(f"{row['name'][:50]}")
    print(f"  → {row['address'][:80]}...")
    print()

print("\n❌ COMPLETELY MISSING (sample):")
print("-" * 80)
for i, row in df[missing].head(5).iterrows():
    print(f"{row['name'][:50]}")
    print(f"  → (no address)")
    print()

print("=" * 80)
print("\n📊 RECOMMENDATION:")
print("-" * 80)
total_invalid = snippets.sum() + partial.sum() + missing.sum()
print(f"Total addresses to fix with HERE API: {total_invalid}")
print(f"Estimated cost: $0 (within free tier)")
print(f"Estimated time: ~{total_invalid * 0.5 / 60:.0f} minutes")
print("=" * 80)
