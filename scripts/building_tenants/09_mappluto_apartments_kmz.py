#!/usr/bin/env python3
"""
Query MapPLUTO directly for all apartment buildings in Lower Manhattan
and export to KMZ for Google My Maps.

Covers bldgclass C (walk-up), D (elevator), RM/R1 (residential condo).
No single-family (A) or townhouses (B).
"""

import csv
import requests
import zipfile
from pathlib import Path
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, ElementTree


# Lower Manhattan bounding box (Battery to 14th St)
BBOX = {
    'south': 40.7000,
    'north': 40.7342,
    'west': -74.0200,
    'east': -73.9800,
}

MAPPLUTO_URL = 'https://data.cityofnewyork.us/resource/64uk-42ks.json'
MIN_FLOORS = 7

OUTPUT_DIR = Path('data/building_tenants/exports')

# Latitude midpoint for splitting walk-ups north/south
LAT_MID = (BBOX['south'] + BBOX['north']) / 2  # ~40.717

# BldgClass prefix → human label
BLDG_CLASS_LABELS = {
    'C': 'Walk-up Apartments',
    'D': 'Elevator Apartments',
    'R': 'Residential Condo',
}


def fetch_mappluto_apartments() -> list:
    """Fetch all apartment lots from MapPLUTO with pagination."""
    where = (
        f"latitude between {BBOX['south']} and {BBOX['north']} "
        f"AND longitude between {BBOX['west']} and {BBOX['east']} "
        "AND (bldgclass like 'C%' OR bldgclass like 'D%' "
        "OR bldgclass like 'RM%' OR bldgclass like 'R1%' "
        "OR bldgclass like 'RC%' OR bldgclass like 'R4%') "
        f"AND numfloors >= {MIN_FLOORS}"
    )
    select = 'address,ownername,numfloors,bldgclass,landuse,yearbuilt,bbl,zipcode,latitude,longitude'

    results = []
    limit = 5000
    offset = 0

    while True:
        params = {
            '$where': where,
            '$select': select,
            '$limit': limit,
            '$offset': offset,
            '$order': 'bbl',
        }
        resp = requests.get(MAPPLUTO_URL, params=params, timeout=30)
        resp.raise_for_status()
        page = resp.json()
        results.extend(page)
        print(f"  Fetched {len(results)} lots so far...")
        if len(page) < limit:
            break
        offset += limit

    return results


def bldg_class_label(bldgclass: str) -> str:
    prefix = bldgclass[:1].upper() if bldgclass else ''
    return BLDG_CLASS_LABELS.get(prefix, f'Residential ({bldgclass})')


def create_kml_styles(doc: Element) -> None:
    styles = [
        ('elevator',  'http://maps.google.com/mapfiles/ms/icons/blue-dot.png'),    # D class
        ('walkup',    'http://maps.google.com/mapfiles/ms/icons/yellow-dot.png'),  # C class
        ('condo',     'http://maps.google.com/mapfiles/ms/icons/green-dot.png'),   # R class
        ('other',     'http://maps.google.com/mapfiles/ms/icons/orange-dot.png'),
    ]
    for style_id, icon_url in styles:
        style = SubElement(doc, 'Style', id=style_id)
        icon_style = SubElement(style, 'IconStyle')
        icon = SubElement(icon_style, 'Icon')
        href = SubElement(icon, 'href')
        href.text = icon_url


def marker_style(bldgclass: str) -> str:
    prefix = bldgclass[:1].upper() if bldgclass else ''
    return {'D': 'elevator', 'C': 'walkup', 'R': 'condo'}.get(prefix, 'other')


def create_placemark(doc: Element, lot: dict) -> None:
    try:
        lat = float(lot['latitude'])
        lon = float(lot['longitude'])
    except (KeyError, ValueError, TypeError):
        return

    address = lot.get('address', 'Unknown')
    owner = lot.get('ownername', '').title()
    bldgclass = lot.get('bldgclass', '')
    zipcode = lot.get('zipcode', '')
    yearbuilt = lot.get('yearbuilt', '')

    try:
        floors = int(float(lot.get('numfloors', 0))) or 'N/A'
    except (ValueError, TypeError):
        floors = 'N/A'

    parts = [bldg_class_label(bldgclass), f'Floors: {floors}']
    if zipcode:
        parts.append(f'ZIP: {zipcode}')
    if owner:
        parts.append(f'Owner: {owner}')
    if yearbuilt:
        parts.append(f'Built: {yearbuilt}')
    desc_text = ' | '.join(parts)

    placemark = SubElement(doc, 'Placemark')
    name_el = SubElement(placemark, 'name')
    name_el.text = address
    desc = SubElement(placemark, 'description')
    desc.text = desc_text
    style_url = SubElement(placemark, 'styleUrl')
    style_url.text = f'#{marker_style(bldgclass)}'
    point = SubElement(placemark, 'Point')
    coords = SubElement(point, 'coordinates')
    coords.text = f'{lon},{lat},0'


def build_kmz(lots: list, name: str, description: str, stem: str) -> int:
    """Build a KMZ for a subset of lots. Returns placemark count."""
    kml = Element('kml', xmlns='http://www.opengis.net/kml/2.2')
    document = SubElement(kml, 'Document')
    SubElement(document, 'name').text = name
    SubElement(document, 'description').text = description
    create_kml_styles(document)

    count = 0
    for lot in lots:
        if not lot.get('latitude') or not lot.get('longitude'):
            continue
        create_placemark(document, lot)
        count += 1

    kml_path = OUTPUT_DIR / f'{stem}.kml'
    kmz_path = OUTPUT_DIR / f'{stem}.kmz'
    ElementTree(kml).write(kml_path, encoding='utf-8', xml_declaration=True)
    with zipfile.ZipFile(kmz_path, 'w', zipfile.ZIP_DEFLATED) as kmz:
        kmz.write(kml_path, arcname='doc.kml')
    kml_path.unlink()  # clean up temp KML

    size_kb = kmz_path.stat().st_size / 1024
    print(f'  {kmz_path.name}: {count} placemarks, {size_kb:.1f} KB')
    return count


def main():
    print('=' * 60)
    print('MAPPLUTO → APARTMENT KMZ GENERATOR')
    print('=' * 60)
    print(f'Area: Lower Manhattan ({BBOX["south"]}–{BBOX["north"]} lat)')
    print(f'Types: Walk-up (C), Elevator (D), Condo (R)\n')

    print('Fetching apartment buildings from MapPLUTO...')
    lots = fetch_mappluto_apartments()
    print(f'Total lots fetched: {len(lots)}\n')

    from collections import Counter
    class_counts = Counter(lot.get('bldgclass', '')[:1] for lot in lots)
    print('By class prefix:')
    for prefix, count in sorted(class_counts.items()):
        print(f'  {prefix} ({BLDG_CLASS_LABELS.get(prefix, prefix)}): {count}')
    print(f'  Walk-up split latitude: {LAT_MID:.4f}\n')

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print('Writing KMZ...')
    total = build_kmz(
        lots,
        f'Lower Manhattan Apartments {MIN_FLOORS}+ Floors',
        (f'Apartment buildings in Lower Manhattan with {MIN_FLOORS}+ floors\n'
         f'Source: NYC MapPLUTO\n\n'
         f'Blue = Elevator (D) | Yellow = Walk-up (C) | Green = Condo (R)'),
        f'lower_manhattan_apartments_{MIN_FLOORS}plus_floors',
    )

    print(f'\n{"=" * 60}')
    print('DONE')
    print(f'{"=" * 60}')
    print(f'Placemarks : {total}')
    print(f'Output     : {OUTPUT_DIR}/lower_manhattan_apartments_{MIN_FLOORS}plus_floors.kmz')
    print(f'\nReady to import into Google My Maps.')


if __name__ == '__main__':
    main()
