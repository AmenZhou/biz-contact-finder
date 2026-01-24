#!/usr/bin/env python3
"""
Filter pharmacies that are open on Sunday
"""

import pandas as pd
import os

def is_open_sunday(business_hours):
    """Check if a pharmacy is open on Sunday based on business_hours string"""
    if pd.isna(business_hours) or business_hours == "":
        return False

    business_hours_str = str(business_hours).lower()

    # Check if Sunday information exists
    if 'sun:' not in business_hours_str:
        return False

    # Check if it says "Closed" for Sunday
    if 'sun: closed' in business_hours_str:
        return False

    return True

def main():
    # Input and output paths
    input_file = 'data/pharmacies/queens_pharmacies_enriched.csv'
    output_file = 'data/pharmacies/queens_pharmacies_open_sunday.csv'

    print(f"Reading data from {input_file}...")
    df = pd.read_csv(input_file)

    print(f"Total pharmacies: {len(df)}")

    # Filter pharmacies open on Sunday
    df_sunday = df[df['business_hours'].apply(is_open_sunday)]

    print(f"Pharmacies open on Sunday: {len(df_sunday)}")

    # Save to new file
    df_sunday.to_csv(output_file, index=False)
    print(f"\nSaved {len(df_sunday)} pharmacies open on Sunday to {output_file}")

    # Show some examples
    if len(df_sunday) > 0:
        print("\nSample entries:")
        for idx, row in df_sunday.head(3).iterrows():
            print(f"\n{row['name']}")
            print(f"  Address: {row['address']}")
            print(f"  Hours: {row['business_hours']}")

if __name__ == '__main__':
    main()
