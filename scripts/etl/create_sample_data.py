#!/usr/bin/env python3
"""
Download sample NASCAR data and create extended dataset.
"""

import requests
from pathlib import Path
import json
from datetime import datetime
import pandas as pd

BASE_DIR = Path(__file__).parent.parent / "data"
HISTORICAL_DIR = BASE_DIR / "historical"
HISTORICAL_DIR.mkdir(parents=True, exist_ok=True)

def print_log(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

print_log("Creating extended sample dataset...")

# Read existing sample
sample_file = Path(__file__).parent.parent.parent / "sample_race_data.csv"
if sample_file.exists():
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
            salary_factor = 0.8 + 0.4 * (j / len(tracks))
            points_factor = 0.7 + 0.6 * (j / len(tracks))
            extended_samples.append({
                'race_id': race_num,
                'date': dates[i % len(dates)],
                'track': track,
                'name': df.iloc[j % len(df)]['Name'],
                'position': df.iloc[j % len(df)]['Position'],
                'team': df.iloc[j % len(df)]['Team'],
                'salary': int(df.iloc[j % len(df)]['Salary'] * salary_factor),
                'points': float(df.iloc[j % len(df)]['Points'] * points_factor)
            })

    extended_df = pd.DataFrame(extended_samples)
    extended_file = HISTORICAL_DIR / "sample_races_extended.csv"
    extended_df.to_csv(extended_file, index=False)

    print_log(f"Created: {extended_file.name}")
    print_log(f"  Races: {len(extended_samples)}")
    print_log(f"  Tracks: {', '.join(tracks)}")
    print_log(f"  Dates: {dates[0]} to {dates[-1]}")
    print_log()
    print_log("=== Complete ===")
else:
    print_log(f"Sample file not found: {sample_file}")
