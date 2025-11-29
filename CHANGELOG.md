# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Census Income Map for Brooklyn & Queens**: Choropleth visualization of median household income
  - Downloads TIGER/Line census tract shapefiles (1,530 tracts)
  - Queries US Census ACS API for Table B19013 (Median Household Income 2022)
  - Generates color-coded KMZ with 6 income bins (< $40k to $125k+)
  - Script: `scripts/census/export_income_to_kmz.py`
  - Output: `data/census/exports/brooklyn_queens_income.kmz` (184 KB)
  - Google My Maps compatible with Document-level style placement
  - Full Windows compatibility with UTF-8 BOM encoding
- **Combined Building Management Contact Exports**: Consolidated CSV files for easy access
  - District 18: 153 contacts from 41 buildings (`district18_building_management_contacts.csv`)
  - District 9: 27 contacts from 6 buildings (`district9_building_management_contacts.csv`)
  - Windows-compatible with UTF-8 BOM encoding and ASCII character normalization
  - Script: `05_combine_building_contacts.py` for both districts
- **KMZ Export Enhancements for District 18**:
  - Building management contacts now highlighted with searchable marker text
  - Improved HTML popup formatting with visual separators (divider lines between merchants)
  - Company grouping for law firms and building management (multiple contacts under same company)
  - Gray box styling for law firms and building management sections
  - Divider lines between merchant entries for better readability
  - Fixed spacing issues between sections
- **District 18 Building Tenant Scraper**: Complete 4-step workflow for scraping tenant data from District 18 buildings
  - **Step 1**: `01_convert_excel_to_buildings.py` - Converts Excel file (`data/district_18/18.xlsx`) to building CSV with geocoded coordinates
  - **Step 2**: `02_scrape_tenant_directories.py` - Scrapes tenant directories using Serper.dev API and OpenAI LLM extraction
  - **Step 3**: `03_enrich_contacts.py` - Enriches tenant contact data (emails, phones, LinkedIn) for top buildings
  - **Step 4**: `04_export_to_kmz.py` - Generates Google Maps KMZ file with color-coded markers and interactive popups
  - Processes 91 buildings in District 18 (Midtown Manhattan)
  - Output: 62 buildings with tenant data, 352 total tenants extracted
  - Follows same pattern as Lower Manhattan workflow for consistency
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
- **Docker Environment**: Added geospatial dependencies for census data processing
  - Installed GDAL, libgdal-dev, libspatialindex-dev in Docker container
  - Added Python packages: geopandas>=0.14.0, simplekml>=1.3.6, fiona>=1.9.0, shapely>=2.0.0
  - Updated Dockerfile to include GDAL system dependencies
- **KMZ Export Format**: Enhanced District 18 KMZ with improved visual organization
  - Added text-based divider lines (──────) between merchants for clarity
  - Implemented company grouping with gray boxes for building management and law firms
  - Improved spacing and margins throughout popup HTML
- **Input File**: Updated default input file to `data/477 Madison Ave.xlsx`
- **Output Columns**: Added `company_size` and `company_type_hunter` columns to merchant output CSV
- **Configuration**: Added Area #9 geographic boundaries and pharmacy CSV path to `config/settings.py`

### Fixed
- **Google My Maps KML Compatibility**: Fixed polygon colors not displaying in Google My Maps
  - Root cause: Google My Maps doesn't support styles at `<Folder>` level, only at `<Document>` level
  - Created `fix_kml_styles.py` post-processing script to move all Style elements to Document level
  - KMZ files now display vibrant color-coded income levels correctly
- **Building Management Contact Field Mapping**: Fixed "Unknown" values in KMZ popups
  - Updated to use correct CSV field names: `contact_name` instead of `contact_person`
  - Added fallback handling for `building_name` vs `name` field inconsistencies
- **KMZ Visual Formatting Issues**: Fixed merchant entries running together in Google Maps popups
  - Changed from background-based separation (not rendered by Google Maps) to text-based dividers
  - Adjusted spacing between sections (merchants, law firms, building management)
  - Removed non-functional "[Building Management Contact Available]" yellow banner
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

