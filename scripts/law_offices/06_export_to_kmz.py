#!/usr/bin/env python3
"""
Export Queens & Brooklyn Law Offices to KMZ for Google Maps (Final with ratings)
"""

import os
import sys
import zipfile
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

import pandas as pd
import simplekml
from simplekml import Kml

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "law_offices"
INPUT_CSV = DATA_DIR / "queens_brooklyn_law_offices_final.csv"
OUTPUT_KML = DATA_DIR / "queens_brooklyn_law_offices.kml"
OUTPUT_KMZ = DATA_DIR / "queens_brooklyn_law_offices.kmz"


def get_coordinates_from_serper(name: str, address: str) -> tuple:
    """
    Get coordinates for law office using Serper API
    """
    import requests
    import time

    SERPER_API_KEY = os.getenv("SERPER_API_KEY")

    if not SERPER_API_KEY:
        return None, None

    # Build search query
    query = f"{name} {address}"

    url = "https://google.serper.dev/maps"
    payload = {
        "q": query,
        "location": "New York, NY",
        "gl": "us"
    }
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Check for places results
        if "places" in data and len(data["places"]) > 0:
            place = data["places"][0]
            lat = place.get("latitude")
            lon = place.get("longitude")
            if lat and lon:
                return float(lat), float(lon)

        time.sleep(0.5)  # Rate limiting

    except Exception as e:
        print(f"   ⚠️  Geocoding error for {name}: {e}")

    return None, None


def create_kmz(df: pd.DataFrame):
    """Create KMZ file with law office markers"""
    print("=" * 80)
    print("CREATING KMZ VISUALIZATION")
    print("=" * 80)
    print()

    kml = Kml()
    kml.document.name = "Queens & Brooklyn Law Offices"
    kml.document.description = f"""
Law Offices in Queens and Brooklyn

Total Offices: {len(df)}
With Phone: {df['phone'].astype(bool).sum()}
With Address: {df['address'].astype(bool).sum()}
With Rating: {df['rating'].astype(bool).sum()}
With Business Hours: {df['business_hours'].astype(bool).sum()}

Data collected: {pd.Timestamp.now().strftime('%Y-%m-%d')}
"""

    # Create folders for Queens and Brooklyn
    queens_folder = kml.newfolder(name="Queens")
    brooklyn_folder = kml.newfolder(name="Brooklyn")

    # Track statistics
    total = len(df)
    geocoded = 0
    missing_coords = 0

    for idx, row in df.iterrows():
        print(f"[{idx + 1}/{total}] Processing: {row['name'][:60]}")

        # Determine borough folder
        location = str(row.get('location', '')).lower()
        address = str(row.get('address', '')).lower()

        if 'queens' in location or 'queens' in address:
            folder = queens_folder
        elif 'brooklyn' in location or 'brooklyn' in address:
            folder = brooklyn_folder
        else:
            # Default to Queens
            folder = queens_folder

        # Get coordinates
        lat = row.get('latitude')
        lon = row.get('longitude')

        # If missing coordinates, try to geocode
        if pd.isna(lat) or pd.isna(lon) or lat == '' or lon == '':
            if row.get('address'):
                print(f"   🔍 Geocoding address...")
                lat, lon = get_coordinates_from_serper(
                    row['name'],
                    row['address']
                )
                if lat and lon:
                    geocoded += 1
                    print(f"   ✓ Found coordinates: {lat}, {lon}")
            else:
                print(f"   ⚠️  No address available, skipping")
                missing_coords += 1
                continue

        if not lat or not lon:
            print(f"   ⚠️  Could not find coordinates, skipping")
            missing_coords += 1
            continue

        # Create placemark
        pnt = folder.newpoint(name=row['name'])
        pnt.coords = [(float(lon), float(lat))]

        # Build description HTML
        description_parts = []

        if row.get('address'):
            description_parts.append(f"<b>Address:</b> {row['address']}<br/>")

        if row.get('phone'):
            description_parts.append(f"<b>Phone:</b> {row['phone']}<br/>")

        if row.get('email'):
            description_parts.append(f"<b>Email:</b> {row['email']}<br/>")

        if row.get('website'):
            description_parts.append(f"<b>Website:</b> <a href='{row['website']}'>{row['website']}</a><br/>")

        if row.get('rating') and pd.notna(row['rating']) and row['rating'] != '':
            reviews = row.get('reviews', 0)
            description_parts.append(f"<b>Rating:</b> {row['rating']} ⭐ ({reviews} reviews)<br/>")

        if row.get('business_hours') and pd.notna(row['business_hours']) and row['business_hours'] != '':
            description_parts.append(f"<b>Hours:</b> {row['business_hours']}<br/>")

        if row.get('practice_areas') and pd.notna(row['practice_areas']) and row['practice_areas'] != '':
            description_parts.append(f"<b>Practice Areas:</b> {row['practice_areas']}<br/>")

        description_parts.append(f"<br/><i>Source: {row.get('source', 'unknown')}</i>")

        pnt.description = "\n".join(description_parts)

        # Style the marker - different colors based on rating
        rating = row.get('rating')
        if pd.notna(rating) and rating != '':
            try:
                rating_val = float(rating)
                if rating_val >= 4.5:
                    # Green for excellent ratings
                    pnt.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/paddle/grn-circle.png'
                elif rating_val >= 4.0:
                    # Yellow for good ratings
                    pnt.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/paddle/ylw-circle.png'
                elif rating_val >= 3.0:
                    # Orange for average ratings
                    pnt.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/paddle/orange-circle.png'
                else:
                    # Red for low ratings
                    pnt.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/paddle/red-circle.png'
            except:
                # Default blue for no rating
                pnt.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/paddle/blu-circle.png'
        else:
            # Default blue for no rating
            pnt.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/paddle/blu-circle.png'

        pnt.style.iconstyle.scale = 1.2

    print()
    print(f"✓ Processed {total} law offices")
    print(f"  Geocoded: {geocoded}")
    print(f"  Missing coordinates: {missing_coords}")
    print()

    # Save KML
    print("💾 Saving files...")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    kml.save(str(OUTPUT_KML))
    print(f"   ✓ KML saved: {OUTPUT_KML}")

    # Create KMZ (zipped KML)
    with zipfile.ZipFile(OUTPUT_KMZ, 'w', zipfile.ZIP_DEFLATED) as kmz:
        kmz.write(OUTPUT_KML, arcname='doc.kml')
    print(f"   ✓ KMZ saved: {OUTPUT_KMZ}")

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
        print(f"❌ Error: CSV file not found at {INPUT_CSV}")
        sys.exit(1)

    # Load CSV
    print(f"📂 Loading data from {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV)
    print(f"   ✓ Loaded {len(df)} law offices")
    print()

    # Create KMZ
    create_kmz(df)

    print()
    print("=" * 80)
    print("✅ KMZ EXPORT COMPLETE")
    print("=" * 80)
    print(f"Output File: {OUTPUT_KMZ}")
    print()
    print("🗺️  Ready to import into Google My Maps!")
    print("   → Go to https://mymaps.google.com")
    print("   → Click 'Create a New Map'")
    print("   → Click 'Import'")
    print("   → Upload the .kmz file")
    print()
    print("📊 Color Legend:")
    print("   🟢 Green - Excellent (4.5+ stars)")
    print("   🟡 Yellow - Good (4.0-4.4 stars)")
    print("   🟠 Orange - Average (3.0-3.9 stars)")
    print("   🔴 Red - Low (< 3.0 stars)")
    print("   🔵 Blue - No rating available")
    print("=" * 80)


if __name__ == "__main__":
    main()
