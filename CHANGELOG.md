# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Pharmacy Scraper for Area #9**: New `PharmacyScraper` class and `scrape_pharmacies_area9.py` script to find all pharmacies in Chelsea/NoMad district (Area #9) using Google Places API
  - Grid-based search with 3x3 coverage pattern for comprehensive area scanning
  - Text-based search with location bias for additional coverage
  - Automatic boundary filtering to ensure all results are within district boundaries
  - Output saved to `data/area9_pharmacies.csv` with pharmacy details (name, address, phone, website, ratings, hours, etc.)
- **Hunter.io Integration**: New `HunterScraper` class for retrieving company size and employee information
  - Hunter.io API integration for company data lookup
  - LinkedIn company page scraping as fallback using Playwright and LLM parsing
  - Automatic mapping of employee counts to standardized size ranges (1-10, 11-50, 51-200, etc.)
  - Company type/industry extraction from both Hunter.io and LinkedIn
- **Company Size Tracking**: Added `company_size` and `company_type_hunter` fields to merchant data
  - Company size ranges extracted from Hunter.io or LinkedIn
  - Industry/company type information from Hunter.io
  - Data source attribution for tracking where information came from

### Changed
- **Input File**: Updated default input file to `data/477 Madison Ave.xlsx`
- **Output Columns**: Added `company_size` and `company_type_hunter` columns to merchant output CSV
- **Configuration**: Added Area #9 geographic boundaries and pharmacy CSV path to `config/settings.py`

### Fixed
- **Resource Leak in HunterScraper**: Fixed memory leak where Playwright browser instances were not properly closed
  - Added `cleanup()` method to `ContactInfoScraper` class
  - Browser resources are now properly released after scraping completes
  - Cleanup is called both at end of `run()` method and in `main()` function with try/finally to ensure cleanup even on errors
- **Incomplete Data Source Attribution**: Fixed issue where `'linkedin'` was only added to `data_source` when `company_size` was found
  - Now correctly adds `'linkedin'` to `data_source` when either `company_size` OR `company_type` is extracted from LinkedIn
  - Ensures proper attribution for all data retrieved from LinkedIn, not just company size

### Technical Details
- **Boundary Enforcement**: Optimized pharmacy scraper to filter results at multiple levels (early geometry check, detailed coordinate check, post-processing filter) for efficiency
- **Error Handling**: Improved error handling in HunterScraper with proper resource cleanup on exceptions
- **Code Organization**: Separated pharmacy scraping functionality into dedicated scraper class and script for better maintainability

