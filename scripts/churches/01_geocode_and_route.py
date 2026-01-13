#!/usr/bin/env python3
"""
Geocode NJ churches and create optimized driving routes for each circled area
"""

import pandas as pd
import requests
import time
import json
import os
from typing import List, Tuple, Dict
import numpy as np
from scipy.spatial.distance import cdist

# API key for HERE Geocoding API
HERE_API_KEY = os.environ.get('HERE_API_KEY', '0zt1IVbSQt3cPrM8_jaLXyFoq9TALX4OPXWfIsxGg1s')

# Define the 7 circles based on the map image description
# Format: (name, center_lat, center_lng, radius_km, description)
CIRCLES = [
    ("Circle1_Northwest_Bergen", 40.915, -74.155, 5.0, "Nutley, Clifton, Passaic, Wallington area"),
    ("Circle2_North_Woodbridge", 40.850, -74.100, 4.0, "Woodbridge, Carlstadt, East Rutherford area"),
    ("Circle3_Northeast_Palisades", 40.870, -73.995, 3.0, "Palisades Park, Ridgefield, Fort Lee area"),
    ("Circle4_East_Edgewater", 40.820, -73.970, 2.5, "Edgewater, Grantwood area"),
    ("Circle5_South_Union_City", 40.770, -74.030, 3.5, "Union City, Weehawken, West New York area"),
    ("Circle6_Southwest_Newark", 40.750, -74.180, 4.5, "Newark, Belleville, Kearny area"),
    ("Circle7_Southeast_Secaucus", 40.790, -74.060, 3.0, "Secaucus and surrounding areas"),
]

def geocode_address(address: str) -> Tuple[float, float]:
    """Geocode an address using HERE Geocoding API"""
    try:
        url = "https://geocode.search.hereapi.com/v1/geocode"
        params = {
            'q': address,
            'apiKey': HERE_API_KEY,
            'limit': 1
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        if data.get('items') and len(data['items']) > 0:
            position = data['items'][0]['position']
            return position['lat'], position['lng']
        else:
            print(f"  Warning: No coordinates found for: {address}")
            return None, None

    except Exception as e:
        print(f"  Error geocoding {address}: {e}")
        return None, None

def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance in km between two points using Haversine formula"""
    from math import radians, sin, cos, sqrt, atan2

    R = 6371  # Earth's radius in km

    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1

    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))

    return R * c

def point_in_circle(lat: float, lng: float, circle_center_lat: float,
                    circle_center_lng: float, radius_km: float) -> bool:
    """Check if a point is within a circle"""
    distance = calculate_distance(lat, lng, circle_center_lat, circle_center_lng)
    return distance <= radius_km

def nearest_neighbor_route(points: List[Dict], start_idx: int = 0) -> List[int]:
    """
    Solve TSP using nearest neighbor heuristic
    Returns list of indices representing the optimal route order
    """
    if len(points) <= 1:
        return list(range(len(points)))

    # Create distance matrix
    coords = np.array([[p['latitude'], p['longitude']] for p in points])
    distances = cdist(coords, coords, metric='euclidean')

    n = len(points)
    unvisited = set(range(n))
    route = [start_idx]
    unvisited.remove(start_idx)

    current = start_idx
    while unvisited:
        # Find nearest unvisited point
        nearest = min(unvisited, key=lambda x: distances[current][x])
        route.append(nearest)
        unvisited.remove(nearest)
        current = nearest

    return route

def optimize_route_2opt(points: List[Dict], initial_route: List[int], max_iterations: int = 1000) -> List[int]:
    """
    Improve route using 2-opt algorithm
    """
    if len(points) <= 3:
        return initial_route

    coords = np.array([[points[i]['latitude'], points[i]['longitude']] for i in initial_route])
    route = list(range(len(initial_route)))

    improved = True
    iteration = 0

    while improved and iteration < max_iterations:
        improved = False
        iteration += 1

        for i in range(1, len(route) - 2):
            for j in range(i + 1, len(route)):
                if j - i == 1:
                    continue

                # Calculate current distance
                current_dist = (
                    np.linalg.norm(coords[route[i]] - coords[route[i-1]]) +
                    np.linalg.norm(coords[route[j]] - coords[route[(j+1) % len(route)]])
                )

                # Calculate new distance if we reverse the segment
                new_dist = (
                    np.linalg.norm(coords[route[j]] - coords[route[i-1]]) +
                    np.linalg.norm(coords[route[i]] - coords[route[(j+1) % len(route)]])
                )

                if new_dist < current_dist:
                    # Reverse the segment
                    route[i:j+1] = reversed(route[i:j+1])
                    improved = True

    return [initial_route[i] for i in route]

def main():
    print("=" * 80)
    print("NJ CHURCH ROUTE OPTIMIZER")
    print("=" * 80)

    # Create output directory
    output_dir = 'data/churches'
    os.makedirs(output_dir, exist_ok=True)

    # Read church data
    print("\n1. Reading church data...")
    df = pd.read_excel('data/church_NJ.xlsx', sheet_name=0)
    print(f"   Found {len(df)} churches")

    # Geocode addresses
    print("\n2. Geocoding addresses...")
    progress_file = f'{output_dir}/geocoding_progress.json'

    # Load existing progress if available
    if os.path.exists(progress_file):
        with open(progress_file, 'r') as f:
            progress = json.load(f)
        print(f"   Resuming from existing progress ({len(progress)} already geocoded)")
    else:
        progress = {}

    geocoded_churches = []

    for idx, row in df.iterrows():
        address = row['Address']

        if pd.isna(address) or address == '':
            print(f"   [{idx+1}/{len(df)}] Skipping - no address")
            continue

        # Check if already geocoded
        if address in progress:
            lat, lng = progress[address]
        else:
            print(f"   [{idx+1}/{len(df)}] Geocoding: {address}")
            lat, lng = geocode_address(address)

            if lat is not None and lng is not None:
                progress[address] = [lat, lng]
                # Save progress every 10 addresses
                if idx % 10 == 0:
                    with open(progress_file, 'w') as f:
                        json.dump(progress, f, indent=2)

            # Rate limiting
            time.sleep(0.2)

        if lat is not None and lng is not None:
            geocoded_churches.append({
                'name': row['Names'],
                'address': address,
                'type': row['Type'],
                'latitude': lat,
                'longitude': lng,
                'phone': row.get('Phone Number', ''),
                'website': row.get('Website', ''),
                'opens_at': row.get('Opens At', ''),
                'review_count': row.get('Review Count', 0),
                'avg_review': row.get('Average Review Count', 0),
            })

    # Save final progress
    with open(progress_file, 'w') as f:
        json.dump(progress, f, indent=2)

    print(f"\n   Successfully geocoded {len(geocoded_churches)} churches")

    # Assign churches to circles
    print("\n3. Assigning churches to circles...")

    circle_assignments = {circle[0]: [] for circle in CIRCLES}
    unassigned = []

    for church in geocoded_churches:
        assigned = False
        for circle_name, center_lat, center_lng, radius_km, description in CIRCLES:
            if point_in_circle(church['latitude'], church['longitude'],
                              center_lat, center_lng, radius_km):
                circle_assignments[circle_name].append(church)
                assigned = True
                break

        if not assigned:
            unassigned.append(church)

    print("\n   Circle assignments:")
    for circle_name in circle_assignments:
        count = len(circle_assignments[circle_name])
        print(f"   - {circle_name}: {count} churches")
    print(f"   - Unassigned: {len(unassigned)} churches")

    # Generate optimized routes for each circle
    print("\n4. Generating optimized routes...")

    all_routes = []

    for circle_name, center_lat, center_lng, radius_km, description in CIRCLES:
        churches = circle_assignments[circle_name]

        if len(churches) == 0:
            print(f"\n   {circle_name}: No churches to route")
            continue

        print(f"\n   {circle_name}: {len(churches)} churches")
        print(f"   Description: {description}")

        if len(churches) == 1:
            route_order = [0]
        else:
            # Find starting point (closest to circle center)
            start_idx = min(range(len(churches)),
                          key=lambda i: calculate_distance(
                              churches[i]['latitude'], churches[i]['longitude'],
                              center_lat, center_lng))

            # Generate initial route using nearest neighbor
            initial_route = nearest_neighbor_route(churches, start_idx)

            # Optimize using 2-opt
            route_order = optimize_route_2opt(churches, initial_route)

        # Create ordered list
        ordered_churches = [churches[i] for i in route_order]

        # Calculate total distance
        total_distance = 0
        for i in range(len(ordered_churches) - 1):
            dist = calculate_distance(
                ordered_churches[i]['latitude'],
                ordered_churches[i]['longitude'],
                ordered_churches[i+1]['latitude'],
                ordered_churches[i+1]['longitude']
            )
            total_distance += dist

        print(f"   Route optimized: {len(ordered_churches)} stops, {total_distance:.2f} km total")

        # Add to all routes with sequence numbers
        for seq, church in enumerate(ordered_churches, 1):
            route_record = church.copy()
            route_record['circle'] = circle_name
            route_record['sequence'] = seq
            route_record['circle_description'] = description
            all_routes.append(route_record)

    # Save routes to CSV
    print("\n5. Exporting routes...")

    routes_df = pd.DataFrame(all_routes)
    output_csv = f'{output_dir}/nj_churches_routes.csv'
    routes_df.to_csv(output_csv, index=False)
    print(f"   ✓ Saved to {output_csv}")

    # Create separate CSV for each circle
    for circle_name in circle_assignments:
        circle_routes = routes_df[routes_df['circle'] == circle_name]
        if len(circle_routes) > 0:
            circle_csv = f'{output_dir}/{circle_name}_route.csv'
            circle_routes.to_csv(circle_csv, index=False)
            print(f"   ✓ Saved {circle_name} to {circle_csv}")

    # Save unassigned churches
    if unassigned:
        unassigned_df = pd.DataFrame(unassigned)
        unassigned_csv = f'{output_dir}/unassigned_churches.csv'
        unassigned_df.to_csv(unassigned_csv, index=False)
        print(f"   ✓ Saved {len(unassigned)} unassigned churches to {unassigned_csv}")

    # Print summary
    print("\n" + "=" * 80)
    print("ROUTE OPTIMIZATION COMPLETE")
    print("=" * 80)
    print(f"\nTotal churches processed: {len(geocoded_churches)}")
    print(f"Total churches routed: {len(all_routes)}")
    print(f"Unassigned churches: {len(unassigned)}")
    print(f"\nOutput files saved to: {output_dir}/")
    print("  - nj_churches_routes.csv (all routes combined)")
    print("  - [CircleName]_route.csv (individual circle routes)")
    print("  - unassigned_churches.csv (churches outside circles)")

if __name__ == '__main__':
    main()
