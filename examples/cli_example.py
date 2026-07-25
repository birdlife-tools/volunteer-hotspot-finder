#!/usr/bin/env python3
"""CLI example: Find coverage gaps in eBird data.

Usage:
    1. Copy .env.example to .env and fill in your eBird API key
    2. Run: python cli_example.py RS          # Serbia
            python cli_example.py SE          # Sweden
            python cli_example.py US-NY       # New York
            python cli_example.py --lat 44.8 --lng 20.4  # Coordinates
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from birdlife_hotspot_finder import Config, HotspotFinder


async def main() -> None:
    parser = argparse.ArgumentParser(description="Find eBird coverage gaps")
    parser.add_argument("region", nargs="?", help="eBird region code (e.g., RS, HR)")
    parser.add_argument("--lat", type=float, help="Latitude")
    parser.add_argument("--lng", type=float, help="Longitude")
    parser.add_argument(
        "--radius", type=float, default=25, help="Search radius in km (default: 25)"
    )
    parser.add_argument(
        "--limit", type=int, default=10, help="Max results (default: 10)"
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(__file__).parent / ".env",
        help="Path to .env file",
    )

    args = parser.parse_args()

    if not args.region and not (args.lat and args.lng):
        parser.error("Provide either a region code or --lat and --lng")

    if not args.env_file.exists():
        print(f"Error: {args.env_file} not found", file=sys.stderr)
        print("Copy .env.example to .env and fill in your API key", file=sys.stderr)
        sys.exit(1)

    config = Config(_env_file=args.env_file)
    finder = HotspotFinder.from_config(config)

    try:
        if args.region:
            print(f"Finding coverage gaps in {args.region}...", file=sys.stderr)
            result = await finder.find_gaps(region=args.region, limit=args.limit)
        else:
            print(
                f"Finding coverage gaps near ({args.lat}, {args.lng})...",
                file=sys.stderr,
            )
            result = await finder.find_gaps(
                lat=args.lat,
                lng=args.lng,
                radius_km=args.radius,
                limit=args.limit,
            )

        # Output as JSON
        print(json.dumps(result.to_response_dict(), indent=2))

    finally:
        await finder.close()


if __name__ == "__main__":
    asyncio.run(main())
