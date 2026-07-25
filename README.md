# Volunteer Hotspot Finder

Find data gaps in eBird coverage and propose survey missions to volunteers.

## Status

🔨 **In Progress** — Foundation phase

## Problem

Birdwatchers typically visit popular, already well-surveyed locations. This creates massive "blind spots" — areas with low observation coverage despite high biodiversity potential.

## Solution

Grid-based analysis that identifies geographic cells with low eBird coverage, ranks them by priority, and outputs actionable survey recommendations.

## Installation

```bash
pip install birdlife-hotspot-finder
```

## Usage

```python
from birdlife_hotspot_finder import HotspotFinder

finder = HotspotFinder.from_env()  # Reads EBIRD_API_KEY
gaps = await finder.find_gaps(region="RS", limit=10)
```

## Output Formats

- JSON (API response envelope)
- CSV (spreadsheet import)
- GeoJSON (maps — Leaflet, QGIS)

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
    "gridSizeKm": "10"
  }
}
```

## Community

[![Matrix](https://img.shields.io/badge/Matrix-Chat-black?logo=matrix)](https://matrix.to/#/#volunteer-hotspot-finder:matrix.org)

## License

MIT — see [LICENSE](LICENSE)
