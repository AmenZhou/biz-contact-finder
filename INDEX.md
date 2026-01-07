# Project Index

Complete index of all scripts and data files in the SY Promotion Merchant Scraper project.

**Last Updated:** December 2, 2025

---

## Table of Contents

1. [Scripts Index](#scripts-index)
2. [Data Files Index](#data-files-index)
3. [Folder Structure](#folder-structure)
4. [Quick Reference](#quick-reference)

---

## Scripts Index

### Core Scrapers

#### Main Entry Point
- **`main.py`** - Main script entry point for general company contact scraping

#### Utility Scripts (Root)
- **`check_sheets.py`** - Check Excel sheet structure
- **`convert_to_csv.py`** - Convert Excel to CSV format
- **`convert_xlsx.py`** - Convert XLSX files
- **`convert_xlsx_v2.py`** - Enhanced XLSX conversion
- **`read_excel.py`** - Read Excel files
- **`extract_building_contacts.py`** - Extract building contact information

---

### Building Tenants Scripts

#### General Building Tenants

**Location:** `scripts/building_tenants/`

**Workflow Scripts:**
1. **`01_scrape_office_buildings.py`** - Scrape office building coordinates in Lower Manhattan
   - **Output:** `data/building_tenants/buildings/lower_manhattan_office_buildings.csv`
   - **Run:** `docker-compose run --rm scraper python scripts/building_tenants/01_scrape_office_buildings.py`

2. **`02_scrape_tenant_directories.py`** - Extract tenant directories from buildings
   - **Output:** Creates CSV files in `data/building_tenants/tenants/lower_manhattan/`
   - **Run:** `docker-compose run --rm scraper python scripts/building_tenants/02_scrape_tenant_directories.py`

3. **`03_enrich_contacts.py`** - Enrich buildings with missing contact info
   - **Input:** Existing CSV files in `data/building_tenants/tenants/lower_manhattan/`
   - **Output:** Updates all tenant CSV files
   - **Run:** `docker-compose run --rm scraper python scripts/building_tenants/03_enrich_contacts.py`

4. **`04_export_to_kmz.py`** - Generate Google Maps KMZ file
   - **Output:** `data/building_tenants/exports/lower_manhattan_tenants.kmz`
   - **Run:** `python3 scripts/building_tenants/04_export_to_kmz.py`

5. **`07_universal_contact_enrichment.py`** - Universal contact enrichment script

#### District 9 Scripts

**Location:** `scripts/building_tenants/district9/`

1. **`00_create_building_list.py`** - Create building list for District 9
2. **`01_convert_excel_to_buildings.py`** - Convert Excel to building CSV
3. **`02_scrape_tenant_directories.py`** - Scrape tenant directories for District 9
4. **`04_export_to_kmz.py`** - Export District 9 to KMZ
5. **`05_combine_building_contacts.py`** - Combine building contacts

#### District 18 Scripts

**Location:** `scripts/building_tenants/district18/`

1. **`01_convert_excel_to_buildings.py`** - Convert Excel to building CSV
   - **Input:** `data/district_18/18.xlsx`
   - **Output:** `data/building_tenants/buildings/district18_buildings.csv`

2. **`02_scrape_tenant_directories.py`** - Scrape tenant directories for District 18
   - **Output:** CSV files in `data/building_tenants/tenants/district18/`

3. **`03_enrich_contacts.py`** - Enrich District 18 contacts
   - **Output:** Updates tenant CSV files

4. **`04_export_to_kmz.py`** - Export District 18 to KMZ
   - **Output:** `data/building_tenants/exports/district18_tenants.kmz`

5. **`05_combine_building_contacts.py`** - Combine building contacts

6. **`06_enrich_building_management.py`** - Enrich building management contacts

7. **`07_enhanced_contact_enrichment.py`** - Enhanced contact enrichment

#### District 9 Backup

**Location:** `scripts/building_tenants/district9_old_backup/`

- **`district9_export_to_kmz.py`** - Legacy District 9 export script
- **`district9_get_coordinates.py`** - Legacy coordinate extraction

---

### Census Data Scripts

**Location:** `scripts/census/`

1. **`export_income_to_kmz.py`** - Export Brooklyn & Queens median household income to KMZ
   - **Output:** `data/census/exports/brooklyn_queens_income.kmz`
   - **Run:** `docker-compose run --rm scraper python scripts/census/export_income_to_kmz.py`
   - **Description:** Creates color-coded choropleth map of census tract income levels

2. **`fix_kml_styles.py`** - Fix KML file styles (move from Folder to Document level)
   - **Input:** `data/census/exports/brooklyn_queens_income.kml`
   - **Description:** Post-processing script to fix Google My Maps compatibility

---

### Pharmacy Scripts

**Location:** `scripts/pharmacies/`

1. **`scrape_all_pharmacies.py`** - Scrape all NYC pharmacies using Google Places API
   - **Output:** `data/pharmacies/pharmacy_results.csv`
   - **Run:** `docker-compose run --rm scraper python scripts/pharmacies/scrape_all_pharmacies.py`

2. **`scrape_pharmacies_area9.py`** - Scrape pharmacies in Area 9
   - **Output:** `data/pharmacies/area9_pharmacies.csv`
   - **Run:** `docker-compose run --rm scraper python scripts/pharmacies/scrape_pharmacies_area9.py`

3. **`export_pharmacies_to_kmz.py`** - Convert pharmacy CSV to KMZ
   - **Input:** `data/pharmacies/pharmacy_results.csv`
   - **Output:** `data/pharmacies/exports/pharmacies.kmz`
   - **Run:** `python3 scripts/pharmacies/export_pharmacies_to_kmz.py`

---

### Law Offices Scripts

**Location:** `scripts/law_offices/`

1. **`01_scrape_law_offices_queens_brooklyn.py`** - Scrape law offices in Queens and Brooklyn
   - **Output:** `data/law_offices/queens_brooklyn_law_offices.csv`
   - **Run:** `docker-compose run --rm scraper python scripts/law_offices/01_scrape_law_offices_queens_brooklyn.py`

2. **`02_export_to_kmz.py`** - Initial KMZ export
   - **Output:** `data/law_offices/queens_brooklyn_law_offices.kmz`

3. **`03_enrich_with_addresses.py`** - Enrich with addresses
   - **Output:** `data/law_offices/queens_brooklyn_law_offices_with_addresses.csv`

4. **`04_scrape_addresses_from_websites.py`** - Scrape addresses from websites
   - **Output:** `data/law_offices/queens_brooklyn_law_offices_with_addresses_llm.csv`

5. **`05_enrich_with_ratings.py`** - Enrich with ratings
   - **Output:** Updates CSV files

6. **`06_export_to_kmz.py`** - Final KMZ export with enriched data
   - **Output:** `data/law_offices/queens_brooklyn_law_offices.kmz`

7. **`07_enrich_with_practice_areas.py`** - Enrich with practice areas
   - **Output:** `data/law_offices/queens_brooklyn_law_offices_final.csv`

8. **`test_address_enrichment.py`** - Test script for address enrichment

---

### Medical Offices Scripts

**Location:** `scripts/medical_offices/`

1. **`01_scrape_doctors_queens_brooklyn.py`** - Scrape doctors in Queens and Brooklyn
   - **Output:** `data/medical_offices/queens_brooklyn_doctors.csv`
   - **Run:** `docker-compose run --rm scraper python scripts/medical_offices/01_scrape_doctors_queens_brooklyn.py`

2. **`02_export_to_kmz.py`** - Initial KMZ export
   - **Output:** `data/medical_offices/queens_brooklyn_doctors.kmz`

3. **`03_enrich_with_addresses.py`** - Enrich with addresses
   - **Output:** `data/medical_offices/queens_brooklyn_doctors_with_addresses.csv`

4. **`04_scrape_addresses_from_websites.py`** - Scrape addresses from websites
   - **Output:** `data/medical_offices/queens_brooklyn_doctors_with_addresses_llm.csv`

5. **`05_enrich_with_ratings.py`** - Enrich with ratings
   - **Output:** Updates CSV files

6. **`06_export_to_kmz.py`** - Final KMZ export with enriched data
   - **Output:** `data/medical_offices/queens_brooklyn_doctors.kmz`

7. **`07_enrich_with_specialties.py`** - Enrich with medical specialties
   - **Output:** `data/medical_offices/queens_brooklyn_doctors_with_specialties.csv`

8. **`test_scraper.py`** - Test script for scraper
9. **`test_simple.py`** - Simple test script

---

### Utility Scripts

**Location:** `scripts/utils/`

1. **`consolidate_results.py`** - Merge multiple CSV result files into single file
   - **Run:** `python3 scripts/utils/consolidate_results.py`

2. **`manage_cache.py`** - Manage API response cache
   - **Run:** `python3 scripts/utils/manage_cache.py [stats|clear|view]`

3. **`parse_districts.py`** - Parse and process NYC district geographic boundaries
   - **Run:** `python3 scripts/utils/parse_districts.py`

4. **`populate_cache_from_csv.py`** - Pre-populate cache from existing CSV data
   - **Run:** `python3 scripts/utils/populate_cache_from_csv.py`

---

### Core Scraper Modules

**Location:** `scrapers/`

- **`google_places.py`** - Google Places API integration
- **`hunter_scraper.py`** - Hunter.io email discovery
- **`llm_parser.py`** - OpenAI LLM parser for contact extraction
- **`pharmacy_cache.py`** - Pharmacy data caching
- **`pharmacy_scraper.py`** - Pharmacy scraping logic
- **`website_scraper.py`** - Web scraping with BeautifulSoup

---

### Configuration

**Location:** `config/`

- **`settings.py`** - Main configuration file
- **`districts.py`** - District definitions
- **`districts.json`** - District JSON data

---

### Utilities

**Location:** `utils/`

- **`logger.py`** - Logging setup
- **`validators.py`** - Data validation utilities

---

## Data Files Index

### Building Tenants Data

**Location:** `data/building_tenants/`

#### Building Coordinates

**Location:** `data/building_tenants/buildings/`
- **`lower_manhattan_office_buildings.csv`** - ~324 office buildings in Lower Manhattan
- **`district9_buildings.csv`** - 6 District 9 premium buildings
- **`district18_buildings.csv`** - 91 District 18 buildings

#### Tenant Data

**Location:** `data/building_tenants/tenants/`

**Lower Manhattan** (`tenants/lower_manhattan/`):
- `{building}_merchants.csv` - Merchants and businesses per building
- `{building}_lawyers.csv` - Law firms and attorneys per building
- `{building}_building_contacts.csv` - Building management per building

**District 9** (`tenants/district9/`):
- `{building}_merchants.csv` - District 9 merchants
- `{building}_lawyers.csv` - District 9 lawyers
- `{building}_building_contacts.csv` - District 9 building management

**District 18** (`tenants/district18/`):
- `{building}_merchants.csv` - District 18 merchants
- `{building}_lawyers.csv` - District 18 lawyers
- `{building}_building_contacts.csv` - District 18 building management

#### Exports

**Location:** `data/building_tenants/exports/`
- **`lower_manhattan_tenants.kml`** - KML for Google Maps
- **`lower_manhattan_tenants.kmz`** - Compressed KML (final deliverable)
- **`district9_tenants.kml`** - District 9 KML
- **`district9_tenants.kmz`** - District 9 compressed KML
- **`district18_tenants.kml`** - District 18 KML
- **`district18_tenants.kmz`** - District 18 compressed KML

#### Reports

**Location:** `data/building_tenants/reports/`
- **`scraping_coverage_report.csv`** - General scraping coverage report
- **`scraping_coverage_report_district9.csv`** - District 9 coverage report
- **`scraping_coverage_report_district18.csv`** - District 18 coverage report

#### Progress Files

**Location:** `data/building_tenants/progress/`
- **`enrichment_progress.json`** - Lower Manhattan enrichment progress
- **`district18_enrichment_progress.json`** - District 18 enrichment progress
- **`targeted_buildings_51.txt`** - List of buildings for targeted enrichment

---

### Pharmacy Data

**Location:** `data/pharmacies/`

#### Main Files
- **`all_districts_pharmacies.csv`** - All NYC pharmacies across all districts
- **`area9_pharmacies.csv`** - Area 9 pharmacies
- **`pharmacy_results.csv`** - Main pharmacy results (if exists)

#### District Files

**Location:** `data/pharmacies/districts/`
- **`district_01_pharmacies.csv`** through **`district_55_pharmacies.csv`** - Individual district pharmacy data

#### Exports

**Location:** `data/pharmacies/exports/`
- **`pharmacies.kml`** - KML for Google Maps
- **`pharmacies.kmz`** - Compressed KML

---

### Census Data

**Location:** `data/census/`

#### Boundaries

**Location:** `data/census/boundaries/`
- **`tl_2022_36_tract.shp`** - TIGER/Line 2022 shapefile for NY census tracts
- Supporting files: `.dbf`, `.shx`, `.prj`, `.xml`, `.cpg`

#### Exports

**Location:** `data/census/exports/`
- **`brooklyn_queens_income.kml`** - KML file with income data
- **`brooklyn_queens_income.kmz`** - KMZ file for Google My Maps
  - **Description:** Color-coded choropleth map of 1,530 census tracts (805 Brooklyn + 725 Queens)
  - **Color Scheme:** 9 income brackets with distinct colors
  - **Data Source:** US Census Bureau ACS 2022 5-Year Estimates

---

### Law Offices Data

**Location:** `data/law_offices/`

- **`queens_brooklyn_law_offices.csv`** - Initial scrape results
- **`queens_brooklyn_law_offices_with_addresses.csv`** - With addresses added
- **`queens_brooklyn_law_offices_with_addresses_llm.csv`** - LLM-enriched addresses
- **`queens_brooklyn_law_offices_final.csv`** - Final enriched data with practice areas
- **`queens_brooklyn_law_offices.kml`** - KML file
- **`queens_brooklyn_law_offices.kmz`** - KMZ file for Google Maps
- **`scraping_progress.json`** - Progress tracking

---

### Medical Offices Data

**Location:** `data/medical_offices/`

- **`queens_brooklyn_doctors.csv`** - Initial scrape results
- **`queens_brooklyn_doctors_with_addresses.csv`** - With addresses added
- **`queens_brooklyn_doctors_with_addresses_llm.csv`** - LLM-enriched addresses
- **`queens_brooklyn_doctors_with_specialties.csv`** - With medical specialties
- **`queens_brooklyn_doctors_final.csv`** - Final enriched data
- **`queens_brooklyn_doctors.kml`** - KML file
- **`queens_brooklyn_doctors.kmz`** - KMZ file for Google Maps
- **`scraping_progress.json`** - Progress tracking

---

## Folder Structure

```
sy_promotion_merchant_scraper/
├── INDEX.md                    # This file
├── README.md                   # Main project documentation
├── PLAN.md                     # Detailed project plan
├── requirements.txt            # Python dependencies
├── docker-compose.yml          # Docker configuration
├── Dockerfile                  # Docker image definition
│
├── config/                      # Configuration files
│   ├── settings.py
│   ├── districts.py
│   └── districts.json
│
├── scrapers/                    # Core scraper modules
│   ├── google_places.py
│   ├── website_scraper.py
│   ├── llm_parser.py
│   ├── hunter_scraper.py
│   ├── pharmacy_scraper.py
│   └── pharmacy_cache.py
│
├── utils/                       # Utility modules
│   ├── logger.py
│   └── validators.py
│
├── scripts/                     # All scripts organized by category
│   ├── building_tenants/       # Building tenant scraping
│   │   ├── 01_scrape_office_buildings.py
│   │   ├── 02_scrape_tenant_directories.py
│   │   ├── 03_enrich_contacts.py
│   │   ├── 04_export_to_kmz.py
│   │   ├── 07_universal_contact_enrichment.py
│   │   ├── district9/          # District 9 specific scripts
│   │   ├── district18/         # District 18 specific scripts
│   │   └── district9_old_backup/
│   │
│   ├── census/                 # Census data scripts
│   │   ├── export_income_to_kmz.py
│   │   └── fix_kml_styles.py
│   │
│   ├── pharmacies/             # Pharmacy scraping scripts
│   │   ├── scrape_all_pharmacies.py
│   │   ├── scrape_pharmacies_area9.py
│   │   └── export_pharmacies_to_kmz.py
│   │
│   ├── law_offices/            # Law office scraping scripts
│   │   ├── 01_scrape_law_offices_queens_brooklyn.py
│   │   ├── 02_export_to_kmz.py
│   │   ├── 03_enrich_with_addresses.py
│   │   ├── 04_scrape_addresses_from_websites.py
│   │   ├── 05_enrich_with_ratings.py
│   │   ├── 06_export_to_kmz.py
│   │   ├── 07_enrich_with_practice_areas.py
│   │   └── test_address_enrichment.py
│   │
│   ├── medical_offices/        # Medical office scraping scripts
│   │   ├── 01_scrape_doctors_queens_brooklyn.py
│   │   ├── 02_export_to_kmz.py
│   │   ├── 03_enrich_with_addresses.py
│   │   ├── 04_scrape_addresses_from_websites.py
│   │   ├── 05_enrich_with_ratings.py
│   │   ├── 06_export_to_kmz.py
│   │   ├── 07_enrich_with_specialties.py
│   │   ├── test_scraper.py
│   │   └── test_simple.py
│   │
│   └── utils/                  # Utility scripts
│       ├── consolidate_results.py
│       ├── manage_cache.py
│       ├── parse_districts.py
│       └── populate_cache_from_csv.py
│
└── data/                        # All data files
    ├── building_tenants/
    │   ├── buildings/          # Building coordinate CSVs
    │   ├── tenants/             # Tenant data CSVs
    │   │   ├── lower_manhattan/
    │   │   ├── district9/
    │   │   └── district18/
    │   ├── exports/             # KMZ/KML exports
    │   ├── reports/             # Coverage reports
    │   └── progress/            # Progress JSON files
    │
    ├── pharmacies/
    │   ├── districts/           # District-specific pharmacy CSVs
    │   │   ├── district_01_pharmacies.csv
    │   │   ├── district_02_pharmacies.csv
    │   │   └── ... (through district_55)
    │   ├── all_districts_pharmacies.csv
    │   ├── area9_pharmacies.csv
    │   └── exports/             # KMZ/KML exports
    │
    ├── census/
    │   ├── boundaries/          # TIGER/Line shapefiles
    │   └── exports/             # Income map KMZ files
    │
    ├── law_offices/             # Law office data
    │   ├── queens_brooklyn_law_offices.csv
    │   ├── queens_brooklyn_law_offices_with_addresses.csv
    │   ├── queens_brooklyn_law_offices_with_addresses_llm.csv
    │   ├── queens_brooklyn_law_offices_final.csv
    │   ├── queens_brooklyn_law_offices.kmz
    │   └── scraping_progress.json
    │
    └── medical_offices/          # Medical office data
        ├── queens_brooklyn_doctors.csv
        ├── queens_brooklyn_doctors_with_addresses.csv
        ├── queens_brooklyn_doctors_with_addresses_llm.csv
        ├── queens_brooklyn_doctors_with_specialties.csv
        ├── queens_brooklyn_doctors_final.csv
        ├── queens_brooklyn_doctors.kmz
        └── scraping_progress.json
```

---

## Quick Reference

### Most Common Workflows

#### Building Tenants (Lower Manhattan)
```bash
# 1. Get building coordinates
docker-compose run --rm scraper python scripts/building_tenants/01_scrape_office_buildings.py

# 2. Scrape tenant directories
docker-compose run --rm scraper python scripts/building_tenants/02_scrape_tenant_directories.py

# 3. Enrich contacts (optional)
docker-compose run --rm scraper python scripts/building_tenants/03_enrich_contacts.py

# 4. Export to KMZ
python3 scripts/building_tenants/04_export_to_kmz.py
```

#### Census Income Map
```bash
docker-compose run --rm scraper python scripts/census/export_income_to_kmz.py
```

#### Law Offices
```bash
docker-compose run --rm scraper python scripts/law_offices/01_scrape_law_offices_queens_brooklyn.py
docker-compose run --rm scraper python scripts/law_offices/03_enrich_with_addresses.py
docker-compose run --rm scraper python scripts/law_offices/07_enrich_with_practice_areas.py
```

#### Medical Offices
```bash
docker-compose run --rm scraper python scripts/medical_offices/01_scrape_doctors_queens_brooklyn.py
docker-compose run --rm scraper python scripts/medical_offices/03_enrich_with_addresses.py
docker-compose run --rm scraper python scripts/medical_offices/07_enrich_with_specialties.py
```

---

## File Naming Conventions

### CSV Files
- **Building coordinates:** `{location}_buildings.csv`
- **Tenant data:** `{building}_merchants.csv`, `{building}_lawyers.csv`, `{building}_building_contacts.csv`
- **District pharmacies:** `district_{NN}_pharmacies.csv`
- **Enriched data:** `{base_name}_with_{enrichment}.csv` or `{base_name}_final.csv`

### KMZ/KML Files
- **Exports:** `{name}.kmz` (compressed) and `{name}.kml` (uncompressed)
- **Location:** Always in `{category}/exports/` subdirectory

### Progress Files
- **Format:** `{name}_progress.json`
- **Location:** `{category}/progress/` or `{category}/` root

---

## Notes

- All CSV files use UTF-8 BOM encoding for Windows Excel compatibility
- KMZ files are optimized for Google My Maps import
- Progress files allow resuming interrupted scraping operations
- District pharmacy files are organized by district number (01-55)
- Building tenant data is organized by geographic district (9, 18, lower_manhattan)

---

**For detailed usage instructions, see [README.md](README.md)**

