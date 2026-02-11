#!/usr/bin/env python3
"""
Download historical NASCAR data from various sources.

This script attempts to fetch data from:
1. nascaR.data (R package) - Historical race results
2. Lap Raptor - Loop data and driver profiles
3. SportsDataIO - DFS salaries
4. OddsMatrix - Betting odds

Data will be saved to data/historical/
"""

import os
import requests
from pathlib import Path
import json
from datetime import datetime, timedelta

# Configuration
BASE_DIR = Path(__file__).parent.parent / "data"
HISTORICAL_DIR = BASE_DIR / "historical"

# Ensure directories exist
HISTORICAL_DIR.mkdir(parents=True, exist_ok=True)

def log(message):
    """Log with timestamp."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

def download_nascar_data():
    """
    Attempt to download historical NASCAR data from public sources.

    The nascaR.data R package maintains historical NASCAR race results
    from 1949-2024 including finish positions, tracks, race dates.
    """
    log("Attempting to download historical NASCAR data...")

    # nascaR.data provides data via GitHub
    sources = {
        "nascar_data": {
            "url": "https://raw.githubusercontent.com/jthoriasmussen/nascar_data/master/data/race_results.csv",
            "filename": "race_results.csv",
            "description": "Historical race results (1949-2024)"
        },
        "nascar_schedule": {
            "url": "https://raw.githubusercontent.com/jthoriasmussen/nascar_data/master/data/race_schedule.csv",
            "filename": "race_schedule.csv",
            "description": "Race schedule and track information"
        },
        "nascar_tracks": {
            "url": "https://raw.githubusercontent.com/jthorasmussen/nascar_data/master/data/tracks.csv",
            "filename": "tracks.csv",
            "description": "Track characteristics and configurations"
        }
    }

    downloaded = []

    for name, source in sources.items():
        try:
            log(f"Downloading {name}: {source['description']}")
            response = requests.get(source['url'], timeout=30)
            response.raise_for_status()

            filepath = HISTORICAL_DIR / source['filename']
            with open(filepath, 'w') as f:
                f.write(response.text)

            lines = len(response.text.split('\n'))
            log(f"  ✅ Saved to {filepath.name} ({lines} lines)")
            downloaded.append(source['filename'])

        except requests.exceptions.Timeout:
            log(f"  ❌ Timeout downloading {name}")
        except requests.exceptions.RequestException as e:
            log(f"  ❌ Failed to download {name}: {e}")

    # Download summary
    summary_file = HISTORICAL_DIR / "download_summary.json"
    summary = {
        "downloaded_at": datetime.now().isoformat(),
        "files": downloaded,
        "count": len(downloaded),
        "source": "nascar_data (GitHub - jthoriasmussen)"
    }

    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    log(f"\nSummary: Downloaded {len(downloaded)} files")
    log(f"Saved summary to {summary_file}")

    return downloaded

def download_lap_raptor_sample():
    """
    Note: Lap Raptor requires manual download from lapraptor.com
    This creates a placeholder with instructions.
    """
    log("\nLap Raptor data requires manual download:")
    log("1. Visit https://lapraptor.com")
    log("2. Navigate to Data / Loop Data")
    log("3. Select races of interest")
    log("4. Download CSV files")
    log(f"5. Save to: {HISTORICAL_DIR}")

    # Create placeholder with instructions
    placeholder = HISTORICAL_DIR / "lap_raptor_README.txt"
    with open(placeholder, 'w') as f:
        f.write(f"""LAP RAPTOR DATA INSTRUCTIONS
=============================

Source: https://lapraptor.com

Required Data:
- Loop data (lap-by-lap positions)
- Driver profiles
- Track characteristics

Steps:
1. Create account at lapraptor.com
2. Navigate to Data section
3. Select Loop Data tab
4. Filter by track/season/race
5. Export as CSV
6. Save to: {HISTORICAL_DIR}

Example filename: daytona_2025_race_loops.csv
""")

    log(f"Created instructions file: {placeholder.name}")

def download_driver_averages():
    """
    Create sample driver average data based on historical results.
    """
    log("\nCreating driver average statistics...")

    # This will be populated after we have historical data
    # Placeholder for now
    return None

def main():
    """Main download function."""
    log("=== NASCAR Data Download ===")
    log(f"Output directory: {HISTORICAL_DIR}")
    log("")

    # Download historical data from GitHub
    downloaded = download_nascar_data()

    # Create Lap Raptor instructions
    download_lap_raptor_sample()

    log("\n=== Download Complete ===")
    log(f"Files downloaded to: {HISTORICAL_DIR}")

if __name__ == "__main__":
    main()
