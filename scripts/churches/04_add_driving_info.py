#!/usr/bin/env python3
"""
Add real driving distances and times to existing optimized routes
This is faster than full re-optimization since we only need N-1 API calls per circle
"""

import pandas as pd
import requests
import time
import json
import os
from typing import Dict, Optional

# HERE API key
HERE_API_KEY = os.environ.get('HERE_API_KEY', '0zt1IVbSQt3cPrM8_jaLXyFoq9TALX4OPXWfIsxGg1s')

def get_driving_route(origin_lat: float, origin_lng: float,
                      dest_lat: float, dest_lng: float) -> Optional[Dict]:
    """
    Get driving route between two points using HERE Routing API
    """
    try:
        url = "https://router.hereapi.com/v8/routes"

        params = {
            'apiKey': HERE_API_KEY,
            'transportMode': 'car',
            'origin': f'{origin_lat},{origin_lng}',
            'destination': f'{dest_lat},{dest_lng}',
            'return': 'summary'
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
                'distance_miles': (section['summary']['length'] / 1000) * 0.621371,
                'duration_seconds': section['summary']['duration'],
                'duration_minutes': section['summary']['duration'] / 60,
                'duration_hours': section['summary']['duration'] / 3600
            }
        return None

    except Exception as e:
        print(f"    Error: {e}")
        return None

def add_driving_info_to_route(circle_name: str, input_csv: str, output_dir: str):
    """
    Add real driving distances and times to an existing route
    """
    print(f"\n{'='*80}")
    print(f"ADDING DRIVING INFO: {circle_name}")
    print(f"{'='*80}")

    # Read current route
    df = pd.read_csv(input_csv)
    churches = df.to_dict('records')

    print(f"Churches in route: {len(churches)}")

    enhanced_churches = []
    total_distance_km = 0
    total_time_min = 0
    cumulative_distance = 0
    cumulative_time = 0

    for idx, church in enumerate(churches):
        church_enhanced = church.copy()
        church_enhanced['cumulative_distance_km'] = round(cumulative_distance, 2)
        church_enhanced['cumulative_distance_miles'] = round(cumulative_distance * 0.621371, 2)
        church_enhanced['cumulative_time_minutes'] = round(cumulative_time, 1)
        church_enhanced['cumulative_time_hours'] = round(cumulative_time / 60, 2)

        # Get route to next stop
        if idx < len(churches) - 1:
            next_church = churches[idx + 1]

            print(f"  Stop {idx+1} -> {idx+2}: {church['name'][:40]}")

            route_info = get_driving_route(
                church['latitude'], church['longitude'],
                next_church['latitude'], next_church['longitude']
            )

            if route_info:
                church_enhanced['distance_to_next_km'] = round(route_info['distance_km'], 2)
                church_enhanced['distance_to_next_miles'] = round(route_info['distance_miles'], 2)
                church_enhanced['drive_time_to_next_min'] = round(route_info['duration_minutes'], 1)
                church_enhanced['next_stop'] = next_church['name']

                total_distance_km += route_info['distance_km']
                total_time_min += route_info['duration_minutes']
                cumulative_distance += route_info['distance_km']
                cumulative_time += route_info['duration_minutes']
            else:
                # Fallback to straight-line estimate
                from math import radians, sin, cos, sqrt, atan2
                R = 6371
                lat1, lng1 = radians(church['latitude']), radians(church['longitude'])
                lat2, lng2 = radians(next_church['latitude']), radians(next_church['longitude'])
                dlat, dlng = lat2 - lat1, lng2 - lng1
                a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
                distance_km = R * 2 * atan2(sqrt(a), sqrt(1-a))

                church_enhanced['distance_to_next_km'] = round(distance_km, 2)
                church_enhanced['distance_to_next_miles'] = round(distance_km * 0.621371, 2)
                church_enhanced['drive_time_to_next_min'] = round(distance_km * 2, 1)  # Rough estimate: 30 km/h
                church_enhanced['next_stop'] = next_church['name']

                total_distance_km += distance_km
                total_time_min += distance_km * 2
                cumulative_distance += distance_km
                cumulative_time += distance_km * 2

                print(f"    Warning: Using straight-line estimate")

            time.sleep(0.15)  # Rate limiting
        else:
            church_enhanced['distance_to_next_km'] = 0
            church_enhanced['distance_to_next_miles'] = 0
            church_enhanced['drive_time_to_next_min'] = 0
            church_enhanced['next_stop'] = 'End of route'

        enhanced_churches.append(church_enhanced)

    # Save enhanced route
    output_csv = f"{output_dir}/{circle_name}_with_driving_info.csv"
    enhanced_df = pd.DataFrame(enhanced_churches)
    enhanced_df.to_csv(output_csv, index=False)

    print(f"\n  ✓ Route enhanced")
    print(f"  Total distance: {total_distance_km:.2f} km ({total_distance_km*0.621371:.2f} miles)")
    print(f"  Total drive time: {total_time_min:.1f} min ({total_time_min/60:.2f} hours)")
    print(f"  ✓ Saved to {output_csv}")

    return {
        'circle': circle_name,
        'churches': len(churches),
        'total_distance_km': round(total_distance_km, 2),
        'total_distance_miles': round(total_distance_km * 0.621371, 2),
        'total_time_minutes': round(total_time_min, 1),
        'total_time_hours': round(total_time_min / 60, 2),
        'avg_distance_per_stop_km': round(total_distance_km / max(len(churches)-1, 1), 2),
        'avg_time_per_stop_min': round(total_time_min / max(len(churches)-1, 1), 1)
    }

def main():
    print("=" * 80)
    print("ADDING REAL DRIVING INFO TO CHURCH ROUTES")
    print("=" * 80)

    input_dir = 'data/churches'
    output_dir = 'data/churches/enhanced'
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
            stats = add_driving_info_to_route(circle_name, csv_file, output_dir)
            all_stats.append(stats)
        else:
            print(f"\nWarning: {csv_file} not found, skipping")

    # Create summary report
    print("\n" + "=" * 80)
    print("SUMMARY REPORT")
    print("=" * 80)

    report_lines = []
    report_lines.append("# Church Route Driving Information Report\n\n")
    report_lines.append("Routes enhanced with actual driving distances and times from HERE Routing API\n\n")
    report_lines.append("## Summary by Circle\n\n")
    report_lines.append("| Circle | Churches | Distance (km) | Distance (mi) | Drive Time | Avg/Stop |\n")
    report_lines.append("|--------|----------|---------------|---------------|------------|----------|\n")

    for stats in all_stats:
        report_lines.append(
            f"| {stats['circle'].replace('_', ' ')} | {stats['churches']} | "
            f"{stats['total_distance_km']:.1f} | {stats['total_distance_miles']:.1f} | "
            f"{stats['total_time_hours']:.1f}h | {stats['avg_distance_per_stop_km']:.2f}km |\n"
        )

        print(f"\n{stats['circle']}:")
        print(f"  Churches: {stats['churches']}")
        print(f"  Distance: {stats['total_distance_km']:.1f} km ({stats['total_distance_miles']:.1f} miles)")
        print(f"  Drive time: {stats['total_time_hours']:.1f} hours")
        print(f"  Avg per stop: {stats['avg_distance_per_stop_km']:.2f} km, {stats['avg_time_per_stop_min']:.1f} min")

    # Calculate totals
    total_churches = sum(s['churches'] for s in all_stats)
    total_distance_km = sum(s['total_distance_km'] for s in all_stats)
    total_distance_miles = sum(s['total_distance_miles'] for s in all_stats)
    total_time_hours = sum(s['total_time_hours'] for s in all_stats)

    report_lines.append(f"\n## Overall Totals\n\n")
    report_lines.append(f"- **Total Churches:** {total_churches}\n")
    report_lines.append(f"- **Total Driving Distance:** {total_distance_km:.1f} km ({total_distance_miles:.1f} miles)\n")
    report_lines.append(f"- **Total Driving Time:** {total_time_hours:.1f} hours\n")
    report_lines.append(f"- **Average per Circle:** {total_distance_km/len(all_stats):.1f} km, {total_time_hours/len(all_stats):.1f} hours\n")

    report_lines.append(f"\n## Route Details\n\n")
    report_lines.append(f"Each enhanced route CSV includes:\n")
    report_lines.append(f"- **distance_to_next_km/miles:** Actual driving distance to next stop\n")
    report_lines.append(f"- **drive_time_to_next_min:** Estimated driving time to next stop\n")
    report_lines.append(f"- **cumulative_distance_km/miles:** Total distance traveled so far\n")
    report_lines.append(f"- **cumulative_time_minutes/hours:** Total time elapsed so far\n")
    report_lines.append(f"- **next_stop:** Name of the next church on the route\n\n")

    report_lines.append(f"## Usage Tips\n\n")
    report_lines.append(f"1. **Plan your day:** Use cumulative time to estimate when you'll reach each stop\n")
    report_lines.append(f"2. **Add breaks:** Remember to add time for breaks, meals, and actual visits\n")
    report_lines.append(f"3. **Traffic:** Driving times don't account for traffic - add buffer time during rush hours\n")
    report_lines.append(f"4. **Combine routes:** Some circles are close enough to combine in one day\n\n")

    report_lines.append(f"## Files Generated\n\n")
    for circle_name, _ in circle_files:
        report_lines.append(f"- `{circle_name}_with_driving_info.csv`\n")

    # Save report
    report_file = f"{output_dir}/driving_info_report.md"
    with open(report_file, 'w') as f:
        f.writelines(report_lines)

    print(f"\n✓ Report saved to {report_file}")
    print(f"\nAll enhanced routes saved to: {output_dir}/")

if __name__ == '__main__':
    main()
