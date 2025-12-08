# Queens & Brooklyn Law Office Scraper

Find all law offices and attorneys in Queens and Brooklyn using Serper.dev API.

## Features

- ✅ **Serper.dev API Only**: No Google Places API needed
- ⚖️ **Comprehensive Coverage**: Searches 50 neighborhoods across Queens & Brooklyn
- 📞 **Full Contact Info**: Phone, email, address, website, and contact names
- 🗺️ **KMZ Export**: Google My Maps visualization
- 💾 **Progress Tracking**: Resumable scraping
- 🤖 **AI Enrichment**: Uses OpenAI to extract structured contact data

## Prerequisites

```bash
# Required API keys
export SERPER_API_KEY="your_serper_api_key"
export OPENAI_API_KEY="your_openai_api_key"  # Optional but recommended
```

## Usage

### Step 1: Scrape Law Offices

```bash
# In Docker
docker-compose run --rm scraper python3 scripts/law_offices/01_scrape_law_offices_queens_brooklyn.py

# Or locally
python3 scripts/law_offices/01_scrape_law_offices_queens_brooklyn.py
```

**Output**: `data/law_offices/queens_brooklyn_law_offices.csv`

### Step 2: Export to KMZ

```bash
python3 scripts/law_offices/02_export_to_kmz.py
```

**Output**: `data/law_offices/queens_brooklyn_law_offices.kmz`

## Search Strategy

- **50 Neighborhoods**: 20 in Queens + 30 in Brooklyn
- **9 Search Terms** per neighborhood:
  1. "law office"
  2. "attorney"
  3. "lawyer"
  4. "legal services"
  5. "immigration lawyer"
  6. "family law attorney"
  7. "personal injury attorney"
  8. "criminal defense lawyer"
  9. "real estate lawyer"

**Total**: 450 searches

## Output Fields

| Field | Description |
|-------|-------------|
| `name` | Law office or attorney name |
| `address` | Full street address |
| `phone` | Formatted phone number |
| `email` | Contact email |
| `website` | Office website |
| `contact_name` | Attorney or office manager name |
| `rating` | Google rating |
| `reviews` | Number of reviews |
| `latitude` | GPS latitude |
| `longitude` | GPS longitude |

## Performance

- **API Calls**: ~450 Serper searches
- **Rate Limiting**: 1 second delay between searches
- **Estimated Time**: ~8-10 minutes
- **Cost**: ~$2.25 (Serper charges $5/1000 searches)
