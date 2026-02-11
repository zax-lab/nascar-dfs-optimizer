#!/usr/bin/env python3
"""Fixed API test."""
import requests
import json
from pathlib import Path

# Load simulation data
sim_file = Path(__file__).parent / "output" / "sim_results.json"
with open(sim_file, 'r') as f:
    projections = json.load(f)

FINISH_POINTS = {
    1: 46, 2: 40, 3: 35, 4: 31, 5: 28, 6: 25, 7: 22, 8: 20, 9: 18, 10: 17,
    11: 15, 12: 15, 13: 15, 14: 15, 15: 15, 16: 12, 17: 12, 18: 12, 19: 12, 20: 12,
    21: 10, 22: 10, 23: 10, 24: 10, 25: 10, 26: 8, 27: 8, 28: 8, 29: 8, 30: 8,
    31: 6, 32: 6, 33: 6, 34: 6, 35: 6, 36: 6, 37: 3, 38: 3, 39: 3, 40: 3, 41: 3, 42: 3, 43: 3
}

def calc_exp_points(data):
    exp = 0.0
    for pos, prob in data.get('distribution', {}).items():
        exp += prob * FINISH_POINTS.get(int(pos), 0)
    return exp

# Use all drivers
all_drivers = list(projections.items())

# Build request - NOTE: field name is 'driver_data' not 'drivers'
request_body = {
    "salary_cap": 50000,
    "n_drivers": 6,
    "driver_data": [
        {
            "driver_id": int(did),
            "name": d['name'],
            "team": d.get('team', 'Unknown'),
            "car_number": int(did),
            "salary": int(d.get('salary', 0)),
            "avg_finish": d.get('avg_finish'),
            "wins": d.get('wins', 0),
            "top5": d.get('top5', 0),
            "top10": d.get('top10', 0),
            "projected_points": calc_exp_points(d),
            "beliefs": []
        }
        for did, d in all_drivers
    ],
    "objective": "maximize_points",
    "lineup_count": 1
}

print(f"Testing with all {len(all_drivers)} drivers...")

try:
    resp = requests.post(
        "http://localhost:8000/api/v2/optimize/nascar",
        json=request_body,
        timeout=30
    )
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        print("✅ SUCCESS!")
        print(json.dumps(resp.json(), indent=2))
    else:
        print(f"❌ Error: {resp.text}")
except Exception as e:
    print(f"❌ Exception: {e}")
    import traceback
    traceback.print_exc()
