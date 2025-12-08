#!/usr/bin/env python3
"""
Test script for doctor scraper - searches only 2 areas
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

# Temporarily modify the main script to only search a few areas
import scripts.medical_offices.scrape_doctors_queens_brooklyn as scraper_module

# Override the areas to search only 2 neighborhoods
scraper_module.QUEENS_AREAS = ["Astoria", "Flushing"]
scraper_module.BROOKLYN_AREAS = ["Williamsburg", "Park Slope"]
scraper_module.SEARCH_TERMS = ["doctors office", "medical clinic"]

# API keys should be set in environment variables before running this script
# Make sure SERPER_API_KEY and OPENAI_API_KEY are set in your environment

# Run main
if __name__ == "__main__":
    # Update config in the module
    scraper_module.SERPER_API_KEY = os.getenv("SERPER_API_KEY")
    scraper_module.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    scraper_module.openai_client = scraper_module.OpenAI(api_key=scraper_module.OPENAI_API_KEY) if scraper_module.OPENAI_API_KEY else None

    print("🧪 TEST MODE: Searching only 4 neighborhoods with 2 search terms each (8 searches total)")
    print()
    scraper_module.main()
