#!/usr/bin/env python3
"""
Filter pharmacies that are open on Saturday
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

def main():
    # Input and output paths
    input_file = 'data/pharmacies/queens_pharmacies_enriched.csv'
    output_file = 'data/pharmacies/queens_pharmacies_open_saturday.csv'

    print(f"Reading data from {input_file}...")
    df = pd.read_csv(input_file)

    print(f"Total pharmacies: {len(df)}")

    # Filter pharmacies open on Saturday
    df_saturday = df[df['business_hours'].apply(is_open_saturday)]

    print(f"Pharmacies open on Saturday: {len(df_saturday)}")

    # Save to new file
    df_saturday.to_csv(output_file, index=False)
    print(f"\nSaved {len(df_saturday)} pharmacies open on Saturday to {output_file}")

    # Show some examples
    if len(df_saturday) > 0:
        print("\nSample entries:")
        for idx, row in df_saturday.head(3).iterrows():
            print(f"\n{row['name']}")
            print(f"  Address: {row['address']}")
            print(f"  Hours: {row['business_hours']}")

if __name__ == '__main__':
    main()
