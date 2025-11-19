#!/usr/bin/env python3
import zipfile
import xml.etree.ElementTree as ET
import csv
import sys

def xlsx_to_csv(xlsx_file, csv_file):
    with zipfile.ZipFile(xlsx_file, 'r') as zip_ref:
        # Read shared strings if they exist
        shared_strings = []
        try:
            with zip_ref.open('xl/sharedStrings.xml') as f:
                tree = ET.parse(f)
                root = tree.getroot()
                ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                for si in root.findall('.//ns:si', ns):
                    t = si.find('.//ns:t', ns)
                    if t is not None:
                        shared_strings.append(t.text)
        except KeyError:
            pass  # No shared strings

        # Read the first worksheet
        with zip_ref.open('xl/worksheets/sheet1.xml') as f:
            tree = ET.parse(f)
            root = tree.getroot()
            ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

            rows_data = []
            for row in root.findall('.//ns:row', ns):
                cells = row.findall('.//ns:c', ns)

                if not cells:
                    continue

                # Get max column index
                max_col = 0
                for cell in cells:
                    ref = cell.get('r')
                    col_idx = 0
                    for char in ref:
                        if char.isalpha():
                            col_idx = col_idx * 26 + (ord(char.upper()) - ord('A') + 1)
                        else:
                            break
                    max_col = max(max_col, col_idx)

                # Initialize row with empty strings
                row_data = [''] * max_col

                for cell in cells:
                    ref = cell.get('r')
                    cell_type = cell.get('t')

                    # Parse column index
                    col_idx = 0
                    for char in ref:
                        if char.isalpha():
                            col_idx = col_idx * 26 + (ord(char.upper()) - ord('A') + 1)
                        else:
                            break
                    col_idx -= 1  # Convert to 0-based

                    value = ''

                    # Check for inline string
                    if cell_type == 'inlineStr':
                        is_elem = cell.find('.//ns:is', ns)
                        if is_elem is not None:
                            t_elem = is_elem.find('.//ns:t', ns)
                            if t_elem is not None:
                                value = t_elem.text if t_elem.text else ''
                    # Check for shared string
                    elif cell_type == 's':
                        v = cell.find('.//ns:v', ns)
                        if v is not None and v.text:
                            try:
                                value = shared_strings[int(v.text)]
                            except (IndexError, ValueError):
                                value = v.text
                    # Regular value
                    else:
                        v = cell.find('.//ns:v', ns)
                        if v is not None:
                            value = v.text if v.text else ''

                    row_data[col_idx] = value

                rows_data.append(row_data)

            # Write to CSV
            with open(csv_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerows(rows_data)

            print(f"Successfully converted {xlsx_file} to {csv_file}")
            print(f"Total rows: {len(rows_data)}")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        xlsx_file = sys.argv[1]
        csv_file = sys.argv[2] if len(sys.argv) > 2 else xlsx_file.replace('.xlsx', '.csv')
    else:
        xlsx_file = '330Madison.xlsx'
        csv_file = '330Madison.csv'

    xlsx_to_csv(xlsx_file, csv_file)
