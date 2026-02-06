#!/usr/bin/env python3
"""
Export Massachusetts Community Facilities to KMZ for Google Maps
Uses HERE API for any missing geocoding
"""

import os
import sys
import zipfile
import time
import requests
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

import pandas as pd
import simplekml
from simplekml import Kml

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "ma_facilities"
INPUT_CSV = DATA_DIR / "ma_facilities_with_addresses.csv"
OUTPUT_KML = DATA_DIR / "ma_facilities.kml"
OUTPUT_KMZ = DATA_DIR / "ma_facilities.kmz"

# API Configuration
HERE_API_KEY = os.getenv("HERE_API_KEY")


def get_coordinates_from_here(name: str, address: str) -> tuple:
    """
    Get coordinates for facility using HERE Geocoding API
    """
    if not HERE_API_KEY:
        return None, None

    # Build search query
    query = f"{name} {address}"

    url = "https://discover.search.hereapi.com/v1/discover"
    params = {
        "q": query,
        "in": "circle:42.0,-71.0;r=100000",  # 100km radius around MA
        "limit": 1,
        "apiKey": HERE_API_KEY
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if "items" in data and len(data["items"]) > 0:
            position = data["items"][0].get("position", {})
            lat = position.get("lat")
            lng = position.get("lng")
            if lat and lng:
                return float(lat), float(lng)

        time.sleep(0.3)  # Rate limiting

    except Exception as e:
        print(f"   Warning: Geocoding error for {name}: {e}")

    return None, None


def get_marker_style(facility_type: str):
    """Return marker color URL based on facility type"""
    marker_urls = {
        "town_hall": "http://maps.google.com/mapfiles/kml/paddle/red-circle.png",
        "school": "http://maps.google.com/mapfiles/kml/paddle/blu-circle.png",
        "supermarket": "http://maps.google.com/mapfiles/kml/paddle/grn-circle.png",
        "building_office": "http://maps.google.com/mapfiles/kml/paddle/wht-circle.png",
        "law_office": "http://maps.google.com/mapfiles/kml/paddle/purple-circle.png",
        "clinical_office": "http://maps.google.com/mapfiles/kml/paddle/pink-circle.png",
        "university": "http://maps.google.com/mapfiles/kml/paddle/orange-circle.png",
        "senior_center": "http://maps.google.com/mapfiles/kml/paddle/ylw-circle.png",
        "library": "http://maps.google.com/mapfiles/kml/paddle/ltblu-circle.png"
    }
    return marker_urls.get(facility_type, "http://maps.google.com/mapfiles/kml/paddle/blu-circle.png")


def create_kmz(df: pd.DataFrame):
    """Create KMZ file with facility markers"""
    print("=" * 80)
    print("CREATING KMZ VISUALIZATION")
    print("=" * 80)
    print()

    kml = Kml()
    kml.document.name = "Massachusetts Community Facilities"
    kml.document.description = f"""
Community Facilities in Massachusetts

Total Facilities: {len(df)}
- Town Halls: {len(df[df['facility_type'] == 'town_hall'])}
- Schools: {len(df[df['facility_type'] == 'school'])}
- Supermarkets: {len(df[df['facility_type'] == 'supermarket'])}
- Building Offices: {len(df[df['facility_type'] == 'building_office'])}
- Law Offices: {len(df[df['facility_type'] == 'law_office'])}
- Clinical Offices: {len(df[df['facility_type'] == 'clinical_office'])}
- Universities: {len(df[df['facility_type'] == 'university'])}
- Senior Centers: {len(df[df['facility_type'] == 'senior_center'])}
- Libraries: {len(df[df['facility_type'] == 'library'])}

Data collected: {pd.Timestamp.now().strftime('%Y-%m-%d')}
"""

    # Create folders for each facility type
    folders = {
        "town_hall": kml.newfolder(name="Town Halls"),
        "school": kml.newfolder(name="Schools"),
        "supermarket": kml.newfolder(name="Supermarkets"),
        "building_office": kml.newfolder(name="Building Offices"),
        "law_office": kml.newfolder(name="Law Offices"),
        "clinical_office": kml.newfolder(name="Clinical Offices"),
        "university": kml.newfolder(name="Universities"),
        "senior_center": kml.newfolder(name="Senior Centers"),
        "library": kml.newfolder(name="Libraries")
    }

    # Track statistics
    total = len(df)
    geocoded = 0
    missing_coords = 0

    for idx, row in df.iterrows():
        print(f"[{idx + 1}/{total}] Processing: {row['name'][:60]}")

        # Get facility type folder
        facility_type = row.get('facility_type', 'building_office')
        folder = folders.get(facility_type, folders['building_office'])

        # Get coordinates
        lat = row.get('latitude')
        lon = row.get('longitude')

        # If missing coordinates, try to geocode with HERE
        if pd.isna(lat) or pd.isna(lon) or lat == '' or lon == '':
            if row.get('address'):
                print(f"   Geocoding with HERE API...")
                lat, lon = get_coordinates_from_here(
                    row['name'],
                    row['address']
                )
                if lat and lon:
                    geocoded += 1
                    print(f"   Found coordinates: {lat}, {lon}")
            else:
                print(f"   Warning: No address available, skipping")
                missing_coords += 1
                continue

        if not lat or not lon:
            print(f"   Warning: Could not find coordinates, skipping")
            missing_coords += 1
            continue

        # Create placemark
        pnt = folder.newpoint(name=row['name'])
        pnt.coords = [(float(lon), float(lat))]

        # Build description HTML
        description_parts = []

        # Facility type
        type_names = {
            "town_hall": "Town Hall",
            "school": "School",
            "supermarket": "Supermarket",
            "building_office": "Building Office",
            "law_office": "Law Office",
            "clinical_office": "Clinical Office",
            "university": "University/College",
            "senior_center": "Senior Center",
            "library": "Library"
        }
        description_parts.append(f"<b>Type:</b> {type_names.get(facility_type, facility_type)}<br/>")

        if row.get('address'):
            description_parts.append(f"<b>Address:</b> {row['address']}<br/>")

        if row.get('zip_code'):
            description_parts.append(f"<b>Zip Code:</b> {row['zip_code']}<br/>")

        if row.get('phone'):
            description_parts.append(f"<b>Phone:</b> {row['phone']}<br/>")

        if row.get('business_hours'):
            hours = str(row['business_hours'])
            description_parts.append(f"<b>Hours:</b> {hours}<br/>")

        if row.get('email'):
            description_parts.append(f"<b>Email:</b> {row['email']}<br/>")

        if row.get('website'):
            description_parts.append(f"<b>Website:</b> <a href='{row['website']}'>{row['website']}</a><br/>")

        if row.get('rating') and pd.notna(row['rating']) and row['rating'] != '':
            reviews = row.get('reviews', 0)
            description_parts.append(f"<b>Rating:</b> {row['rating']} ({reviews} reviews)<br/>")

        description_parts.append(f"<br/><i>Source: {row.get('source', 'here_discover')}</i>")

        pnt.description = "\n".join(description_parts)

        # Style the marker with facility type color
        pnt.style.iconstyle.icon.href = get_marker_style(facility_type)
        pnt.style.iconstyle.scale = 1.2

    print()
    print(f"Processed {total} facilities")
    print(f"  Geocoded: {geocoded}")
    print(f"  Missing coordinates: {missing_coords}")
    print()

    # Save KML
    print("Saving files...")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    kml.save(str(OUTPUT_KML))
    print(f"   KML saved: {OUTPUT_KML}")

    # Create KMZ (zipped KML)
    with zipfile.ZipFile(OUTPUT_KMZ, 'w', zipfile.ZIP_DEFLATED) as kmz:
        kmz.write(OUTPUT_KML, arcname='doc.kml')
    print(f"   KMZ saved: {OUTPUT_KMZ}")

    # File sizes
    kml_size = OUTPUT_KML.stat().st_size / 1024
    kmz_size = OUTPUT_KMZ.stat().st_size / 1024
    print(f"   KML size: {kml_size:.1f} KB")
    print(f"   KMZ size: {kmz_size:.1f} KB")


def main():
    """Main execution"""
    print()

    # Check if CSV exists
    if not INPUT_CSV.exists():
        # Try the non-enriched version
        alt_input = DATA_DIR / "ma_facilities.csv"
        if alt_input.exists():
            global INPUT_CSV
            INPUT_CSV = alt_input
            print(f"Using non-enriched CSV: {INPUT_CSV}")
        else:
            print(f"Error: CSV file not found at {INPUT_CSV}")
            sys.exit(1)

    # Load CSV
    print(f"Loading data from {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV)
    print(f"   Loaded {len(df)} facilities")
    print()

    # Create KMZ
    create_kmz(df)

    print()
    print("=" * 80)
    print("KMZ EXPORT COMPLETE")
    print("=" * 80)
    print(f"Output File: {OUTPUT_KMZ}")
    print()
    print("Ready to import into Google My Maps!")
    print("   1. Go to https://mymaps.google.com")
    print("   2. Click 'Create a New Map'")
    print("   3. Click 'Import'")
    print("   4. Upload the .kmz file")
    print()
    print("Color Legend:")
    print("   Red - Town Halls")
    print("   Blue - Schools")
    print("   Green - Supermarkets")
    print("   White - Building Offices")
    print("   Purple - Law Offices")
    print("   Pink - Clinical Offices")
    print("   Orange - Universities/Colleges")
    print("   Yellow - Senior Centers")
    print("   Light Blue - Libraries")
    print("=" * 80)


if __name__ == "__main__":
    main()
