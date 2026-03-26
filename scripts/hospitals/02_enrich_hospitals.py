#!/usr/bin/env python3
"""
Enrich hospital records with lat/lon, phone, website, and full address
using the Google Places API.

Input:  data/hospitals/hospitals_raw.csv
Output: data/hospitals/hospitals_enriched.csv
"""

import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

import pandas as pd
import googlemaps

DATA_DIR = PROJECT_ROOT / "data" / "hospitals"
INPUT_CSV  = DATA_DIR / "hospitals_raw.csv"
OUTPUT_CSV = DATA_DIR / "hospitals_enriched.csv"

GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
RATE_DELAY_S = 0.2  # seconds between API calls


def enrich_record(client: googlemaps.Client, name: str, address: str) -> dict:
    """
    Call Google Places API to get full details for one hospital.
    Returns a dict with enrichment fields (all may be empty on failure).
    """
    empty = {
        "latitude": None, "longitude": None,
        "formatted_address": None, "phone": None,
        "website": None, "rating": None, "reviews": None,
        "place_id": None,
    }

    if not name:
        return empty

    query = f"{name} hospital {address}" if address else f"{name} hospital"

    try:
        # find_place is cheaper than a full text search
        resp = client.find_place(
            input=query,
            input_type="textquery",
            fields=["place_id", "name", "geometry", "formatted_address",
                    "rating", "user_ratings_total"],
        )
        candidates = resp.get("candidates", [])
        if not candidates:
            return empty

        place_id = candidates[0].get("place_id")
        if not place_id:
            return empty

        time.sleep(RATE_DELAY_S)

        # Full details
        details = client.place(
            place_id=place_id,
            fields=["name", "formatted_address", "geometry", "formatted_phone_number",
                    "website", "rating", "user_ratings_total", "place_id"],
        ).get("result", {})

        loc = details.get("geometry", {}).get("location", {})
        return {
            "latitude":          loc.get("lat"),
            "longitude":         loc.get("lng"),
            "formatted_address": details.get("formatted_address"),
            "phone":             details.get("formatted_phone_number"),
            "website":           details.get("website"),
            "rating":            details.get("rating"),
            "reviews":           details.get("user_ratings_total"),
            "place_id":          details.get("place_id"),
        }

    except Exception as e:
        print(f"    WARNING: Places API error for '{name}': {e}")
        return empty


def main():
    if not GOOGLE_PLACES_API_KEY:
        print("ERROR: GOOGLE_PLACES_API_KEY environment variable not set.")
        sys.exit(1)

    if not INPUT_CSV.exists():
        print(f"ERROR: {INPUT_CSV} not found. Run 01_scrape_hospitals.py first.")
        sys.exit(1)

    df = pd.read_csv(INPUT_CSV)
    print("=" * 70)
    print("HOSPITAL ENRICHMENT — Google Places API")
    print("=" * 70)
    print(f"Loaded {len(df)} hospitals from {INPUT_CSV}")
    print()

    # Resume support: load existing output and skip already-enriched rows
    if OUTPUT_CSV.exists():
        done_df = pd.read_csv(OUTPUT_CSV)
        done_names = set(done_df["name"].dropna())
        print(f"Resuming — {len(done_names)} already enriched, skipping them.")
    else:
        done_df = pd.DataFrame()
        done_names = set()

    client = googlemaps.Client(key=GOOGLE_PLACES_API_KEY, timeout=30)

    enriched_rows = []
    total = len(df)

    for idx, row in df.iterrows():
        name = str(row.get("name", "")).strip()
        address = str(row.get("address", "")).strip()

        if name in done_names:
            continue

        print(f"[{idx + 1}/{total}] {name[:60]}")

        enrichment = enrich_record(client, name, address)

        merged = {
            "name":    name,
            "address": address,
            "rating_raw":  row.get("rating", ""),
            "reviews_raw": row.get("reviews", ""),
            "place_url":   row.get("place_url", ""),
            **enrichment,
        }
        enriched_rows.append(merged)

        time.sleep(RATE_DELAY_S)

        # Save incrementally every 20 rows
        if (len(enriched_rows) % 20) == 0:
            new_df = pd.DataFrame(enriched_rows)
            combined = pd.concat([done_df, new_df], ignore_index=True) if not done_df.empty else new_df
            combined.to_csv(OUTPUT_CSV, index=False)
            print(f"  (checkpoint saved — {len(combined)} total rows)")

    # Final save
    new_df = pd.DataFrame(enriched_rows)
    if not new_df.empty:
        combined = pd.concat([done_df, new_df], ignore_index=True) if not done_df.empty else new_df
        combined.to_csv(OUTPUT_CSV, index=False)
    elif done_df.empty:
        df.to_csv(OUTPUT_CSV, index=False)  # nothing enriched, write raw
        combined = df
    else:
        combined = done_df

    total_enriched = combined["latitude"].notna().sum()
    print()
    print(f"Saved {len(combined)} records to {OUTPUT_CSV}")
    print(f"  With coordinates: {total_enriched} / {len(combined)}")
    print()
    print("=" * 70)
    print("DONE. Next: run 03_export_to_kmz.py")
    print("=" * 70)


if __name__ == "__main__":
    main()
