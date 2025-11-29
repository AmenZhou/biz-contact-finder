#!/usr/bin/env python3
"""
Fix KML file by moving styles from Folder level to Document level
Google My Maps requires styles at Document level, not Folder level
"""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
KML_FILE = PROJECT_ROOT / "data" / "census" / "exports" / "brooklyn_queens_income.kml"

def fix_kml_styles(kml_path: Path):
    """Move all <Style> elements from Folder to Document level"""
    print(f"Fixing KML styles in {kml_path}...")

    # Read KML file
    with open(kml_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract all <Style>...</Style> blocks from the file
    style_pattern = r'<Style id="(\d+)".*?</Style>\s*'
    styles = re.findall(style_pattern, content, re.DOTALL)

    print(f"Found {len(styles)} style elements")

    # Extract full style blocks
    style_blocks = re.findall(r'(<Style id="\d+".*?</Style>)', content, re.DOTALL)

    # Remove styles from their current locations
    for style_block in style_blocks:
        content = content.replace(style_block + '\n', '', 1)

    # Find the </description> tag after Document and insert styles there
    # This puts styles at Document level
    insert_point = content.find('</description>', content.find('<Document'))

    if insert_point == -1:
        print("Error: Could not find insertion point")
        return False

    # Move past the </description> tag and newline
    insert_point = content.find('\n', insert_point) + 1

    # Create styles section
    styles_section = '\n        <!-- Styles moved to Document level for Google My Maps compatibility -->\n'
    for style_block in style_blocks:
        # Indent properly for Document level
        indented_style = '        ' + style_block.replace('\n', '\n        ')
        styles_section += indented_style + '\n'

    # Insert styles at Document level
    content = content[:insert_point] + styles_section + content[insert_point:]

    # Write fixed KML
    with open(kml_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✓ Moved {len(style_blocks)} styles to Document level")
    return True

if __name__ == "__main__":
    fix_kml_styles(KML_FILE)
    print("✓ KML file fixed successfully!")
