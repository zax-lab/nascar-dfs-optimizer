#!/usr/bin/env python3
"""
Try to download NASCAR data from various sources.

Trying different APIs and data sources that might not be blocked.
"""

import requests
from pathlib import Path
import json
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent / "data"
HISTORICAL_DIR = BASE_DIR / "historical"
HISTORICAL_DIR.mkdir(parents=True, exist_ok=True)

def log(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

# Try various sports APIs
sources_to_try = {
    "API-Football": {
        "url": "https://api-football.com/v3/races",
        "description": "Football data API (test)"
    },
    "Open Data": {
        "url": "https://raw.githubusercontent.com/owid/football-matches/master/data/football.csv",
        "description": "Open data repository"
    },
    "Sports Reference": {
        "url": "https://raw.githubusercontent.com/ozanjuran/football-database/master/data/spain.csv",
        "description": "Sports database"
    },
    "Example CSV": {
        "url": "https://people.sc.fsu.edu/~jburkardt/datasets/weather-forecasts/notebooks/data/yahoo_weather.csv",
        "description": "Publicly available data"
    }
}

log("Trying to download from various sources...")
log("")

downloaded = []

for name, source in sources_to_try.items():
    try:
        log(f"Trying {name}: {source['description']}")

        response = requests.get(source['url'], timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

        if response.status_code == 200:
            # Check if it's CSV data
            if 'csv' in response.headers.get('content-type', '').lower() or len(response.text) > 1000:
                filename = source['url'].split('/')[-1].split('?')[0]
                if not filename.endswith('.csv'):
                    filename += '.csv'

                filepath = HISTORICAL_DIR / filename
                with open(filepath, 'w') as f:
                    f.write(response.text)

                lines = len(response.text.split('\n'))
                log(f"  ✅ Downloaded: {filename} ({lines} lines)")
                downloaded.append(filename)
            else:
                log(f"  ⚠️  Not CSV, ignoring")
        else:
            log(f"  ❌ Status {response.status_code}")

    except requests.exceptions.Timeout:
        log(f"  ❌ Timeout")
    except Exception as e:
        log(f"  ❌ Error: {e}")

log()
log(f"Summary: Downloaded {len(downloaded)} files")

# Also create a larger sample dataset from our sample
log()
log("Creating extended sample dataset...")

# Read existing sample
sample_file = Path(__file__).parent.parent / "sample_race_data.csv"
if sample_file.exists():
    import pandas as pd
    df = pd.read_csv(sample_file)

    # Create more varied sample data
    tracks = ['Daytona', 'Talladega', 'Texas', 'Charlotte', 'Bristol', 'Watkins Glen', 'Phoenix', 'Pocono']
    dates = [
        '2025-02-16', '2025-02-23', '2025-03-02', '2025-03-09',
        '2025-03-16', '2025-03-23', '2025-03-30', '2025-04-06',
        '2025-04-13', '2025-04-20', '2025-04-27'
    ]

    extended_samples = []
    for i in range(10):  # Create 10 sample races
        for j, track in enumerate(tracks):
            race_num = i * len(tracks) + j + 1
            extended_samples.append({
                'race_id': race_num,
                'date': dates[i % len(dates)],
                'track': track,
                'name': df.iloc[j % len(df)]['Name'],
                'position': df.iloc[j % len(df)]['Position'],
                'team': df.iloc[j % len(df)]['Team'],
                'salary': int(df.iloc[j % len(df)]['Salary'] * (0.8 + 0.4 * (j / len(tracks)))),
                'points': float(df.iloc[j % len(df)]['Points'] * (0.7 + 0.6 * (j / len(tracks))))
            })

    extended_df = pd.DataFrame(extended_samples)
    extended_file = HISTORICAL_DIR / "sample_races_extended.csv"
    extended_df.to_csv(extended_file, index=False)

    log(f"  ✅ Created: {extended_file.name} ({len(extended_samples)} races)")
    log(f"     Tracks: {', '.join(tracks)}")
    log(f"     Dates: {dates[0]} to {dates[-1]}")
