#!/usr/bin/env python3
"""
Export enriched hospital data to KMZ for Google My Maps.

Input:  data/hospitals/hospitals_enriched.csv
Output: data/hospitals/hospitals.kmz
"""

import os
import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

import pandas as pd
from simplekml import Kml

DATA_DIR   = PROJECT_ROOT / "data" / "hospitals"
INPUT_CSV  = DATA_DIR / "hospitals_enriched.csv"
OUTPUT_KML = DATA_DIR / "hospitals.kml"
OUTPUT_KMZ = DATA_DIR / "hospitals.kmz"

SERPER_API_KEY = os.getenv("SERPER_API_KEY")


def get_coordinates_from_serper(name: str, address: str):
    """Fallback geocoding via Serper Maps API."""
    import requests, time
    if not SERPER_API_KEY:
        return None, None
    try:
        resp = requests.post(
            "https://google.serper.dev/maps",
            json={"q": f"{name} {address}", "gl": "us"},
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        places = resp.json().get("places", [])
        if places:
            p = places[0]
            return float(p["latitude"]), float(p["longitude"])
        time.sleep(0.5)
    except Exception as e:
        print(f"   Serper geocoding error for {name}: {e}")
    return None, None


def marker_color(rating) -> str:
    """Return KML paddle icon URL based on rating."""
    base = "http://maps.google.com/mapfiles/kml/paddle/"
    try:
        r = float(rating)
        if r >= 4.5:
            return base + "grn-circle.png"
        if r >= 4.0:
            return base + "ylw-circle.png"
        if r >= 3.0:
            return base + "orange-circle.png"
        return base + "red-circle.png"
    except (TypeError, ValueError):
        return base + "blu-circle.png"


def build_description(row) -> str:
    parts = []
    addr = row.get("formatted_address") or row.get("address", "")
    if addr and str(addr) != "nan":
        parts.append(f"<b>Address:</b> {addr}<br/>")

    phone = row.get("phone", "")
    if phone and str(phone) != "nan":
        parts.append(f"<b>Phone:</b> {phone}<br/>")

    website = row.get("website", "")
    if website and str(website) != "nan":
        parts.append(f"<b>Website:</b> <a href='{website}'>{website}</a><br/>")

    rating = row.get("rating", "")
    reviews = row.get("reviews", "")
    if rating and str(rating) != "nan":
        rev_str = f" ({int(float(reviews))} reviews)" if reviews and str(reviews) != "nan" else ""
        parts.append(f"<b>Rating:</b> {rating} ⭐{rev_str}<br/>")

    return "\n".join(parts)


def create_kmz(df: pd.DataFrame):
    print("=" * 70)
    print("CREATING KMZ")
    print("=" * 70)

    kml = Kml()
    kml.document.name = "Hospitals — NJ Area"
    kml.document.description = (
        f"Hospitals scraped from Google Maps\n"
        f"Total: {len(df)}\n"
        f"Date: {pd.Timestamp.now().strftime('%Y-%m-%d')}"
    )

    folder = kml.newfolder(name="Hospitals")

    geocoded = 0
    skipped = 0

    for idx, row in df.iterrows():
        name = str(row.get("name", "")).strip()
        if not name or name == "nan":
            continue

        print(f"[{idx + 1}/{len(df)}] {name[:60]}")

        lat = row.get("latitude")
        lon = row.get("longitude")

        if pd.isna(lat) or pd.isna(lon):
            addr = str(row.get("formatted_address") or row.get("address", "")).strip()
            if addr and addr != "nan":
                print(f"   Geocoding via Serper...")
                lat, lon = get_coordinates_from_serper(name, addr)
                if lat:
                    geocoded += 1
                    print(f"   Found: {lat}, {lon}")
            if not lat or not lon:
                print(f"   Skipping (no coordinates)")
                skipped += 1
                continue

        pnt = folder.newpoint(name=name)
        pnt.coords = [(float(lon), float(lat))]
        pnt.description = build_description(row)

        rating = row.get("rating")
        pnt.style.iconstyle.icon.href = marker_color(rating)
        pnt.style.iconstyle.scale = 1.2

    print()
    print(f"Processed {len(df)} records")
    print(f"  Fallback geocoded: {geocoded}")
    print(f"  Skipped (no coords): {skipped}")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    kml.save(str(OUTPUT_KML))
    print(f"Saved KML: {OUTPUT_KML}")

    with zipfile.ZipFile(OUTPUT_KMZ, "w", zipfile.ZIP_DEFLATED) as kmz:
        kmz.write(OUTPUT_KML, arcname="doc.kml")
    print(f"Saved KMZ: {OUTPUT_KMZ}  ({OUTPUT_KMZ.stat().st_size / 1024:.1f} KB)")


def main():
    if not INPUT_CSV.exists():
        print(f"ERROR: {INPUT_CSV} not found. Run 02_enrich_hospitals.py first.")
        sys.exit(1)

    df = pd.read_csv(INPUT_CSV)
    print(f"Loaded {len(df)} hospitals from {INPUT_CSV}")
    print()

    create_kmz(df)

    print()
    print("=" * 70)
    print("KMZ EXPORT COMPLETE")
    print("=" * 70)
    print(f"Output: {OUTPUT_KMZ}")
    print()
    print("Import into Google My Maps:")
    print("  1. Go to https://mymaps.google.com")
    print("  2. Create a New Map → Import → Upload hospitals.kmz")
    print()
    print("Color legend:")
    print("  Green  — 4.5+ stars")
    print("  Yellow — 4.0–4.4 stars")
    print("  Orange — 3.0–3.9 stars")
    print("  Red    — < 3.0 stars")
    print("  Blue   — no rating")
    print("=" * 70)


if __name__ == "__main__":
    main()
