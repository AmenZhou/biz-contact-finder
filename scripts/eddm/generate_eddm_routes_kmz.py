#!/usr/bin/env python3
"""
Generate KMZ from USPS EDDM Carrier Routes by Zip Code

Fetches carrier route data from the USPS EDDM ArcGIS API and generates
a KMZ file with color-coded route paths and demographic popups,
importable into Google My Maps.

Usage:
    python scripts/eddm/generate_eddm_routes_kmz.py <zipcode>
    python scripts/eddm/generate_eddm_routes_kmz.py 10001
"""

import sys
import zipfile
from pathlib import Path

import requests
import simplekml
from simplekml import Kml, Style, LineStyle

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "eddm"

# USPS EDDM ArcGIS API
EDDM_API_URL = "https://gis.usps.com/arcgis/rest/services/EDDM/selectZIP/GPServer/routes/execute"

# Color bins by residential count (KML aabbggrr format)
RES_COUNT_BINS = [
    {"max": 250,        "color": "ff0000ff", "width": 2, "label": "< 250 residences"},       # Red
    {"max": 500,        "color": "ff00a5ff", "width": 3, "label": "250 - 500 residences"},    # Orange
    {"max": 750,        "color": "ff00ffff", "width": 4, "label": "500 - 750 residences"},    # Yellow
    {"max": 1000,       "color": "ff00ff00", "width": 5, "label": "750 - 1,000 residences"},  # Green
    {"max": float('inf'), "color": "ffff0000", "width": 6, "label": "1,000+ residences"},     # Blue
]


def get_style_for_res_count(res_count):
    """Return (color, width, label) for a residential count."""
    for bin_cfg in RES_COUNT_BINS:
        if res_count < bin_cfg["max"]:
            return bin_cfg["color"], bin_cfg["width"], bin_cfg["label"]
    last = RES_COUNT_BINS[-1]
    return last["color"], last["width"], last["label"]


def fetch_routes(zipcode):
    """Fetch carrier route data from the USPS EDDM API."""
    print(f"\n1. Fetching EDDM carrier routes for ZIP {zipcode}...")

    params = {
        "f": "json",
        "env:outSR": "4326",
        "ZIP": zipcode,
        "Rte_Box": "R",
        "UserName": "EDDM",
    }

    response = requests.get(EDDM_API_URL, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    # Check for API-level errors
    if "error" in data:
        raise RuntimeError(f"USPS API error: {data['error'].get('message', data['error'])}")

    results = data.get("results", [])
    if not results:
        raise RuntimeError(f"No results returned for ZIP {zipcode}")

    features = results[0].get("value", {}).get("features", [])
    if not features:
        raise RuntimeError(f"No carrier routes found for ZIP {zipcode}")

    print(f"   Found {len(features)} carrier routes")
    return features


def build_description(attrs):
    """Build an HTML popup description from route attributes."""
    route_id = attrs.get("CRID_ID", "N/A")
    zip_code = attrs.get("ZIP_CODE", "N/A")
    city_state = attrs.get("CITY_STATE", "N/A")
    res_cnt = attrs.get("RES_CNT", 0)
    bus_cnt = attrs.get("BUS_CNT", 0)
    tot_cnt = attrs.get("TOT_CNT", 0)
    med_income = attrs.get("MED_INCOME", None)
    med_age = attrs.get("MED_AGE", None)
    avg_hh = attrs.get("AVG_HH_SIZ", None)
    facility = attrs.get("FACILITY_NAME", "N/A")

    income_str = f"${med_income:,.0f}" if med_income else "N/A"
    age_str = f"{med_age}" if med_age else "N/A"
    hh_str = f"{avg_hh}" if avg_hh else "N/A"

    return f"""<b>Route:</b> {route_id}<br/>
<b>ZIP:</b> {zip_code} | {city_state}<br/>
<b>Post Office:</b> {facility}<br/>
<hr/>
<b>Residential:</b> {res_cnt:,}<br/>
<b>Business:</b> {bus_cnt:,}<br/>
<b>Total Addresses:</b> {tot_cnt:,}<br/>
<hr/>
<b>Median Income:</b> {income_str}<br/>
<b>Median Age:</b> {age_str}<br/>
<b>Avg Household Size:</b> {hh_str}<br/>
<hr/>
<i>Source: USPS EDDM / ArcGIS</i>"""


def create_kmz(features, zipcode):
    """Generate a KMZ file with color-coded carrier route lines."""
    print(f"\n2. Generating KMZ for {len(features)} routes...")

    kml = Kml()
    kml.document.name = f"EDDM Carrier Routes - ZIP {zipcode}"
    kml.document.description = (
        f"USPS EDDM carrier routes for ZIP code {zipcode}\n"
        f"Color-coded by residential address count\n\n"
        + "\n".join(f"  {b['label']}" for b in RES_COUNT_BINS)
    )

    # Pre-create shared styles
    style_map = {}
    for bin_cfg in RES_COUNT_BINS:
        key = bin_cfg["color"]
        if key not in style_map:
            style = Style()
            style.linestyle = LineStyle(color=bin_cfg["color"], width=bin_cfg["width"])
            kml.document.styles.append(style)
            style_map[key] = style

    route_count = 0
    for feature in features:
        attrs = feature.get("attributes", {})
        geometry = feature.get("geometry", {})
        paths = geometry.get("paths", [])

        if not paths:
            continue

        route_id = attrs.get("CRID_ID", "Unknown")
        res_cnt = attrs.get("RES_CNT", 0) or 0

        color, width, label = get_style_for_res_count(res_cnt)

        # Each path is a list of [lng, lat] pairs
        for path in paths:
            coords = [(pt[0], pt[1]) for pt in path]

            ls = kml.newlinestring(name=f"{route_id} ({res_cnt:,} res)")
            ls.coords = coords
            ls.description = build_description(attrs)
            ls.style.linestyle.color = color
            ls.style.linestyle.width = width

        route_count += 1

    print(f"   Processed {route_count} routes")

    # Save KML then package as KMZ
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    kml_path = DATA_DIR / f"{zipcode}_eddm_routes.kml"
    kmz_path = DATA_DIR / f"{zipcode}_eddm_routes.kmz"

    kml.save(str(kml_path))

    with zipfile.ZipFile(kmz_path, "w", zipfile.ZIP_DEFLATED) as kmz:
        kmz.write(kml_path, arcname="doc.kml")

    # Clean up intermediate KML
    kml_path.unlink()

    kmz_size = kmz_path.stat().st_size / 1024
    print(f"   KMZ saved: {kmz_path} ({kmz_size:.1f} KB)")

    return kmz_path


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/eddm/generate_eddm_routes_kmz.py <zipcode>")
        sys.exit(1)

    zipcode = sys.argv[1].strip()
    if not zipcode.isdigit() or len(zipcode) != 5:
        print(f"Error: '{zipcode}' is not a valid 5-digit ZIP code")
        sys.exit(1)

    print("=" * 60)
    print(f"EDDM CARRIER ROUTES -> KMZ : ZIP {zipcode}")
    print("=" * 60)

    try:
        features = fetch_routes(zipcode)
        kmz_path = create_kmz(features, zipcode)

        print("\n" + "=" * 60)
        print("EXPORT COMPLETE")
        print("=" * 60)
        print(f"Output: {kmz_path}")
        print()
        print("Color Legend (by residential count):")
        for b in RES_COUNT_BINS:
            print(f"   {b['label']}")
        print()
        print("Import into Google My Maps:")
        print("   1. Go to https://mymaps.google.com")
        print("   2. Create a New Map -> Import -> Upload the .kmz file")
        print("=" * 60)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
