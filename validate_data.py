import pandas as pd
import os
import sys
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

# Add project root to path for imports
sys.path.append(os.getcwd())

from apps.backend.app.models import Driver, Race, Belief, Proposition, Base

def validate_csv(file_path):
    print(f"\n--- Validating CSV: {file_path} ---")
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    try:
        df = pd.read_csv(file_path)
        print(f"Rows: {len(df)}")
        print(f"Columns: {list(df.columns)}")

        # Completeness
        missing = df.isnull().sum()
        if missing.sum() > 0:
            print("\n[WARN] Missing Values Detected:")
            print(missing[missing > 0])
        else:
            print("\n[PASS] No missing values found.")

        # Uniqueness
        if df['Name'].is_unique:
            print("[PASS] Driver names are unique.")
        else:
            print(f"[FAIL] Duplicate drivers found: {df[df['Name'].duplicated()]['Name'].tolist()}")

        # Ranges
        if 'Position' in df.columns:
            invalid_pos = df[(df['Position'] < 1) | (df['Position'] > 40)]
            if not invalid_pos.empty:
                 print(f"[FAIL] Invalid positions found (must be 1-40): {invalid_pos['Position'].tolist()}")
            else:
                 print("[PASS] Positions are within valid range (1-40).")

        if 'Salary' in df.columns:
            min_sal = df['Salary'].min()
            max_sal = df['Salary'].max()
            print(f"Salary Range: {min_sal} - {max_sal}")
            if min_sal < 2000: # DraftKings min usually around here
                 print("[WARN] Extremely low salaries detected.")

    except Exception as e:
        print(f"[ERROR] Could not read CSV: {e}")

def validate_db(db_path):
    print(f"\n--- Validating Database: {db_path} ---")
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        print("Recommendation: Run 'python scripts/seed_historical_data.py' to seed synthetic data.")
        return

    try:
        engine = create_engine(f"sqlite:///{db_path}")
        Session = sessionmaker(bind=engine)
        session = Session()

        driver_count = session.query(Driver).count()
        race_count = session.query(Race).count()
        belief_count = session.query(Belief).count()
        prop_count = session.query(Proposition).count()

        print(f"Drivers: {driver_count}")
        print(f"Races: {race_count}")
        print(f"Propositions: {prop_count}")
        print(f"Beliefs: {belief_count}")

        if driver_count == 0:
            print("[WARN] Database has no drivers.")
        if race_count == 0:
            print("[WARN] Database has no races.")
            
        # Check for real vs synthetic
        # Heuristic: Check for exact 1.0 confidence beliefs (synthetic "Facts") vs < 1.0
        synthetic_facts = session.query(Belief).filter(Belief.confidence == 1.0).count()
        print(f"Deterministic Beliefs (Confidence=1.0): {synthetic_facts}")
        
        session.close()

    except Exception as e:
        print(f"[ERROR] Database validation failed: {e}")

if __name__ == "__main__":
    validate_csv("sample_race_data.csv")
    validate_db("epistemic.db")
