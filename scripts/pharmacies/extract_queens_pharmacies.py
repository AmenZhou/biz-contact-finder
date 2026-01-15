#!/usr/bin/env python3
"""
Extract Queens pharmacies from the consolidated pharmacy dataset.

This script filters the all_districts_pharmacies.csv file to extract only
pharmacies located in Queens, NY. It identifies Queens pharmacies by:
1. Address containing "Queens, NY" or Queens neighborhood names
2. ZIP codes in the Queens range
"""

import csv
import re
from pathlib import Path
from collections import Counter

# Define Queens ZIP code ranges
QUEENS_ZIP_CODES = set(range(11004, 11110))  # 11004-11109
QUEENS_ZIP_CODES.update(range(11351, 11698))  # 11351-11697

# Queens neighborhood names to search for in addresses
QUEENS_NEIGHBORHOODS = [
    "Queens",
    "Astoria",
    "Long Island City",
    "Jamaica",
    "Flushing",
    "Forest Hills",
    "Rego Park",
    "Elmhurst",
    "Jackson Heights",
    "Corona",
    "Woodside",
    "Sunnyside",
    "Ridgewood",
    "Middle Village",
    "Glendale",
    "Bayside",
    "Whitestone",
    "College Point",
    "Fresh Meadows",
    "Kew Gardens",
    "Richmond Hill",
    "South Ozone Park",
    "Howard Beach",
    "Rockaway",
    "Far Rockaway",
    "Arverne",
    "Breezy Point",
    "Belle Harbor",
    "Neponsit",
    "Hollis",
    "St. Albans",
    "Cambria Heights",
    "Rosedale",
    "Laurelton",
    "Springfield Gardens",
    "Bellerose",
    "Floral Park",
    "Glen Oaks",
    "New Hyde Park",
    "Douglaston",
    "Little Neck",
    "Auburndale",
    "Murray Hill",
    "Briarwood",
    "Ozone Park",
    "Woodhaven",
]

def extract_zip_from_address(address):
    """Extract ZIP code from address string."""
    zip_match = re.search(r'\b(\d{5})\b', address)
    if zip_match:
        return int(zip_match.group(1))
    return None

def is_queens_pharmacy(address):
    """Check if the pharmacy is located in Queens based on address."""
    # Check for "Queens, NY" in address
    if "Queens, NY" in address:
        return True

    # Check for Queens neighborhoods
    for neighborhood in QUEENS_NEIGHBORHOODS:
        if f"{neighborhood}, NY" in address:
            return True

    # Check ZIP code
    zip_code = extract_zip_from_address(address)
    if zip_code and zip_code in QUEENS_ZIP_CODES:
        return True

    return False

def main():
    # File paths
    project_root = Path(__file__).parent.parent.parent
    input_file = project_root / "data" / "pharmacies" / "all_districts_pharmacies.csv"
    output_file = project_root / "data" / "pharmacies" / "queens_pharmacies.csv"

    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("QUEENS PHARMACY EXTRACTOR")
    print("=" * 60)
    print(f"\nReading from: {input_file}")
    print(f"Writing to: {output_file}")

    # Statistics
    total_count = 0
    queens_count = 0
    neighborhood_counter = Counter()
    chain_counter = Counter()

    queens_pharmacies = []

    # Read and filter pharmacies
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames

        for row in reader:
            total_count += 1
            address = row.get('address', '')

            if is_queens_pharmacy(address):
                queens_count += 1

                # Add borough column
                row['borough'] = 'Queens'
                queens_pharmacies.append(row)

                # Track neighborhood (extract from address)
                for neighborhood in QUEENS_NEIGHBORHOODS:
                    if f"{neighborhood}, NY" in address:
                        neighborhood_counter[neighborhood] += 1
                        break

                # Track pharmacy chains
                name = row.get('name', '').lower()
                if 'cvs' in name:
                    chain_counter['CVS'] += 1
                elif 'walgreens' in name or 'duane reade' in name:
                    chain_counter['Walgreens/Duane Reade'] += 1
                elif 'rite aid' in name:
                    chain_counter['Rite Aid'] += 1
                else:
                    chain_counter['Independent/Other'] += 1

    # Write Queens pharmacies to CSV
    if queens_pharmacies:
        # Add borough to fieldnames
        output_fieldnames = ['borough'] + list(fieldnames)

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=output_fieldnames)
            writer.writeheader()
            writer.writerows(queens_pharmacies)

    # Print summary report
    print("\n" + "=" * 60)
    print("EXTRACTION COMPLETE")
    print("=" * 60)
    print(f"\nTotal pharmacies in dataset: {total_count}")
    print(f"Queens pharmacies found: {queens_count}")
    print(f"Percentage: {queens_count/total_count*100:.1f}%")

    print("\n" + "-" * 60)
    print("TOP 10 NEIGHBORHOODS BY PHARMACY COUNT")
    print("-" * 60)
    for neighborhood, count in neighborhood_counter.most_common(10):
        print(f"  {neighborhood:30s} {count:3d} pharmacies")

    print("\n" + "-" * 60)
    print("PHARMACY CHAINS BREAKDOWN")
    print("-" * 60)
    for chain, count in chain_counter.most_common():
        print(f"  {chain:30s} {count:3d} locations")

    print("\n" + "=" * 60)
    print(f"✓ Queens pharmacy data saved to:")
    print(f"  {output_file}")
    print("=" * 60)

if __name__ == "__main__":
    main()
