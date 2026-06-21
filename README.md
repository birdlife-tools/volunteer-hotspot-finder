# Volunteer Hotspot Finder

Algorithm that identifies data gaps and proposes survey missions to volunteers.

## Problem

Birdwatchers typically visit popular, already well-surveyed locations. This creates massive "blind spots" (data gaps) on maps — hundreds of kilometers of forests and mountains without a single entry for years.

## Solution

Algorithm that analyzes historical sighting data and identifies geographic cells with high ecological potential but lacking fresh data, then proposes them to volunteers as "missions."

## Technical Stack

- Uber H3 spatial index or UTM grid 10x10km
- Objective function (ratio of habitat diversity to number of entries in last N months)

## Status

🚧 Planning

## Community

Join the discussion:

[![Matrix](https://img.shields.io/badge/Matrix-%23volunteer-hotspot-finder-black?logo=matrix)](https://matrix.to/#/#volunteer-hotspot-finder:matrix.org)

## License

MIT — see [LICENSE](LICENSE)
