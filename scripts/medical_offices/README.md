# Queens & Brooklyn Doctor's Office Scraper

Find all doctor's offices and medical practices in Queens and Brooklyn using Serper.dev API (no Google Places API required).

## Features

- ✅ **Serper.dev API Only**: No Google Places API needed - uses Serper for search and geocoding
- 🏥 **Comprehensive Coverage**: Searches 50 neighborhoods across Queens & Brooklyn
- 📞 **Full Contact Info**: Extracts phone, email, address, website, and contact names
- 🗺️ **KMZ Export**: Creates Google My Maps visualization
- 💾 **Progress Tracking**: Resumable scraping - stop and restart anytime
- 🤖 **AI Enrichment**: Uses OpenAI to extract structured contact data

## Prerequisites

```bash
# Required API keys
export SERPER_API_KEY="your_serper_api_key"
export OPENAI_API_KEY="your_openai_api_key"  # Optional but recommended

# Install dependencies
pip install pandas openai simplekml requests
```

## Usage

### Step 1: Scrape Doctor's Offices

```bash
python3 scripts/medical_offices/01_scrape_doctors_queens_brooklyn.py
```

This will:
1. Search **50 neighborhoods** in Queens & Brooklyn
2. Use **7 different search terms** per neighborhood (350 total searches)
3. Extract doctor offices with contact information
4. Enrich contacts using Serper + OpenAI
5. Save results to CSV with progress tracking

**Output**: `data/medical_offices/queens_brooklyn_doctors.csv`

### Step 2: Export to KMZ for Google Maps

```bash
python3 scripts/medical_offices/02_export_to_kmz.py
```

This will:
1. Load the CSV from Step 1
2. Geocode any missing coordinates using Serper
3. Create KMZ file with map markers
4. Separate folders for Queens and Brooklyn

**Output**: `data/medical_offices/queens_brooklyn_doctors.kmz`

## Search Strategy

The scraper uses a comprehensive neighborhood-based approach:

### Queens Areas (20 neighborhoods)
- Astoria, Long Island City, Flushing, Jamaica, Forest Hills
- Rego Park, Elmhurst, Jackson Heights, Corona, Woodside
- Sunnyside, Bayside, Whitestone, College Point, Fresh Meadows
- Kew Gardens, Richmond Hill, Ozone Park, Howard Beach, Rockaway

### Brooklyn Areas (30 neighborhoods)
- Williamsburg, Greenpoint, Bushwick, Bedford-Stuyvesant, Crown Heights
- Park Slope, Prospect Heights, Carroll Gardens, Cobble Hill, Brooklyn Heights
- Downtown Brooklyn, Fort Greene, Clinton Hill, Boerum Hill, Red Hook
- Sunset Park, Bay Ridge, Bensonhurst, Dyker Heights, Borough Park
- Flatbush, Midwood, Sheepshead Bay, Brighton Beach, Coney Island
- Canarsie, East New York, Brownsville, East Flatbush, Flatlands

### Search Terms (7 variations)
1. "doctors office"
2. "medical clinic"
3. "physician office"
4. "primary care doctor"
5. "family medicine"
6. "internal medicine"
7. "medical practice"

**Total Searches**: 50 neighborhoods × 7 terms = 350 searches

## Contact Enrichment

The scraper enriches doctor office contacts using multiple strategies:

1. **Serper Places Results**
   - Direct phone numbers and addresses from Google local pack
   - Coordinates for mapping
   - Ratings and review counts

2. **Serper Organic Results**
   - Extracts phone numbers from search snippets
   - Finds addresses in result descriptions
   - Collects practice websites

3. **OpenAI Extraction** (if API key provided)
   - Structured extraction of email addresses
   - Contact person names (office managers, administrators)
   - Validates and formats phone numbers

## Output Schema

### CSV Fields

| Field | Description | Example |
|-------|-------------|---------|
| `name` | Doctor's office or practice name | "NYU Langone Astoria Medical Associates" |
| `address` | Full street address | "23-18 31st Street, Astoria, NY 11105" |
| `phone` | Formatted phone number | "(718) 626-6220" |
| `email` | Contact email | "info@nyulangone.org" |
| `website` | Practice website | "https://nyulangone.org/..." |
| `contact_name` | Office manager or contact person | "Jane Smith, Office Manager" |
| `rating` | Google rating | "4.5" |
| `reviews` | Number of reviews | "234" |
| `latitude` | GPS latitude | "40.7614" |
| `longitude` | GPS longitude | "-73.9242" |
| `source` | Data source | "serper_places" or "serper_organic" |
| `search_query` | Original search term | "doctors office" |
| `location` | Search location | "Astoria, Queens, NY" |
| `found_date` | When discovered | "2025-12-04T20:15:30" |

## Progress Tracking

The scraper saves progress to `data/medical_offices/scraping_progress.json`:

```json
{
  "completed_searches": [
    "doctors office|Astoria, Queens, NY",
    "medical clinic|Astoria, Queens, NY"
  ],
  "found_doctors": {
    "nyu langone astoria medical associates|23-18 31st street": { ... }
  },
  "last_updated": "2025-12-04T20:15:30"
}
```

**To resume**: Simply run the script again. It will skip completed searches.

## Performance

- **API Calls**: ~350 Serper searches (1 per neighborhood/term combo)
- **Rate Limiting**: 1 second delay between searches
- **Estimated Time**: ~6-8 minutes for complete run
- **Cost**: ~$1.75 (Serper charges $5/1000 searches)

## Troubleshooting

### No results found
- Check that SERPER_API_KEY is set correctly
- Verify API key has remaining credits
- Try running the test script: `python3 scripts/medical_offices/test_simple.py`

### Missing coordinates in KMZ
- The geocoding step requires Serper API calls
- Script will attempt to geocode missing addresses automatically
- Some offices without addresses will be skipped

### Enrichment not finding emails
- Ensure OPENAI_API_KEY is set
- Some medical practices don't publish public emails
- Check the CSV - phone numbers should still be present

## Example Usage

```bash
# Set API keys
export SERPER_API_KEY="your_key_here"
export OPENAI_API_KEY="your_key_here"

# Run complete workflow
python3 scripts/medical_offices/01_scrape_doctors_queens_brooklyn.py
python3 scripts/medical_offices/02_export_to_kmz.py

# Import into Google My Maps
# 1. Go to https://mymaps.google.com
# 2. Create a New Map
# 3. Click "Import"
# 4. Upload data/medical_offices/queens_brooklyn_doctors.kmz
```

## Notes

- The scraper filters results to only include medical-related businesses
- Duplicate offices (same name + address) are automatically removed
- Progress is saved every 10 searches to prevent data loss
- The KMZ file separates Queens and Brooklyn into different folders for easy navigation

## Files Generated

```
data/medical_offices/
├── queens_brooklyn_doctors.csv        # Main dataset
├── queens_brooklyn_doctors.kmz        # Google Maps file
├── queens_brooklyn_doctors.kml        # Uncompressed KML
└── scraping_progress.json             # Resume data
```
