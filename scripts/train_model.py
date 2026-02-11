#!/usr/bin/env python3
"""
Train NASCAR projection model from imported data.

This script generates prior beliefs from driver statistics and prepares
the model for Monte Carlo simulation.

Usage:
    python train_model.py --data-type historical
    python train_model.py --data-type sample
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import json

import numpy as np
import yaml

# Add backend to path
backend_path = Path(__file__).parent.parent / "apps" / "backend"
sys.path.append(str(backend_path))

from app.models import (
    Driver, SessionLocal
)

# Add project root for imports
sys.path.append(str(Path(__file__).parent.parent))
from projector import EpistemicProjector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ModelTrainer:
    """Train NASCAR projection model from historical data."""
    
    def __init__(self, db_session=None, config_path: str = None):
        self.db_session = db_session or SessionLocal()
        
        # Load config
        if config_path:
            try:
                with open(config_path, 'r') as f:
                    self.config = yaml.safe_load(f)
            except:
                logger.warning("Could not load config, using defaults")
                self.config = {}
        else:
            self.config = {}
        
        # Get configuration values
        self.form_window = self.config.get('priors', {}).get('form_window', 6)
        self.track_types = self.config.get('priors', {}).get('track_types', {})
        self.weights = self.config.get('priors', {}).get('weights', {})
        
    def generate_prior_beliefs(self) -> Dict[int, Dict[int, float]]:
        """
        Generate prior belief distributions from driver statistics.
        
        This creates baseline finishing position distributions based on:
        - Average finish position
        - Team tier
        - Historical win rate
        
        Returns:
            Dictionary mapping driver_id to position probability distribution
        """
        logger.info("Generating prior beliefs from driver statistics...")
        
        drivers = self.db_session.query(Driver).all()
        
        priors = {}
        
        for driver in drivers:
            # Generate position distribution based on average finish
            dist = self._position_distribution_from_avg(
                driver.avg_finish,
                driver.wins,
                driver.top5,
                driver.top10
            )
            
            priors[driver.id] = dist
            
            logger.info(f"Driver {driver.name}: avg_finish={driver.avg_finish}, "
                      f"priors generated (top10_prob={sum([p for k,p in dist.items() if k <= 10]):.3f})")
        
        return priors
    
    def _position_distribution_from_avg(
        self,
        avg_finish: float,
        wins: int,
        top5: int,
        top10: int
    ) -> Dict[int, float]:
        """
        Generate a finishing position distribution from driver stats.
        
        This uses a simple heuristic:
        - Driver's average finish becomes the peak of distribution
        - Stronger drivers (lower avg_finish) have tighter distributions
        - Wins/top5/top10 adjust peak probability
        
        Args:
            avg_finish: Average finishing position
            wins: Number of career wins
            top5: Number of top-5 finishes
            top10: Number of top-10 finishes
            
        Returns:
            Dictionary mapping finishing position to probability
        """
        if avg_finish is None or avg_finish <= 0:
            # No data - uniform distribution
            return {i: 1.0/40.0 for i in range(1, 41)}
        
        # Peak at average finish
        peak_pos = int(avg_finish)
        peak_pos = max(1, min(40, peak_pos))
        
        # Distribution width based on driver quality
        # Better drivers (lower avg) have tighter distributions
        # Worse drivers (higher avg) have wider distributions
        quality = max(1.0, 50.0 / avg_finish)
        width = 15.0 / quality  # Better drivers: narrower
        
        # Generate distribution
        distribution = {}
        for pos in range(1, 41):
            # Normal-ish distribution around average
            dist = abs(pos - avg_finish)
            prob = 1.0 / (dist + width)**2
        
        # Normalize
        total = sum(distribution.values())
        distribution = {k: v/total for k, v in distribution.items()}
        
        # Boost based on historical performance
        # If driver has wins/top5, boost top positions
        if wins > 0:
            # Boost P1-P5
            boost = 1.0 + (wins / 100.0)
            for pos in range(1, 6):
                if pos in distribution:
                    distribution[pos] *= boost
        
        if top5 > 10:
            # Boost P1-P10
            boost = 1.0 + (top5 / 200.0)
            for pos in range(1, 11):
                if pos in distribution:
                    distribution[pos] *= boost
        
        # Renormalize
        total = sum(distribution.values())
        if total > 0:
            distribution = {k: v/total for k, v in distribution.items()}
        
        return distribution
    
    def export_priors_to_json(self, priors: Dict[int, Dict[int, float]], output_path: str):
        """
        Export prior beliefs to JSON file for analysis.
        
        Args:
            priors: Dictionary of prior distributions
            output_path: Path to output JSON file
        """
        logger.info(f"Exporting priors to {output_path}")
        
        # Build priors dict
        priors_dict = {}
        for driver_id, dist in priors.items():
            priors_dict[str(driver_id)] = {
                str(pos): float(prob)
                for pos, prob in dist.items()
            }
        
        output = {
            "generated_at": "2026-02-03",  # Simple timestamp for now
            "n_drivers": len(priors),
            "priors": priors_dict
        }
        
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)
        
        logger.info(f"Exported {len(priors)} driver priors")


def main():
    parser = argparse.ArgumentParser(
        description="Train NASCAR projection model"
    )
    parser.add_argument(
        "--data-type",
        type=str,
        choices=["historical", "sample"],
        default="sample",
        help="Type of data to train on"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to config file"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="output/priors.json",
        help="Path to output priors JSON"
    )
    
    args = parser.parse_args()
    
    # Create trainer
    trainer = ModelTrainer(config_path=args.config)
    
    # Generate prior beliefs
    priors = trainer.generate_prior_beliefs()
    
    # Export priors
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    trainer.export_priors_to_json(priors, args.output)
    
    logger.info("Model training complete")


if __name__ == "__main__":
    main()
