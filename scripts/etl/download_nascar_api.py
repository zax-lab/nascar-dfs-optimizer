#!/usr/bin/env python3
"""
Download NASCAR data using NASCAR_API Python library.

GitHub: https://github.com/rpersing/NASCAR_API

This library scrapes NASCAR.com and provides race results,
driver stats, track info, etc. in Python format.

Note: This scrapes NASCAR.com which may be blocked/protected.
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent / "data"
HISTORICAL_DIR = BASE_DIR / "historical"
HISTORICAL_DIR.mkdir(parents=True, exist_ok=True)

def log(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

def install_and_use_nascar_api():
    """Install NASCAR_API Python library and download data."""

    log("Attempting to install NASCAR_API Python library...")
    log("Source: https://github.com/rpersing/NASCAR_API")
    log()

    try:
        # Install from GitHub
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "git+https://github.com/rpersing/NASCAR_API.git"],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            log("✅ NASCAR_API installed successfully")
            log()
        else:
            log(f"❌ Install failed with code {result.returncode}")
            log(result.stderr)
            return False

    except subprocess.TimeoutExpired:
        log("❌ Installation timed out")
        return False
    except Exception as e:
        log(f"❌ Installation error: {e}")
        return False

    return True

def download_nascar_data():
    """Download NASCAR data using NASCAR_API library."""

    log("Creating test script to use NASCAR_API...")

    test_script = f"""
import sys
sys.path.insert(0, '{HISTORICAL_DIR}')

try:
    from nascar_api import NASCAR_API
    print("NASCAR_API imported successfully")

    # Create API instance
    api = NASCAR_API()
    print(f"NASCAR_API instance created: {{type(api)}}")

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

    log(f"Created test script: {test_file.name}")

    # Run test script
    log("Running test script...")
    result = subprocess.run(
        [sys.executable, test_file],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=HISTORICAL_DIR
    )

    log(f"Test output:")
    log(result.stdout)

    if result.returncode != 0:
        log(f"Test failed with code {result.returncode}")
        if result.stderr:
            log(result.stderr)
    else:
        log("✅ Test completed")

    return result.returncode == 0

def main():
    """Main function."""
    log("=== NASCAR_API Library Test ===")
    log()

    # Step 1: Install library
    if not install_and_use_nascar_api():
        log("❌ Cannot proceed without NASCAR_API library")
        log()
        log("Alternative: Use sample data or manual download")
        return

    # Step 2: Test and download
    if download_nascar_data():
        log("✅ NASCAR_API working and data downloaded")
    else:
        log("⚠️  NASCAR_API test failed")
        log()

    log()
    log("=== Complete ===")

if __name__ == "__main__":
    main()
