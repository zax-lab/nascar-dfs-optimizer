#!/usr/bin/env python3
"""
Driver Calibration Script for NASCAR DFS Optimizer.

This script initializes driver skill priors in Neo4j based on 
historical finishing positions stored in the epistemic database.
"""

import os
import sys
import re
import numpy as np
import logging

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'apps', 'backend'))

# Mock the logger in app.ontology if it causes issues
import app.ontology

from app.models import SessionLocal, Driver, Proposition, Belief
from app.ontology import OntologyDriver, DriverNode
from app.config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def calibrate_drivers():
    settings = get_settings()
    
    # Initialize Neo4j
    logger.info("Connecting to Neo4j...")
    try:
        # Note: We pass auth directly since OntologyDriver singleton might need first init
        ontology = OntologyDriver(
            uri=str(settings.NEO4J_URI),
            user=settings.NEO4J_USER,
            password=settings.NEO4J_PASSWORD
        )
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        return

    db = SessionLocal()
    try:
        drivers = db.query(Driver).all()
        logger.info(f"Calibrating {len(drivers)} drivers based on historical data...")
        
        for driver in drivers:
            # 1. Fetch historical results
            # Results are stored as Beliefs with source='history'
            historical_beliefs = db.query(Belief).join(Proposition).filter(
                Proposition.driver_id == driver.id,
                Belief.source == 'history'
            ).all()
            
            if not historical_beliefs:
                logger.debug(f"No history for {driver.name}, skipping.")
                continue
                
            finishes = []
            for belief in historical_beliefs:
                # Parse finish position from content "Name finish Pos"
                content = belief.proposition.content
                match = re.search(r'finish (\d+)', content)
                if match:
                    finishes.append(int(match.group(1)))
            
            if not finishes:
                continue
                
            avg_finish = np.mean(finishes)
            win_count = sum(1 for f in finishes if f == 1)
            
            # 2. Map to metaphysical properties (0-1 range)
            # Skill: 1.0 (best) to 0.0 (worst)
            # Heuristic: skill = 1 - (avg_finish - 1) / 39
            # (Assuming 40 car field)
            skill = max(0.0, min(1.0, 1.0 - (avg_finish - 1) / 39.0))
            
            # Aggression: slightly higher for winners
            psyche_aggression = 0.5 + (0.1 if win_count > 0 else 0)
            
            # Risk: higher for middle-of-pack drivers who might have more volatility
            # Or just correlate with avg_finish for now
            shadow_risk = max(0.0, min(1.0, (avg_finish / 40.0)))
            
            # 4. Update Neo4j
            driver_node = DriverNode(
                driver_id=str(driver.id),
                name=driver.name,
                team=driver.team,
                car_number=driver.car_number,
                skill=float(skill),
                psyche_aggression=float(psyche_aggression),
                shadow_risk=float(shadow_risk),
                realpolitik_pos=0.5 # Neutral prior
            )
            
            success = ontology.create_driver_node(driver_node)
            if success:
                logger.info(f"✓ Calibrated {driver.name:20} | Avg: {avg_finish:4.1f} | Skill: {skill:.3f}")
            else:
                logger.error(f"✗ Failed to update {driver.name} in Neo4j")
            
        logger.info("Calibration cycle complete.")
        
    except Exception as e:
        logger.error(f"An error occurred during calibration: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
        ontology.close()

if __name__ == "__main__":
    calibrate_drivers()
