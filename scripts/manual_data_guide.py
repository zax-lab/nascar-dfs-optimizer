#!/usr/bin/env python3
"""
Manual data collection guide for NASCAR DFS project.

Since automated download sources are blocked/unavailable,
this script provides instructions for manual data collection.
"""

from pathlib import Path

BASE_DIR = Path(__file__).parent.parent / "data"
HISTORICAL_DIR = BASE_DIR / "historical"
HISTORICAL_DIR.mkdir(parents=True, exist_ok=True)

def print_guide():
    """Print manual data collection instructions."""

    print("=" * 70)
    print(" MANUAL DATA COLLECTION GUIDE")
    print("=" * 70)
    print()

    print("Option 1: Lap Raptor Data (Best Source)")
    print("-" * 70)
    print("Steps:")
    print("1. Visit https://lapraptor.com")
    print("2. Create free account")
    print("3. Navigate to Data → Loop Data")
    print("4. Select recent races (e.g., 2025 Daytona 500)")
    print("5. Download CSV files:")
    print("   - Loop data (lap-by-lap positions)")
    print("   - Driver profiles")
    print("6. Save to:", HISTORICAL_DIR)
    print()

    print("Option 2: DraftKings Salaries")
    print("-" * 70)
    print("Steps:")
    print("1. Visit https://frcs.pro/dfs/draftkings/")
    print("2. Find 'Season Driver Salary' section")
    print("3. Download CSV for current season")
    print("4. Save as:", HISTORICAL_DIR / "draftkings_salaries.csv")
    print()

    print("Option 3: NASCAR Historical Results")
    print("-" * 70)
    print("Sources:")
    print("1. https://www.nascarreference.com")
    print("2. https://www.driveraverages.com")
    print("3. https://www.racing-reference.info")
    print()
    print("Data to collect:")
    print("- Race results (driver, track, finish position, date)")
    print("- Track characteristics (length, banking, surface)")
    print("- Driver statistics (wins, top5, top10, avg finish)")
    print()

    print("Option 4: Use Sample Data for Development")
    print("-" * 70)
    print("Current sample data available:")
    sample_file = Path(__file__).parent.parent / "sample_race_data.csv"
    if sample_file.exists():
        print(f"   {sample_file}")
        print("   Contains: 40 drivers with salary, points, stats")
        print("   Format: CSV ready for import")
    else:
        print("   Not found")
    print()

    print("Data File Format Expected:")
    print("-" * 70)
    print("CSV columns needed for import:")
    print("- driver_id, name, team, car_number")
    print("- salary (DFS salary)")
    print("- points (fantasy points for race)")
    print("- avg_finish (historical average finish)")
    print("- wins, top5, top10 (career stats)")
    print("- track, race_date (for historical races)")
    print()

    print("After Collecting Data:")
    print("-" * 70)
    print("1. Save CSV files to:", HISTORICAL_DIR)
    print("2. Run import script:")
    print("   python3 scripts/etl/import_race_data.py")
    print("3. Re-run Monte Carlo simulator")
    print("   python3 scripts/track_aware_simulator.py")
    print("4. Test optimizer with new data")
    print("   python3 scripts/test_api_fixed.py")
    print()

    print("=" * 70)
    print("END OF GUIDE")
    print("=" * 70)

if __name__ == "__main__":
    print_guide()
