# Interactive KMZ Map - Implementation Plan

## Goal
Create an interactive KMZ file where users can click building locations on Google Maps and view all tenant data in rich popups.

---

## Overview

### What Users Will See:
1. **Map with 324 building markers** (color-coded by tenant count)
2. **Click any marker** → Opens detailed popup
3. **Popup shows**:
   - Building name & address
   - Complete tenant list with contact info
   - Clickable website links
   - Email addresses & phone numbers
   - Law firms (if any)
   - Building management contacts

---

## Implementation Details

### Script to Create: `scripts/export_tenants_to_kmz.py`

### Input Data Sources:
- `data/{building}_merchants.csv` - Tenant businesses
- `data/{building}_lawyers.csv` - Lawyer details from law firms
- `data/{building}_building_contacts.csv` - Property management
- `data/lower_manhattan_office_buildings.csv` - Building coordinates

### Data Processing Flow:

```
1. Load building master list (324 buildings)
   ↓
2. For each building:
   - Read merchants CSV → Get all tenants
   - Read lawyers CSV → Get law firm attorneys
   - Read contacts CSV → Get building management
   ↓
3. Aggregate by building address:
   - Combine all tenant data
   - Count total tenants
   - Format for display
   ↓
4. Generate KML:
   - Create placemark for each building
   - Add coordinates (lat/long)
   - Create HTML popup with formatted data
   - Apply color-coded style
   ↓
5. Package as KMZ:
   - Zip KML file
   - Save as .kmz
```

---

## KML Structure

### Document Hierarchy:
```xml
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Lower Manhattan Office Building Tenants</name>
    <description>324 buildings with tenant directories</description>

    <!-- Styles Section -->
    <Style id="high-density">    <!-- 20+ tenants - Green marker -->
    <Style id="medium-density">  <!-- 10-19 tenants - Yellow marker -->
    <Style id="low-density">     <!-- 5-9 tenants - Orange marker -->
    <Style id="minimal-data">    <!-- <5 tenants - Gray marker -->

    <!-- Buildings Section -->
    <Placemark>
      <name>28 Liberty Street</name>
      <description>
        <![CDATA[
          <!-- Rich HTML content here -->
        ]]>
      </description>
      <styleUrl>#high-density</styleUrl>
      <Point>
        <coordinates>-74.0089818,40.7078496,0</coordinates>
      </Point>
    </Placemark>

    <!-- Repeat for all 324 buildings -->
  </Document>
</kml>
```

---

## Popup HTML Template

### Structure:
```html
<div style="font-family: Arial; max-width: 400px;">

  <!-- Header -->
  <h3 style="color: #1a73e8; margin: 0;">
    🏢 [BUILDING NAME]
  </h3>
  <p style="color: #666; margin: 5px 0;">
    📍 [FULL ADDRESS]
  </p>
  <hr style="border: 1px solid #ddd;">

  <!-- Summary Stats -->
  <p><b>Total Tenants:</b> [COUNT]</p>
  <p><b>Building Levels:</b> [FLOORS]</p>

  <!-- Tenants Section -->
  <h4 style="color: #333; border-bottom: 2px solid #1a73e8; padding-bottom: 5px;">
    📋 Tenants ([COUNT])
  </h4>

  <div style="margin-left: 10px;">
    <!-- For each tenant -->
    <div style="margin-bottom: 15px; padding: 8px; background: #f8f9fa; border-radius: 4px;">
      <p style="margin: 2px 0;"><b>[TENANT NAME]</b></p>
      <p style="margin: 2px 0; font-size: 0.9em;">
        🌐 <a href="[WEBSITE]" target="_blank">Visit Website</a>
      </p>
      <p style="margin: 2px 0; font-size: 0.9em;">
        📧 [EMAIL]
      </p>
      <p style="margin: 2px 0; font-size: 0.9em;">
        📞 [PHONE]
      </p>
      <p style="margin: 2px 0; font-size: 0.9em; color: #666;">
        👤 [CONTACT PERSON] - [TITLE]
      </p>
    </div>
  </div>

  <!-- Law Firms Section (if applicable) -->
  <h4 style="color: #333; border-bottom: 2px solid #d32f2f; padding-bottom: 5px;">
    ⚖️ Law Firms ([COUNT])
  </h4>

  <div style="margin-left: 10px;">
    <!-- For each law firm -->
    <div style="margin-bottom: 10px;">
      <p style="margin: 2px 0;"><b>[FIRM NAME]</b></p>
      <ul style="margin: 5px 0; padding-left: 20px; font-size: 0.9em;">
        <li>[LAWYER NAME] - [TITLE]</li>
        <li>📧 [EMAIL] | 📞 [PHONE]</li>
      </ul>
    </div>
  </div>

  <!-- Building Management Section -->
  <h4 style="color: #333; border-bottom: 2px solid #f9a825; padding-bottom: 5px;">
    🏗️ Building Management
  </h4>

  <div style="margin-left: 10px;">
    <p style="margin: 2px 0;"><b>[COMPANY NAME]</b></p>
    <p style="margin: 2px 0; font-size: 0.9em;">
      👤 [CONTACT NAME] - [TITLE]
    </p>
    <p style="margin: 2px 0; font-size: 0.9em;">
      📧 [EMAIL] | 📞 [PHONE]
    </p>
    <p style="margin: 2px 0; font-size: 0.9em;">
      🌐 <a href="[WEBSITE]" target="_blank">Website</a>
    </p>
  </div>

  <!-- Footer -->
  <hr style="border: 1px solid #ddd; margin-top: 15px;">
  <p style="font-size: 0.8em; color: #999; text-align: center;">
    Data scraped: [DATE]<br>
    Quality Score: [SCORE]/100
  </p>
</div>
```

---

## Marker Color Coding

### Tenant Density Thresholds:

| Tenant Count | Color  | Style ID         | Icon                                    |
|--------------|--------|------------------|-----------------------------------------|
| 20+          | 🟢 Green | `high-density`   | `paddle/grn-circle.png`                 |
| 10-19        | 🟡 Yellow | `medium-density` | `paddle/ylw-circle.png`                 |
| 5-9          | 🟠 Orange | `low-density`    | `paddle/orange-circle.png`              |
| <5           | ⚪ Gray   | `minimal-data`   | `paddle/wht-circle.png`                 |

### Google Maps Icon URLs:
```
http://maps.google.com/mapfiles/kml/paddle/grn-circle.png
http://maps.google.com/mapfiles/kml/paddle/ylw-circle.png
http://maps.google.com/mapfiles/kml/paddle/orange-circle.png
http://maps.google.com/mapfiles/kml/paddle/wht-circle.png
```

---

## Script Implementation (`export_tenants_to_kmz.py`)

### Core Functions:

```python
def load_building_data() -> List[Dict]:
    """Load all building coordinates from CSV"""

def load_tenant_data(building_address: str) -> Dict:
    """
    Load all tenant data for a building:
    - merchants.csv
    - lawyers.csv
    - building_contacts.csv

    Returns aggregated data dictionary
    """

def create_html_popup(building: Dict, tenants: Dict) -> str:
    """Generate HTML popup content"""

def determine_marker_style(tenant_count: int) -> str:
    """Return style ID based on tenant count"""

def create_kml_styles(doc: Element) -> None:
    """Create color-coded marker styles"""

def create_building_placemark(building: Dict, tenants: Dict) -> Element:
    """Create KML placemark for a building"""

def export_to_kmz(output_path: Path) -> None:
    """Main export function"""

def main():
    """
    1. Load buildings
    2. Load tenant data
    3. Create KML
    4. Package as KMZ
    5. Generate summary stats
    """
```

---

## Output Files

### Primary Output:
- `data/lower_manhattan_tenants.kmz` (Main file for distribution)
  - Size: ~500KB - 2MB
  - Contains: 324 building placemarks with full tenant data

### Debug/Reference:
- `data/lower_manhattan_tenants.kml` (Uncompressed KML)
  - For debugging and editing
  - Can be opened in text editor

### Statistics File:
- `data/kmz_export_summary.txt`
  ```
  KMZ Export Summary
  ==================
  Total Buildings: 324
  Total Tenants: 2,847
  Total Law Firms: 156
  Total Lawyers: 423

  Marker Distribution:
  - High Density (20+): 87 buildings
  - Medium (10-19): 124 buildings
  - Low (5-9): 89 buildings
  - Minimal (<5): 24 buildings

  File Size: 1.2 MB
  ```

---

## User Instructions

### How to Use the KMZ File:

**Option 1: Google My Maps (Recommended)**
1. Go to https://mymaps.google.com
2. Click "Create a New Map"
3. Click "Import"
4. Upload `lower_manhattan_tenants.kmz`
5. View and share the map

**Option 2: Google Earth**
1. Download Google Earth (desktop or web)
2. File → Open → Select KMZ file
3. Buildings appear in sidebar
4. Click to view details

**Option 3: Google Maps Mobile**
1. Email KMZ file to yourself
2. Open on mobile device
3. Tap KMZ attachment
4. Opens in Google Maps app

---

## Advanced Features (Future Enhancements)

### Phase 2 Possibilities:

1. **Search Functionality**
   - Add folder organization by:
     - District
     - Industry type
     - Tenant count tier

2. **Filtering**
   - Separate layers for:
     - Law firms only
     - Tech companies
     - Financial services
     - Real estate

3. **Rich Media**
   - Building photos
   - Street view links
   - Company logos

4. **Export Options**
   - CSV export from map
   - Printable reports
   - API for live updates

---

## Testing Checklist

Before finalizing KMZ:

- [ ] All 324 buildings have placemarks
- [ ] Coordinates are accurate (verify with known addresses)
- [ ] Popups render correctly in Google Maps
- [ ] Links are clickable and work
- [ ] Marker colors match tenant counts
- [ ] File size is under 5MB (Google My Maps limit)
- [ ] No broken HTML in popups
- [ ] Special characters are escaped
- [ ] KMZ imports successfully to Google My Maps
- [ ] Data is up-to-date (from latest scrape)

---

## Timeline

- **Implementation**: 30-60 minutes
- **Testing**: 15 minutes
- **Documentation**: 15 minutes
- **Total**: ~1.5 hours

---

## Success Metrics

- ✅ All scraped buildings appear on map
- ✅ >95% of buildings have clickable popups
- ✅ Tenant data is complete and formatted
- ✅ Users can easily navigate and explore
- ✅ File imports successfully to Google My Maps
- ✅ Performance: Map loads in <5 seconds

---

## Next Steps

1. Wait for Phase 1 scraping to complete (~324 buildings)
2. Run `export_tenants_to_kmz.py`
3. Test KMZ file in Google My Maps
4. Share with users
5. Gather feedback for improvements

---

**Created**: 2025-11-25
**Status**: Planning Phase
**Priority**: High
**Dependencies**: Phase 1 scraping must complete first
