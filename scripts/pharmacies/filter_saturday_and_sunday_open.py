#!/usr/bin/env python3
"""
Filter pharmacies that are open on both Saturday and Sunday
"""

import pandas as pd
import os

def is_open_saturday(business_hours):
    """Check if a pharmacy is open on Saturday based on business_hours string"""
    if pd.isna(business_hours) or business_hours == "":
        return False

    business_hours_str = str(business_hours).lower()

    # Check if Saturday information exists
    if 'sat:' not in business_hours_str:
        return False

    # Check if it says "Closed" for Saturday
    if 'sat: closed' in business_hours_str:
        return False

    return True

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
    output_file = 'data/pharmacies/queens_pharmacies_open_saturday_and_sunday.csv'

    print(f"Reading data from {input_file}...")
    df = pd.read_csv(input_file)

    print(f"Total pharmacies: {len(df)}")

    # Filter pharmacies open on both Saturday and Sunday
    df_weekend = df[df['business_hours'].apply(lambda x: is_open_saturday(x) and is_open_sunday(x))]

    print(f"Pharmacies open on Saturday: {len(df[df['business_hours'].apply(is_open_saturday)])}")
    print(f"Pharmacies open on Sunday: {len(df[df['business_hours'].apply(is_open_sunday)])}")
    print(f"Pharmacies open on BOTH Saturday and Sunday: {len(df_weekend)}")

    # Save to new file
    df_weekend.to_csv(output_file, index=False)
    print(f"\nSaved {len(df_weekend)} pharmacies open on both days to {output_file}")

    # Show some examples
    if len(df_weekend) > 0:
        print("\nSample entries:")
        for idx, row in df_weekend.head(3).iterrows():
            print(f"\n{row['name']}")
            print(f"  Address: {row['address']}")
            print(f"  Hours: {row['business_hours']}")

if __name__ == '__main__':
    main()
