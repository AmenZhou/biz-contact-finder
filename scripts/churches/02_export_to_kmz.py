#!/usr/bin/env python3
"""
Export church routes to KMZ files for Google Earth/Maps visualization
"""

import pandas as pd
import simplekml
import os
from pathlib import Path

# Color scheme for different circles
CIRCLE_COLORS = {
    'Circle1_Northwest_Bergen': simplekml.Color.red,
    'Circle2_North_Woodbridge': simplekml.Color.blue,
    'Circle3_Northeast_Palisades': simplekml.Color.green,
    'Circle4_East_Edgewater': simplekml.Color.yellow,
    'Circle5_South_Union_City': simplekml.Color.orange,
    'Circle6_Southwest_Newark': simplekml.Color.purple,
    'Circle7_Southeast_Secaucus': simplekml.Color.cyan,
}

def create_kmz_for_circle(circle_name: str, df: pd.DataFrame, output_dir: str):
    """Create a KMZ file for a specific circle with numbered markers and route lines"""

    kml = simplekml.Kml()

    # Create folder for this circle
    folder = kml.newfolder(name=circle_name.replace('_', ' '))

    # Get color for this circle
    color = CIRCLE_COLORS.get(circle_name, simplekml.Color.white)

    # Add route line
    line_coords = []
    for _, row in df.iterrows():
        line_coords.append((row['longitude'], row['latitude']))

    if len(line_coords) > 1:
        linestring = folder.newlinestring(name=f"{circle_name} Route")
        linestring.coords = line_coords
        linestring.style.linestyle.color = color
        linestring.style.linestyle.width = 3

    # Add numbered markers
    for idx, row in df.iterrows():
        point = folder.newpoint(
            name=f"{int(row['sequence'])}. {row['name']}",
            coords=[(row['longitude'], row['latitude'])]
        )

        # Create description
        description = f"""
        <![CDATA[
        <b>Stop #{int(row['sequence'])}</b><br/>
        <b>Name:</b> {row['name']}<br/>
        <b>Type:</b> {row['type']}<br/>
        <b>Address:</b> {row['address']}<br/>
        <b>Phone:</b> {row['phone']}<br/>
        <b>Website:</b> {row['website']}<br/>
        <b>Opens:</b> {row['opens_at']}<br/>
        <b>Reviews:</b> {row['review_count']} ({row['avg_review']} stars)<br/>
        <br/>
        <a href="https://www.google.com/maps/dir/?api=1&destination={row['latitude']},{row['longitude']}" target="_blank">Get Directions</a>
        ]]>
        """
        point.description = description

        # Style the marker
        point.style.iconstyle.color = color
        point.style.iconstyle.scale = 1.2
        point.style.labelstyle.scale = 1.0

    # Save as KMZ
    output_file = f'{output_dir}/{circle_name}.kmz'
    kml.savekmz(output_file)
    print(f"   ✓ Created {output_file}")

    return output_file

def create_combined_kmz(routes_df: pd.DataFrame, output_dir: str):
    """Create a single KMZ with all routes"""

    kml = simplekml.Kml(name="NJ Churches - All Routes")

    # Group by circle
    for circle_name in routes_df['circle'].unique():
        circle_df = routes_df[routes_df['circle'] == circle_name].sort_values('sequence')

        # Create folder for this circle
        folder = kml.newfolder(name=circle_name.replace('_', ' '))

        # Get color
        color = CIRCLE_COLORS.get(circle_name, simplekml.Color.white)

        # Add route line
        line_coords = []
        for _, row in circle_df.iterrows():
            line_coords.append((row['longitude'], row['latitude']))

        if len(line_coords) > 1:
            linestring = folder.newlinestring(name=f"{circle_name} Route")
            linestring.coords = line_coords
            linestring.style.linestyle.color = color
            linestring.style.linestyle.width = 3

        # Add numbered markers
        for idx, row in circle_df.iterrows():
            point = folder.newpoint(
                name=f"{circle_name} #{int(row['sequence'])}: {row['name']}",
                coords=[(row['longitude'], row['latitude'])]
            )

            description = f"""
            <![CDATA[
            <b>Circle:</b> {circle_name.replace('_', ' ')}<br/>
            <b>Stop #{int(row['sequence'])}</b><br/>
            <b>Name:</b> {row['name']}<br/>
            <b>Type:</b> {row['type']}<br/>
            <b>Address:</b> {row['address']}<br/>
            <b>Phone:</b> {row['phone']}<br/>
            <b>Website:</b> {row['website']}<br/>
            <b>Opens:</b> {row['opens_at']}<br/>
            <b>Reviews:</b> {row['review_count']} ({row['avg_review']} stars)<br/>
            <br/>
            <a href="https://www.google.com/maps/dir/?api=1&destination={row['latitude']},{row['longitude']}" target="_blank">Get Directions</a>
            ]]>
            """
            point.description = description

            point.style.iconstyle.color = color
            point.style.iconstyle.scale = 1.0

    # Save combined KMZ
    output_file = f'{output_dir}/all_churches_routes.kmz'
    kml.savekmz(output_file)
    print(f"   ✓ Created combined KMZ: {output_file}")

    return output_file

def create_driving_directions(circle_name: str, df: pd.DataFrame, output_dir: str):
    """Create a text file with turn-by-turn driving directions"""

    output_file = f'{output_dir}/{circle_name}_directions.txt'

    with open(output_file, 'w') as f:
        f.write(f"{'='*80}\n")
        f.write(f"DRIVING ROUTE: {circle_name.replace('_', ' ')}\n")
        f.write(f"{'='*80}\n\n")

        f.write(f"Total Stops: {len(df)}\n")
        f.write(f"Description: {df.iloc[0]['circle_description']}\n\n")

        f.write(f"{'='*80}\n")
        f.write(f"ROUTE SEQUENCE\n")
        f.write(f"{'='*80}\n\n")

        for idx, row in df.iterrows():
            seq = int(row['sequence'])
            f.write(f"STOP {seq}: {row['name']}\n")
            f.write(f"{'-'*60}\n")
            f.write(f"Address:    {row['address']}\n")
            f.write(f"Type:       {row['type']}\n")
            f.write(f"Phone:      {row['phone']}\n")
            f.write(f"Website:    {row['website']}\n")
            f.write(f"Opens:      {row['opens_at']}\n")
            f.write(f"Reviews:    {row['review_count']} reviews ({row['avg_review']} stars)\n")
            f.write(f"GPS:        {row['latitude']}, {row['longitude']}\n")
            f.write(f"Google Map: https://www.google.com/maps/dir/?api=1&destination={row['latitude']},{row['longitude']}\n")
            f.write(f"\n")

        # Add Google Maps multi-stop route URL
        f.write(f"\n{'='*80}\n")
        f.write(f"GOOGLE MAPS ROUTE (Multi-Stop)\n")
        f.write(f"{'='*80}\n\n")

        # Create waypoints for first 9 stops (Google Maps limit)
        waypoints = []
        for idx, row in df.head(10).iterrows():
            waypoints.append(f"{row['latitude']},{row['longitude']}")

        if len(waypoints) > 1:
            origin = waypoints[0]
            destination = waypoints[-1]
            middle_waypoints = '|'.join(waypoints[1:-1]) if len(waypoints) > 2 else ''

            if middle_waypoints:
                maps_url = f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}&waypoints={middle_waypoints}&travelmode=driving"
            else:
                maps_url = f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}&travelmode=driving"

            f.write(f"First 10 stops:\n{maps_url}\n\n")

            if len(df) > 10:
                f.write(f"Note: Google Maps limits to 10 stops per route.\n")
                f.write(f"This route has {len(df)} stops total.\n")
                f.write(f"Break it into multiple segments or use the KMZ file.\n\n")

    print(f"   ✓ Created directions: {output_file}")
    return output_file

def main():
    print("=" * 80)
    print("EXPORTING CHURCH ROUTES TO KMZ")
    print("=" * 80)

    input_dir = 'data/churches'
    output_dir = 'data/churches/exports'
    os.makedirs(output_dir, exist_ok=True)

    # Read all routes
    print("\n1. Reading route data...")
    routes_df = pd.read_csv(f'{input_dir}/nj_churches_routes.csv')
    print(f"   Loaded {len(routes_df)} church stops across {routes_df['circle'].nunique()} circles")

    # Create KMZ for each circle
    print("\n2. Creating individual KMZ files...")
    for circle_name in sorted(routes_df['circle'].unique()):
        circle_df = routes_df[routes_df['circle'] == circle_name].sort_values('sequence')
        print(f"\n   {circle_name}: {len(circle_df)} churches")
        create_kmz_for_circle(circle_name, circle_df, output_dir)

    # Create combined KMZ
    print("\n3. Creating combined KMZ file...")
    create_combined_kmz(routes_df, output_dir)

    # Create driving directions
    print("\n4. Creating driving direction files...")
    for circle_name in sorted(routes_df['circle'].unique()):
        circle_df = routes_df[routes_df['circle'] == circle_name].sort_values('sequence')
        create_driving_directions(circle_name, circle_df, output_dir)

    # Create summary
    print("\n" + "=" * 80)
    print("EXPORT COMPLETE")
    print("=" * 80)
    print(f"\nOutput directory: {output_dir}/\n")

    print("Generated files:")
    print("  KMZ Files (for Google Earth/Maps):")
    for circle_name in sorted(routes_df['circle'].unique()):
        print(f"    - {circle_name}.kmz")
    print(f"    - all_churches_routes.kmz (combined)")

    print("\n  Driving Directions (text files):")
    for circle_name in sorted(routes_df['circle'].unique()):
        print(f"    - {circle_name}_directions.txt")

    print("\n" + "=" * 80)
    print("ROUTE SUMMARY BY CIRCLE")
    print("=" * 80)

    for circle_name in sorted(routes_df['circle'].unique()):
        circle_df = routes_df[routes_df['circle'] == circle_name]
        print(f"\n{circle_name.replace('_', ' ')}:")
        print(f"  Churches: {len(circle_df)}")
        print(f"  Description: {circle_df.iloc[0]['circle_description']}")

    print("\n")

if __name__ == '__main__':
    main()
