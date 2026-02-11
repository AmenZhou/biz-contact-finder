# Generate EDDM Routes KMZ

Generate KMZ files from USPS EDDM carrier routes for Google My Maps.

## Usage
```
/generate-eddm-kmz <mode> <argument>
```

## Modes

### Single ZIP code
Fetch all carrier routes for a ZIP code:
```
/generate-eddm-kmz zip 10001
```

### Targeted routes from CSV
Fetch specific ZIP/CRID pairs from a CSV file:
```
/generate-eddm-kmz csv data/eddm/target_routes.csv
```

The CSV must have `ZIP` and `CRID` columns:
```csv
ZIP,CRID
12302,C008
12309,C026
```

## Instructions

When this command is invoked:

1. Parse the mode and argument from `$ARGUMENTS`
2. If mode is `zip`:
   - Run: `venv/bin/python scripts/eddm/generate_eddm_routes_kmz.py <zipcode>`
   - Output goes to `data/eddm/<zipcode>_eddm_routes.kmz`
3. If mode is `csv`:
   - Run: `venv/bin/python scripts/eddm/generate_targeted_routes_kmz.py <csv_path>`
   - Output goes to `data/eddm/targeted_eddm_routes.kmz`
   - Each route is a flat top-level item (no folder nesting) for per-route control in Google My Maps
4. Report the results: number of routes found, any missing routes, output file path
5. Remind the user to import the KMZ into Google My Maps

## Color Legend (by residential count)
- Red (thin): < 250 residences
- Orange: 250 - 500 residences
- Yellow: 500 - 750 residences
- Green: 750 - 1,000 residences
- Blue (thick): 1,000+ residences

## API Details
- Endpoint: `https://gis.usps.com/arcgis/rest/services/EDDM/selectZIP/GPServer/routes/execute`
- Each route popup shows: Route ID, residential/business/total counts, median income, median age, avg household size, post office facility

## Scripts
- `scripts/eddm/generate_eddm_routes_kmz.py` — single ZIP mode
- `scripts/eddm/generate_targeted_routes_kmz.py` — CSV batch mode with targeted ZIP/CRID pairs
