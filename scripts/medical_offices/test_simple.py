#!/usr/bin/env python3
"""Simple test of Serper API for doctor search"""

import os
import requests
import json

SERPER_API_KEY = os.getenv("SERPER_API_KEY")

def test_serper_search():
    """Test a single Serper search"""
    print("Testing Serper API with doctor search...")
    print()

    url = "https://google.serper.dev/search"

    payload = {
        "q": "doctors office in Astoria, Queens, NY",
        "location": "New York, NY",
        "gl": "us",
        "hl": "en"
    }

    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        print(f"✓ API call successful!")
        print()

        # Show places results
        if "places" in data:
            print(f"Found {len(data['places'])} places:")
            for i, place in enumerate(data['places'][:3], 1):
                print(f"\n{i}. {place.get('title', 'N/A')}")
                print(f"   Address: {place.get('address', 'N/A')}")
                print(f"   Phone: {place.get('phoneNumber', 'N/A')}")
                print(f"   Website: {place.get('website', 'N/A')}")
                print(f"   Rating: {place.get('rating', 'N/A')} ({place.get('ratingCount', 0)} reviews)")
                print(f"   Coords: {place.get('latitude', 'N/A')}, {place.get('longitude', 'N/A')}")

        # Show organic results
        if "organic" in data:
            print(f"\nFound {len(data['organic'])} organic results (showing first 3):")
            for i, result in enumerate(data['organic'][:3], 1):
                print(f"\n{i}. {result.get('title', 'N/A')}")
                print(f"   Link: {result.get('link', 'N/A')}")
                print(f"   Snippet: {result.get('snippet', 'N/A')[:100]}...")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    test_serper_search()