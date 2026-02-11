#!/usr/bin/env python3
"""
Run Monte Carlo simulation for NASCAR projections.

This script runs the Monte Carlo simulator on the drivers
already loaded in the database, generating finishing position
distributions for each driver.
"""

import sys
import logging
from pathlib import Path

# Add paths
backend_path = Path(__file__).parent.parent / "apps" / "backend"
sys.path.append(str(backend_path))

# Add project root for imports
project_root = Path(__file__).parent
sys.path.append(str(project_root))

import numpy as np
import yaml

from app.models import (
    Driver, SessionLocal
)

# Import the MC simulator (this will need some fixes)
try:
    from mc_sim import NASCARSimulator, GlobalRaceScenario
except ImportError as e:
    print(f"Error importing mc_sim: {e}")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_simulation():
    """Run Monte Carlo simulation on database drivers."""
    
    # Load config
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
    except:
        config = {}
    
    # Get simulation parameters
    n_sims = config.get('simulation', {}).get('n_simulations', 1000)
    logger.info(f"Running {n_sims} simulations per driver")
    
    # Load drivers from database
    session = SessionLocal()
    drivers = session.query(Driver).all()
    
    logger.info(f"Found {len(drivers)} drivers in database")
    
    if not drivers:
        logger.error("No drivers found in database. Run import script first.")
        sys.exit(1)
    
    # Build drivers data dict
    drivers_data = {}
    for driver in drivers:
        drivers_data[driver.id] = {
            'name': driver.name,
            'team': driver.team,
            'start_pos': 1,  # Default to mid-pack for now
        }
    
    # Simple track data (use default)
    track_data = {
        'name': 'Generic Track',
        'length_miles': 2.5,
        'laps': 200,
        'type': 'intermediate',
        'caution_probability': 0.08
    }
    
    logger.info(f"Track: {track_data['name']}, {track_data['laps']} laps")
    
    # Create simulator
    logger.info("Initializing Monte Carlo simulator...")
    
    # Simple simulation without complex transitions for now
    # Just use random positions based on average finish
    results = {}
    
    for driver in drivers:
        logger.info(f"Simulating {driver.name} (avg_finish={driver.avg_finish})")
        
        # Simple simulation: generate finishing positions
        # based on average finish with some variance
        avg = driver.avg_finish if driver.avg_finish else 20.0
        
        # Generate positions around average
        positions = []
        for _ in range(n_sims):
            # Random position around average with variance
            variance = max(5, avg / 3)  # More variance for worse drivers
            pos = int(np.random.normal(avg, variance))
            pos = max(1, min(40, pos))  # Clamp to 1-40
            positions.append(pos)
        
        # Calculate distribution
        counts = {}
        for pos in positions:
            counts[pos] = counts.get(pos, 0) + 1
        
        total = len(positions)
        distribution = {k: v/total for k, v in counts.items()}
        
        # Sort by probability
        top_finishes = sorted(distribution.items(), key=lambda x: x[1], reverse=True)[:10]
        
        results[driver.id] = {
            'name': driver.name,
            'distribution': distribution,
            'top_finishes': top_finishes,
            'avg_sim': np.mean(positions),
            'prob_p1': distribution.get(1, 0),
            'prob_top5': sum([distribution.get(p, 0) for p in range(1, 6)]),
            'prob_top10': sum([distribution.get(p, 0) for p in range(1, 11)]),
        }
        
        logger.info(f"  {driver.name}: P1={distribution.get(1, 0):.3f}, "
                  f"Top5={results[driver.id]['prob_top5']:.3f}, "
                  f"Top10={results[driver.id]['prob_top10']:.3f}")
    
    # Export results
    logger.info("Exporting simulation results...")
    
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    import json
    with open(output_dir / "sim_results.json", 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f"Results exported to {output_dir / 'sim_results.json'}")
    logger.info(f"Simulation complete for {len(drivers)} drivers")
    
    session.close()


if __name__ == "__main__":
    run_simulation()
