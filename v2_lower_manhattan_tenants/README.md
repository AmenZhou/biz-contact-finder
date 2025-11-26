# V2: Lower Manhattan Office Building Tenant Scraper

## Overview
Scrapes tenant/merchant data from office buildings in Lower Manhattan (below 14th Street) with minimal Google API costs.

## Approach
- **Phase 1**: Web Scraping + OpenAI LLM (Cost: ~$0.50-1.00)
  - Uses Serper.dev API (free tier) for Google search
  - Scrapes building directory websites
  - OpenAI GPT-4o-mini extracts structured data
  - Generates coverage report

- **Phase 2** (Optional): Fill gaps with Google Places API (~$5-10)

## Files

### Scripts
- `scrape_office_buildings.py` - OSM-based building discovery (FREE)
- `scrape_building_tenants_phase1.py` - Tenant data scraper (Phase 1)

### Data
- `lower_manhattan_office_buildings.csv` - 782 buildings from OSM
- Generated per-building files:
  - `{building}_merchants.csv`
  - `{building}_building_contacts.csv`
  - `{building}_lawyers.csv`
- `scraping_coverage_report.csv` - Phase 1 results

## CSV Format (Matches Existing)

### merchants.csv
```
name, type, is_law_firm, website, email, phone, address, linkedin,
twitter, facebook, instagram, contact_person, contact_title,
quality_score, data_source, last_updated
```

### building_contacts.csv
```
building_name, contact_name, contact_title, email, phone,
linkedin, instagram, website, address
```

### lawyers.csv
```
company_name, lawyer_name, lawyer_title, lawyer_email,
lawyer_phone, lawyer_linkedin
```

## Requirements
- OpenAI API key (in .env: `OPENAI_API_KEY`)
- Serper.dev API key (in .env: `SERPER_API_KEY`)
- Optional: Google Places API key for Phase 2

## Usage

### Phase 1: Web Scraping Only
```bash
docker-compose run --rm scraper python v2_lower_manhattan_tenants/scripts/scrape_building_tenants_phase1.py
```

### Results
- Per-building CSV files in `data/`
- Coverage report: `data/scraping_coverage_report.csv`
- Review report to decide if Phase 2 (Google API) is needed

## Cost Estimate
- Phase 1: $0.50 - $1.00 (OpenAI + free Serper tier)
- Phase 2: $5 - $10 (Google Places API for gaps)

## Current Status
- **324 commercial/office buildings** identified
- **Testing**: First 10 buildings processed
- **Success**: Finding tenant data via web scraping!
