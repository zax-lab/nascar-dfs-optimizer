#!/usr/bin/env python3
"""
Simple Monte Carlo simulation for NASCAR projections.

This is a simplified version that works with the current
project structure without requiring the full mc_sim module.
"""

import sys
import logging
from pathlib import Path
import json
import numpy as np

# Add paths
backend_path = Path(__file__).parent.parent / "apps" / "backend"
sys.path.append(str(backend_path))

from app.models import Driver, SessionLocal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_simple_simulation():
    """Run simplified Monte Carlo simulation."""
    
    # Load drivers from database
    session = SessionLocal()
    drivers = session.query(Driver).all()
    
    logger.info(f"Found {len(drivers)} drivers in database")
    
    if not drivers:
        logger.error("No drivers found. Run import script first.")
        sys.exit(1)
    
    # Simulation parameters
    n_simulations = 1000
    logger.info(f"Running {n_simulations} simulations per driver")
    
    results = {}
    
    for driver in drivers:
        avg = driver.avg_finish if driver.avg_finish else 20.0
        logger.info(f"Simulating {driver.name} (avg_finish={avg})")
        
        # Generate finishing positions
        positions = []
        for _ in range(n_simulations):
            # Random position around average with variance
            variance = max(5, avg / 3)
            pos = int(np.random.normal(avg, variance))
            pos = max(1, min(40, pos))
            positions.append(pos)
        
        # Calculate distribution
        counts = {}
        for pos in positions:
            counts[pos] = counts.get(pos, 0) + 1
        
        total = len(positions)
        distribution = {k: v/total for k, v in counts.items()}
        
        # Calculate stats
        avg_sim = np.mean(positions)
        prob_p1 = distribution.get(1, 0)
        prob_top5 = sum([distribution.get(p, 0) for p in range(1, 6)])
        prob_top10 = sum([distribution.get(p, 0) for p in range(1, 11)])
        
        results[driver.id] = {
            'name': driver.name,
            'team': driver.team,
            'salary': driver.salary,
            'avg_finish': driver.avg_finish,
            'distribution': distribution,
            'avg_sim': float(avg_sim),
            'prob_p1': prob_p1,
            'prob_top5': prob_top5,
            'prob_top10': prob_top10,
        }
        
        logger.info(f"  {driver.name}: P1={prob_p1:.3f}, "
                  f"Top5={prob_top5:.3f}, Top10={prob_top10:.3f}")
    
    # Export results
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / "sim_results.json", 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f"Results exported to {output_dir / 'sim_results.json'}")
    logger.info(f"Simulation complete for {len(drivers)} drivers")
    
    session.close()


if __name__ == "__main__":
    run_simple_simulation()
