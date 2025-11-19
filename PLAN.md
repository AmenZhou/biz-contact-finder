# Company Contact Info Scraper - Project Plan

## Project Overview

**Goal:** Extract comprehensive contact information for 68 companies listed in `330Madison.csv`

**Input:** CSV with company names, addresses, some phone numbers
**Output:** Enriched CSV with websites, emails, LinkedIn profiles, verified phone numbers

**Approach:** Hybrid system combining web scraping + LLM parsing + API verification

---

## Architecture Overview

```
┌─────────────┐
│ Input CSV   │
│ (68 companies)
└──────┬──────┘
       │
       ▼
┌──────────────────────────────┐
│  Google Places API           │
│  - Get official website URLs │
│  - Verify phone numbers      │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  Website Scraper             │
│  - Visit company website     │
│  - Find contact page         │
│  - Extract HTML content      │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  LLM Parser (GPT-4o-mini)    │
│  - Parse unstructured HTML   │
│  - Extract contact info      │
│  - Return structured JSON    │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  Validation & Enrichment     │
│  - Email format validation   │
│  - Phone number formatting   │
│  - Deduplication             │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  Output Enriched CSV         │
└──────────────────────────────┘
```

---

## Technical Stack

### Core Technologies
- **Python 3.9+** - Main language
- **pandas** - CSV manipulation
- **requests** - HTTP requests
- **beautifulsoup4** - HTML parsing
- **openai** - GPT-4o-mini API
- **python-dotenv** - Environment variables
- **ratelimit** - API rate limiting

### APIs Required
1. **Google Places API** (Optional but recommended)
   - Free tier: 100 requests/day
   - Get official websites, phone numbers
   - Cost: $0 (within free tier)

2. **OpenAI API** (Required)
   - GPT-4o-mini model
   - Cost: ~$0.01 per company
   - Total estimated: ~$0.68 for 68 companies

3. **Hunter.io** (Optional)
   - Email verification
   - Free tier: 25 requests/month
   - Cost: $0 (within free tier)

---

## Project Structure

```
sy_promotion_merchants_craw/
├── PLAN.md                    # This file
├── README.md                  # Usage instructions
├── requirements.txt           # Python dependencies
├── .env.example              # API key template
├── .env                      # Actual API keys (gitignored)
├── .gitignore               # Git ignore file
│
├── config/
│   └── settings.py          # Configuration constants
│
├── scrapers/
│   ├── __init__.py
│   ├── google_places.py     # Google Places API integration
│   ├── website_scraper.py   # Website scraping logic
│   └── llm_parser.py        # OpenAI LLM integration
│
├── utils/
│   ├── __init__.py
│   ├── validators.py        # Email/phone validation
│   ├── logger.py           # Logging setup
│   └── rate_limiter.py     # Rate limiting utilities
│
├── main.py                  # Main orchestration script
├── test_sample.py          # Test with sample data
│
├── data/
│   ├── 330Madison.csv      # Input file
│   ├── progress.json       # Incremental progress tracker
│   └── output_enriched.csv # Final output
│
└── logs/
    └── scraper.log         # Execution logs
```

---

## Workflow Details

### Phase 1: Google Places Enrichment
For each company in CSV:
1. Search Google Places API with company name + address
2. Extract:
   - Official website URL
   - Formatted phone number
   - Business status (open/closed)
   - Google rating
3. Handle rate limits (50 requests/second max)
4. Cache results to avoid re-requests

### Phase 2: Website Scraping
For each company with a website:
1. Make HTTP GET request to company website
2. Find potential contact pages:
   - `/contact`, `/contact-us`, `/about`, `/about-us`
   - Check footer for contact links
   - Look for "Contact" in navigation
3. Extract HTML content from contact pages
4. Handle errors (404, timeouts, SSL issues)

### Phase 3: LLM Parsing
For each scraped page:
1. Send HTML to GPT-4o-mini with structured prompt
2. Request JSON output with fields:
   ```json
   {
     "email": "contact@company.com",
     "phone": "(212) 555-1234",
     "linkedin": "https://linkedin.com/company/...",
     "address": "Full formatted address",
     "contact_person": "Name (if found)",
     "other_contacts": []
   }
   ```
3. Validate JSON response
4. Handle parsing errors gracefully

### Phase 4: Validation & Enrichment
1. **Email validation:**
   - Check format with regex
   - Verify domain exists (DNS lookup)
   - Optional: Hunter.io verification

2. **Phone formatting:**
   - Standardize to (XXX) XXX-XXXX format
   - Validate US phone numbers

3. **Deduplication:**
   - Remove duplicate emails/phones per company
   - Prioritize generic emails (info@, contact@)

### Phase 5: Output Generation
1. Merge all extracted data
2. Create enriched CSV with columns:
   - Original columns from input
   - `website`
   - `email_primary`
   - `email_secondary`
   - `phone_verified`
   - `linkedin_url`
   - `contact_person`
   - `last_updated`
   - `data_quality_score` (0-100)

---

## API Requirements & Setup

### Google Places API
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project or select existing
3. Enable "Places API"
4. Create API credentials (API Key)
5. Restrict key to Places API only (security)
6. Add to `.env`: `GOOGLE_PLACES_API_KEY=your_key_here`

### OpenAI API
1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Create account and add payment method
3. Generate API key
4. Add to `.env`: `OPENAI_API_KEY=sk-...`

### Hunter.io (Optional)
1. Sign up at [Hunter.io](https://hunter.io/)
2. Get free API key (25 requests/month)
3. Add to `.env`: `HUNTER_API_KEY=your_key_here`

---

## Rate Limiting Strategy

### API Rate Limits
- **Google Places:** 100 requests/day (free), 50 req/sec
- **OpenAI:** 500 requests/min (tier 1), 200k tokens/min
- **Website Scraping:** 1 request/second (be polite)

### Implementation
```python
from ratelimit import limits, sleep_and_retry

@sleep_and_retry
@limits(calls=1, period=1)  # 1 call per second
def scrape_website(url):
    # scraping logic
    pass
```

---

## Error Handling Strategy

### Types of Errors
1. **Network errors:** Timeout, connection refused
2. **HTTP errors:** 404, 403, 500
3. **Parsing errors:** Invalid HTML, missing elements
4. **API errors:** Rate limit exceeded, invalid key
5. **LLM errors:** Invalid JSON, hallucinations

### Handling Approach
```python
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def fetch_with_retry(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response
    except Exception as e:
        logging.error(f"Error fetching {url}: {e}")
        raise
```

---

## Data Quality Scoring

Each company gets a quality score (0-100) based on:
- **Website found:** +30 points
- **Email found:** +25 points
- **Phone verified:** +20 points
- **LinkedIn found:** +15 points
- **Contact person found:** +10 points

---

## Cost Estimation

### API Costs (68 companies)
- **Google Places API:** $0 (free tier sufficient)
- **OpenAI API:**
  - ~5 API calls per company average
  - GPT-4o-mini: $0.15/1M input tokens, $0.60/1M output tokens
  - Estimated: ~$0.50 - $1.00 total
- **Hunter.io:** $0 (free tier)

**Total estimated cost:** < $2

### Time Estimation
- Setup: 30-60 minutes
- Development: 2-3 hours
- Testing: 30 minutes
- Execution: 10-15 minutes (for 68 companies)

---

## Testing Strategy

### Unit Tests
- Test individual scrapers with mock data
- Test validators with edge cases
- Test LLM parser with sample HTML

### Integration Tests
1. Test with 5 sample companies first
2. Verify output format
3. Check error handling
4. Validate data quality

### Sample Test Companies (from CSV)
- Bluestone Lane (has website, popular)
- CMIT Solutions (has phone)
- JLL (large company, good data)
- Guggenheim Partners (financial, may have limited public info)
- The Granola Bar (small business, might be challenging)

---

## Success Criteria

### Minimum Viable Output
- ✅ 80%+ companies have websites
- ✅ 60%+ companies have emails
- ✅ 90%+ companies have verified phone numbers
- ✅ No hallucinated/fake contact info
- ✅ CSV format is clean and usable

### Stretch Goals
- 🎯 90%+ companies have emails
- 🎯 50%+ companies have LinkedIn profiles
- 🎯 Find contact person names for 30%+

---

## Security & Ethics

### Best Practices
- ✅ Respect robots.txt
- ✅ Rate limit to avoid overwhelming servers
- ✅ User-Agent header identifies scraper
- ✅ Don't scrape personal social media
- ✅ Only use publicly available information
- ✅ Store API keys in .env (never commit)

### Legal Compliance
- ✅ Public business information only
- ✅ No GDPR/privacy violations
- ✅ Follow website terms of service
- ✅ Use for business purposes only

---

## Future Enhancements

### Phase 2 Ideas
1. **Scheduled updates:** Run weekly to keep data fresh
2. **Web interface:** FastAPI + React dashboard
3. **Email validation:** Integrate real email verification
4. **Social media:** Extract Twitter, Facebook handles
5. **Key contacts:** Find specific roles (CEO, Sales Director)
6. **Export formats:** Excel, JSON, API endpoints

---

## Troubleshooting Guide

### Common Issues

**Issue:** Google Places API not finding companies
**Solution:** Adjust search query, include ZIP code, try variations of company name

**Issue:** Websites blocking scraper
**Solution:** Add proper User-Agent, rotate IPs, use Selenium for JS-heavy sites

**Issue:** LLM hallucinating contact info
**Solution:** Improve prompt, add validation, cross-reference with other sources

**Issue:** Rate limits exceeded
**Solution:** Implement exponential backoff, reduce concurrency

---

## Maintenance

### Regular Tasks
- Monitor API usage and costs
- Update dependencies monthly
- Refresh API keys before expiration
- Archive old output files
- Review and improve prompts based on results

---

## References & Resources

- [Google Places API Docs](https://developers.google.com/maps/documentation/places/web-service)
- [OpenAI API Docs](https://platform.openai.com/docs)
- [BeautifulSoup Documentation](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [Requests Documentation](https://requests.readthedocs.io/)
- [Web Scraping Best Practices](https://www.scrapehero.com/web-scraping-best-practices/)

---

**Last Updated:** November 18, 2024
**Version:** 1.0
**Status:** Ready for Implementation
