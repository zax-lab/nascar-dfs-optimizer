#!/usr/bin/env python3
"""
Download NASCAR data using Sportradar US API.

Sportradar provides official NASCAR data including:
- Race results
- Driver statistics
- Track information
- Real-time race data

API Documentation: https://developer.sportradar.com/docs/read/racing/NASCAR_v3
"""

import requests
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent / "data"
HISTORICAL_DIR = BASE_DIR / "historical"
HISTORICAL_DIR.mkdir(parents=True, exist_ok=True)

BRAVE_API_KEY = "BSAekzKLM6e5-r4ZAYKbMfo3Ll7A7n9"

def log(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

# Try Sportradar API
SPORTRADAR_KEY = "YOUR_SPORTRADAR_API_KEY"  # Need to get this

def download_sportradar_data():
    """Download NASCAR data from Sportradar US API."""
    log("Attempting Sportradar US API...")
    log("API Documentation: https://developer.sportradar.com/docs/read/racing/NASCAR_v3")
    log()

    # Common NASCAR endpoints
    endpoints = {
        "race_schedule": "/racing/nascar/v3/series/cup/races",
        "race_results": "/racing/nascar/v3/series/cup/results",
        "driver_standings": "/racing/nascar/v3/series/cup/standings/drivers",
        "tracks": "/racing/nascar/v3/series/cup/tracks",
    }

    base_url = "https://api.sportradar.com/us"
    headers = {
        "apiKey": SPORTRADAR_KEY,
        "Accept": "application/json"
    }

    downloaded = []

    for endpoint_name, endpoint_path in endpoints.items():
        log(f"Trying {endpoint_name}: {endpoint_path}")

        try:
            response = requests.get(
                f"{base_url}{endpoint_path}",
                headers=headers,
                timeout=30,
                params={"season": "2025"}  # 2025 season
            )

            if response.status_code == 200:
                data = response.json()

                filename = HISTORICAL_DIR / f"sportradar_{endpoint_name}.json"
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)

                # Get basic info
                if isinstance(data, dict):
                    count = len(data.get('races', [])) if 'races' in data else 0
                elif isinstance(data, list):
                    count = len(data)
                else:
                    count = 0

                log(f"  ✅ Downloaded: {filename.name} ({count} items)")
                downloaded.append(filename.name)
            else:
                log(f"  ❌ Status: {response.status_code}")

        except requests.exceptions.RequestException as e:
            log(f"  ❌ Error: {e}")

    # Save summary
    summary = {
        "downloaded_at": datetime.now().isoformat(),
        "source": "sportradar_api",
        "files": downloaded,
        "count": len(downloaded),
        "status": "success" if downloaded else "failed"
    }

    summary_file = HISTORICAL_DIR / "sportradar_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    log()
    log(f"Summary: {len(downloaded)} files downloaded")
    log(f"Saved to: {summary_file.name}")
    log()

    if len(downloaded) == 0:
        log("NOTE: Sportradar API key required!")
        log("Get API key at: https://developer.sportradar.com/")
        log()
        log("Alternative: Use NASCAR_API Python library:")
        log("  https://github.com/rpersing/NASCAR_API")

def main():
    """Main function."""
    log("=== Sportradar NASCAR Data Download ===")
    log()

    download_sportradar_data()

    log()
    log("=== Complete ===")

if __name__ == "__main__":
    main()
