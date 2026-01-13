#!/usr/bin/env python3
"""
Analyze NJ church data and display basic information
"""

import pandas as pd
import sys

def main():
    # Read the Excel file
    excel_file = 'data/church_NJ.xlsx'

    print(f"Reading {excel_file}...\n")

    # Try to read all sheets
    xl_file = pd.ExcelFile(excel_file)
    print(f"Sheet names: {xl_file.sheet_names}\n")

    # Read the first sheet
    df = pd.read_excel(excel_file, sheet_name=0)

    print(f"Total records: {len(df)}")
    print(f"\nColumns: {df.columns.tolist()}\n")
    print(f"First 10 rows:\n{df.head(10)}\n")

    # Show data types
    print(f"Data types:\n{df.dtypes}\n")

    # Check for coordinate columns
    coord_cols = [col for col in df.columns if any(x in col.lower() for x in ['lat', 'lon', 'lng', 'coord', 'address'])]
    print(f"Potential coordinate/address columns: {coord_cols}\n")

    # Show sample of each column
    print("Sample data for each column:")
    for col in df.columns:
        print(f"\n{col}:")
        print(df[col].dropna().head(3).tolist())

if __name__ == '__main__':
    main()
