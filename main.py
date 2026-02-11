import argparse
import sys
import os

# Add apps/backend to path for imports
sys.path.append(os.path.join(os.getcwd(), "apps/backend"))
# Add project root for scripts
sys.path.append(os.getcwd())

def seed_historical():
    """Seed the database with real historical race data."""
    try:
        from scripts.seed_real_data import seed_from_csv
        from apps.native_mac.persistence.database import DatabaseManager
        
        # Check if data file exists
        data_files = [
            'race-logs.csv',  # In project root
            'apps/native_mac/Resources/data/race-logs.csv',  # In app bundle
            'Resources/data/race-logs.csv',  # In .app bundle (frozen)
            'Resources/race-logs.csv',  # Also in .app root Resources
        ]
        
        csv_path = None
        for f in data_files:
            if os.path.exists(f):
                csv_path = f
                print(f"Found data file: {csv_path}")
                break
        
        if not csv_path:
            print("Error: race-logs.csv not found")
            print("Place race-logs.csv in project root or bundle it in Resources/data/")
            sys.exit(1)
        
        # Initialize database and seed
        db = DatabaseManager()
        seed_from_csv(csv_path, db)
        print("✓ Historical data seeding complete!")
        
    except ImportError as e:
        print(f"Error: Could not import seeding script. {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error during seeding: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="NASCAR DFS Optimizer CLI")
    parser.add_argument(
        "--seed-historical", 
        action="store_true", 
        help="Seed the database with historical race data to enable the 'Select Race' dropdown."
    )
    
    # Add other modes here if needed in the future
    
    args = parser.parse_args()
    
    if args.seed_historical:
        seed_historical()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
