#!/usr/bin/env python3
"""
Export Hartford College Campus Buildings & Parking to KMZ.
Uses OpenStreetMap Overpass API. Writes lean KML with shared styles.
"""

import math
import sys
import time
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

sys.stdout.reconfigure(line_buffering=True)
sys.path.append(str(Path(__file__).parent.parent.parent))

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "ct_facilities"
INPUT_CSV = DATA_DIR / "ct_facilities.csv"
OUTPUT_KML = DATA_DIR / "ct_college_campus.kml"
OUTPUT_KMZ = DATA_DIR / "ct_college_campus.kmz"

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
SEARCH_RADIUS_M = 300
RATE_LIMIT_DELAY = 3.0
DEDUP_RADIUS_M = 400

ICON_COLLEGE  = "http://maps.google.com/mapfiles/kml/paddle/orange-circle.png"
ICON_BUILDING = "http://maps.google.com/mapfiles/kml/shapes/schools.png"
ICON_PARKING  = "http://maps.google.com/mapfiles/kml/shapes/parking_lot.png"


# ── KML helpers ──────────────────────────────────────────────────────────────

KML_HEADER = """\
<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
  <name>Hartford College Campuses</name>
  <Style id="college">
    <IconStyle><scale>1.2</scale><Icon><href>{college}</href></Icon></IconStyle>
  </Style>
  <Style id="building">
    <IconStyle><scale>1.0</scale><Icon><href>{building}</href></Icon></IconStyle>
  </Style>
  <Style id="parking">
    <IconStyle><scale>1.0</scale><Icon><href>{parking}</href></Icon></IconStyle>
  </Style>
""".format(college=ICON_COLLEGE, building=ICON_BUILDING, parking=ICON_PARKING)

KML_FOOTER = "</Document>\n</kml>\n"


def placemark(name: str, lat: float, lon: float, style_id: str, description: str = "") -> str:
    desc_block = f"  <description><![CDATA[{description}]]></description>\n" if description else ""
    return (
        f"  <Placemark>\n"
        f"    <name>{escape(name)}</name>\n"
        f"    <styleUrl>#{style_id}</styleUrl>\n"
        f"{desc_block}"
        f"    <Point><coordinates>{lon},{lat},0</coordinates></Point>\n"
        f"  </Placemark>\n"
    )


def folder_open(name: str) -> str:
    return f"  <Folder><name>{escape(name)}</name>\n"


def folder_close() -> str:
    return "  </Folder>\n"


# ── Overpass ──────────────────────────────────────────────────────────────────

def query_overpass(lat: float, lon: float) -> dict:
    query = f"""
[out:json][timeout:25];
(
  way[building][name](around:{SEARCH_RADIUS_M},{lat},{lon});
  node[building][name](around:{SEARCH_RADIUS_M},{lat},{lon});
  way[amenity=parking](around:{SEARCH_RADIUS_M},{lat},{lon});
  node[amenity=parking](around:{SEARCH_RADIUS_M},{lat},{lon});
  relation[amenity=parking](around:{SEARCH_RADIUS_M},{lat},{lon});
);
out center;
"""
    for attempt in range(3):
        try:
            r = requests.post(OVERPASS_URL, data={"data": query}, timeout=20)
            if r.status_code == 429:
                wait = 10 * (attempt + 1)
                print(f"   Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            if r.status_code in (502, 504):
                wait = 8 * (attempt + 1)
                print(f"   Server error {r.status_code}, waiting {wait}s...")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except requests.exceptions.Timeout:
            print(f"   Timeout attempt {attempt + 1}")
            time.sleep(5)
    raise RuntimeError("Overpass failed after 3 attempts")


def get_coords(el: dict):
    if el["type"] == "node":
        return el.get("lat"), el.get("lon")
    c = el.get("center", {})
    return c.get("lat"), c.get("lon")


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    R = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin(math.radians(lat2-lat1)/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(math.radians(lon2-lon1)/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print()
    df = pd.read_csv(INPUT_CSV)
    colleges = df[df["facility_type"] == "college"].copy()
    colleges = colleges[colleges["latitude"].notna() & colleges["longitude"].notna()].copy()
    colleges = colleges.drop_duplicates(subset=["name"], keep="first").reset_index(drop=True)

    noise = ["highway auto", " llc", "planner", "gsu univ", "cafe", "bookstore",
             "driving school", "high school", "congress of", "community colleges", "student union"]
    keywords = ["university", "college", "institute", "polytechnic"]

    def real_campus(name):
        n = name.lower()
        return any(k in n for k in keywords) and not any(bad in n for bad in noise)

    before = len(colleges)
    colleges = colleges[colleges["name"].apply(real_campus)].reset_index(drop=True)
    print(f"Found {before} entries → {len(colleges)} CT colleges")
    print()

    # Collect data per campus
    campuses = []
    queried: list[tuple[float, float]] = []

    for idx, row in colleges.iterrows():
        name = row["name"]
        lat, lon = float(row["latitude"]), float(row["longitude"])

        if any(haversine_m(lat, lon, qlat, qlon) < DEDUP_RADIUS_M for qlat, qlon in queried):
            print(f"[{idx+1}/{len(colleges)}] SKIP: {name}")
            continue

        print(f"[{idx+1}/{len(colleges)}] {name}")
        try:
            data = query_overpass(lat, lon)
            elements = data.get("elements", [])
            queried.append((lat, lon))
        except Exception as e:
            print(f"   Failed: {e}")
            time.sleep(RATE_LIMIT_DELAY)
            continue

        buildings = [e for e in elements if e.get("tags", {}).get("name") and "building" in e.get("tags", {})]
        parking   = [e for e in elements if e.get("tags", {}).get("amenity") == "parking"]
        print(f"   Buildings: {len(buildings)}  Parking: {len(parking)}")

        campuses.append({
            "name": name, "lat": lat, "lon": lon,
            "address": row.get("address", ""), "website": row.get("website", ""),
            "buildings": buildings, "parking": parking,
        })
        time.sleep(RATE_LIMIT_DELAY)

    # Build KML string — single folder to avoid multi-layer warnings
    parts = [KML_HEADER]
    parts.append(folder_open("CT College Campuses"))

    for c in campuses:
        # College marker
        desc = f"<b>{c['name']}</b><br/>"
        if c["address"]:
            desc += f"Address: {c['address']}<br/>"
        if c["website"]:
            desc += f'<a href="{c["website"]}">{c["website"]}</a>'
        parts.append(placemark(c["name"], c["lat"], c["lon"], "college", desc))

        # Buildings
        for el in c["buildings"]:
            tags = el.get("tags", {})
            bname = tags.get("name", "").strip()
            if not bname or bname.lower() == "building":
                continue
            blat, blon = get_coords(el)
            if not blat or not blon:
                continue
            desc = f"<b>{bname}</b><br/>Campus: {c['name']}"
            if tags.get("building") not in (None, "yes"):
                desc += f"<br/>Type: {tags['building']}"
            parts.append(placemark(bname, blat, blon, "building", desc))

        # Parking
        for el in c["parking"]:
            tags = el.get("tags", {})
            plat, plon = get_coords(el)
            if not plat or not plon:
                continue
            pname = tags.get("name", "").strip() or "Parking Lot"
            desc = f"<b>{pname}</b><br/>Campus: {c['name']}"
            if tags.get("capacity"):
                desc += f"<br/>Capacity: {tags['capacity']}"
            parts.append(placemark(pname, plat, plon, "parking", desc))

    parts.append(folder_close())

    parts.append(KML_FOOTER)
    kml_content = "".join(parts)

    # Save
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_KML.write_text(kml_content, encoding="utf-8")
    with zipfile.ZipFile(OUTPUT_KMZ, "w", zipfile.ZIP_DEFLATED) as kmz:
        kmz.write(OUTPUT_KML, arcname="doc.kml")

    kml_kb = OUTPUT_KML.stat().st_size / 1024
    kmz_kb = OUTPUT_KMZ.stat().st_size / 1024
    print()
    print(f"Saved: {OUTPUT_KMZ}")
    print(f"KML: {kml_kb:.1f} KB  |  KMZ: {kmz_kb:.1f} KB")
    print(f"Campuses: {len(campuses)}, Layers: 3 (Colleges / Buildings / Parking)")


if __name__ == "__main__":
    main()
