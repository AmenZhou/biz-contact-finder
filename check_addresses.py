#!/usr/bin/env python3
import pandas as pd

df = pd.read_csv('data/queens_brooklyn_facilities/queens_brooklyn_facilities.csv')

# Completely missing
completely_missing = df['address'].isna() | (df['address'] == '')

# Has some data but not a valid street address (doesn't start with a number)
has_data = pd.notna(df['address']) & (df['address'] != '')
no_street_number = ~df['address'].astype(str).str.strip().str[0].str.isdigit()
partial_address = has_data & no_street_number

print(f'Total records: {len(df)}')
print(f'Completely missing addresses: {completely_missing.sum()}')
print(f'Partial/invalid addresses (no street number): {partial_address.sum()}')
print(f'Valid addresses (start with number): {(~completely_missing & ~partial_address).sum()}')
print()
print('Examples of partial addresses:')
for addr in df[partial_address]['address'].head(10).tolist():
    print(f'  - {addr[:80]}')
