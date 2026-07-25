# Volunteer Hotspot Finder

[![PyPI](https://img.shields.io/pypi/v/birdlife-hotspot-finder)](https://pypi.org/project/birdlife-hotspot-finder/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Find data gaps in eBird coverage and propose survey missions to volunteers.

## Status

✅ **Released** — v0.1.1

## Problem

Birdwatchers typically visit popular, already well-surveyed locations. This creates massive "blind spots" — areas with low observation coverage despite high biodiversity potential.

## Solution

Grid-based analysis that identifies geographic cells with low eBird coverage, ranks them by priority, and outputs actionable survey recommendations.

## Installation

```bash
pip install birdlife-hotspot-finder
```

With PostgreSQL cache support:

```bash
pip install birdlife-hotspot-finder[postgres]
```

## Usage

```python
from birdlife_hotspot_finder import HotspotFinder

finder = HotspotFinder.from_env()  # Reads EBIRD_API_KEY

# Find gaps in any eBird region (country, state, county)
gaps = await finder.find_gaps(region="RS", limit=10)
gaps = await finder.find_gaps(region="US-NY", limit=10)
gaps = await finder.find_gaps(region="SE-BD", limit=10)  # Swedish county

# Find gaps near coordinates
gaps = await finder.find_gaps(lat=44.8, lng=20.4, radius_km=25, limit=10)

# Clean up
await finder.close()
```

## Output Formats

```python
from birdlife_hotspot_finder.serializers import JsonSerializer, CsvSerializer, GeoJsonSerializer

# JSON (API response envelope)
json_output = JsonSerializer().serialize(gaps)

# CSV (spreadsheet import)
csv_output = CsvSerializer().serialize(gaps)

# GeoJSON (maps — Leaflet, QGIS)
geojson_output = GeoJsonSerializer().serialize(gaps)
```

## API Response Convention

Follows [BirdLife API Response Convention](https://github.com/birdlife-tools/birdlife-schema):

```json
{
  "data": [
    {
      "locationID": "...",
      "name": "Grid cell 44.8N 20.4E",
      "decimalLatitude": 44.8,
      "decimalLongitude": 20.4,
      "extensions": {
        "coverage.checklistCount": "0",
        "coverage.gapType": "spatial",
        "coverage.priorityScore": "0.85"
      }
    }
  ],
  "meta": {
    "resultType": "coverage-gaps",
    "gridSizeKm": 10
  }
}
```

## Live API

Try it without installing: https://birdlife.tech/services/hotspots

## Community

[![Matrix](https://img.shields.io/badge/Matrix-Chat-black?logo=matrix)](https://matrix.to/#/#birdlife-tools:matrix.org)

## License

MIT — see [LICENSE](LICENSE)
