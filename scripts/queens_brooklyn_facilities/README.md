# Queens & Brooklyn Community Facilities Scraper

This directory contains scripts for scraping and enriching community facilities data in Queens and Brooklyn, NY.

## Facility Types Covered

1. **Senior Centers** - Senior citizen centers and elderly care facilities
2. **Libraries** - Public libraries and library branches
3. **City Halls** - Borough halls, community boards, and municipal buildings
4. **Community Centers** - Recreation centers, civic centers, youth centers
5. **Colleges/Universities** - Higher education institutions, community colleges, technical colleges
6. **Golf Clubs** - Golf courses and country clubs
7. **Yacht Clubs** - Yacht clubs, boat clubs, sailing clubs, marina clubs
8. **Social Clubs** - Private social clubs and members clubs

## Coverage Areas

### Queens Neighborhoods
- Astoria, Long Island City, Flushing, Jamaica, Forest Hills
- Rego Park, Elmhurst, Corona, Jackson Heights, Woodside
- Sunnyside, Bayside, Whitestone, Fresh Meadows
- Kew Gardens, Richmond Hill, Ozone Park, Howard Beach, Rockaway
- And more...

### Brooklyn Neighborhoods
- Williamsburg, Greenpoint, Bushwick, Bedford-Stuyvesant
- Crown Heights, Park Slope, Prospect Heights, Downtown Brooklyn
- Brooklyn Heights, DUMBO, Fort Greene, Clinton Hill
- Sunset Park, Bay Ridge, Bensonhurst, Borough Park
- Flatbush, East Flatbush, Canarsie, Sheepshead Bay
- Brighton Beach, Coney Island
- And more...

## Scripts

### 1. `01_scrape_facilities.py`
Scrapes facility data from Serper Google Maps and Organic Search APIs.

**Usage:**
```bash
export SERPER_API_KEY="your_api_key"
python3 scripts/queens_brooklyn_facilities/01_scrape_facilities.py
```

**Output:** `data/queens_brooklyn_facilities/queens_brooklyn_facilities.csv`

**Features:**
- Searches across 40+ neighborhoods in Queens and Brooklyn
- 8 facility types with multiple search terms each
- Automatic deduplication
- Progress tracking and resume capability
- Rate limiting to respect API limits

### 2. `03_enrich_with_addresses.py`
Enriches facilities with complete address information using HERE Geocoding & Search API.

**Usage:**
```bash
export HERE_API_KEY="your_api_key"
python3 scripts/queens_brooklyn_facilities/03_enrich_with_addresses.py
```

**Output:** `data/queens_brooklyn_facilities/queens_brooklyn_facilities_with_addresses.csv`

**Features:**
- Validates and enriches missing addresses
- Updates coordinates and phone numbers using HERE API
- Progress saving every 50 records
- Rate limiting

### 3. `05_refine_invalid_addresses.py`
Refines invalid addresses (long snippets or non-street addresses) using Serper Google Maps API.

**Usage:**
```bash
export SERPER_API_KEY="your_api_key"
python3 scripts/queens_brooklyn_facilities/05_refine_invalid_addresses.py
```

**Output:** `data/queens_brooklyn_facilities/queens_brooklyn_facilities_with_addresses_refined.csv`

**Features:**
- Identifies invalid addresses (too long, no street number)
- Re-searches Google Maps for correct addresses
- Updates coordinates and contact information
- Progress saving every 50 records
- Rate limiting

### 4. `06_export_to_kmz.py`
Exports enriched data to KMZ format for Google My Maps visualization.

**Usage:**
```bash
export SERPER_API_KEY="your_api_key"  # Optional, for geocoding missing coordinates
python3 scripts/queens_brooklyn_facilities/06_export_to_kmz.py
```

**Output:** `data/queens_brooklyn_facilities/queens_brooklyn_facilities.kmz`

**Features:**
- Color-coded markers by facility type
- Organized into folders by category
- Rich descriptions with contact info, hours, ratings
- Ready to import into Google My Maps

## Workflow

1. **Scrape facilities:**
   ```bash
   python3 scripts/queens_brooklyn_facilities/01_scrape_facilities.py
   ```

2. **Enrich with addresses:**
   ```bash
   python3 scripts/queens_brooklyn_facilities/03_enrich_with_addresses.py
   ```

3. **Refine invalid addresses:**
   ```bash
   python3 scripts/queens_brooklyn_facilities/05_refine_invalid_addresses.py
   ```

4. **Export to KMZ:**
   ```bash
   python3 scripts/queens_brooklyn_facilities/06_export_to_kmz.py
   ```

5. **Import to Google My Maps:**
   - Go to https://mymaps.google.com
   - Create a new map
   - Click "Import"
   - Upload the `.kmz` file

## Data Fields

Each facility record includes:
- `name` - Facility name
- `facility_type` - Type of facility
- `address` - Street address
- `phone` - Phone number
- `email` - Email address (if available)
- `website` - Website URL
- `business_hours` - Operating hours
- `rating` - Google rating
- `reviews` - Number of reviews
- `latitude` - Latitude coordinate
- `longitude` - Longitude coordinate
- `source` - Data source (serper_maps or serper_organic)
- `search_query` - Search query used
- `location` - Search location
- `found_date` - Date scraped

## Color Legend (KMZ)

- 🟣 **Purple** - Senior Centers
- 🟢 **Green** - Libraries
- 🔴 **Red** - City/Borough Halls
- 🟡 **Yellow** - Community Centers
- 🟠 **Orange** - Colleges/Universities
- 🩷 **Pink** - Golf Clubs
- 🔵 **Light Blue** - Yacht Clubs
- ⚪ **White** - Social Clubs

## Requirements

- Python 3.7+
- pandas
- requests
- simplekml
- SERPER_API_KEY environment variable (for initial scraping)
- HERE_API_KEY environment variable (for address enrichment)

## Notes

- The scraper includes automatic rate limiting to avoid API throttling
- Progress is saved automatically to allow resuming interrupted runs
- Deduplication is performed based on facility name and location
- All scripts include progress tracking and detailed console output
