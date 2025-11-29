#!/usr/bin/env python3
"""
Combine all District 18 building management contacts into a single CSV file
Ensures Windows compatibility with proper encoding
"""

import csv
import os
from pathlib import Path
from typing import List, Dict
import unicodedata

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "building_tenants"
TENANTS_DIR = DATA_DIR / "tenants" / "district18"
OUTPUT_CSV = DATA_DIR / "exports" / "district18_building_management_contacts.csv"


def clean_for_windows(text: str) -> str:
    """Clean text to be Windows-compatible, removing problematic Unicode characters"""
    if not text or text == 'N/A':
        return ''

    # Replace common problematic characters
    replacements = {
        '\u2013': '-',  # en dash
        '\u2014': '--',  # em dash
        '\u2018': "'",  # left single quote
        '\u2019': "'",  # right single quote
        '\u201c': '"',  # left double quote
        '\u201d': '"',  # right double quote
        '\u2026': '...',  # ellipsis
        '\xa0': ' ',  # non-breaking space
        '\u00a0': ' ',  # non-breaking space (alternate)
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # Normalize Unicode (convert accented characters to closest ASCII equivalent)
    text = unicodedata.normalize('NFKD', text)

    # Remove any remaining non-ASCII characters
    text = text.encode('ascii', 'ignore').decode('ascii')

    # Clean up whitespace
    text = ' '.join(text.split())

    return text.strip()


def combine_building_contacts() -> None:
    """Combine all building management contact CSV files into one"""
    print("=" * 60)
    print("COMBINING DISTRICT 18 BUILDING MANAGEMENT CONTACTS")
    print("=" * 60)

    # Find all building_contacts CSV files
    contact_files = list(TENANTS_DIR.glob("*_building_contacts.csv"))
    print(f"\nFound {len(contact_files)} building contact files")

    if not contact_files:
        print("No building contact files found!")
        return

    # Collect all contacts
    all_contacts = []
    buildings_processed = 0

    for contact_file in sorted(contact_files):
        # Extract building address from filename
        # Format: "630 5th Ave New York NY_building_contacts.csv"
        building_address = contact_file.stem.replace('_building_contacts', '').replace(' New York NY', ', New York, NY')

        try:
            with open(contact_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                contacts = list(reader)

                if contacts:
                    buildings_processed += 1
                    print(f"  {building_address}: {len(contacts)} contact(s)")

                    # Add building address to each contact
                    for contact in contacts:
                        contact['building_address'] = building_address
                        all_contacts.append(contact)

        except Exception as e:
            print(f"  ERROR reading {contact_file.name}: {e}")
            continue

    print(f"\nTotal contacts collected: {len(all_contacts)}")
    print(f"Buildings with contacts: {buildings_processed}")

    if not all_contacts:
        print("No contacts to export!")
        return

    # Define output columns (reordered for clarity)
    output_columns = [
        'building_address',
        'building_name',
        'contact_name',
        'contact_title',
        'email',
        'email_secondary',
        'phone',
        'phone_secondary',
        'website',
        'linkedin',
        'instagram',
        'address'
    ]

    # Create exports directory
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    # Write combined CSV with Windows-compatible encoding
    print(f"\nWriting to: {OUTPUT_CSV}")

    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8-sig') as f:  # utf-8-sig adds BOM for Excel
        writer = csv.DictWriter(f, fieldnames=output_columns, extrasaction='ignore')
        writer.writeheader()

        for contact in all_contacts:
            # Clean all fields for Windows compatibility
            cleaned_contact = {}
            for key, value in contact.items():
                if key in output_columns:
                    cleaned_contact[key] = clean_for_windows(str(value)) if value else ''

            writer.writerow(cleaned_contact)

    print(f"✓ Combined CSV saved: {OUTPUT_CSV}")
    print(f"  Total rows: {len(all_contacts)}")
    print(f"  Encoding: UTF-8 with BOM (Windows Excel compatible)")

    # Print summary statistics
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    # Count contacts with email/phone
    with_email = sum(1 for c in all_contacts if c.get('email') and c['email'] not in ['', 'N/A'])
    with_phone = sum(1 for c in all_contacts if c.get('phone') and c['phone'] not in ['', 'N/A'])
    with_website = sum(1 for c in all_contacts if c.get('website') and c['website'] not in ['', 'N/A'])

    print(f"Total Contacts: {len(all_contacts)}")
    print(f"Contacts with Email: {with_email} ({with_email/len(all_contacts)*100:.1f}%)")
    print(f"Contacts with Phone: {with_phone} ({with_phone/len(all_contacts)*100:.1f}%)")
    print(f"Contacts with Website: {with_website} ({with_website/len(all_contacts)*100:.1f}%)")
    print("=" * 60)


def main():
    """Entry point"""
    try:
        combine_building_contacts()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
