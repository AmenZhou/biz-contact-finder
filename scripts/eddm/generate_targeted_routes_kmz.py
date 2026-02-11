#!/usr/bin/env python3
"""
Generate KMZ for targeted USPS EDDM Carrier Routes from a CSV of ZIP/CRID pairs.

Reads a CSV with ZIP,CRID columns, fetches route data from the USPS EDDM API
for each unique ZIP, filters to only the targeted CRIDs, and outputs a single
combined KMZ file with color-coded routes and demographic popups.

Usage:
    python scripts/eddm/generate_targeted_routes_kmz.py data/eddm/target_routes.csv
    python scripts/eddm/generate_targeted_routes_kmz.py data/eddm/target_routes.csv --output my_routes.kmz
"""

import csv
import sys
import time
import zipfile
from collections import defaultdict
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
    {"max": 250,          "color": "ff0000ff", "width": 2, "label": "< 250 residences"},
    {"max": 500,          "color": "ff00a5ff", "width": 3, "label": "250 - 500 residences"},
    {"max": 750,          "color": "ff00ffff", "width": 4, "label": "500 - 750 residences"},
    {"max": 1000,         "color": "ff00ff00", "width": 5, "label": "750 - 1,000 residences"},
    {"max": float('inf'), "color": "ffff0000", "width": 6, "label": "1,000+ residences"},
]


def get_style_for_res_count(res_count):
    """Return (color, width, label) for a residential count."""
    for bin_cfg in RES_COUNT_BINS:
        if res_count < bin_cfg["max"]:
            return bin_cfg["color"], bin_cfg["width"], bin_cfg["label"]
    last = RES_COUNT_BINS[-1]
    return last["color"], last["width"], last["label"]


def load_targets(csv_path):
    """Load ZIP/CRID pairs from CSV and group CRIDs by ZIP."""
    targets = defaultdict(set)
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            zipcode = row["ZIP"].strip()
            crid = row["CRID"].strip()
            targets[zipcode].add(crid)
    return targets


def fetch_routes(zipcode):
    """Fetch carrier route data from the USPS EDDM API."""
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

    if "error" in data:
        raise RuntimeError(f"USPS API error for {zipcode}: {data['error'].get('message', data['error'])}")

    results = data.get("results", [])
    if not results:
        return []

    features = results[0].get("value", {}).get("features", [])
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


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/eddm/generate_targeted_routes_kmz.py <csv_path> [--output <name.kmz>]")
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    if not csv_path.exists():
        print(f"Error: CSV file not found: {csv_path}")
        sys.exit(1)

    # Optional output name
    output_name = "targeted_eddm_routes.kmz"
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_name = sys.argv[idx + 1]

    # Load targets
    targets = load_targets(csv_path)
    total_pairs = sum(len(crids) for crids in targets.values())
    print("=" * 60)
    print("TARGETED EDDM CARRIER ROUTES -> KMZ")
    print("=" * 60)
    print(f"CSV: {csv_path}")
    print(f"Unique ZIPs: {len(targets)}")
    print(f"Target routes: {total_pairs}")
    print()

    # Build KMZ
    kml = Kml()
    kml.document.name = "Targeted EDDM Carrier Routes"
    kml.document.description = (
        f"Targeted USPS EDDM carrier routes ({total_pairs} routes across {len(targets)} ZIPs)\n"
        f"Color-coded by residential address count\n\n"
        + "\n".join(f"  {b['label']}" for b in RES_COUNT_BINS)
    )

    matched = 0
    missing = []
    total_res = 0
    total_bus = 0
    total_addr = 0

    for zipcode in sorted(targets.keys()):
        wanted_crids = targets[zipcode]
        print(f"  ZIP {zipcode}: fetching ({len(wanted_crids)} target routes)...", end=" ", flush=True)

        try:
            features = fetch_routes(zipcode)
        except Exception as e:
            print(f"ERROR: {e}")
            for crid in wanted_crids:
                missing.append((zipcode, crid))
            continue

        # Index features by CRID_ID
        by_crid = {}
        for f in features:
            crid_id = f.get("attributes", {}).get("CRID_ID", "")
            by_crid[crid_id] = f

        zip_found = 0

        for crid in sorted(wanted_crids):
            feature = by_crid.get(crid)
            if not feature:
                missing.append((zipcode, crid))
                continue

            attrs = feature.get("attributes", {})
            geometry = feature.get("geometry", {})
            paths = geometry.get("paths", [])
            if not paths:
                missing.append((zipcode, crid))
                continue

            res_cnt = attrs.get("RES_CNT", 0) or 0
            bus_cnt = attrs.get("BUS_CNT", 0) or 0
            tot_cnt = attrs.get("TOT_CNT", 0) or 0
            color, width, _ = get_style_for_res_count(res_cnt)

            # Each route as a top-level item (no folder nesting)
            for path in paths:
                coords = [(pt[0], pt[1]) for pt in path]
                ls = kml.newlinestring(name=f"{zipcode}-{crid} ({res_cnt:,} res)")
                ls.coords = coords
                ls.description = build_description(attrs)
                ls.style.linestyle.color = color
                ls.style.linestyle.width = width

            matched += 1
            zip_found += 1
            total_res += res_cnt
            total_bus += bus_cnt
            total_addr += tot_cnt

        print(f"found {zip_found}/{len(wanted_crids)}")
        time.sleep(0.3)  # Be polite to the API

    # Save KMZ
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    kml_path = DATA_DIR / output_name.replace(".kmz", ".kml")
    kmz_path = DATA_DIR / output_name

    kml.save(str(kml_path))
    with zipfile.ZipFile(kmz_path, "w", zipfile.ZIP_DEFLATED) as kmz:
        kmz.write(kml_path, arcname="doc.kml")
    kml_path.unlink()

    kmz_size = kmz_path.stat().st_size / 1024
    print()
    print("=" * 60)
    print("EXPORT COMPLETE")
    print("=" * 60)
    print(f"Output: {kmz_path} ({kmz_size:.1f} KB)")
    print(f"Routes matched: {matched}/{total_pairs}")
    print(f"Total residential: {total_res:,}")
    print(f"Total business:    {total_bus:,}")
    print(f"Total addresses:   {total_addr:,}")

    if missing:
        print(f"\nMissing routes ({len(missing)}):")
        for z, c in missing:
            print(f"   {z} {c}")

    print()
    print("Color Legend (by residential count):")
    for b in RES_COUNT_BINS:
        print(f"   {b['label']}")
    print()
    print("Import into Google My Maps:")
    print("   1. Go to https://mymaps.google.com")
    print("   2. Create a New Map -> Import -> Upload the .kmz file")
    print("=" * 60)


if __name__ == "__main__":
    main()
