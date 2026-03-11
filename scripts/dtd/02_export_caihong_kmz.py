#!/usr/bin/env python3
"""
Generate KMZ for EDDM carrier routes listed in Albany 2026 CaiHong_180K-2.xls.

Reads all three mailing-date sheets (Mar 10, Mar 17, Mar 24), fetches route
geometry from the USPS EDDM ArcGIS API, and outputs a KMZ with color-coded
routes grouped by sheet and demographic popups.

Usage:
    python scripts/dtd/02_export_caihong_kmz.py
"""

import time
import zipfile
from collections import defaultdict
from pathlib import Path

import xlrd
import requests
from simplekml import Kml

PROJECT_ROOT = Path(__file__).parent.parent.parent
XLS_PATH = Path(__file__).parent / "Albany 2026 CaiHong_180K-2.xls"
OUTPUT_DIR = PROJECT_ROOT / "data" / "dtd"
OUTPUT_NAME = "albany_2026_caihong_180k_2_routes.kmz"  # combined (kept for reference)
OUTPUT_NAMES = {
    "Mar 10": "albany_2026_caihong_mar10.kmz",
    "Mar 17": "albany_2026_caihong_mar17.kmz",
    "Mar 24": "albany_2026_caihong_mar24.kmz",
}

EDDM_API_URL = "https://gis.usps.com/arcgis/rest/services/EDDM/selectZIP/GPServer/routes/execute"

# 16 visually distinct colors (KML format: AABBGGRR)
ROUTE_COLORS = [
    "ff0000ff",  # Red
    "ffff0000",  # Blue
    "ff00cc00",  # Green
    "ff00ffff",  # Yellow
    "ffff00ff",  # Magenta
    "ff00a5ff",  # Orange
    "ff800080",  # Purple
    "ffffff00",  # Cyan
    "ffb469ff",  # Hot Pink
    "ff7fff00",  # Spring Green
    "ffffbf00",  # Deep Sky Blue
    "ff3c14dc",  # Crimson
    "ff00d7ff",  # Gold
    "ff00ff7f",  # Chartreuse
    "ffd1ce00",  # Dark Turquoise
    "ff2d52a0",  # Sienna
]

SHEET_NAMES = ["Mar 10", "Mar 17", "Mar 24"]


def load_xls_sheet(ws, sheet_name):
    """Load ZIP/CRID pairs and demographic data from one xlrd worksheet.

    Returns:
        routes: {(zip, crid): {demographic fields...}}
        grouped: {zip: set of crids}
    """
    headers = ws.row_values(0)

    routes = {}
    grouped = defaultdict(set)

    for r in range(1, ws.nrows):
        row = ws.row_values(r)
        data = dict(zip(headers, row))

        # ZIP may come back as a float (e.g. 12159.0) from xlrd
        raw_zip = data.get("ZIP", "")
        if isinstance(raw_zip, float):
            raw_zip = str(int(raw_zip))
        zipcode = str(raw_zip).strip().zfill(5)

        crid = str(data.get("CRID", "")).strip()
        if not zipcode or not crid or zipcode == "00000":
            continue

        grouped[zipcode].add(crid)
        routes[(zipcode, crid)] = {
            "sheet": sheet_name,
            "city": str(data.get("City", "")).strip(),
            "state": str(data.get("State", "")).strip(),
            "segment": str(data.get("Segment", "")).strip(),
            "sfdu": int(data.get("SFDU", 0) or 0),
            "mfdu": int(data.get("MFDU", 0) or 0),
            "trailers": int(data.get("Trailers", 0) or 0),
            "sub_total": int(data.get("Sub Total", 0) or 0),
            "bus": int(data.get("Bus", 0) or 0),
            "total": int(data.get("Total", 0) or 0),
            "names": int(data.get("Names", 0) or 0),
            "median_income": data.get("Median Income") or None,
            "median_home_value": data.get("Median Home Value") or None,
            "median_age": data.get("Median Age") or None,
            "phwc": str(data.get("PHWC", "")).strip(),
            "sat": str(data.get("Sat", "")).strip(),
            "dfo": str(data.get("DFO", "")).strip(),
            "pct_black": str(data.get("PCT Black", "")).strip(),
            "pct_asian": str(data.get("PCT Asian", "")).strip(),
            "pct_hispanic": str(data.get("PCT Hispanic", "")).strip(),
        }

    return routes, grouped


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
    return results[0].get("value", {}).get("features", [])


def build_description(xlsx_data, api_attrs):
    """Build an HTML popup from demographic data + API attributes."""
    d = xlsx_data
    zipcode = api_attrs.get("ZIP_CODE", "N/A")
    facility = api_attrs.get("FACILITY_NAME", "N/A")

    income_str = f"${d['median_income']:,.0f}" if d.get("median_income") else "N/A"
    home_str = f"${d['median_home_value']:,.0f}" if d.get("median_home_value") else "N/A"
    age_str = str(int(d["median_age"])) if d.get("median_age") else "N/A"

    return f"""<b>Route:</b> {zipcode}-{api_attrs.get('CRID_ID', 'N/A')}<br/>
<b>City:</b> {d['city']}, {d['state']}<br/>
<b>Post Office:</b> {facility}<br/>
<b>Mailing Date:</b> {d['sheet']}<br/>
<hr/>
<b>SFDU:</b> {d['sfdu']:,} | <b>MFDU:</b> {d['mfdu']:,} | <b>Trailers:</b> {d['trailers']:,}<br/>
<b>Residential Sub Total:</b> {d['sub_total']:,}<br/>
<b>Business:</b> {d['bus']:,}<br/>
<b>Total:</b> {d['total']:,} | <b>Names:</b> {d['names']:,}<br/>
<hr/>
<b>Median Income:</b> {income_str}<br/>
<b>Median Home Value:</b> {home_str}<br/>
<b>Median Age:</b> {age_str}<br/>
<b>PHWC:</b> {d['phwc']}<br/>
<b>Saturday Delivery:</b> {d['sat']}<br/>
<b>DFO:</b> {d['dfo']}<br/>
<hr/>
<b>PCT Black:</b> {d['pct_black']} | <b>PCT Asian:</b> {d['pct_asian']} | <b>PCT Hispanic:</b> {d['pct_hispanic']}<br/>
<hr/>
<i>Source: USPS EDDM / Albany 2026 CaiHong_180K-2.xls</i>"""


def save_kmz(kml, kmz_path):
    kml_path = kmz_path.with_suffix(".kml")
    kml.save(str(kml_path))
    with zipfile.ZipFile(kmz_path, "w", zipfile.ZIP_DEFLATED) as kmz:
        kmz.write(kml_path, arcname="doc.kml")
    kml_path.unlink()
    return kmz_path.stat().st_size / 1024


def main():
    if not XLS_PATH.exists():
        print(f"Error: xls file not found: {XLS_PATH}")
        return

    wb = xlrd.open_workbook(str(XLS_PATH))

    grand_total_routes = 0
    grand_matched = 0
    all_missing = []

    sheet_summaries = []
    for sheet_name in SHEET_NAMES:
        ws = wb.sheet_by_name(sheet_name)
        routes, grouped = load_xls_sheet(ws, sheet_name)
        sheet_summaries.append((sheet_name, routes, grouped))
        grand_total_routes += len(routes)

    print("=" * 60)
    print("Albany 2026 CaiHong 180K EDDM CARRIER ROUTES -> KMZ")
    print("=" * 60)
    print(f"Source: {XLS_PATH.name}")
    print(f"Total routes: {grand_total_routes} (split into {len(SHEET_NAMES)} files)")
    print()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_files = []

    for sheet_name, routes, grouped in sheet_summaries:
        print(f"--- {sheet_name} ({len(routes)} routes, {len(grouped)} ZIPs) ---")

        kml = Kml()
        kml.document.name = f"Albany 2026 CaiHong – {sheet_name}"
        kml.document.description = (
            f"EDDM carrier routes – mailing date {sheet_name} "
            f"({len(routes)} routes across {len(grouped)} ZIPs)"
        )

        color_idx = 0
        matched = 0
        missing = []

        for zipcode in sorted(grouped.keys()):
            wanted_crids = grouped[zipcode]
            print(f"  ZIP {zipcode}: fetching ({len(wanted_crids)} routes)...", end=" ", flush=True)

            try:
                features = fetch_routes(zipcode)
            except Exception as e:
                print(f"ERROR: {e}")
                for crid in wanted_crids:
                    missing.append((zipcode, crid))
                continue

            by_crid = {f.get("attributes", {}).get("CRID_ID", ""): f for f in features}

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

                xlsx_data = routes[(zipcode, crid)]
                color = ROUTE_COLORS[color_idx % len(ROUTE_COLORS)]
                color_idx += 1

                label = f"{zipcode}-{crid} ({xlsx_data['total']:,} total)"
                mg = kml.newmultigeometry(name=label)
                mg.description = build_description(xlsx_data, attrs)
                mg.style.linestyle.color = color
                mg.style.linestyle.width = 4
                for path in paths:
                    coords = [(round(pt[0], 5), round(pt[1], 5)) for pt in path]
                    mg.newlinestring().coords = coords

                matched += 1
                zip_found += 1

            print(f"found {zip_found}/{len(wanted_crids)}")
            time.sleep(0.3)

        kmz_path = OUTPUT_DIR / OUTPUT_NAMES[sheet_name]
        kmz_size = save_kmz(kml, kmz_path)
        output_files.append((kmz_path, kmz_size, matched, len(routes)))

        grand_matched += matched
        all_missing.extend(missing)
        print(f"  => matched {matched}/{len(routes)}, saved {kmz_path.name} ({kmz_size:.1f} KB)")
        print()

    print("=" * 60)
    print("EXPORT COMPLETE")
    print("=" * 60)
    for kmz_path, kmz_size, matched, total in output_files:
        print(f"  {kmz_path.name}  ({kmz_size:.1f} KB)  {matched}/{total} routes")
    print(f"\nTotal routes matched: {grand_matched}/{grand_total_routes}")

    if all_missing:
        print(f"\nMissing routes ({len(all_missing)}):")
        for z, c in all_missing:
            print(f"   {z} {c}")

    print()
    print("Import into Google My Maps:")
    print("   1. Go to https://mymaps.google.com")
    print("   2. Create a New Map -> Import -> Upload each .kmz file as a separate layer")
    print("=" * 60)


if __name__ == "__main__":
    main()
