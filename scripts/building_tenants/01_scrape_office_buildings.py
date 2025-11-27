#!/usr/bin/env python3
"""
Scrape office buildings in Lower Manhattan (below 14th Street) with 5+ tenants.
Uses hybrid approach:
1. OSM Overpass API for building data (FREE)
2. Count businesses per address using web scraping or APIs
"""

import csv
import json
import requests
from collections import defaultdict
from pathlib import Path
from typing import Dict, List
import time


# Configuration
DATA_DIR = Path('data')
OUTPUT_CSV = DATA_DIR / 'lower_manhattan_office_buildings.csv'

# Overpass API endpoint
OVERPASS_API = "https://overpass-api.de/api/interpreter"

# Geographic boundaries (Lower Manhattan below 14th Street)
LOWER_MANHATTAN_BBOX = {
    'south': 40.7000,  # Battery
    'north': 40.7342,  # 14th Street
    'west': -74.0200,  # West side
    'east': -73.9800,  # East side
}

# Minimum number of tenants to qualify as multi-tenant office building
MIN_TENANTS = 5


def fetch_offices_from_osm() -> List[Dict]:
    """
    Fetch office buildings from OpenStreetMap using Overpass API.

    Returns:
        List of office buildings with addresses
    """
    bbox = LOWER_MANHATTAN_BBOX

    # Overpass QL query to find office buildings
    # We look for nodes/ways tagged as office buildings
    overpass_query = f"""
    [out:json][timeout:60];
    (
      // Commercial office buildings
      way["building:use"="commercial"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
      way["building"="commercial"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
      way["building"="office"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});

      // Buildings with multiple units/levels (likely multi-tenant)
      way["building:levels"~"^([5-9]|[1-9][0-9]+)$"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});

      // Known office addresses
      node["office"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
    );
    out center;
    """

    print("  Querying OpenStreetMap Overpass API...")

    try:
        response = requests.post(
            OVERPASS_API,
            data={'data': overpass_query},
            timeout=90
        )
        response.raise_for_status()
        data = response.json()

        buildings = []
        for element in data.get('elements', []):
            tags = element.get('tags', {})

            # Get coordinates
            if 'center' in element:
                lat = element['center']['lat']
                lon = element['center']['lon']
            elif 'lat' in element:
                lat = element['lat']
                lon = element['lon']
            else:
                continue

            # Get address
            addr_parts = []
            if 'addr:housenumber' in tags:
                addr_parts.append(tags['addr:housenumber'])
            if 'addr:street' in tags:
                addr_parts.append(tags['addr:street'])

            address = ' '.join(addr_parts) if addr_parts else None

            if address:  # Only include if has address
                buildings.append({
                    'osm_id': element.get('id'),
                    'osm_type': element.get('type'),
                    'address': address,
                    'full_address': f"{address}, New York, NY",
                    'latitude': lat,
                    'longitude': lon,
                    'building_levels': tags.get('building:levels'),
                    'building_type': tags.get('building'),
                    'name': tags.get('name'),
                    'postcode': tags.get('addr:postcode')
                })

        print(f"    Found {len(buildings)} buildings with addresses from OSM")
        return buildings

    except requests.exceptions.RequestException as e:
        print(f"    Error fetching from OSM: {e}")
        return []


def normalize_address(building: str, street: str) -> str:
    """
    Normalize address for consistent grouping.

    Args:
        building: Building number
        street: Street name

    Returns:
        Normalized address string
    """
    building = (building or '').strip().upper()
    street = (street or '').strip().upper()

    # Remove common variations
    street = street.replace('AVENUE', 'AVE')
    street = street.replace('STREET', 'ST')
    street = street.replace('BOULEVARD', 'BLVD')
    street = street.replace('  ', ' ')

    return f"{building} {street}".strip()


def is_below_14th_street(latitude: str) -> bool:
    """
    Check if latitude is below 14th Street.

    Args:
        latitude: Latitude as string

    Returns:
        True if below 14th Street
    """
    try:
        lat = float(latitude)
        return lat <= LOWER_MANHATTAN_BOUNDARY['max_latitude']
    except (ValueError, TypeError):
        return False


def estimate_tenant_count(building: Dict) -> int:
    """
    Estimate tenant count based on building characteristics.

    Args:
        building: Building dictionary from OSM

    Returns:
        Estimated number of tenants
    """
    # Use building levels as proxy for tenant count
    # Assumption: ~2-3 tenants per floor for office buildings
    levels = building.get('building_levels')

    if levels:
        try:
            num_levels = int(levels)
            # Estimate 2.5 tenants per floor on average
            return int(num_levels * 2.5)
        except (ValueError, TypeError):
            pass

    # Default estimate for buildings without level data
    # If marked as office/commercial, assume at least 8 tenants
    building_type = building.get('building_type') or ''
    if building_type.lower() in ['office', 'commercial']:
        return 8

    # Conservative default
    return 1


def filter_office_buildings(buildings: List[Dict], min_tenants: int = MIN_TENANTS) -> List[Dict]:
    """
    Filter buildings with minimum number of tenants.

    Args:
        buildings: List of buildings from OSM
        min_tenants: Minimum number of tenants required

    Returns:
        List of qualifying office buildings
    """
    office_buildings = []

    for building in buildings:
        # Estimate tenant count
        tenant_count = estimate_tenant_count(building)

        if tenant_count >= min_tenants:
            office_buildings.append({
                'address': building['full_address'],
                'estimated_tenants': tenant_count,
                'building_levels': building.get('building_levels', 'Unknown'),
                'building_type': building.get('building_type', 'Unknown'),
                'building_name': building.get('name', ''),
                'zip_code': building.get('postcode', ''),
                'latitude': building['latitude'],
                'longitude': building['longitude']
            })

    # Sort by tenant count (descending)
    office_buildings.sort(key=lambda x: x['estimated_tenants'], reverse=True)

    return office_buildings


def save_to_csv(buildings: List[Dict], output_file: Path):
    """
    Save office buildings to CSV file.

    Args:
        buildings: List of office buildings
        output_file: Output CSV file path
    """
    if not buildings:
        print("No buildings to save")
        return

    output_file.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        'address', 'building_name', 'estimated_tenants', 'building_levels',
        'building_type', 'zip_code', 'latitude', 'longitude'
    ]

    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for building in buildings:
            writer.writerow({
                'address': building['address'],
                'building_name': building['building_name'],
                'estimated_tenants': building['estimated_tenants'],
                'building_levels': building['building_levels'],
                'building_type': building['building_type'],
                'zip_code': building['zip_code'],
                'latitude': building['latitude'] or '',
                'longitude': building['longitude'] or ''
            })

    print(f"\n✓ Saved {len(buildings)} office buildings to: {output_file}")


def print_summary(buildings: List[Dict]):
    """Print summary statistics."""
    if not buildings:
        print("\n✗ No office buildings found matching criteria")
        return

    print(f"\n{'='*60}")
    print("SUMMARY STATISTICS")
    print(f"{'='*60}")
    print(f"Total office buildings found: {len(buildings)}")
    print(f"Minimum tenants: {MIN_TENANTS}")
    print("Note: Tenant counts are ESTIMATES based on building levels")

    if buildings:
        avg_tenants = sum(b['estimated_tenants'] for b in buildings) / len(buildings)
        max_building = max(buildings, key=lambda x: x['estimated_tenants'])

        print(f"\nAverage estimated tenants per building: {avg_tenants:.1f}")
        print(f"Max estimated tenants: {max_building['estimated_tenants']}")
        print(f"\nTop building: {max_building['address']}")
        print(f"  Name: {max_building.get('building_name', 'N/A')}")
        print(f"  Estimated tenants: {max_building['estimated_tenants']}")
        print(f"  Levels: {max_building.get('building_levels', 'Unknown')}")

        # Show top 5 buildings
        print(f"\nTop 5 office buildings:")
        for i, b in enumerate(buildings[:5], 1):
            name = b.get('building_name') or 'Unnamed'
            print(f"  {i}. {name} - {b['address']}")
            print(f"     {b['estimated_tenants']} est. tenants, {b.get('building_levels', '?')} levels")


def main():
    """Main function to scrape office buildings."""
    print(f"{'='*60}")
    print("LOWER MANHATTAN OFFICE BUILDING SCRAPER")
    print(f"{'='*60}")
    print(f"Target: Buildings below 14th Street with {MIN_TENANTS}+ tenants")
    print(f"Source: OpenStreetMap Overpass API (FREE)")
    print(f"Method: Estimate tenants from building levels")
    print(f"{'='*60}\n")

    # Fetch office buildings from OSM
    print("Fetching building data from OpenStreetMap...")
    buildings = fetch_offices_from_osm()

    if not buildings:
        print("\n✗ No buildings found from OSM")
        print("This could be due to:")
        print("  - Limited OSM data coverage in this area")
        print("  - API timeout")
        print("  - Network issues")
        return

    print(f"✓ Found {len(buildings)} buildings from OSM")

    # Filter for buildings with 5+ estimated tenants
    print(f"\nFiltering for buildings with {MIN_TENANTS}+ estimated tenants...")
    office_buildings = filter_office_buildings(buildings, MIN_TENANTS)
    print(f"✓ Found {len(office_buildings)} qualifying office buildings")

    # Save results
    save_to_csv(office_buildings, OUTPUT_CSV)

    # Print summary
    print_summary(office_buildings)

    print(f"\n{'='*60}")
    print("SCRAPING COMPLETED!")
    print(f"{'='*60}")
    print(f"Output file: {OUTPUT_CSV}")
    print(f"\nIMPORTANT NOTES:")
    print("- Tenant counts are ESTIMATES based on building levels")
    print("- Assumption: ~2.5 tenants per floor on average")
    print("- For actual tenant counts, use Google Places API enrichment")
    print(f"\nTotal cost: $0 (OpenStreetMap is free!)")


if __name__ == '__main__':
    main()
