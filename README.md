# Company Contact Info Scraper

Automated tool to extract company contact information (websites, emails, phone numbers, social media) from a CSV list using web scraping and LLM parsing.

## Features

- 🔍 **Google Places API** integration for official websites
- 🌐 **Intelligent web scraping** with BeautifulSoup
- 🤖 **LLM-powered parsing** using GPT-4o-mini for accurate extraction
- ✅ **Data validation** and quality scoring
- 📊 **Progress tracking** with incremental saves
- 🛡️ **Rate limiting** and retry logic
- 📝 **Comprehensive logging**

## Project Structure

```
sy_promotion_merchants_craw/
├── README.md              # This file
├── PLAN.md               # Detailed project plan
├── requirements.txt      # Python dependencies
├── .env.example         # Environment template
├── config/
│   └── settings.py      # Configuration
├── scrapers/
│   ├── google_places.py # Google Places integration
│   ├── website_scraper.py # Web scraping logic
│   └── llm_parser.py    # OpenAI LLM parser
├── utils/
│   ├── validators.py    # Validation utilities
│   └── logger.py        # Logging setup
├── main.py              # Main script
└── data/
    ├── 330Madison.csv   # Input file
    └── output_enriched.csv # Output file
```

## Setup

### Option 1: Docker Setup (Recommended)

The easiest way to run this project is using Docker:

```bash
# 1. Configure API keys
cp .env.example .env
nano .env  # Add your OpenAI and Google Places API keys

# 2. Build and run with Docker Compose
docker-compose up --build

# Or run in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

**Docker Benefits:**
- No Python environment setup needed
- Consistent environment across all machines
- Automatic data persistence via volumes
- Easy to deploy and scale

### Option 2: Local Python Setup

If you prefer to run without Docker:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux

# Install requirements
pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your API keys
nano .env
```

Required API keys:
- **OpenAI API Key** (Required) - Get from [OpenAI Platform](https://platform.openai.com/)
- **Google Places API Key** (Optional but recommended) - Get from [Google Cloud Console](https://console.cloud.google.com/)

### 3. Prepare Input Data

Place your CSV file in the `data/` directory. Expected columns:
- `Name` - Company name
- `Addr` - Address
- `Phone` - Phone number (optional)
- `Type` - Business type (optional)

## Usage

### Using Docker (Recommended)

**Test with Sample Data (5 companies):**
```bash
docker-compose up
```

**Process All Companies:**

1. Edit `main.py` and change line 260:
   ```python
   scraper.run(limit=5)  # Remove limit
   ```
   to:
   ```python
   scraper.run()  # Process all
   ```

2. Rebuild and run:
   ```bash
   docker-compose up --build
   ```

**Advanced Docker Commands:**
```bash
# Run specific Python command
docker-compose run scraper python main.py

# Interactive shell inside container
docker-compose run scraper /bin/bash

# View real-time logs
docker-compose logs -f scraper

# Remove container and volumes
docker-compose down -v
```

### Using Local Python

**Test with Sample Data (5 companies):**
```bash
python main.py
```

**Process All Companies:**

Edit `main.py` and change:
```python
scraper.run(limit=5)  # Remove limit
```
to:
```python
scraper.run()  # Process all
```

Then run:
```bash
python main.py
```

## Output

The script generates:

1. **output_enriched.csv** - Enriched CSV with:
   - Original company info
   - Website URL
   - Primary and secondary emails
   - Verified phone numbers
   - LinkedIn, Twitter, Facebook profiles
   - Contact person details
   - Quality score (0-100)

2. **progress.json** - Incremental progress tracker (allows resuming)

3. **logs/scraper.log** - Detailed execution logs

## Output Schema

```csv
name, type, website, email, email_secondary, phone, phone_secondary,
address, linkedin, twitter, facebook, contact_person, contact_title,
stars, reviews, quality_score, data_source, last_updated
```

## How It Works

```
Input CSV → Google Places API → Website Scraper → LLM Parser → Validation → Output CSV
```

1. **Google Places API**: Gets official website and verified phone
2. **Website Scraper**: Finds and scrapes contact pages
3. **LLM Parser**: Extracts structured contact info from HTML
4. **Validation**: Verifies email/phone formats, calculates quality score
5. **Output**: Saves enriched data to CSV

## Quality Scoring

Each company gets a score (0-100) based on:
- Website found: +30 points
- Email found: +25 points
- Phone verified: +20 points
- LinkedIn found: +15 points
- Contact person found: +10 points

## Cost Estimation

For 68 companies:
- **Google Places API**: $0 (free tier)
- **OpenAI API**: ~$0.50-$1.00 (GPT-4o-mini)
- **Total**: < $2

## Troubleshooting

### Docker Issues

**"docker: command not found"**
- Install Docker Desktop from [docker.com](https://www.docker.com/products/docker-desktop)

**"Cannot connect to Docker daemon"**
- Ensure Docker Desktop is running

**"Port already in use"**
- The scraper doesn't expose ports by default
- If you modified docker-compose.yml, change the port mapping

**Rebuild after code changes:**
```bash
docker-compose up --build
```

### Common Issues

**"No module named 'googlemaps'"**
```bash
# If using local Python:
pip install -r requirements.txt

# If using Docker:
docker-compose up --build
```

**"OpenAI API key is required"**
- Add your API key to `.env` file
- If using Docker, restart: `docker-compose restart`

**"Rate limit exceeded"**
- The script has built-in rate limiting
- Check your API quotas

**"No results found"**
- Some companies may not have public websites
- Check Google Places availability for that business

### Resume After Interruption

The script automatically saves progress to `data/progress.json`. If interrupted, simply run again and it will skip already processed companies.

**With Docker:**
```bash
docker-compose up  # Will resume from where it stopped
```

## Configuration

Edit `config/settings.py` to customize:
- Rate limiting settings
- Retry logic
- LLM model and parameters
- Quality score weights
- Logging level

## Examples

### Successful Output Example

```
Processing: Bluestone Lane 330 Madison Avenue
✓ Found website: https://bluestonelane.com
✓ Successfully scraped website
✓ LLM parsing successful
  Email: contact@bluestonelane.com
  Phone: (212) 555-1234
  LinkedIn: https://linkedin.com/company/bluestone-lane
Quality Score: 85/100
```

## Best Practices

- ✅ Start with test run (5 companies)
- ✅ Check logs for errors
- ✅ Verify output quality before full batch
- ✅ Respect rate limits (built-in)
- ✅ Monitor API costs in OpenAI dashboard
- ✅ Keep API keys secure (never commit .env)

## Contributing

For bugs or improvements, please open an issue or submit a pull request.

## License

MIT License - See LICENSE file for details

## Support

For questions or issues:
1. Check logs in `logs/scraper.log`
2. Review `PLAN.md` for technical details
3. Verify API keys and quotas

---

## Scripts Reference

### Pharmacy Scraping

#### `scripts/scrape_all_pharmacies.py`
**Purpose**: Scrape all NYC pharmacies using Google Places API
**Output**: `data/pharmacy_results.csv`
**Run**: `docker-compose run --rm scraper python scripts/scrape_all_pharmacies.py`
**Notes**: Main pharmacy scraper, uses Google Places API + web scraping for contact details

#### `scripts/scrape_pharmacies_area9.py`
**Purpose**: Scrape pharmacies in specific geographic area (Area 9)
**Output**: `data/area9_pharmacies.csv`
**Run**: `docker-compose run --rm scraper python scripts/scrape_pharmacies_area9.py`
**Notes**: Specialized script for testing specific area boundaries

#### `scripts/convert_pharmacies_to_kml.py`
**Purpose**: Convert pharmacy CSV data to KML/KMZ format for Google Maps
**Input**: `data/pharmacy_results.csv`
**Output**: `data/pharmacies.kml`, `data/pharmacies.kmz`
**Run**: `python3 scripts/convert_pharmacies_to_kml.py`
**Notes**: Creates interactive map with pharmacy markers and contact popups

---

### Building Tenant Scraping (Lower Manhattan Office Buildings)

#### Complete 4-Step Workflow

**Step 1: Get Building Coordinates**
```bash
docker-compose run --rm scraper python scripts/scrape_office_buildings.py
```
- **Purpose**: Scrape office building coordinates in Lower Manhattan
- **Output**: `v2_lower_manhattan_tenants/data/lower_manhattan_office_buildings.csv`
- **Notes**: Uses Google Places API to find ~324 office buildings

**Step 2: Scrape Tenant Directories**
```bash
docker-compose run --rm scraper python scripts/scrape_building_tenants_phase1.py
```
- **Purpose**: Extract tenant directories from each building
- **Output**: Creates 3 CSV files per building:
  - `data/{building}_merchants.csv` - Businesses/merchants
  - `data/{building}_lawyers.csv` - Law firms and attorneys
  - `data/{building}_building_contacts.csv` - Building management
- **Notes**: Uses Hunter.io API + LLM parsing; processes all 324 buildings

**Step 3: Enrich Contact Data** (Optional but recommended)
```bash
docker-compose run --rm scraper python scripts/enrich_top_buildings.py
```
- **Purpose**: Enrich top 25 buildings with missing contact info (emails, phones, LinkedIn)
- **Input**: Existing CSV files in `data/` directory
- **Output**: Updates all `*_merchants.csv`, `*_lawyers.csv`, `*_building_contacts.csv`
- **Duration**: 6-8 hours for 25 buildings (~20-30 sec per tenant)
- **Method**: Serper.dev API (Google Search) → Web scraping → OpenAI LLM extraction
- **Progress**: Saved to `data/enrichment_progress.json` (can resume if interrupted)

**Step 4: Generate Google Maps KMZ**
```bash
cd v2_lower_manhattan_tenants
python3 scripts/export_tenants_to_kmz.py
```
- **Purpose**: Create KMZ file with all enriched tenant data
- **Input**:
  - `v2_lower_manhattan_tenants/data/lower_manhattan_office_buildings.csv`
  - All tenant CSV files from `data/` directory
- **Output**:
  - `v2_lower_manhattan_tenants/data/lower_manhattan_tenants.kml`
  - `v2_lower_manhattan_tenants/data/lower_manhattan_tenants.kmz` (upload this)
- **Upload to**: https://mymaps.google.com
- **Features**: Color-coded markers by tenant density, interactive popups with full contact details

---

### Data Processing & Utilities

#### `scripts/consolidate_results.py`
**Purpose**: Merge multiple CSV result files into single consolidated file
**Run**: `python3 scripts/consolidate_results.py`

#### `scripts/parse_districts.py`
**Purpose**: Parse and process NYC district geographic boundaries
**Run**: `python3 scripts/parse_districts.py`
**Notes**: Used for area-based pharmacy scraping

#### `scripts/manage_cache.py`
**Purpose**: Manage API response cache to reduce costs
**Run**: `python3 scripts/manage_cache.py [stats|clear|view]`
**Notes**: Cache responses to avoid duplicate API calls

#### `scripts/populate_cache_from_csv.py`
**Purpose**: Pre-populate cache from existing CSV data
**Run**: `python3 scripts/populate_cache_from_csv.py`
**Notes**: Bootstrap cache from previous scraping runs

---

### Legacy/Duplicate Scripts ⚠️

**The following scripts in `v2_lower_manhattan_tenants/scripts/` are duplicates.**
**Use the versions in main `scripts/` folder instead:**

- ❌ `v2_lower_manhattan_tenants/scripts/enrich_top_buildings.py`
  ✅ **USE**: `scripts/enrich_top_buildings.py` (Docker-compatible with env vars)

- ❌ `v2_lower_manhattan_tenants/scripts/scrape_building_tenants_phase1.py`
  ✅ **USE**: `scripts/scrape_building_tenants_phase1.py`

- ❌ `v2_lower_manhattan_tenants/scripts/scrape_office_buildings.py`
  ✅ **USE**: `scripts/scrape_office_buildings.py`

**Exception** (no duplicate, use this one):
- ✅ `v2_lower_manhattan_tenants/scripts/export_tenants_to_kmz.py` - Only KMZ export script

**Why duplicates exist**: V2 scripts had import issues in Docker. Fixed versions are in main `scripts/` folder using environment variables instead of config imports.

---

## Environment Variables

Required API keys (set in `.env` file):

```bash
# Required for all scripts
OPENAI_API_KEY=your_key_here           # OpenAI for LLM parsing
GOOGLE_PLACES_API_KEY=your_key_here    # Google Places API

# Required for enrichment (Step 3)
SERPER_API_KEY=your_key_here           # Serper.dev for Google Search
HUNTER_API_KEY=your_key_here           # Hunter.io for email finding
```

---

## Data Output Structure

### Main Data Directory: `data/`

**Tenant CSV Files** (per building):
- `{building_address}_merchants.csv` - Merchants and businesses
- `{building_address}_lawyers.csv` - Law firms and attorneys
- `{building_address}_building_contacts.csv` - Building management contacts

**Pharmacy Data**:
- `pharmacy_results.csv` - All NYC pharmacies
- `area9_pharmacies.csv` - Area 9 pharmacies

**Progress Files**:
- `enrichment_progress.json` - Enrichment script progress (allows resume)

### V2 Data Directory: `v2_lower_manhattan_tenants/data/`

- `lower_manhattan_office_buildings.csv` - Building coordinates (~324 buildings)
- `lower_manhattan_tenants.kml` - KML for Google Maps
- `lower_manhattan_tenants.kmz` - Compressed KML (final deliverable)

---

## CSV Output Schema

### Merchants CSV
```
name, type, is_law_firm, website, email, email_secondary, phone, phone_secondary,
address, linkedin, twitter, facebook, instagram, contact_person, contact_title,
stars, reviews, quality_score, data_source, last_updated
```

### Lawyers CSV
```
lawyer_name, lawyer_title, company_name, lawyer_email, lawyer_phone,
lawyer_linkedin, practice_areas, bar_admissions, years_experience,
address, quality_score, data_source, last_updated
```

### Building Contacts CSV
```
building_name, name, contact_name, contact_title, email, phone, website,
address, company_type, quality_score, data_source, last_updated
```

---

## Common Command Patterns

### Full Building Tenant Pipeline
```bash
# 1. Get building coordinates
docker-compose run --rm scraper python scripts/scrape_office_buildings.py

# 2. Scrape tenant directories (all 324 buildings)
docker-compose run --rm scraper python scripts/scrape_building_tenants_phase1.py

# 3. Enrich top 25 buildings (6-8 hours)
docker-compose run --rm scraper python scripts/enrich_top_buildings.py

# 4. Generate KMZ file
cd v2_lower_manhattan_tenants && python3 scripts/export_tenants_to_kmz.py
```

### Pharmacy Pipeline
```bash
# Scrape all NYC pharmacies
docker-compose run --rm scraper python scripts/scrape_all_pharmacies.py

# Convert to KMZ
python3 scripts/convert_pharmacies_to_kml.py
```

### Cache Management
```bash
# View cache stats
python3 scripts/manage_cache.py stats

# Clear cache
python3 scripts/manage_cache.py clear

# Pre-populate from CSV
python3 scripts/populate_cache_from_csv.py
```

---

**Last Updated:** November 26, 2024
**Version:** 2.0
