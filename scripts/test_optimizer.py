#!/usr/bin/env python3
"""
Test NASCAR optimizer API with POST request.

This script sends a proper POST request to the optimizer endpoint
using our simulation data.
"""

import requests
import json
import sys
from pathlib import Path

# API URL
API_URL = "http://localhost:8000/api/v2/optimize/nascar"

# Load simulation results
sim_file = Path(__file__).parent / "output" / "sim_results.json"

print("🔄 Testing NASCAR Optimizer API")
print(f"   API URL: {API_URL}")
print()

# Load simulation data
if not sim_file.exists():
    print(f"❌ Simulation file not found: {sim_file}")
    sys.exit(1)

with open(sim_file, 'r') as f:
    projections = json.load(f)

print(f"✅ Loaded projections for {len(projections)} drivers")

# Build optimization request with ALL drivers so optimizer can choose
# This gives the optimizer flexibility to select 6 drivers within the salary cap
all_drivers = list(projections.items())

# Calculate total salary for all drivers
total_salary_all = sum([d[1].get('salary', 0) for d in all_drivers])

print(f"   Using all {len(all_drivers)} drivers for optimization")
print(f"   Total salary pool: ${total_salary_all}")

# Calculate expected points from simulation (weighted by finish position)
def calculate_expected_points_from_sim(sim_data):
    """Calculate expected points from finish position distribution."""
    FINISH_POINTS = {
        1: 46, 2: 40, 3: 35, 4: 31, 5: 28, 6: 25, 7: 22, 8: 20, 9: 18, 10: 17,
        11: 15, 12: 15, 13: 15, 14: 15, 15: 15, 16: 12, 17: 12, 18: 12, 19: 12, 20: 12,
        21: 10, 22: 10, 23: 10, 24: 10, 25: 10, 26: 8, 27: 8, 28: 8, 29: 8, 30: 8,
        31: 6, 32: 6, 33: 6, 34: 6, 35: 6, 36: 6, 37: 3, 38: 3, 39: 3, 40: 3, 41: 3, 42: 3, 43: 3
    }

    expected_points = 0.0
    distribution = sim_data.get('distribution', {})
    for pos_str, prob in distribution.items():
        pos = int(pos_str)
        if pos <= 43:
            expected_points += prob * FINISH_POINTS.get(pos, 0)

    return expected_points

# Build request body
request_body = {
    "salary_cap": 50000,
    "n_drivers": 6,
    "drivers": [
        {
            "driver_id": int(driver_id),
            "name": data['name'],
            "team": data.get('team', 'Unknown'),
            "car_number": int(driver_id),  # Simplified
            "salary": int(data.get('salary', 0)),
            "avg_finish": data.get('avg_finish'),
            "wins": data.get('wins', 0),
            "top5": data.get('top5', 0),
            "top10": data.get('top10', 0),
            "projected_points": calculate_expected_points_from_sim(data),  # Add expected points
            "beliefs": []
        }
        for driver_id, data in all_drivers
    ],
    "objective": "maximize_points",
    "lineup_count": 1
}

print(f"\n📤 Sending POST request...")
print(f"   Request: {json.dumps(request_body, indent=2)}")

try:
    response = requests.post(
        API_URL,
        json=request_body,
        headers={"Content-Type": "application/json"},
        timeout=30
    )
    
    print(f"\n✅ Response status: {response.status_code}")
    print(f"   Response time: {response.elapsed.total_seconds():.2f}s")
    
    if response.status_code == 200:
        result = response.json()
        print(f"   Lineup generated: {json.dumps(result, indent=2)}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"   Response: {response.text}")

except requests.exceptions.Timeout:
    print("❌ Request timed out")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
