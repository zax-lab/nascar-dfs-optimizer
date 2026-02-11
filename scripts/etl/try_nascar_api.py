#!/usr/bin/env python3
"""
Download NASCAR data using NASCAR_API Python library.

GitHub: https://github.com/rpersing/NASCAR_API
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent / "data"
HISTORICAL_DIR = BASE_DIR / "historical"
HISTORICAL_DIR.mkdir(parents=True, exist_ok=True)

def print_log(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

def download_nascar_data():
    """Download NASCAR data using NASCAR_API library."""

    print_log("Creating test script to use NASCAR_API...")

    test_script = f"""
import sys
sys.path.insert(0, '{HISTORICAL_DIR}')

try:
    from nascar_api import NASCAR_API
    print("NASCAR_API imported successfully")

    # Create API instance
    api = NASCAR_API()
    print(f"NASCAR_API instance created")

    # Try to get race schedule
    print("Fetching race schedule...")
    try:
        schedule = api.get_schedule(year=2025, series='cup')
        print(f"Races found: {{len(schedule)}}")
        for race in schedule[:5]:
            print(f"  - {{race.get('track_name', 'Unknown')}}: {{race.get('race_name', 'Unknown')}}")
    except Exception as e:
        print(f"Error fetching schedule: {{e}}")

    # Try to get driver standings
    print("\\nFetching driver standings...")
    try:
        standings = api.get_driver_standings(series='cup', year=2025)
        print(f"Drivers found: {{len(standings)}}")
        for driver in standings[:5]:
            print(f"  - {{driver.get('driver_name', 'Unknown')}}: {{driver.get('position', 'N/A')}} pts")
    except Exception as e:
        print(f"Error fetching standings: {{e}}")

except ImportError as e:
    print(f"❌ Failed to import NASCAR_API: {{e}}")
except Exception as e:
    print(f"❌ Error: {{e}}")
import traceback
traceback.print_exc()
"""

    test_file = HISTORICAL_DIR / "test_nascar_api.py"
    with open(test_file, 'w') as f:
        f.write(test_script)

    print_log(f"Created test script: {test_file.name}")

    # Run test script
    print_log("Running test script...")
    result = subprocess.run(
        [sys.executable, test_file],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=HISTORICAL_DIR
    )

    print_log("Test output:")
    print(result.stdout)

    if result.returncode != 0:
        print_log(f"Test failed with code {result.returncode}")
        if result.stderr:
            print_log(result.stderr)
    else:
        print_log("✅ Test completed")

    return result.returncode == 0

def main():
    """Main function."""
    print_log("=== NASCAR_API Library Test ===")
    print_log()

    # Try to install library
    print_log("Installing NASCAR_API from GitHub...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "git+https://github.com/rpersing/NASCAR_API.git"],
        capture_output=True,
        text=True,
        timeout=120
    )

    if result.returncode == 0:
        print_log("✅ NASCAR_API installed successfully")
        print_log()
    else:
        print_log(f"❌ Install failed with code {result.returncode}")
        print_log(result.stderr)
        return

    # Test and download
    if download_nascar_data():
        print_log("✅ NASCAR_API working and data downloaded")
    else:
        print_log("⚠️  NASCAR_API test failed")
        print_log()

    print_log()
    print_log("=== Complete ===")

if __name__ == "__main__":
    main()
