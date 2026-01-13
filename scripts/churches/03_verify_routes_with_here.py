#!/usr/bin/env python3
"""
Verify and optimize church routes using HERE Routing API for actual road distances
"""

import pandas as pd
import requests
import time
import json
import os
from typing import List, Tuple, Dict, Optional
import numpy as np
from scipy.spatial.distance import cdist

# HERE API key
HERE_API_KEY = os.environ.get('HERE_API_KEY', '0zt1IVbSQt3cPrM8_jaLXyFoq9TALX4OPXWfIsxGg1s')

def get_driving_route(origin_lat: float, origin_lng: float,
                      dest_lat: float, dest_lng: float) -> Optional[Dict]:
    """
    Get driving route between two points using HERE Routing API
    Returns distance (meters), time (seconds), and route geometry
    """
    try:
        url = "https://router.hereapi.com/v8/routes"

        params = {
            'apiKey': HERE_API_KEY,
            'transportMode': 'car',
            'origin': f'{origin_lat},{origin_lng}',
            'destination': f'{dest_lat},{dest_lng}',
            'return': 'summary,polyline'
        }

        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()

        data = response.json()

        if 'routes' in data and len(data['routes']) > 0:
            route = data['routes'][0]
            section = route['sections'][0]

            return {
                'distance_meters': section['summary']['length'],
                'distance_km': section['summary']['length'] / 1000,
                'duration_seconds': section['summary']['duration'],
                'duration_minutes': section['summary']['duration'] / 60,
                'polyline': section.get('polyline', '')
            }
        else:
            print(f"  Warning: No route found")
            return None

    except Exception as e:
        print(f"  Error getting route: {e}")
        return None

def calculate_route_matrix(churches: List[Dict], cache_file: str) -> np.ndarray:
    """
    Calculate distance matrix using actual driving distances
    Uses caching to avoid repeated API calls
    """
    n = len(churches)

    # Load cache if exists
    if os.path.exists(cache_file):
        print(f"  Loading cached route matrix from {cache_file}")
        with open(cache_file, 'r') as f:
            cache = json.load(f)
    else:
        cache = {}

    # Initialize distance matrix
    distance_matrix = np.zeros((n, n))

    total_calls = 0
    cache_hits = 0

    for i in range(n):
        for j in range(n):
            if i == j:
                distance_matrix[i][j] = 0
                continue

            # Create cache key
            key = f"{churches[i]['latitude']:.6f},{churches[i]['longitude']:.6f}_to_{churches[j]['latitude']:.6f},{churches[j]['longitude']:.6f}"

            if key in cache:
                distance_matrix[i][j] = cache[key]
                cache_hits += 1
            else:
                # Get actual driving distance
                route = get_driving_route(
                    churches[i]['latitude'], churches[i]['longitude'],
                    churches[j]['latitude'], churches[j]['longitude']
                )

                if route:
                    distance_km = route['distance_km']
                    distance_matrix[i][j] = distance_km
                    cache[key] = distance_km
                else:
                    # Fallback to straight-line distance if routing fails
                    from math import radians, sin, cos, sqrt, atan2
                    R = 6371
                    lat1, lng1 = radians(churches[i]['latitude']), radians(churches[i]['longitude'])
                    lat2, lng2 = radians(churches[j]['latitude']), radians(churches[j]['longitude'])
                    dlat, dlng = lat2 - lat1, lng2 - lng1
                    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
                    distance_km = R * 2 * atan2(sqrt(a), sqrt(1-a))
                    distance_matrix[i][j] = distance_km
                    cache[key] = distance_km
                    print(f"  Warning: Using straight-line distance for route {i}->{j}")

                total_calls += 1

                # Rate limiting
                time.sleep(0.1)

                # Save cache periodically
                if total_calls % 50 == 0:
                    with open(cache_file, 'w') as f:
                        json.dump(cache, f)
                    print(f"  Progress: {total_calls} API calls, {cache_hits} cache hits")

    # Save final cache
    with open(cache_file, 'w') as f:
        json.dump(cache, f)

    print(f"  Complete: {total_calls} new API calls, {cache_hits} cache hits")

    return distance_matrix

def nearest_neighbor_route_with_matrix(distance_matrix: np.ndarray,
                                       start_idx: int = 0) -> List[int]:
    """
    Solve TSP using nearest neighbor with pre-computed distance matrix
    """
    n = distance_matrix.shape[0]

    if n <= 1:
        return list(range(n))

    unvisited = set(range(n))
    route = [start_idx]
    unvisited.remove(start_idx)

    current = start_idx
    while unvisited:
        # Find nearest unvisited
        nearest = min(unvisited, key=lambda x: distance_matrix[current][x])
        route.append(nearest)
        unvisited.remove(nearest)
        current = nearest

    return route

def optimize_route_2opt_with_matrix(distance_matrix: np.ndarray,
                                    initial_route: List[int],
                                    max_iterations: int = 1000) -> List[int]:
    """
    Improve route using 2-opt with pre-computed distance matrix
    """
    if len(initial_route) <= 3:
        return initial_route

    route = initial_route.copy()
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
                    distance_matrix[route[i-1]][route[i]] +
                    distance_matrix[route[j]][route[(j+1) % len(route)]]
                )

                # Calculate new distance if we reverse
                new_dist = (
                    distance_matrix[route[i-1]][route[j]] +
                    distance_matrix[route[i]][route[(j+1) % len(route)]]
                )

                if new_dist < current_dist:
                    # Reverse segment
                    route[i:j+1] = reversed(route[i:j+1])
                    improved = True

    return route

def add_detailed_route_info(churches: List[Dict], route_order: List[int]) -> List[Dict]:
    """
    Add detailed driving information for each segment
    """
    detailed_route = []

    for idx, church_idx in enumerate(route_order):
        church = churches[church_idx].copy()
        church['sequence'] = idx + 1

        # Get route to next stop
        if idx < len(route_order) - 1:
            next_church_idx = route_order[idx + 1]
            next_church = churches[next_church_idx]

            print(f"  Getting route for stop {idx+1} -> {idx+2}")

            route_info = get_driving_route(
                church['latitude'], church['longitude'],
                next_church['latitude'], next_church['longitude']
            )

            if route_info:
                church['distance_to_next_km'] = route_info['distance_km']
                church['distance_to_next_miles'] = route_info['distance_km'] * 0.621371
                church['drive_time_to_next_min'] = route_info['duration_minutes']
                church['next_stop'] = next_church['name']
            else:
                church['distance_to_next_km'] = 0
                church['distance_to_next_miles'] = 0
                church['drive_time_to_next_min'] = 0
                church['next_stop'] = next_church['name']

            time.sleep(0.1)  # Rate limiting
        else:
            church['distance_to_next_km'] = 0
            church['distance_to_next_miles'] = 0
            church['drive_time_to_next_min'] = 0
            church['next_stop'] = 'End of route'

        detailed_route.append(church)

    return detailed_route

def verify_circle_route(circle_name: str, input_csv: str, output_dir: str):
    """
    Verify and optimize a single circle's route using actual driving distances
    """
    print(f"\n{'='*80}")
    print(f"VERIFYING: {circle_name}")
    print(f"{'='*80}")

    # Read current route
    df = pd.read_csv(input_csv)
    churches = df.to_dict('records')

    print(f"Churches in route: {len(churches)}")

    if len(churches) <= 1:
        print("Only 1 church, no optimization needed")
        # Save as verified
        output_csv = f"{output_dir}/{circle_name}_verified.csv"
        df.to_csv(output_csv, index=False)
        return

    # Calculate distance matrix using actual driving distances
    print("\n1. Calculating driving distance matrix...")
    cache_file = f"{output_dir}/{circle_name}_route_cache.json"
    distance_matrix = calculate_route_matrix(churches, cache_file)

    # Find optimal route
    print("\n2. Optimizing route with actual road distances...")

    # Start from first church in original route
    start_idx = 0

    # Generate initial route
    initial_route = nearest_neighbor_route_with_matrix(distance_matrix, start_idx)

    # Optimize
    optimized_route = optimize_route_2opt_with_matrix(distance_matrix, initial_route)

    # Calculate total distances
    original_total = sum(distance_matrix[i][j] for i, j in zip(range(len(churches)), range(1, len(churches))))
    optimized_total = sum(distance_matrix[optimized_route[i]][optimized_route[i+1]]
                         for i in range(len(optimized_route) - 1))

    print(f"   Original route total: {original_total:.2f} km")
    print(f"   Optimized route total: {optimized_total:.2f} km")
    print(f"   Improvement: {original_total - optimized_total:.2f} km ({(1 - optimized_total/original_total)*100:.1f}%)")

    # Add detailed route info
    print("\n3. Adding detailed driving information...")
    ordered_churches = [churches[i] for i in optimized_route]
    detailed_route = add_detailed_route_info(ordered_churches, list(range(len(ordered_churches))))

    # Calculate cumulative stats
    cumulative_distance = 0
    cumulative_time = 0

    for church in detailed_route:
        church['cumulative_distance_km'] = cumulative_distance
        church['cumulative_time_min'] = cumulative_time
        cumulative_distance += church.get('distance_to_next_km', 0)
        cumulative_time += church.get('drive_time_to_next_min', 0)

    # Save verified route
    print("\n4. Saving verified route...")
    verified_df = pd.DataFrame(detailed_route)
    output_csv = f"{output_dir}/{circle_name}_verified.csv"
    verified_df.to_csv(output_csv, index=False)
    print(f"   ✓ Saved to {output_csv}")

    # Return stats
    return {
        'circle': circle_name,
        'churches': len(churches),
        'original_distance_km': original_total,
        'optimized_distance_km': optimized_total,
        'improvement_km': original_total - optimized_total,
        'improvement_pct': (1 - optimized_total/original_total) * 100 if original_total > 0 else 0,
        'total_drive_time_min': cumulative_time,
        'total_drive_time_hours': cumulative_time / 60
    }

def main():
    print("=" * 80)
    print("CHURCH ROUTE VERIFICATION WITH HERE ROUTING API")
    print("=" * 80)

    input_dir = 'data/churches'
    output_dir = 'data/churches/verified'
    os.makedirs(output_dir, exist_ok=True)

    # Get all circle route files
    circle_files = [
        ('Circle1_Northwest_Bergen', f'{input_dir}/Circle1_Northwest_Bergen_route.csv'),
        ('Circle2_North_Woodbridge', f'{input_dir}/Circle2_North_Woodbridge_route.csv'),
        ('Circle3_Northeast_Palisades', f'{input_dir}/Circle3_Northeast_Palisades_route.csv'),
        ('Circle4_East_Edgewater', f'{input_dir}/Circle4_East_Edgewater_route.csv'),
        ('Circle5_South_Union_City', f'{input_dir}/Circle5_South_Union_City_route.csv'),
        ('Circle6_Southwest_Newark', f'{input_dir}/Circle6_Southwest_Newark_route.csv'),
        ('Circle7_Southeast_Secaucus', f'{input_dir}/Circle7_Southeast_Secaucus_route.csv'),
    ]

    all_stats = []

    # Process each circle
    for circle_name, csv_file in circle_files:
        if os.path.exists(csv_file):
            stats = verify_circle_route(circle_name, csv_file, output_dir)
            if stats:
                all_stats.append(stats)
        else:
            print(f"\nWarning: {csv_file} not found, skipping")

    # Create summary report
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)

    report_lines = []
    report_lines.append("# Church Route Verification Report\n")
    report_lines.append("Routes verified using HERE Routing API with actual road distances\n\n")
    report_lines.append("## Summary by Circle\n\n")
    report_lines.append("| Circle | Churches | Original (km) | Optimized (km) | Improvement | Drive Time |\n")
    report_lines.append("|--------|----------|---------------|----------------|-------------|------------|\n")

    for stats in all_stats:
        report_lines.append(
            f"| {stats['circle'].replace('_', ' ')} | {stats['churches']} | "
            f"{stats['original_distance_km']:.2f} | {stats['optimized_distance_km']:.2f} | "
            f"{stats['improvement_pct']:.1f}% | {stats['total_drive_time_hours']:.1f}h |\n"
        )

        print(f"\n{stats['circle']}:")
        print(f"  Churches: {stats['churches']}")
        print(f"  Optimized distance: {stats['optimized_distance_km']:.2f} km ({stats['optimized_distance_km']*0.621371:.2f} miles)")
        print(f"  Total drive time: {stats['total_drive_time_hours']:.1f} hours")
        print(f"  Improvement: {stats['improvement_pct']:.1f}%")

    # Calculate totals
    total_churches = sum(s['churches'] for s in all_stats)
    total_distance = sum(s['optimized_distance_km'] for s in all_stats)
    total_time = sum(s['total_drive_time_min'] for s in all_stats)

    report_lines.append(f"\n## Totals\n\n")
    report_lines.append(f"- **Total Churches:** {total_churches}\n")
    report_lines.append(f"- **Total Distance:** {total_distance:.2f} km ({total_distance*0.621371:.2f} miles)\n")
    report_lines.append(f"- **Total Drive Time:** {total_time/60:.1f} hours\n")
    report_lines.append(f"- **Average Improvement:** {np.mean([s['improvement_pct'] for s in all_stats]):.1f}%\n")

    report_lines.append(f"\n## Notes\n\n")
    report_lines.append(f"- Routes optimized using actual driving distances from HERE Routing API\n")
    report_lines.append(f"- Distance matrix cached to minimize API calls\n")
    report_lines.append(f"- Drive times are estimates and may vary with traffic\n")
    report_lines.append(f"- Each verified route includes:\n")
    report_lines.append(f"  - Optimized visit sequence\n")
    report_lines.append(f"  - Distance and time to next stop\n")
    report_lines.append(f"  - Cumulative distance and time\n")

    # Save report
    report_file = f"{output_dir}/verification_report.md"
    with open(report_file, 'w') as f:
        f.writelines(report_lines)

    print(f"\n✓ Verification report saved to {report_file}")
    print(f"\nAll verified routes saved to: {output_dir}/")

if __name__ == '__main__':
    main()
