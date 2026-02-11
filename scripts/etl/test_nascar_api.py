#!/usr/bin/env python3
"""Test NASCAR_API library."""
import subprocess
import sys
from pathlib import Path

HISTORICAL_DIR = Path(__file__).parent.parent / "data" / "historical"
HISTORICAL_DIR.mkdir(parents=True, exist_ok=True)

print("[23:41:35] === NASCAR_API Library Test ===")
print()

# Step 1: Install NASCAR_API
print("[23:41:35] Installing NASCAR_API from GitHub...")
result = subprocess.run(
    [sys.executable, "-m", "pip", "install", "git+https://github.com/rpersing/NASCAR_API.git"],
    capture_output=True,
    text=True,
    timeout=120
)

if result.returncode == 0:
    print("[23:41:36] NASCAR_API installed successfully")
else:
    print(f"[23:41:36] Install failed with code {result.returncode}")
    print(result.stderr)
    sys.exit(1)

# Step 2: Create and run test script
print()
print("[23:41:36] Creating test script...")

test_code = """
import sys
sys.path.insert(0, '')

try:
    from nascar_api import NASCAR_API
    print('NASCAR_API imported successfully')
    api = NASCAR_API()
    print('Fetching race schedule...')
    schedule = api.get_schedule(year=2025, series='cup')
    print(f'Races found: {len(schedule)}')
    for race in schedule[:3]:
        print(f'  - {race.get(\"track_name\", \"Unknown\")}: {race.get(\"race_name\", \"Unknown\")}')
except ImportError as e:
    print(f'Failed to import: {e}')
except Exception as e:
    print(f'Error: {e}')
"""

test_file = HISTORICAL_DIR / "test_api.py"
with open(test_file, 'w') as f:
    f.write(test_code)

print(f"[23:41:36] Created: {test_file.name}")

print()
print("[23:41:36] Running test script...")
result = subprocess.run(
    [sys.executable, str(test_file)],
    capture_output=True,
    text=True,
    timeout=60,
    cwd=str(HISTORICAL_DIR)
)

print()
print("[23:41:36] Test output:")
print(result.stdout)

if result.returncode != 0:
    print(f"[23:41:36] Test failed with code {result.returncode}")
    if result.stderr:
        print(result.stderr)
else:
    print("[23:41:36] Test completed successfully")
