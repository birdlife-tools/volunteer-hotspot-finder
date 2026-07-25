# Examples

## Setup

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Get your eBird API key from https://ebird.org/api/keygen

3. Edit `.env` and add your API key:
   ```
   EBIRD_API_KEY=your-key-here
   ```

4. Install the package:
   ```bash
   pip install -e ..
   ```

## Jupyter Notebook

Open `notebook_example.ipynb` for an interactive walkthrough.

## CLI Example

Find coverage gaps in a region:

```bash
# Serbia
python cli_example.py RS

# Croatia  
python cli_example.py HR

# Near specific coordinates (25km radius)
python cli_example.py --lat 44.8 --lng 20.4

# Custom radius and limit
python cli_example.py RS --limit 20
python cli_example.py --lat 44.8 --lng 20.4 --radius 50 --limit 15
```

## Output

Returns JSON following the BirdLife API Response Convention:

```json
{
  "data": [
    {
      "locationID": "uuid-here",
      "slug": "grid-44-80n-20-40e",
      "name": "Grid cell 44.80N 20.40E",
      "geodeticDatum": "WGS84",
      "decimalLatitude": 44.8,
      "decimalLongitude": 20.4,
      "extensions": {
        "coverage.gapType": "spatial",
        "coverage.priorityScore": "0.9",
        "coverage.checklistCount": "0",
        "coverage.reasoning": "No eBird hotspots in this grid cell",
        "coverage.nearestHotspotName": "Košutnjak",
        "coverage.nearestHotspotDistanceKm": "8.5"
      }
    }
  ],
  "meta": {
    "resultType": "coverage-gaps",
    "queryTimestamp": "2026-07-25T12:00:00Z",
    "gridSizeKm": 10,
    "region": "RS"
  }
}
```

## Cache

By default, hotspot data is cached to `.cache/` as JSON files (30-day TTL).

Change cache settings in `.env`:

```bash
# Use SQLite (single file)
CACHE_TYPE=sqlite

# Use PostgreSQL (for API deployment)
CACHE_TYPE=postgres
POSTGRES_URL=postgresql://user:pass@localhost:5432/dbname

# Disable caching
CACHE_TYPE=none
```
