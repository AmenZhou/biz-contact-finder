#!/usr/bin/env python3
"""
Export Brooklyn & Queens Census Tract Median Household Income to KMZ
Creates color-coded choropleth map similar to JusticeMap.org
"""

import os
import sys
import requests
import zipfile
from pathlib import Path
from typing import Dict, List, Optional
import json

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

import geopandas as gpd
import pandas as pd
import simplekml
from simplekml import Kml


# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "census"
BOUNDARIES_DIR = DATA_DIR / "boundaries"
EXPORTS_DIR = DATA_DIR / "exports"
OUTPUT_KML = EXPORTS_DIR / "brooklyn_queens_income.kml"
OUTPUT_KMZ = EXPORTS_DIR / "brooklyn_queens_income.kmz"

# Census API Configuration
CENSUS_API_URL = "https://api.census.gov/data/2022/acs/acs5"
# Brooklyn (Kings County): 047, Queens County: 081
BROOKLYN_FIPS = "047"
QUEENS_FIPS = "081"
NY_STATE_FIPS = "36"

# Color bins for median household income (vibrant, fully opaque colors)
# KML colors are in 'aabbggrr' format (alpha, blue, green, red)
# Using deep red → orange → yellow → green gradient for intuitive income visualization
INCOME_BINS = [
    {"max": 40000, "color": "ff0000CC", "label": "< $40,000 (Low)"},          # Deep Red
    {"max": 60000, "color": "ff0066FF", "label": "$40,000 - $60,000"},        # Bright Orange
    {"max": 80000, "color": "ff00FFFF", "label": "$60,000 - $80,000"},        # Bright Yellow
    {"max": 100000, "color": "ff66FF66", "label": "$80,000 - $100,000"},      # Light Green
    {"max": 125000, "color": "ff00DD00", "label": "$100,000 - $125,000"},     # Bright Green
    {"max": float('inf'), "color": "ff008800", "label": "$125,000+ (High)"}   # Dark Green
]


def download_census_tracts() -> Path:
    """Download TIGER/Line shapefiles for Brooklyn and Queens census tracts"""
    print("\n1. Downloading census tract boundaries...")

    # Create boundaries directory
    BOUNDARIES_DIR.mkdir(parents=True, exist_ok=True)

    # TIGER/Line 2022 URL for NY census tracts
    url = "https://www2.census.gov/geo/tiger/TIGER2022/TRACT/tl_2022_36_tract.zip"
    zip_path = BOUNDARIES_DIR / "tl_2022_36_tract.zip"

    if not zip_path.exists():
        print(f"   Downloading from {url}...")
        response = requests.get(url, stream=True)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    percent = (downloaded / total_size) * 100
                    print(f"\r   Progress: {percent:.1f}%", end='')
        print()

        # Extract shapefile
        print("   Extracting shapefile...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(BOUNDARIES_DIR)

        print(f"   ✓ Downloaded and extracted to {BOUNDARIES_DIR}")
    else:
        print(f"   ✓ Using cached shapefile at {zip_path}")

    return BOUNDARIES_DIR / "tl_2022_36_tract.shp"


def fetch_income_data() -> pd.DataFrame:
    """Fetch median household income data from Census ACS API"""
    print("\n2. Fetching median household income data from Census API...")

    # Build API request for both Brooklyn and Queens
    params = {
        'get': 'NAME,B19013_001E',  # B19013_001E = Median Household Income
        'for': 'tract:*',
        'in': f'state:{NY_STATE_FIPS}+county:{BROOKLYN_FIPS},{QUEENS_FIPS}'
    }

    print(f"   Querying: {CENSUS_API_URL}")
    print(f"   Parameters: {params}")

    response = requests.get(CENSUS_API_URL, params=params)
    response.raise_for_status()

    # Parse JSON response
    data = response.json()

    # Convert to DataFrame (first row is headers)
    df = pd.DataFrame(data[1:], columns=data[0])

    # Create GEOID from state, county, tract
    df['GEOID'] = df['state'] + df['county'] + df['tract']

    # Convert income to numeric (handle -666666666 as null)
    df['median_income'] = pd.to_numeric(df['B19013_001E'], errors='coerce')
    df.loc[df['median_income'] < 0, 'median_income'] = None

    # Add borough name
    df['borough'] = df['county'].apply(
        lambda x: 'Brooklyn' if x == BROOKLYN_FIPS else 'Queens'
    )

    print(f"   ✓ Fetched {len(df)} census tracts")
    print(f"      Brooklyn: {len(df[df['borough'] == 'Brooklyn'])} tracts")
    print(f"      Queens: {len(df[df['borough'] == 'Queens'])} tracts")
    print(f"      Tracts with income data: {df['median_income'].notna().sum()}")

    return df[['GEOID', 'NAME', 'borough', 'median_income']]


def merge_geo_and_income(shapefile_path: Path, income_df: pd.DataFrame) -> gpd.GeoDataFrame:
    """Merge census tract geometries with income data"""
    print("\n3. Merging geometries with income data...")

    # Read shapefile
    print(f"   Loading shapefile: {shapefile_path}")
    gdf = gpd.read_file(shapefile_path)

    # Filter to Brooklyn and Queens only
    gdf = gdf[gdf['COUNTYFP'].isin([BROOKLYN_FIPS, QUEENS_FIPS])].copy()
    print(f"   ✓ Loaded {len(gdf)} tracts for Brooklyn & Queens")

    # Merge with income data (rename NAME to avoid conflict)
    income_df_renamed = income_df.rename(columns={'NAME': 'tract_name'})
    merged = gdf.merge(income_df_renamed, on='GEOID', how='left')
    print(f"   ✓ Merged {len(merged)} tracts with income data")

    # Simplify geometries to reduce file size
    print("   Simplifying geometries...")
    merged['geometry'] = merged['geometry'].simplify(tolerance=0.0001, preserve_topology=True)

    return merged


def get_color_for_income(income: Optional[float]) -> str:
    """Get color code based on income bin"""
    if pd.isna(income):
        return "80808080"  # Gray with transparency for missing data

    for bin_config in INCOME_BINS:
        if income < bin_config['max']:
            return bin_config['color']

    return INCOME_BINS[-1]['color']


def create_kmz(gdf: gpd.GeoDataFrame) -> None:
    """Generate KML/KMZ file with color-coded census tracts"""
    print("\n4. Creating KML/KMZ file...")

    # Create KML object with inline styles for Google My Maps compatibility
    kml = Kml()
    kml.document.name = "Brooklyn & Queens Median Household Income"
    # Disable shared styles - each polygon gets its own inline style
    kml.document.sharestyle = False
    kml.document.description = f"""
Census Tract Level Median Household Income
Data Source: US Census Bureau American Community Survey (ACS) 2022 5-Year Estimates
Table B19013: Median Household Income in the Past 12 Months

Total Census Tracts: {len(gdf)}
Brooklyn: {len(gdf[gdf['borough'] == 'Brooklyn'])}
Queens: {len(gdf[gdf['borough'] == 'Queens'])}

Color Legend:
{''.join([f'• {bin["label"]}' + chr(10) for bin in INCOME_BINS])}

Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}
"""

    # Add legend as a screen overlay description
    legend_text = "\\n".join([f"{bin['label']}" for bin in INCOME_BINS])

    # Create folders for Brooklyn and Queens
    brooklyn_folder = kml.newfolder(name=f"Brooklyn ({len(gdf[gdf['borough'] == 'Brooklyn'])} tracts)")
    queens_folder = kml.newfolder(name=f"Queens ({len(gdf[gdf['borough'] == 'Queens'])} tracts)")

    # Track statistics
    total_tracts = 0
    missing_data = 0

    # Add each census tract as a polygon
    for idx, row in gdf.iterrows():
        total_tracts += 1

        # Get census tract info
        geoid = row['GEOID']
        tract_name = row.get('tract_name', f"Tract {row['TRACTCE']}")
        borough = row['borough']
        income = row['median_income']
        geometry = row['geometry']

        # Choose folder
        folder = brooklyn_folder if borough == 'Brooklyn' else queens_folder

        # Create placemark name (show income if available)
        if pd.notna(income):
            placemark_name = f"Tract {row['TRACTCE']}: ${income:,.0f}"
        else:
            placemark_name = f"Tract {row['TRACTCE']}: No Data"
            missing_data += 1

        # Create polygon
        pol = folder.newpolygon(name=placemark_name)

        # Extract coordinates from geometry
        if geometry.geom_type == 'Polygon':
            coords = list(geometry.exterior.coords)
        elif geometry.geom_type == 'MultiPolygon':
            # Use largest polygon for multipolygon
            largest = max(geometry.geoms, key=lambda p: p.area)
            coords = list(largest.exterior.coords)
        else:
            continue

        # Set polygon coordinates (lon, lat)
        pol.outerboundaryis = coords

        # CRITICAL: Use inline styles for Google My Maps compatibility
        # Google My Maps does NOT support styles at Folder level
        color = get_color_for_income(income)
        pol.style.polystyle.color = color  # Already in aabbggrr hex format
        pol.style.polystyle.fill = 1
        pol.style.polystyle.outline = 1
        pol.style.linestyle.color = "ff000000"  # Black outline
        pol.style.linestyle.width = 0.5

        # Add popup description
        if pd.notna(income):
            description = f"""
<b>Census Tract:</b> {row['TRACTCE']}<br/>
<b>Borough:</b> {borough}<br/>
<b>Median Household Income:</b> ${income:,.0f}<br/>
<b>GEOID:</b> {geoid}<br/>
<br/>
<i>Source: US Census ACS 2022 5-Year Estimates</i>
"""
        else:
            description = f"""
<b>Census Tract:</b> {row['TRACTCE']}<br/>
<b>Borough:</b> {borough}<br/>
<b>Median Household Income:</b> No Data Available<br/>
<b>GEOID:</b> {geoid}<br/>
<br/>
<i>Data may be unavailable due to insufficient sample size</i>
"""
        pol.description = description

        # Progress indicator
        if total_tracts % 100 == 0:
            print(f"   Progress: {total_tracts} tracts processed...")

    print(f"   ✓ Processed {total_tracts} census tracts")
    print(f"      Tracts with data: {total_tracts - missing_data}")
    print(f"      Tracts without data: {missing_data}")

    # Save KML
    print("\n5. Saving files...")
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    kml.save(str(OUTPUT_KML))
    print(f"   ✓ KML saved: {OUTPUT_KML}")

    # Create KMZ (zipped KML)
    with zipfile.ZipFile(OUTPUT_KMZ, 'w', zipfile.ZIP_DEFLATED) as kmz:
        kmz.write(OUTPUT_KML, arcname='doc.kml')
    print(f"   ✓ KMZ saved: {OUTPUT_KMZ}")

    # File sizes
    kml_size = OUTPUT_KML.stat().st_size / 1024 / 1024
    kmz_size = OUTPUT_KMZ.stat().st_size / 1024 / 1024
    print(f"   KML size: {kml_size:.1f} MB")
    print(f"   KMZ size: {kmz_size:.1f} MB")


def main():
    """Main execution function"""
    print("=" * 60)
    print("BROOKLYN & QUEENS: MEDIAN HOUSEHOLD INCOME MAP")
    print("=" * 60)

    try:
        # Step 1: Download census tract boundaries
        shapefile_path = download_census_tracts()

        # Step 2: Fetch income data from Census API
        income_df = fetch_income_data()

        # Step 3: Merge geometries with income data
        gdf = merge_geo_and_income(shapefile_path, income_df)

        # Step 4: Create KMZ
        create_kmz(gdf)

        # Summary
        print("\n" + "=" * 60)
        print("EXPORT COMPLETE")
        print("=" * 60)
        print(f"Output File: {OUTPUT_KMZ}")
        print()
        print("✅ Ready to import into Google My Maps!")
        print("   → Go to https://mymaps.google.com")
        print("   → Click 'Create a New Map'")
        print("   → Click 'Import'")
        print("   → Upload the .kmz file")
        print()
        print("📊 Color Legend:")
        for bin_config in INCOME_BINS:
            print(f"   • {bin_config['label']}")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
