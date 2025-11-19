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

### 1. Install Dependencies

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

### Test with Sample Data (5 companies)

```bash
python main.py
```

The default configuration processes 5 companies for testing.

### Process All Companies

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

### Common Issues

**"No module named 'googlemaps'"**
```bash
pip install -r requirements.txt
```

**"OpenAI API key is required"**
- Add your API key to `.env` file

**"Rate limit exceeded"**
- The script has built-in rate limiting
- Check your API quotas

**"No results found"**
- Some companies may not have public websites
- Check Google Places availability for that business

### Resume After Interruption

The script automatically saves progress to `data/progress.json`. If interrupted, simply run again and it will skip already processed companies.

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

**Last Updated:** November 18, 2024
**Version:** 1.0
