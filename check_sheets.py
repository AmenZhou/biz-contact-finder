#!/usr/bin/env python3
import zipfile
import xml.etree.ElementTree as ET

xlsx_file = '330Madison.xlsx'

with zipfile.ZipFile(xlsx_file, 'r') as zip_ref:
    # List all files in the xlsx
    print("Files in xlsx:")
    for name in zip_ref.namelist():
        if 'sheet' in name.lower():
            print(f"  {name}")

    # Check workbook.xml for sheet information
    print("\nSheet information:")
    try:
        with zip_ref.open('xl/workbook.xml') as f:
            tree = ET.parse(f)
            root = tree.getroot()
            ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            for sheet in root.findall('.//ns:sheet', ns):
                print(f"  Sheet name: {sheet.get('name')}, ID: {sheet.get('sheetId')}")
    except Exception as e:
        print(f"  Error: {e}")
