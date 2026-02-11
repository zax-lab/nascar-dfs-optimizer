import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from apps.backend.app.models import (
    Driver, Race, Proposition, Belief, Agent, SessionLocal, create_all_tables
)

# 2024 Season Schedule (Sample of key races)
RACES_2024 = [
    {"name": "Daytona 500", "track": "Daytona International Speedway", "type": "superspeedway", "date": "2024-02-19", "laps": 200},
    {"name": "Ambetter Health 400", "track": "Atlanta Motor Speedway", "type": "superspeedway", "date": "2024-02-25", "laps": 260},
    {"name": "Pennzoil 400", "track": "Las Vegas Motor Speedway", "type": "intermediate", "date": "2024-03-03", "laps": 267},
    {"name": "Shriners Children's 500", "track": "Phoenix Raceway", "type": "short_track", "date": "2024-03-10", "laps": 312},
    {"name": "Food City 500", "track": "Bristol Motor Speedway", "type": "short_track", "date": "2024-03-17", "laps": 500},
    {"name": "EchoPark Automotive Grand Prix", "track": "Circuit of the Americas", "type": "road_course", "date": "2024-03-24", "laps": 68},
    {"name": "Coca-Cola 600", "track": "Charlotte Motor Speedway", "type": "intermediate", "date": "2024-05-26", "laps": 400},
    {"name": "NASCAR Cup Series Championship", "track": "Phoenix Raceway", "type": "short_track", "date": "2024-11-10", "laps": 312},
]

# 2025 Season Schedule (Target for backtesting)
RACES_2025 = [
    {"name": "Daytona 500", "track": "Daytona International Speedway", "type": "superspeedway", "date": "2025-02-16", "laps": 200},
    {"name": "Ambetter Health 400", "track": "Atlanta Motor Speedway", "type": "superspeedway", "date": "2025-02-23", "laps": 260},
    {"name": "Pennzoil 400", "track": "Las Vegas Motor Speedway", "type": "intermediate", "date": "2025-03-02", "laps": 267},
]

# Driver Roster (2024-2025 key drivers)
DRIVERS = [
    {"name": "Ryan Blaney", "team": "Team Penske", "car": "12", "skill": 0.92, "aggression": 0.7},
    {"name": "Kyle Larson", "team": "Hendrick Motorsports", "car": "5", "skill": 0.98, "aggression": 0.9},
    {"name": "William Byron", "team": "Hendrick Motorsports", "car": "24", "skill": 0.95, "aggression": 0.6},
    {"name": "Christopher Bell", "team": "Joe Gibbs Racing", "car": "20", "skill": 0.93, "aggression": 0.7},
    {"name": "Denny Hamlin", "team": "Joe Gibbs Racing", "car": "11", "skill": 0.96, "aggression": 0.8},
    {"name": "Tyler Reddick", "team": "23XI Racing", "car": "45", "skill": 0.90, "aggression": 0.9},
    {"name": "Martin Truex Jr.", "team": "Joe Gibbs Racing", "car": "19", "skill": 0.91, "aggression": 0.5},
    {"name": "Chris Buescher", "team": "RFK Racing", "car": "17", "skill": 0.88, "aggression": 0.6},
    {"name": "Brad Keselowski", "team": "RFK Racing", "car": "6", "skill": 0.87, "aggression": 0.7},
    {"name": "Ross Chastain", "team": "Trackhouse Racing", "car": "1", "skill": 0.89, "aggression": 0.95},
    {"name": "Chase Elliott", "team": "Hendrick Motorsports", "car": "9", "skill": 0.94, "aggression": 0.6},
    {"name": "Joey Logano", "team": "Team Penske", "car": "22", "skill": 0.92, "aggression": 0.85},
    {"name": "Kyle Busch", "team": "Richard Childress Racing", "car": "8", "skill": 0.90, "aggression": 0.9},
    {"name": "Bubba Wallace", "team": "23XI Racing", "car": "23", "skill": 0.85, "aggression": 0.8},
    {"name": "Ty Gibbs", "team": "Joe Gibbs Racing", "car": "54", "skill": 0.86, "aggression": 0.75},
    {"name": "Alex Bowman", "team": "Hendrick Motorsports", "car": "48", "skill": 0.84, "aggression": 0.6},
    {"name": "Michael McDowell", "team": "Front Row Motorsports", "car": "34", "skill": 0.82, "aggression": 0.7},
    {"name": "Daniel Suarez", "team": "Trackhouse Racing", "car": "99", "skill": 0.81, "aggression": 0.8},
    {"name": "Chase Briscoe", "team": "Stewart-Haas Racing", "car": "14", "skill": 0.80, "aggression": 0.7},
    {"name": "Erik Jones", "team": "Legacy Motor Club", "car": "43", "skill": 0.79, "aggression": 0.7},
    {"name": "Austin Cindric", "team": "Team Penske", "car": "2", "skill": 0.78, "aggression": 0.6},
    {"name": "Ricky Stenhouse Jr.", "team": "JTG Daugherty Racing", "car": "47", "skill": 0.77, "aggression": 0.9},
    {"name": "Austin Dillon", "team": "Richard Childress Racing", "car": "3", "skill": 0.76, "aggression": 0.7},
    {"name": "Corey LaJoie", "team": "Spire Motorsports", "car": "7", "skill": 0.72, "aggression": 0.8},
    {"name": "Justin Haley", "team": "Rick Ware Racing", "car": "51", "skill": 0.71, "aggression": 0.6},
    {"name": "Todd Gilliland", "team": "Front Row Motorsports", "car": "38", "skill": 0.70, "aggression": 0.6},
    {"name": "Ryan Preece", "team": "Stewart-Haas Racing", "car": "41", "skill": 0.73, "aggression": 0.7},
    {"name": "Noah Gragson", "team": "Stewart-Haas Racing", "car": "10", "skill": 0.75, "aggression": 0.8},
    {"name": "Josh Berry", "team": "Stewart-Haas Racing", "car": "4", "skill": 0.74, "aggression": 0.6},
    {"name": "John Hunter Nemechek", "team": "Legacy Motor Club", "car": "42", "skill": 0.73, "aggression": 0.7},
    {"name": "Zane Smith", "team": "Spire Motorsports", "car": "71", "skill": 0.70, "aggression": 0.7},
    {"name": "Carson Hocevar", "team": "Spire Motorsports", "car": "77", "skill": 0.71, "aggression": 0.8},
    {"name": "Harrison Burton", "team": "Wood Brothers Racing", "car": "21", "skill": 0.68, "aggression": 0.5},
    {"name": "Daniel Hemric", "team": "Kaulig Racing", "car": "31", "skill": 0.69, "aggression": 0.6},
    {"name": "Kaz Grala", "team": "Rick Ware Racing", "car": "15", "skill": 0.65, "aggression": 0.6},
    {"name": "Shane van Gisbergen", "team": "Kaulig Racing", "car": "16", "skill": 0.95, "aggression": 0.8}, # Road Course Specialist
]

def simulate_race_result(driver, track_type):
    """Simulate a single race result based on skill and variance."""
    
    # Base performance
    perf = driver["skill"] * 100
    
    # Track type modifiers
    if track_type == "superspeedway":
        # High variance (drafting, crashes)
        variance = np.random.normal(0, 25) 
    elif track_type == "road_course":
        # Skill dominates, lower variance
        variance = np.random.normal(0, 10)
        if driver["name"] == "Shane van Gisbergen":
            perf += 20 # Specialist bonus
    else:
        # Standard variance
        variance = np.random.normal(0, 15)
        
    score = perf + variance
    return score

def seed_database():
    print("Initializing database...")
    create_all_tables()
    db = SessionLocal()

    try:
        # 1. Create Agents
        print("Creating agents...")
        projector_agent = Agent(name="Projector", type="projector", active=True)
        simulator_agent = Agent(name="Simulator", type="simulator", active=True)
        db.add(projector_agent)
        db.add(simulator_agent)
        db.commit()

        # 2. Create Drivers
        print("Seeding drivers...")
        driver_objs = []
        for d in DRIVERS:
            driver = Driver(
                name=d["name"],
                team=d["team"],
                car_number=int(d["car"]),
                salary=random.randint(5500, 11500), # Mock salary
                avg_finish=20.0, # Placeholder
                wins=0,
                top5=0,
                top10=0
            )
            db.add(driver)
            driver_objs.append((d, driver))
        db.commit()
        
        # Refresh to get IDs
        for _, d_obj in driver_objs:
            db.refresh(d_obj)

        # 3. Seed 2024 Historical Data (Training Data)
        print("Seeding 2024 historical races...")
        for race_info in RACES_2024:
            race = Race(
                name=race_info["name"],
                track=race_info["track"],
                date=datetime.strptime(race_info["date"], "%Y-%m-%d"),
                laps=race_info["laps"],
                status="completed"
            )
            db.add(race)
            db.commit()
            db.refresh(race)

            # Simulate results for this race
            results = []
            for d_dict, d_obj in driver_objs:
                score = simulate_race_result(d_dict, race_info["type"])
                results.append((d_obj, score))
            
            # Sort by score (descending) to determine finish position
            results.sort(key=lambda x: x[1], reverse=True)
            
            # Create beliefs/propositions for results (Training Data)
            for pos, (driver, score) in enumerate(results, 1):
                # Update driver stats
                driver.avg_finish = (driver.avg_finish + pos) / 2
                if pos == 1: driver.wins += 1
                if pos <= 5: driver.top5 += 1
                if pos <= 10: driver.top10 += 1

                # Create Result Proposition
                prop = Proposition(
                    content=f"{driver.name} finish {pos}",
                    driver_id=driver.id,
                    race_id=race.id,
                    session_type="race"
                )
                db.add(prop)
                db.commit()
                db.refresh(prop)

                # Create Belief (Fact)
                belief = Belief(
                    agent_id=projector_agent.id,
                    prop_id=prop.id,
                    confidence=1.0, # Fact
                    epistemic_var=0.0, # Fact has no variance
                    source="history"
                )
                db.add(belief)
        
        db.commit()
        print("2024 History seeded.")

        # 4. Seed 2025 Data (Test Set - Pre-race only)
        print("Seeding 2025 races (Pre-race data only)...")
        for race_info in RACES_2025:
            race = Race(
                name=race_info["name"],
                track=race_info["track"],
                date=datetime.strptime(race_info["date"], "%Y-%m-%d"),
                laps=race_info["laps"],
                status="scheduled" # Not completed yet
            )
            db.add(race)
            db.commit()
            db.refresh(race)

            # Simulate Qualifying/Practice (No Race Results yet)
            for d_dict, d_obj in driver_objs:
                # Simulate Qualifying
                qual_score = simulate_race_result(d_dict, race_info["type"])
                # Add some noise for qualifying vs race pace
                qual_score += np.random.normal(0, 5) 
                
                # We'll just store the "truth" for backtesting to compare against later
                # But typically we'd insert "Practice" beliefs here
                
                # Generate a "Projected" belief based on 2024 stats + random noise
                # This simulates our model's pre-race prediction
                projected_finish = int(d_obj.avg_finish + np.random.normal(0, 3))
                projected_finish = max(1, min(40, projected_finish))
                
                prop = Proposition(
                    content=f"{d_obj.name} projected finish {projected_finish}",
                    driver_id=d_obj.id,
                    race_id=race.id,
                    session_type="prediction"
                )
                db.add(prop)
                db.commit()
                db.refresh(prop)
                
                belief = Belief(
                    agent_id=projector_agent.id,
                    prop_id=prop.id,
                    confidence=0.7, # Prediction, not fact
                    epistemic_var=0.2, # Prediction has variance
                    source="projection_model"
                )
                db.add(belief)

        db.commit()
        print("2025 Test data seeded.")
        print("Database seeding complete!")

    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
