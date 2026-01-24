#!/usr/bin/env python3
"""
Cleanup script to fix misclassified facility types in brooklyn_facilities_validated.csv

This script validates and corrects facility_type assignments based on the actual
business names, since the original scraper assigned types based on search queries
rather than validating the actual results.
"""

import csv
import re
from pathlib import Path
from typing import Dict, List, Tuple

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "queens_brooklyn_facilities"
INPUT_CSV = DATA_DIR / "brooklyn_facilities_validated.csv"
OUTPUT_CSV = DATA_DIR / "brooklyn_facilities_cleaned.csv"
REMOVED_CSV = DATA_DIR / "brooklyn_facilities_removed.csv"

# Validation rules: (positive_keywords, negative_keywords)
# If name contains negative keywords, it's likely misclassified
# If name contains positive keywords, it confirms the type

FACILITY_RULES = {
    "senior_center": {
        "positive": [
            "senior center", "senior citizen", "older adult", "elderly center",
            "aging", "senior services", "senior club", "seniors center",
            "senior residence", "senior housing", "retirement"
        ],
        "negative": [
            "urgent care", "hospital", "nursing home", "nursing and rehabilitation",
            "rehab center", "rehabilitation center", "home care", "homecare",
            "pharmacy", "clinic", "medical center", "health center", "healthcare",
            "doctor", "physician", "pediatric", "dental", "optometry",
            "physical therapy", "chiropract", "veterinar", "animal",
            "preschool", "daycare", "child care", "childcare",
            "insurance", "medicare agent", "real estate", "realty",
            "restaurant", "cafe", "bar", "grill", "pizza", "deli",
            "gym", "fitness", "crossfit", "yoga studio",
            "hotel", "motel", "inn ", "salon", "spa ", "barbershop",
            "laundry", "cleaners", "storage", "moving",
            "auto ", "car wash", "tire", "mechanic",
            "law firm", "attorney", "lawyer", "accountant", "tax service",
            "bank ", "credit union", "atm",
            "church", "temple", "mosque", "synagogue",
            "school", "academy", "college", "university",
            "police", "fire department", "post office"
        ],
        "reclassify_to": None  # Remove if misclassified
    },
    "college": {
        "positive": [
            "college", "university", "cuny", "suny", "community college",
            "polytechnic", "institute of technology"
        ],
        "negative": [
            "high school", "middle school", "elementary", "junior high",
            "prep school", "preparatory", "preschool", "daycare",
            "k-12", "k-8", "grade school", "primary school"
        ],
        "reclassify_to": None  # Remove high schools from college list
    },
    "community_center": {
        "positive": [
            "community center", "recreation center", "civic center",
            "youth center", "ymca", "ywca", "boys club", "girls club",
            "community house", "neighborhood center", "cultural center",
            "jcc", "jewish community center"
        ],
        "negative": [
            "church", "temple", "mosque", "synagogue", "cathedral",
            "school", "academy", "preschool", "daycare",
            "hospital", "clinic", "medical", "health center",
            "police", "fire station", "post office"
        ],
        "reclassify_to": None
    },
    "city_hall": {
        "positive": [
            "city hall", "borough hall", "municipal building", "community board",
            "civic center", "town hall", "government center"
        ],
        "negative": [
            "police", "precinct", "fire department", "firehouse",
            "post office", "dmv", "court", "prison", "jail",
            "school", "library", "hospital"
        ],
        "reclassify_to": None
    },
    "library": {
        "positive": [
            "library", "public library", "branch library"
        ],
        "negative": [
            "bookstore", "book store", "books-a-million", "barnes",
            "school", "university library"  # Keep university libraries but flag
        ],
        "reclassify_to": None
    },
    "golf_club": {
        "positive": [
            "golf", "country club"
        ],
        "negative": [
            "mini golf", "miniature golf", "putt putt",
            "driving range only", "simulator"
        ],
        "reclassify_to": None
    },
    "yacht_club": {
        "positive": [
            "yacht club", "boat club", "sailing club", "marina",
            "yacht", "boating"
        ],
        "negative": [
            "restaurant", "seafood", "fish market",
            "kayak rental", "paddle board"
        ],
        "reclassify_to": None
    },
    "social_club": {
        "positive": [
            "social club", "private club", "members club", "fraternal",
            "lodge", "elks", "moose", "vfw", "american legion"
        ],
        "negative": [
            "nightclub", "night club", "strip club", "gentleman",
            "bar ", "lounge", "tavern", "pub "
        ],
        "reclassify_to": None
    }
}

# Cross-classification rules: detect what type something actually is
DETECTION_RULES = {
    "senior_center": [
        "senior center", "senior citizen", "older adult center", "elderly center",
        "aging services", "senior services"
    ],
    "library": [
        "library", "public library"
    ],
    "college": [
        "college", "university", " cuny", " suny"
    ],
    "community_center": [
        "community center", "recreation center", "ymca", "ywca", "jcc"
    ],
    "city_hall": [
        "city hall", "borough hall", "community board", "municipal"
    ],
    "police_station": [
        "police", "precinct", "nypd"
    ],
    "fire_station": [
        "fire department", "firehouse", "fdny"
    ],
    "hospital": [
        "hospital", "medical center", "nursing home", "rehabilitation center"
    ],
    "school": [
        "high school", "middle school", "elementary school", "academy", "prep school"
    ],
    "church": [
        "church", "cathedral", "temple", "mosque", "synagogue", "congregation"
    ]
}


def normalize_name(name: str) -> str:
    """Normalize name for comparison"""
    return name.lower().strip()


def contains_keyword(text: str, keywords: List[str]) -> bool:
    """Check if text contains any of the keywords"""
    text_lower = normalize_name(text)
    for keyword in keywords:
        if keyword.lower() in text_lower:
            return True
    return False


def detect_actual_type(name: str) -> str:
    """Try to detect the actual facility type based on name"""
    name_lower = normalize_name(name)

    for facility_type, keywords in DETECTION_RULES.items():
        for keyword in keywords:
            if keyword.lower() in name_lower:
                return facility_type

    return "unknown"


def validate_facility(row: Dict) -> Tuple[bool, str, str]:
    """
    Validate a facility's type assignment.

    Returns:
        (is_valid, new_type, reason)
        - is_valid: True if the facility should be kept
        - new_type: The corrected facility type (or original if valid)
        - reason: Explanation of the decision
    """
    name = row.get("name", "")
    current_type = row.get("facility_type", "")

    if not name or not current_type:
        return False, current_type, "Missing name or type"

    rules = FACILITY_RULES.get(current_type)
    if not rules:
        return True, current_type, "No rules defined for this type"

    # Check for negative indicators (misclassification)
    if contains_keyword(name, rules["negative"]):
        detected_type = detect_actual_type(name)

        # If we can reclassify to a valid type in our dataset, do so
        if detected_type in FACILITY_RULES:
            return True, detected_type, f"Reclassified from {current_type} to {detected_type}"
        else:
            return False, current_type, f"Removed: detected as {detected_type}, not {current_type}"

    # Check for positive indicators (confirms classification)
    if contains_keyword(name, rules["positive"]):
        return True, current_type, "Confirmed by positive keywords"

    # No strong indicators either way - keep but flag
    return True, current_type, "No strong indicators, kept as-is"


def cleanup_facilities():
    """Main cleanup function"""
    print("=" * 80)
    print("CLEANING UP FACILITY TYPE MISCLASSIFICATIONS")
    print("=" * 80)
    print()

    # Read input file
    with open(INPUT_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    print(f"Read {len(rows)} rows from {INPUT_CSV}")
    print()

    # Process each row
    kept_rows = []
    removed_rows = []
    reclassified_count = 0

    stats = {
        "kept_original": 0,
        "reclassified": 0,
        "removed": 0
    }

    type_changes = {}
    removal_reasons = {}

    for row in rows:
        is_valid, new_type, reason = validate_facility(row)
        original_type = row.get("facility_type", "")

        if is_valid:
            if new_type != original_type:
                # Reclassified
                change_key = f"{original_type} -> {new_type}"
                type_changes[change_key] = type_changes.get(change_key, 0) + 1
                row["facility_type"] = new_type
                stats["reclassified"] += 1
            else:
                stats["kept_original"] += 1
            kept_rows.append(row)
        else:
            # Removed
            row["removal_reason"] = reason
            removed_rows.append(row)
            stats["removed"] += 1
            removal_reasons[reason] = removal_reasons.get(reason, 0) + 1

    # Write cleaned output
    with open(OUTPUT_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(kept_rows)

    print(f"Wrote {len(kept_rows)} cleaned rows to {OUTPUT_CSV}")

    # Write removed entries for review
    removed_fieldnames = fieldnames + ["removal_reason"]
    with open(REMOVED_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=removed_fieldnames)
        writer.writeheader()
        writer.writerows(removed_rows)

    print(f"Wrote {len(removed_rows)} removed rows to {REMOVED_CSV}")
    print()

    # Print statistics
    print("=" * 80)
    print("STATISTICS")
    print("=" * 80)
    print()
    print(f"Total input rows:     {len(rows)}")
    print(f"Kept (original type): {stats['kept_original']}")
    print(f"Reclassified:         {stats['reclassified']}")
    print(f"Removed:              {stats['removed']}")
    print()

    if type_changes:
        print("TYPE RECLASSIFICATIONS:")
        for change, count in sorted(type_changes.items(), key=lambda x: -x[1]):
            print(f"  {change}: {count}")
        print()

    if removal_reasons:
        print("REMOVAL REASONS:")
        for reason, count in sorted(removal_reasons.items(), key=lambda x: -x[1]):
            print(f"  {reason}: {count}")
        print()

    # Print final type distribution
    print("FINAL TYPE DISTRIBUTION:")
    type_counts = {}
    for row in kept_rows:
        ft = row.get("facility_type", "unknown")
        type_counts[ft] = type_counts.get(ft, 0) + 1

    for ft, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {ft}: {count}")

    print()
    print("=" * 80)
    print("CLEANUP COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    cleanup_facilities()
