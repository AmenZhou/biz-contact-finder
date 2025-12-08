#!/usr/bin/env python3
"""
Export Queens & Brooklyn Doctor's Offices to KMZ for Google Maps
"""

import os
import sys
import zipfile
from pathlib import Path
from typing import Dict, List

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

import pandas as pd
import simplekml
from simplekml import Kml

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "medical_offices"
INPUT_CSV = DATA_DIR / "queens_brooklyn_doctors.csv"
OUTPUT_KML = DATA_DIR / "queens_brooklyn_doctors.kml"
OUTPUT_KMZ = DATA_DIR / "queens_brooklyn_doctors.kmz"


def get_coordinates_from_serper(name: str, address: str) -> tuple:
    """
    Get coordinates for doctor office using Serper API
    """
    import requests
    import time

    SERPER_API_KEY = os.getenv("SERPER_API_KEY")

    if not SERPER_API_KEY:
        return None, None

    # Build search query
    query = f"{name} {address}"

    url = "https://google.serper.dev/search"
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

        # Check for places/local pack results
        if "places" in data and len(data["places"]) > 0:
            place = data["places"][0]
            lat = place.get("latitude")
            lon = place.get("longitude")
            if lat and lon:
                return float(lat), float(lon)

        # Check knowledge graph
        if "knowledgeGraph" in data:
            kg = data["knowledgeGraph"]
            if "latitude" in kg and "longitude" in kg:
                return float(kg["latitude"]), float(kg["longitude"])

        time.sleep(0.5)  # Rate limiting

    except Exception as e:
        print(f"   ⚠️  Geocoding error for {name}: {e}")

    return None, None


def create_kmz(df: pd.DataFrame):
    """Create KMZ file with doctor office markers"""
    print("=" * 80)
    print("CREATING KMZ VISUALIZATION")
    print("=" * 80)
    print()

    kml = Kml()
    kml.document.name = "Queens & Brooklyn Doctor's Offices"
    kml.document.description = f"""
Doctor's Offices and Medical Practices in Queens and Brooklyn

Total Offices: {len(df)}
With Phone: {df['phone'].astype(bool).sum()}
With Email: {df['email'].astype(bool).sum()}
With Address: {df['address'].astype(bool).sum()}

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
        print(f"[{idx + 1}/{total}] Processing: {row['name']}")

        # Determine borough folder
        location = str(row.get('location', '')).lower()
        if 'queens' in location:
            folder = queens_folder
        elif 'brooklyn' in location:
            folder = brooklyn_folder
        else:
            # Try to determine from address
            address = str(row.get('address', '')).lower()
            if 'queens' in address:
                folder = queens_folder
            elif 'brooklyn' in address:
                folder = brooklyn_folder
            else:
                folder = queens_folder  # Default

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

        if row.get('contact_name'):
            description_parts.append(f"<b>Contact:</b> {row['contact_name']}<br/>")

        if row.get('rating'):
            description_parts.append(f"<b>Rating:</b> {row['rating']} ({row.get('reviews', 0)} reviews)<br/>")

        description_parts.append(f"<br/><i>Source: {row.get('source', 'unknown')}</i>")

        pnt.description = "\n".join(description_parts)

        # Style the marker
        pnt.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/paddle/red-circle.png'
        pnt.style.iconstyle.scale = 1.2

    print()
    print(f"✓ Processed {total} doctor offices")
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
        print("   Please run 01_scrape_doctors_queens_brooklyn.py first")
        sys.exit(1)

    # Load CSV
    print(f"📂 Loading data from {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV)
    print(f"   ✓ Loaded {len(df)} doctor offices")
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
    print("=" * 80)


if __name__ == "__main__":
    main()
