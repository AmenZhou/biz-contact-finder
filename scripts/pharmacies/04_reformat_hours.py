#!/usr/bin/env python3
"""
Reformat existing business hours in the enriched CSV to be human-readable
"""

import sys
import ast
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

import pandas as pd

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "pharmacies"
INPUT_CSV = DATA_DIR / "queens_pharmacies_enriched.csv"
OUTPUT_CSV = DATA_DIR / "queens_pharmacies_enriched.csv"


def format_business_hours(hours_data) -> str:
    """
    Format business hours into a human-readable string.
    Input can be dict, list, or string.
    """
    if pd.isna(hours_data) or hours_data == '':
        return ''

    # If it's already a formatted string (contains semicolons), return as-is
    if isinstance(hours_data, str) and ';' in hours_data:
        return hours_data

    # If it's a string representation of a dict, parse it
    if isinstance(hours_data, str) and hours_data.startswith('{'):
        try:
            hours_data = ast.literal_eval(hours_data)
        except:
            return hours_data  # Return as-is if parsing fails

    if isinstance(hours_data, dict):
        # Format as: "Mon: 8 AM–10 PM; Tue: 8 AM–10 PM; ..."
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        formatted_parts = []

        for day in day_order:
            if day in hours_data:
                # Shorten day name and clean up special characters
                day_short = day[:3]
                hours = str(hours_data[day]).replace('\u202f', ' ')  # Replace narrow no-break space
                formatted_parts.append(f"{day_short}: {hours}")

        return "; ".join(formatted_parts)

    # Fallback: return as-is
    return str(hours_data)


def main():
    print("=" * 70)
    print("REFORMATTING BUSINESS HOURS")
    print("=" * 70)
    print(f"Input/Output: {INPUT_CSV}")
    print()

    # Load data
    if not INPUT_CSV.exists():
        print(f"❌ Error: Input file not found: {INPUT_CSV}")
        sys.exit(1)

    df = pd.read_csv(INPUT_CSV)
    print(f"📊 Loaded {len(df)} pharmacies")

    # Count how many have business hours
    has_hours = df['business_hours'].notna().sum()
    print(f"🕐 Pharmacies with business hours: {has_hours}")
    print()

    # Reformat business hours
    print("Reformatting business hours...")
    df['business_hours'] = df['business_hours'].apply(format_business_hours)

    # Save
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8')

    # Show sample
    print("\n" + "=" * 70)
    print("SAMPLE REFORMATTED HOURS")
    print("=" * 70)

    sample_with_hours = df[df['business_hours'] != ''].head(5)
    for idx, row in sample_with_hours.iterrows():
        print(f"\n{row['name'][:50]}")
        print(f"  Hours: {row['business_hours']}")

    print("\n" + "=" * 70)
    print("REFORMATTING COMPLETE")
    print("=" * 70)
    print(f"✅ Updated {has_hours} business hours entries")
    print(f"📁 Output saved to: {OUTPUT_CSV}")
    print("=" * 70)


if __name__ == "__main__":
    main()
