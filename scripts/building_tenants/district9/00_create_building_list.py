#!/usr/bin/env python3
"""
Create District 9 building list Excel file
Based on comprehensive research of W 30th-41st St, 6th-8th Ave area
"""

import pandas as pd
from pathlib import Path

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
OUTPUT_EXCEL = PROJECT_ROOT / "data" / "district_9" / "9.xlsx"

# District 9 Building List (W 30th-41st St, 6th-8th Ave)
buildings = [
    # Penn Plaza Buildings (Top Priority - Tier 1)
    {"Building Name": "One Penn Plaza", "Address": "250 West 34th Street", "Size": "2,524,000 SF", "Class": "A"},
    {"Building Name": "Two Penn Plaza", "Address": "392 Seventh Avenue", "Size": "1,800,000 SF", "Class": "A"},
    {"Building Name": "11 Penn Plaza", "Address": "150 West 32nd Street", "Size": "1,150,000 SF", "Class": "A"},
    {"Building Name": "14 Penn Plaza", "Address": "225 West 34th Street", "Size": "551,000 SF", "Class": "A"},
    {"Building Name": "330 West 34th Street", "Address": "330 West 34th Street", "Size": "682,000 SF", "Class": "A"},
    {"Building Name": "5 Penn Plaza", "Address": "461 Eighth Avenue", "Size": "611,625 SF", "Class": "A"},
    {"Building Name": "7 Penn Plaza", "Address": "370 Seventh Avenue", "Size": "357,000 SF", "Class": "B"},
    {"Building Name": "21 Penn Plaza", "Address": "360 West 31st Street", "Size": "", "Class": "B"},
    {"Building Name": "31 Penn Plaza", "Address": "132 West 31st Street", "Size": "444,556 SF", "Class": "B"},
    {"Building Name": "The Farley Building", "Address": "421 Eighth Avenue", "Size": "730,000 SF", "Class": "A"},

    # Major Broadway Towers (Tier 1)
    {"Building Name": "1411 Broadway", "Address": "1411 Broadway", "Size": "1,226,066 SF", "Class": "A"},
    {"Building Name": "1407 Broadway", "Address": "1407 Broadway", "Size": "1,100,000 SF", "Class": "A"},
    {"Building Name": "1440 Broadway", "Address": "1440 Broadway", "Size": "745,000 SF", "Class": "A"},
    {"Building Name": "1450 Broadway", "Address": "1450 Broadway", "Size": "", "Class": "A"},
    {"Building Name": "1460 Broadway", "Address": "1460 Broadway", "Size": "", "Class": "A"},
    {"Building Name": "1441 Broadway", "Address": "1441 Broadway", "Size": "", "Class": "A"},
    {"Building Name": "1385 Broadway", "Address": "1385 Broadway", "Size": "492,597 SF", "Class": "B"},
    {"Building Name": "1384 Broadway", "Address": "1384 Broadway", "Size": "204,034 SF", "Class": "B"},
    {"Building Name": "1400 Broadway", "Address": "1400 Broadway", "Size": "", "Class": "A"},
    {"Building Name": "1410 Broadway", "Address": "1410 Broadway", "Size": "385,000 SF", "Class": "A"},
    {"Building Name": "1412 Broadway (Fashion Gallery)", "Address": "1412 Broadway", "Size": "400,000 SF", "Class": "B"},
    {"Building Name": "1430 Broadway", "Address": "1430 Broadway", "Size": "", "Class": "B"},
    {"Building Name": "1350 Broadway", "Address": "1350 Broadway", "Size": "404,675 SF", "Class": "A"},
    {"Building Name": "1359 Broadway", "Address": "1359 Broadway", "Size": "", "Class": "B"},
    {"Building Name": "1328 Broadway (Marbridge Building)", "Address": "1328 Broadway", "Size": "362,191 SF", "Class": "B"},

    # Major 7th Avenue Buildings (Tier 1-2)
    {"Building Name": "450 Seventh Avenue (Nelson Tower)", "Address": "450 Seventh Avenue", "Size": "450,000 SF", "Class": "A"},
    {"Building Name": "498 Seventh Avenue", "Address": "498 Seventh Avenue", "Size": "960,000 SF", "Class": "A"},
    {"Building Name": "500 Seventh Avenue", "Address": "500 Seventh Avenue", "Size": "", "Class": "B"},
    {"Building Name": "512 Seventh Avenue", "Address": "512 Seventh Avenue", "Size": "", "Class": "B"},
    {"Building Name": "525 Seventh Avenue (Fashion Center)", "Address": "525 Seventh Avenue", "Size": "510,000 SF", "Class": "B"},
    {"Building Name": "530 Seventh Avenue", "Address": "530 Seventh Avenue", "Size": "", "Class": "B"},
    {"Building Name": "463 Seventh Avenue", "Address": "463 Seventh Avenue", "Size": "467,800 SF", "Class": "B"},
    {"Building Name": "470 Seventh Avenue", "Address": "470 Seventh Avenue", "Size": "84,575 SF", "Class": "B"},
    {"Building Name": "352 Seventh Avenue", "Address": "352 Seventh Avenue", "Size": "130,000 SF", "Class": "B"},

    # Major 8th Avenue Buildings (Tier 2)
    {"Building Name": "520 Eighth Avenue", "Address": "520 Eighth Avenue", "Size": "860,000 SF", "Class": "B"},
    {"Building Name": "545 Eighth Avenue", "Address": "545 Eighth Avenue", "Size": "", "Class": "B"},
    {"Building Name": "580 Eighth Avenue", "Address": "580 Eighth Avenue", "Size": "", "Class": "C"},
    {"Building Name": "589 Eighth Avenue", "Address": "589 Eighth Avenue", "Size": "", "Class": "C"},

    # Herald Square Area (Tier 2)
    {"Building Name": "112 West 34th Street (Kratter Building)", "Address": "112 West 34th Street", "Size": "728,429 SF", "Class": "A"},
    {"Building Name": "111 West 33rd Street", "Address": "111 West 33rd Street", "Size": "", "Class": "A"},
    {"Building Name": "110 West 34th Street", "Address": "110 West 34th Street", "Size": "53,115 SF", "Class": "B"},
    {"Building Name": "100 West 33rd Street (Manhattan Mall)", "Address": "100 West 33rd Street", "Size": "1,107,000 SF", "Class": "B"},
    {"Building Name": "333 West 34th Street", "Address": "333 West 34th Street", "Size": "346,728 SF", "Class": "B"},
    {"Building Name": "224 West 34th Street", "Address": "224 West 34th Street", "Size": "", "Class": "B"},
    {"Building Name": "41-45 West 34th Street (Monolith Building)", "Address": "41-45 West 34th Street", "Size": "114,000 SF", "Class": "B"},
    {"Building Name": "31 West 34th Street", "Address": "31 West 34th Street", "Size": "", "Class": "B"},
    {"Building Name": "50 West 34th Street (Herald Towers)", "Address": "50 West 34th Street", "Size": "1,000,000 SF", "Class": "B"},

    # West 33rd Street (Tier 2-3)
    {"Building Name": "34 West 33rd Street", "Address": "34 West 33rd Street", "Size": "", "Class": "B"},
    {"Building Name": "131 West 33rd Street", "Address": "131 West 33rd Street", "Size": "", "Class": "B"},

    # West 32nd Street (Tier 2-3)
    {"Building Name": "106 West 32nd Street (The Yard)", "Address": "106 West 32nd Street", "Size": "", "Class": "B"},

    # West 30th-31st Streets (Tier 3)
    {"Building Name": "130 West 30th Street (Cass Gilbert Building)", "Address": "130 West 30th Street", "Size": "", "Class": "B"},
    {"Building Name": "300 West 30th Street", "Address": "300 West 30th Street", "Size": "", "Class": "B"},
    {"Building Name": "251 West 30th Street", "Address": "251 West 30th Street", "Size": "", "Class": "B"},
    {"Building Name": "236 West 30th Street", "Address": "236 West 30th Street", "Size": "", "Class": "C"},
    {"Building Name": "115 West 30th Street", "Address": "115 West 30th Street", "Size": "", "Class": "C"},
    {"Building Name": "50 West 30th Street (The NOMA)", "Address": "50 West 30th Street", "Size": "", "Class": "B"},
    {"Building Name": "11 West 30th Street (Empire State Lofts)", "Address": "11 West 30th Street", "Size": "", "Class": "B"},

    # West 35th-37th Streets (Garment District - Tier 3)
    {"Building Name": "147 West 35th Street", "Address": "147 West 35th Street", "Size": "106,000 SF", "Class": "B"},
    {"Building Name": "253 West 35th Street", "Address": "253 West 35th Street", "Size": "119,588 SF", "Class": "B"},
    {"Building Name": "260 West 35th Street", "Address": "260 West 35th Street", "Size": "", "Class": "C"},
    {"Building Name": "261 West 35th Street", "Address": "261 West 35th Street", "Size": "114,368 SF", "Class": "C"},
    {"Building Name": "254-258 West 35th Street", "Address": "254-258 West 35th Street", "Size": "106,000 SF", "Class": "C"},
    {"Building Name": "237 West 35th Street", "Address": "237 West 35th Street", "Size": "", "Class": "C"},
    {"Building Name": "315 West 35th Street (The Farm)", "Address": "315 West 35th Street", "Size": "", "Class": "C"},

    # West 36th Street (Tier 3)
    {"Building Name": "307 West 36th Street", "Address": "307 West 36th Street", "Size": "", "Class": "B"},
    {"Building Name": "260 West 36th Street", "Address": "260 West 36th Street", "Size": "81,375 SF", "Class": "C"},
    {"Building Name": "255 West 36th Street", "Address": "255 West 36th Street", "Size": "", "Class": "C"},
    {"Building Name": "256-258 West 36th Street", "Address": "256-258 West 36th Street", "Size": "", "Class": "C"},
    {"Building Name": "229 West 36th Street", "Address": "229 West 36th Street", "Size": "", "Class": "C"},
    {"Building Name": "142 West 36th Street", "Address": "142 West 36th Street", "Size": "", "Class": "C"},
    {"Building Name": "135 West 36th Street (Fashion Tower)", "Address": "135 West 36th Street", "Size": "", "Class": "C"},
    {"Building Name": "70 West 36th Street", "Address": "70 West 36th Street", "Size": "", "Class": "C"},
    {"Building Name": "38 West 36th Street", "Address": "38 West 36th Street", "Size": "", "Class": "C"},
    {"Building Name": "35 West 36th Street", "Address": "35 West 36th Street", "Size": "", "Class": "C"},
    {"Building Name": "7 West 36th Street", "Address": "7 West 36th Street", "Size": "", "Class": "C"},
    {"Building Name": "355-357 West 36th Street", "Address": "355-357 West 36th Street", "Size": "", "Class": "C"},
    {"Building Name": "390 Fifth Avenue (Gorham Building)", "Address": "390 Fifth Avenue", "Size": "138,066 SF", "Class": "B"},

    # West 37th Street (Tier 3)
    {"Building Name": "134-142 West 37th Street", "Address": "134-142 West 37th Street", "Size": "120,000 SF", "Class": "B"},
    {"Building Name": "40 West 37th Street", "Address": "40 West 37th Street", "Size": "", "Class": "B"},
    {"Building Name": "20 West 37th Street", "Address": "20 West 37th Street", "Size": "69,701 SF", "Class": "B"},
    {"Building Name": "12 West 37th Street", "Address": "12 West 37th Street", "Size": "52,200 SF", "Class": "B"},
    {"Building Name": "5 West 37th Street", "Address": "5 West 37th Street", "Size": "", "Class": "B"},
    {"Building Name": "205 West 37th Street", "Address": "205 West 37th Street", "Size": "", "Class": "C"},
    {"Building Name": "265 West 37th Street", "Address": "265 West 37th Street", "Size": "", "Class": "C"},

    # West 38th-40th Streets (Tier 2-3)
    {"Building Name": "40 West 38th Street", "Address": "40 West 38th Street", "Size": "11,332 SF", "Class": "B"},
    {"Building Name": "17 West 38th Street", "Address": "17 West 38th Street", "Size": "", "Class": "C"},
    {"Building Name": "8 West 38th Street", "Address": "8 West 38th Street", "Size": "", "Class": "C"},
    {"Building Name": "48 West 38th Street", "Address": "48 West 38th Street", "Size": "", "Class": "C"},
    {"Building Name": "57 West 38th Street", "Address": "57 West 38th Street", "Size": "", "Class": "C"},
    {"Building Name": "102 West 38th Street", "Address": "102 West 38th Street", "Size": "", "Class": "C"},
    {"Building Name": "246 West 38th Street", "Address": "246 West 38th Street", "Size": "", "Class": "C"},
    {"Building Name": "256 West 38th Street", "Address": "256 West 38th Street", "Size": "", "Class": "C"},
    {"Building Name": "335 West 38th Street", "Address": "335 West 38th Street", "Size": "", "Class": "C"},
    {"Building Name": "341 West 38th Street", "Address": "341 West 38th Street", "Size": "", "Class": "C"},
    {"Building Name": "351 West 38th Street", "Address": "351 West 38th Street", "Size": "", "Class": "C"},

    # West 39th Street (Tier 2-3)
    {"Building Name": "25 West 39th Street (Engineering Societies)", "Address": "25 West 39th Street", "Size": "208,000 SF", "Class": "B"},
    {"Building Name": "42 West 39th Street", "Address": "42 West 39th Street", "Size": "174,970 SF", "Class": "B"},
    {"Building Name": "32 West 39th Street", "Address": "32 West 39th Street", "Size": "87,072 SF", "Class": "B"},
    {"Building Name": "234 West 39th Street", "Address": "234 West 39th Street", "Size": "94,283 SF", "Class": "B"},
    {"Building Name": "250 West 39th Street", "Address": "250 West 39th Street", "Size": "181,921 SF", "Class": "B"},
    {"Building Name": "251 West 39th Street", "Address": "251 West 39th Street", "Size": "117,500 SF", "Class": "B"},
    {"Building Name": "100 West 39th Street (Bryant Park Tower)", "Address": "100 West 39th Street", "Size": "", "Class": "A"},
    {"Building Name": "18 West 39th Street", "Address": "18 West 39th Street", "Size": "", "Class": "C"},
    {"Building Name": "55 West 39th Street", "Address": "55 West 39th Street", "Size": "", "Class": "C"},
    {"Building Name": "200 West 39th Street", "Address": "200 West 39th Street", "Size": "", "Class": "C"},
    {"Building Name": "214 West 39th Street", "Address": "214 West 39th Street", "Size": "", "Class": "C"},
    {"Building Name": "267 West 39th Street", "Address": "267 West 39th Street", "Size": "", "Class": "C"},
    {"Building Name": "350 West 39th Street", "Address": "350 West 39th Street", "Size": "", "Class": "C"},

    # West 40th Street (Tier 2-3)
    {"Building Name": "110 West 40th Street (World's Tower)", "Address": "110 West 40th Street", "Size": "130,000 SF", "Class": "A"},
    {"Building Name": "104 West 40th Street (Springs Mills)", "Address": "104 West 40th Street", "Size": "", "Class": "B"},
    {"Building Name": "119 West 40th Street (Lewisohn Building)", "Address": "119 West 40th Street", "Size": "", "Class": "B"},
    {"Building Name": "202 West 40th Street", "Address": "202 West 40th Street", "Size": "38,030 SF", "Class": "B"},
    {"Building Name": "24 West 40th Street", "Address": "24 West 40th Street", "Size": "", "Class": "C"},
    {"Building Name": "8 West 40th Street", "Address": "8 West 40th Street", "Size": "", "Class": "C"},
]

def main():
    """Create Excel file with District 9 buildings"""
    print("=" * 70)
    print("CREATING DISTRICT 9 BUILDING LIST")
    print("=" * 70)
    print(f"Total buildings: {len(buildings)}")
    print(f"Output file: {OUTPUT_EXCEL}")
    print()

    # Create DataFrame
    df = pd.DataFrame(buildings)

    # Print summary by class
    print("Buildings by Class:")
    for cls in ['A', 'B', 'C']:
        count = len(df[df['Class'] == cls])
        print(f"  Class {cls}: {count} buildings")
    print()

    # Ensure output directory exists
    OUTPUT_EXCEL.parent.mkdir(parents=True, exist_ok=True)

    # Save to Excel
    df.to_excel(OUTPUT_EXCEL, index=False, sheet_name='Buildings')

    print(f"✅ Created Excel file: {OUTPUT_EXCEL}")
    print(f"   {len(buildings)} buildings saved")
    print()
    print("Next step: Run 01_convert_excel_to_buildings.py to geocode addresses")

if __name__ == "__main__":
    main()
