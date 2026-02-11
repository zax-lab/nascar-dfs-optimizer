import argparse
import sys
import os

# Add apps/backend to path for imports
sys.path.append(os.path.join(os.getcwd(), "apps/backend"))
# Add project root for scripts
sys.path.append(os.getcwd())

def seed_historical():
    """Seed the database with historical race data."""
    try:
        from scripts.seed_historical_data import seed_database
        seed_database()
    except ImportError as e:
        print(f"Error: Could not import seeding script. {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error during seeding: {e}")
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
