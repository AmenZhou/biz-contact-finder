#!/usr/bin/env python3
"""
Validate CSV Data Quality

Pick random rows from a CSV file and validate key fields:
- Address format
- Category values
- Business hours format
- Phone format
- Coordinates

Usage:
    python scripts/utils/validate_csv.py <csv_file> [sample_size]

Example:
    python scripts/utils/validate_csv.py data/ma_facilities/ma_facilities.csv 20
"""

import sys
import re
import pandas as pd
from pathlib import Path


def validate_address(addr):
    """Validate address format"""
    if pd.isna(addr) or not addr:
        return False, "Missing"

    addr_str = str(addr).strip()

    # Should start with a number (street number)
    if not addr_str[0].isdigit():
        return False, "No street number"

    # Should have comma (street, city format)
    if ',' not in addr_str:
        return False, "No city/state"

    # Should have state code
    state_pattern = r',\s*[A-Z]{2}\s*,?\s*\d{5}'
    if not re.search(state_pattern, addr_str):
        return False, "No state/zip"

    return True, "Valid"


def validate_phone(phone):
    """Validate phone format"""
    if pd.isna(phone) or not phone:
        return None, "N/A"

    phone_str = str(phone).strip()

    # Remove common formatting
    digits = re.sub(r'\D', '', phone_str)

    if len(digits) >= 10:
        return True, "Valid"
    else:
        return False, "Invalid format"


def validate_hours(hours):
    """Validate business hours format"""
    if pd.isna(hours) or not hours:
        return None, "N/A"

    hours_str = str(hours).strip()

    # Check for common patterns like "Mon-Fri: 09:00 - 17:00"
    if ':' in hours_str and any(day in hours_str for day in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']):
        return True, "Valid"

    return False, "Unusual format"


def validate_coordinates(lat, lng):
    """Validate latitude/longitude"""
    try:
        if pd.isna(lat) or pd.isna(lng):
            return False, "Missing"

        lat_f = float(lat)
        lng_f = float(lng)

        # Basic range check
        if -90 <= lat_f <= 90 and -180 <= lng_f <= 180:
            return True, "Valid"
        else:
            return False, "Out of range"
    except:
        return False, "Invalid"


def validate_csv(file_path, sample_size=20):
    """Main validation function"""

    # Load CSV
    df = pd.read_csv(file_path)

    # Sample rows
    sample = df.sample(min(sample_size, len(df)), random_state=None)

    print(f"VALIDATION SAMPLE ({len(sample)} rows)")
    print("=" * 90)
    print()

    # Track issues
    issues = {
        'address': 0,
        'phone': 0,
        'hours': 0,
        'coords': 0
    }

    for idx, row in sample.iterrows():
        name = row.get('name', 'Unknown')
        print(f"Name: {name}")

        # Address
        addr = row.get('address', '')
        addr_valid, addr_status = validate_address(addr)
        icon = "✓" if addr_valid else ("○" if addr_status == "Missing" else "✗")
        print(f"  Address: {str(addr)[:60]} [{addr_status}] {icon}")
        if addr_valid == False:
            issues['address'] += 1

        # Category
        cat = row.get('category', row.get('here_category', 'N/A'))
        print(f"  Category: {cat}")

        # Hours
        hours = row.get('business_hours', '')
        hours_valid, hours_status = validate_hours(hours)
        icon = "✓" if hours_valid else ("○" if hours_status == "N/A" else "✗")
        hours_display = str(hours)[:50] if pd.notna(hours) and hours else "N/A"
        print(f"  Hours: {hours_display} [{hours_status}] {icon}")
        if hours_valid == False:
            issues['hours'] += 1

        # Phone
        phone = row.get('phone', '')
        phone_valid, phone_status = validate_phone(phone)
        if phone_status != "N/A":
            icon = "✓" if phone_valid else "✗"
            print(f"  Phone: {phone} [{phone_status}] {icon}")
            if phone_valid == False:
                issues['phone'] += 1

        # Coordinates
        lat = row.get('latitude', '')
        lng = row.get('longitude', '')
        coords_valid, coords_status = validate_coordinates(lat, lng)
        if not coords_valid:
            print(f"  Coords: {lat}, {lng} [{coords_status}] ✗")
            issues['coords'] += 1

        print()

    # Summary
    print("=" * 90)
    print("VALIDATION SUMMARY")
    print("=" * 90)
    print(f"Total rows in file: {len(df)}")
    print(f"Rows sampled: {len(sample)}")
    print()
    print("Issues found:")
    print(f"  Address issues: {issues['address']}")
    print(f"  Phone issues: {issues['phone']}")
    print(f"  Hours issues: {issues['hours']}")
    print(f"  Coordinate issues: {issues['coords']}")
    print()

    total_issues = sum(issues.values())
    if total_issues == 0:
        print("✓ All sampled rows passed validation!")
    else:
        print(f"⚠ {total_issues} issue(s) found in sample")

    print("=" * 90)


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_csv.py <csv_file> [sample_size]")
        print("Example: python validate_csv.py data/ma_facilities/ma_facilities.csv 20")
        sys.exit(1)

    file_path = sys.argv[1]
    sample_size = int(sys.argv[2]) if len(sys.argv) > 2 else 20

    if not Path(file_path).exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    validate_csv(file_path, sample_size)


if __name__ == "__main__":
    main()
