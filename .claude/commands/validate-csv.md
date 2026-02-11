# Validate CSV Data

Validate a sample of rows from a CSV file to ensure data quality.

## Usage
```
/validate-csv <csv_file_path> [sample_size]
```

## Arguments
- `csv_file_path`: Path to the CSV file to validate (required)
- `sample_size`: Number of rows to sample (default: 20)

## Instructions

When this command is invoked:

1. Load the specified CSV file
2. Pick a random sample of rows (default 20)
3. For each row, display and validate:
   - **Name**: Check it's not empty
   - **Address**: Validate format (should have street number, street name, city, state, zip)
   - **Category**: Check it matches expected values for the facility type
   - **Business Hours**: Check format if present (e.g., "Mon-Fri: 09:00 - 17:00")
   - **Phone**: Validate phone format if present
   - **Coordinates**: Check latitude/longitude are valid numbers

4. Provide a summary:
   - Total rows sampled
   - Number of valid rows
   - Any issues found

## Example Output

```
VALIDATION SAMPLE (20 rows)
================================================================================
Name: Richards Memorial Library
  Address: 118, N Washington St, North Attleboro, MA, 02760-1633 ✓
  Category: Library ✓
  Hours: Mon-Thu: 09:00 - 20:00; Fri, Sat: 09:00 - 17:00 ✓

[... more rows ...]

SUMMARY
================================================================================
Rows sampled: 20
Valid rows: 18 (90%)
Issues found:
  - 2 rows missing business hours
```

## Python Script

Run this validation with:

```python
import pandas as pd
import random

def validate_csv(file_path, sample_size=20):
    df = pd.read_csv(file_path)
    sample = df.sample(min(sample_size, len(df)))

    print(f'VALIDATION SAMPLE ({len(sample)} rows)')
    print('='*80)

    issues = []
    for idx, row in sample.iterrows():
        print(f"Name: {row.get('name', 'N/A')}")

        # Address validation
        addr = row.get('address', '')
        addr_valid = bool(addr) and ',' in str(addr)
        print(f"  Address: {addr} {'✓' if addr_valid else '✗'}")
        if not addr_valid:
            issues.append(f"Invalid address: {row.get('name')}")

        # Category validation
        cat = row.get('category', row.get('here_category', 'N/A'))
        print(f"  Category: {cat}")

        # Hours validation
        hours = row.get('business_hours', '')
        hours_str = str(hours) if pd.notna(hours) and hours else 'N/A'
        print(f"  Hours: {hours_str}")

        print()

    print('SUMMARY')
    print('='*80)
    print(f"Rows sampled: {len(sample)}")
    print(f"Issues found: {len(issues)}")
    for issue in issues[:10]:
        print(f"  - {issue}")
```
