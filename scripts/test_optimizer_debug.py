#!/usr/bin/env python3
"""
Test optimizer directly to debug the issue.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from app.lineup_optimizer import NASCAROptimizer
from app.models import SessionLocal

# Load simulation data
sim_file = Path(__file__).parent / "output" / "sim_results.json"

with open(sim_file, 'r') as f:
    import json
    projections = json.load(f)

print(f"Loaded {len(projections)} drivers")

# FINISH_POINTS
FINISH_POINTS = {
    1: 46, 2: 40, 3: 35, 4: 31, 5: 28, 6: 25, 7: 22, 8: 20, 9: 18, 10: 17,
    11: 15, 12: 15, 13: 15, 14: 15, 15: 15, 16: 12, 17: 12, 18: 12, 19: 12, 20: 12,
    21: 10, 22: 10, 23: 10, 24: 10, 25: 10, 26: 8, 27: 8, 28: 8, 29: 8, 30: 8,
    31: 6, 32: 6, 33: 6, 34: 6, 35: 6, 36: 6, 37: 3, 38: 3, 39: 3, 40: 3, 41: 3, 42: 3, 43: 3
}

def calculate_expected_points_from_sim(sim_data):
    """Calculate expected points from finish position distribution."""
    expected_points = 0.0
    distribution = sim_data.get('distribution', {})
    for pos_str, prob in distribution.items():
        pos = int(pos_str)
        if pos <= 43:
            expected_points += prob * FINISH_POINTS.get(pos, 0)
    return expected_points

# Prepare driver data
drivers = []
for driver_id, data in projections.items():
    drivers.append({
        "driver_id": int(driver_id),
        "name": data['name'],
        "team": data.get('team', 'Unknown'),
        "car_number": int(driver_id),
        "salary": int(data.get('salary', 0)),
        "avg_finish": data.get('avg_finish'),
        "wins": data.get('wins', 0),
        "top5": data.get('top5', 0),
        "top10": data.get('top10', 0),
        "projected_points": calculate_expected_points_from_sim(data),
        "beliefs": []
    })

print(f"Prepared {len(drivers)} drivers for optimization")

# Create optimizer
db = SessionLocal()
optimizer = NASCAROptimizer(
    db_session=db,
    salary_cap=50000,
    n_drivers=6,
    min_stack=2,
    max_stack=3
)

# Set drivers directly
optimizer.drivers = drivers

print(f"Optimizer drivers loaded: {len(optimizer.drivers)}")

# Try optimization
try:
    lineups = optimizer.optimize_lineup(race_id=0, n_lineups=1, objective="maximize_points")
    print(f"\n✅ Success! Generated {len(lineups)} lineups")
    for lineup in lineups:
        print(f"  Points: {lineup['total_projected_points']:.2f}, Salary: ${lineup['total_salary']}")
        for driver in lineup['drivers']:
            print(f"    - {driver['name']}: ${driver['salary']}")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
