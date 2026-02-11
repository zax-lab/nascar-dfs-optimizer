"""Seed database with real NASCAR historical data from race-logs.csv"""

import csv
import os
from pathlib import Path
from datetime import datetime

def seed_from_csv(csv_path: str, db_manager):
    """Import real NASCAR race data from CSV file.
    
    Args:
        csv_path: Path to race-logs.csv
        db_manager: DatabaseManager instance
    """
    print(f"Loading historical data from {csv_path}...")
    
    # Get connection
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        
        # Read CSV
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            
            # Counters
            drivers_added = set()
            races_added = set()
            results_added = 0
            
            # Track latest race per series
            latest_races = {}
            
            for row in reader:
                # Extract fields
                driver_name = row['driver_name']
                driver_id = row['driver_id']
                race_date_str = row['race_date']
                series = row['series']
                track_name = row['track_name']
                start_pos = int(row['start'])
                finish_pos = int(row['finish'])
                laps = int(row['laps'])
                rating = float(row['rating']) if row['rating'] else 50.0
                
                # Parse date
                race_date = datetime.strptime(race_date_str, '%Y/%m/%d')
                
                # Create unique race key
                race_key = f"{series}_{track_name}_{race_date_str}"
                
                # Insert race if not exists
                cursor.execute("""
                    INSERT OR IGNORE INTO races (name, track, date, laps, status, series)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    f"{series} at {track_name}",
                    track_name,
                    race_date_str,
                    laps,
                    'completed',
                    series
                ))
                
                races_added.add(race_key)
                
                # Get race_id
                cursor.execute("SELECT id FROM races WHERE name=? AND date=?", 
                             (f"{series} at {track_name}", race_date_str))
                race_id = cursor.fetchone()[0]
                
                # Insert driver if not exists
                cursor.execute("""
                    INSERT OR IGNORE INTO drivers (name, driver_id, team, salary, avg_finish)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    driver_name,
                    driver_id,
                    "Team {}".format(int(driver_id) % 10),  # Mock team from ID
                    int(5500 + rating * 100),  # Salary based on rating
                    finish_pos
                ))
                
                drivers_added.add(driver_id)
                
                # Get driver_id
                cursor.execute("SELECT id FROM drivers WHERE driver_id=?", (driver_id,))
                db_driver_id = cursor.fetchone()[0]
                
                # Insert race result
                cursor.execute("""
                    INSERT INTO race_results (race_id, driver_id, start_position, finish_position, laps, rating)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    race_id,
                    db_driver_id,
                    start_pos,
                    finish_pos,
                    laps,
                    rating
                ))
                
                results_added += 1

                # Track latest race per driver (store datetime for comparison)
                if driver_id not in latest_races or race_date > latest_races[driver_id][1]:
                    latest_races[driver_id] = (race_key, race_date)
            
            conn.commit()
            
            print(f"✓ Seeding complete:")
            print(f"  - Races: {len(races_added)}")
            print(f"  - Drivers: {len(drivers_added)}")
            print(f"  - Results: {results_added}")
            print(f"  - Data spans: 2019-2025")

if __name__ == "__main__":
    # For testing
    print("This script is called by the app on first launch.")
    print("Run: python3 main.py --seed-historical")
