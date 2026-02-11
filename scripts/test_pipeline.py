#!/usr/bin/env python3
"""
Test full pipeline with sample data.

This script:
1. Generates projections (if not already done)
2. Submits optimization request to backend
3. Generates DraftKings export file
"""

import requests
import json
import sys
from pathlib import Path

# Backend API URL
API_URL = "http://localhost:8000/api/v2/optimize/nascar"

# DraftKings salary cap
SALARY_CAP = 50000
DRIVER_COUNT = 6

print("🔄 Testing Full Pipeline")
print(f"   API URL: {API_URL}")
print(f"   Salary Cap: ${SALARY_CAP}")
print(f"   Driver Count: {DRIVER_COUNT}")
print()

# Step 1: Get available drivers
print("Step 1: Fetching drivers...")
try:
    response = requests.get(f"{API_URL}/drivers", timeout=10)
    if response.status_code == 200:
        drivers = response.json()
        print(f"✅ Found {len(drivers)} drivers")
    else:
        print(f"❌ Error fetching drivers: {response.status_code}")
        sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

# Step 2: Build optimization request
print("\nStep 2: Building optimization request...")

# Select top drivers for sample lineup (by projected P1 probability)
# Using simulated data we already have
sim_file = Path(__file__).parent / "output/sim_results.json"
if sim_file.exists():
    with open(sim_file, 'r') as f:
        projections = json.load(f)
    
    # Sort by probability of P1 finish, get top 6 for lineup
    sorted_drivers = sorted(
        projections.items(),
        key=lambda x: x[1].get('prob_p1', 0),
        reverse=True
    )
    
    # Select top 6
    selected = sorted_drivers[:6]
    
    # Calculate total salary
    total_salary = sum([d[1].get('salary', 0) for d in selected])
    print(f"   Selected drivers: {[d[1]['name'] for d in selected]}")
    print(f"   Total salary: ${total_salary}")
    
    if total_salary > SALARY_CAP:
        print(f"⚠️  Warning: Over cap by ${total_salary - SALARY_CAP}")
        sys.exit(1)
    
    # Build request
    drivers_data = []
    for driver_id, data in selected:
        drivers_data.append({
            'driver_id': driver_id,
            'name': data['name'],
            'salary': int(data.get('salary', 0)),
            'team': data.get('team', 'Unknown'),
            'confidence': 0.5,  # Default confidence
        })
    
    request_body = {
        'salary_cap': SALARY_CAP,
        'driver_count': DRIVER_COUNT,
        'drivers': drivers_data
    }
    
    print(f"   Request body: {json.dumps(request_body, indent=2)}")
    
else:
    print("⚠️  Warning: sim_results.json not found")
    print("   Run: python3 scripts/run_simple_sim.py first")
    sys.exit(1)

# Step 3: Submit optimization request
print("\nStep 3: Submitting optimization request...")
try:
    response = requests.post(API_URL, json=request_body, timeout=30)
    print(f"   Status code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Optimization successful!")
        print(f"   Lineup generated: {result}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"   Response: {response.text}")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
