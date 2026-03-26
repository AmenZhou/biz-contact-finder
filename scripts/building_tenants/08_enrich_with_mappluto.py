#!/usr/bin/env python3
"""
Enrich lower_manhattan_office_buildings.csv with NYC MapPLUTO data.

Fixes:
- building_type: replaces meaningless "yes" values with proper types
- zip_code: fills blank values
- building_name: fills blank values from owner name
- building_levels: replaces estimates with authoritative floor counts

Adds new columns: owner_name, year_built, bbl, bldg_class
"""

import csv
import re
import time
import requests
from pathlib import Path


# Paths
DATA_DIR = Path('data/building_tenants/buildings')
INPUT_CSV = DATA_DIR / 'lower_manhattan_office_buildings.csv'

# MapPLUTO Socrata API
MAPPLUTO_URL = 'https://data.cityofnewyork.us/resource/64uk-42ks.json'
SEARCH_RADIUS_M = 50
API_SLEEP_S = 0.2
MAX_RETRIES = 3

# At NYC latitude ~40.7°, degrees per metre:
#   lat: 1/111320 ≈ 8.983e-6 deg/m
#   lon: 1/(111320*cos(40.7°)) ≈ 1.185e-5 deg/m
_LAT_DEG_PER_M = 8.983e-6
_LON_DEG_PER_M = 1.185e-5

# Column order for output
FIELDNAMES = [
    'address', 'building_name', 'estimated_tenants', 'building_levels',
    'building_type', 'zip_code', 'latitude', 'longitude',
    'owner_name', 'year_built', 'bbl', 'bldg_class',
]

# LandUse code → building_type
LANDUSE_MAP = {
    '01': 'residential',
    '02': 'apartments',
    '03': 'apartments',
    '04': 'mixed',
    '05': 'commercial',
    '06': 'industrial',
    '08': 'government',
}

# BldgClass prefix → building_type (higher priority than landuse)
BLDGCLASS_MAP = {
    'O': 'office',
    'D': 'apartments',
    'C': 'apartments',
    'H': 'hotel',
    'R': 'school',
    'K': 'retail',
    'S': 'mixed',
    'I': 'institutional',
}

# Street abbreviation expansions for address matching
ABBREV_EXPANSIONS = {
    r'\bst\b': 'street',
    r'\bave\b': 'avenue',
    r'\bblvd\b': 'boulevard',
    r'\bpl\b': 'place',
    r'\brd\b': 'road',
    r'\bdr\b': 'drive',
    r'\bln\b': 'lane',
    r'\bct\b': 'court',
}


def load_csv(path: Path) -> list:
    with open(path, encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def query_mappluto(lat: float, lon: float) -> list:
    """Query MapPLUTO for lots within SEARCH_RADIUS_M of (lat, lon).
    Uses bounding box on the latitude/longitude columns (the dataset does not
    expose a geom column that supports within_circle).
    Returns list of lot dicts. Retries with exponential back-off on failure.
    """
    dlat = SEARCH_RADIUS_M * _LAT_DEG_PER_M
    dlon = SEARCH_RADIUS_M * _LON_DEG_PER_M
    bbox = (
        f'latitude between {lat - dlat} and {lat + dlat} AND '
        f'longitude between {lon - dlon} and {lon + dlon}'
    )
    params = {
        '$where': bbox,
        '$select': 'zipcode,ownername,numfloors,bldgclass,landuse,yearbuilt,bbl,address',
        '$limit': 10,
    }
    delay = 1
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(MAPPLUTO_URL, params=params, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            if attempt < MAX_RETRIES - 1:
                print(f"    Retry {attempt + 1}/{MAX_RETRIES - 1} after error: {exc}")
                time.sleep(delay)
                delay *= 2
            else:
                print(f"    Skipping row after {MAX_RETRIES} failures: {exc}")
                return []


def normalize_address_for_matching(addr: str) -> str:
    """Lowercase, strip punctuation, expand common street abbreviations."""
    if not addr:
        return ''
    result = addr.lower()
    result = re.sub(r'[^\w\s]', ' ', result)
    for pattern, expansion in ABBREV_EXPANSIONS.items():
        result = re.sub(pattern, expansion, result)
    result = re.sub(r'\s+', ' ', result).strip()
    return result


def pick_best_lot(candidates: list, building_address: str) -> dict | None:
    """Return the lot with the highest token overlap with building_address.
    Falls back to the first candidate if no tokens match.
    """
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    ref_tokens = set(normalize_address_for_matching(building_address).split())
    best_lot = candidates[0]
    best_score = -1

    for lot in candidates:
        lot_tokens = set(normalize_address_for_matching(lot.get('address', '')).split())
        score = len(ref_tokens & lot_tokens)
        if score > best_score:
            best_score = score
            best_lot = lot

    return best_lot


def map_building_type(landuse: str, bldgclass: str) -> str:
    """Derive building_type: bldgclass prefix takes priority over landuse."""
    if bldgclass:
        prefix = bldgclass[0].upper()
        if prefix in BLDGCLASS_MAP:
            return BLDGCLASS_MAP[prefix]
    if landuse and landuse.strip() in LANDUSE_MAP:
        return LANDUSE_MAP[landuse.strip()]
    return ''


def is_meaningful_type(value: str) -> bool:
    """Return False for blank or the literal string "yes"."""
    if not value:
        return False
    return value.strip().lower() != 'yes'


def enrich_row(row: dict, lot: dict, stats: dict) -> dict:
    """Apply MapPLUTO enrichment rules to a single row."""
    # zip_code — fill if blank
    if not row.get('zip_code') and lot.get('zipcode'):
        row['zip_code'] = lot['zipcode']
        stats['zip_filled'] += 1

    # building_type — replace if not meaningful and we have a mapped type
    mapped_type = map_building_type(lot.get('landuse', ''), lot.get('bldgclass', ''))
    if not is_meaningful_type(row.get('building_type')) and mapped_type:
        row['building_type'] = mapped_type
        stats['type_fixed'] += 1

    # building_levels — replace with authoritative MapPLUTO numfloors
    numfloors = lot.get('numfloors', '')
    try:
        row['building_levels'] = int(float(numfloors))
        stats['levels_updated'] += 1
    except (ValueError, TypeError):
        pass  # keep existing value

    # building_name — fill only if blank
    if not row.get('building_name') and lot.get('ownername'):
        row['building_name'] = lot['ownername'].title()
        stats['name_filled'] += 1

    # new columns — always write
    row['owner_name'] = (lot.get('ownername') or '').title()
    row['year_built'] = lot.get('yearbuilt', '')
    row['bbl'] = lot.get('bbl', '')
    row['bldg_class'] = lot.get('bldgclass', '')

    return row


def save_csv(rows: list, path: Path):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def print_summary(stats: dict, total: int):
    print(f"\n{'='*60}")
    print("ENRICHMENT SUMMARY")
    print(f"{'='*60}")
    print(f"Total rows processed : {total}")
    print(f"MapPLUTO matches     : {stats['matched']}  ({stats['matched']/total*100:.1f}%)")
    print(f"No coords / skipped  : {stats['no_coords']}")
    print(f"API failures         : {stats['api_error']}")
    print(f"No lots within {SEARCH_RADIUS_M}m   : {stats['no_lots']}")
    print(f"\nFields enriched:")
    print(f"  zip_code filled    : {stats['zip_filled']}")
    print(f"  building_type fixed: {stats['type_fixed']}")
    print(f"  building_levels upd: {stats['levels_updated']}")
    print(f"  building_name filled:{stats['name_filled']}")


def main():
    print(f"{'='*60}")
    print("MAPPLUTO ENRICHMENT")
    print(f"{'='*60}")
    print(f"Input : {INPUT_CSV}")
    print(f"API   : {MAPPLUTO_URL}")
    print(f"Radius: {SEARCH_RADIUS_M} m\n")

    rows = load_csv(INPUT_CSV)
    total = len(rows)
    print(f"Loaded {total} rows\n")

    stats = {
        'matched': 0,
        'no_coords': 0,
        'api_error': 0,
        'no_lots': 0,
        'zip_filled': 0,
        'type_fixed': 0,
        'levels_updated': 0,
        'name_filled': 0,
    }

    enriched_rows = []

    for i, row in enumerate(rows, 1):
        lat_str = row.get('latitude', '').strip()
        lon_str = row.get('longitude', '').strip()

        # Ensure new columns exist even if we skip
        row.setdefault('owner_name', '')
        row.setdefault('year_built', '')
        row.setdefault('bbl', '')
        row.setdefault('bldg_class', '')

        if not lat_str or not lon_str:
            stats['no_coords'] += 1
            enriched_rows.append(row)
            print(f"[{i:4d}/{total}] SKIP (no coords): {row.get('address', '')[:60]}")
            continue

        try:
            lat = float(lat_str)
            lon = float(lon_str)
        except ValueError:
            stats['no_coords'] += 1
            enriched_rows.append(row)
            print(f"[{i:4d}/{total}] SKIP (bad coords): {row.get('address', '')[:60]}")
            continue

        time.sleep(API_SLEEP_S)
        candidates = query_mappluto(lat, lon)

        if candidates is None or len(candidates) == 0:
            if candidates is None:
                stats['api_error'] += 1
            else:
                stats['no_lots'] += 1
            enriched_rows.append(row)
            print(f"[{i:4d}/{total}] NO MATCH: {row.get('address', '')[:60]}")
            continue

        lot = pick_best_lot(candidates, row.get('address', ''))
        stats['matched'] += 1
        row = enrich_row(row, lot, stats)
        enriched_rows.append(row)

        if i % 50 == 0:
            print(f"[{i:4d}/{total}] Progress: {stats['matched']} matched so far...")

    save_csv(enriched_rows, INPUT_CSV)
    print(f"\nSaved enriched data to: {INPUT_CSV}")

    print_summary(stats, total)

    print(f"\n{'='*60}")
    print("ENRICHMENT COMPLETED!")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
