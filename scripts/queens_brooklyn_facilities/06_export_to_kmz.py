#!/usr/bin/env python3
"""
Export Queens/Brooklyn Community Facilities to KMZ for Google Maps
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
DATA_DIR = PROJECT_ROOT / "data" / "queens_brooklyn_facilities"
INPUT_CSV = DATA_DIR / "queens_brooklyn_facilities_with_addresses.csv"
OUTPUT_KML = DATA_DIR / "queens_brooklyn_facilities.kml"
OUTPUT_KMZ = DATA_DIR / "queens_brooklyn_facilities.kmz"


def get_coordinates_from_serper(name: str, address: str) -> tuple:
    """
    Get coordinates for facility using Serper API
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


def get_marker_style(facility_type: str):
    """Return marker color URL based on facility type"""
    marker_urls = {
        "senior_center": "http://maps.google.com/mapfiles/kml/paddle/purple-circle.png",
        "library": "http://maps.google.com/mapfiles/kml/paddle/grn-circle.png",
        "city_hall": "http://maps.google.com/mapfiles/kml/paddle/red-circle.png",
        "community_center": "http://maps.google.com/mapfiles/kml/paddle/ylw-circle.png",
        "college": "http://maps.google.com/mapfiles/kml/paddle/orange-circle.png",
        "golf_club": "http://maps.google.com/mapfiles/kml/paddle/pink-circle.png",
        "yacht_club": "http://maps.google.com/mapfiles/kml/paddle/ltblu-circle.png",
        "social_club": "http://maps.google.com/mapfiles/kml/paddle/wht-circle.png"
    }
    return marker_urls.get(facility_type, "http://maps.google.com/mapfiles/kml/paddle/blu-circle.png")


def create_kmz(df: pd.DataFrame):
    """Create KMZ file with facility markers"""
    print("=" * 80)
    print("CREATING KMZ VISUALIZATION")
    print("=" * 80)
    print()

    kml = Kml()
    kml.document.name = "Queens & Brooklyn Community Facilities"
    kml.document.description = f"""
Community Facilities in Queens and Brooklyn

Total Facilities: {len(df)}
- Senior Centers: {len(df[df['facility_type'] == 'senior_center'])}
- Libraries: {len(df[df['facility_type'] == 'library'])}
- City/Borough Halls: {len(df[df['facility_type'] == 'city_hall'])}
- Community Centers: {len(df[df['facility_type'] == 'community_center'])}
- Colleges/Universities: {len(df[df['facility_type'] == 'college'])}
- Golf Clubs: {len(df[df['facility_type'] == 'golf_club'])}
- Yacht Clubs: {len(df[df['facility_type'] == 'yacht_club'])}
- Social Clubs: {len(df[df['facility_type'] == 'social_club'])}

Data collected: {pd.Timestamp.now().strftime('%Y-%m-%d')}
"""

    # Create folders for each facility type
    folders = {
        "senior_center": kml.newfolder(name="Senior Centers"),
        "library": kml.newfolder(name="Libraries"),
        "city_hall": kml.newfolder(name="City/Borough Halls"),
        "community_center": kml.newfolder(name="Community Centers"),
        "college": kml.newfolder(name="Colleges/Universities"),
        "golf_club": kml.newfolder(name="Golf Clubs"),
        "yacht_club": kml.newfolder(name="Yacht Clubs"),
        "social_club": kml.newfolder(name="Social Clubs")
    }

    # Track statistics
    total = len(df)
    geocoded = 0
    missing_coords = 0

    for idx, row in df.iterrows():
        print(f"[{idx + 1}/{total}] Processing: {row['name'][:60]}")

        # Get facility type folder
        facility_type = row.get('facility_type', 'community_center')
        folder = folders.get(facility_type, folders['community_center'])

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

        # Facility type
        type_names = {
            "senior_center": "Senior Center",
            "library": "Library",
            "city_hall": "City/Borough Hall",
            "community_center": "Community Center",
            "college": "College/University",
            "golf_club": "Golf Club",
            "yacht_club": "Yacht Club",
            "social_club": "Social Club"
        }
        description_parts.append(f"<b>Type:</b> {type_names.get(facility_type, facility_type)}<br/>")

        if row.get('address'):
            description_parts.append(f"<b>Address:</b> {row['address']}<br/>")

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
            description_parts.append(f"<b>Rating:</b> {row['rating']} ⭐ ({reviews} reviews)<br/>")

        description_parts.append(f"<br/><i>Source: {row.get('source', 'unknown')}</i>")

        pnt.description = "\n".join(description_parts)

        # Style the marker with facility type color
        pnt.style.iconstyle.icon.href = get_marker_style(facility_type)
        pnt.style.iconstyle.scale = 1.2

    print()
    print(f"✓ Processed {total} facilities")
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
    print(f"   ✓ Loaded {len(df)} facilities")
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
    print("   🟣 Purple - Senior Centers")
    print("   🟢 Green - Libraries")
    print("   🔴 Red - City/Borough Halls")
    print("   🟡 Yellow - Community Centers")
    print("   🟠 Orange - Colleges/Universities")
    print("   🩷 Pink - Golf Clubs")
    print("   🔵 Light Blue - Yacht Clubs")
    print("   ⚪ White - Social Clubs")
    print("=" * 80)


if __name__ == "__main__":
    main()
