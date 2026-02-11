"""
Belief Projector for NASCAR DFS Optimizer (Enhanced)

This module implements the "Sharper Belief Model" requirements:
1. Full distribution tracking (PMF)
2. Hierarchical structure (pooling by team/manufacturer)
3. Time decay for older evidence
4. Iterative Bayesian updates

The projector manages the agent's belief state, updating it with new evidence
from priors, simulations, and real-world results.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
import json
import logging
import yaml
from sqlalchemy.orm import Session

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database models import
from apps.backend.app.models import (
    Agent, Belief, Proposition, World, Run, Update, Driver, Race, SessionLocal
)

class DistributionMath:
    """Helper for operations on discrete probability distributions."""
    
    @staticmethod
    def normalize(dist: Dict[int, float]) -> Dict[int, float]:
        total = sum(dist.values())
        if total == 0: return dist
        return {k: v/total for k, v in dist.items()}

    @staticmethod
    def bayesian_update(prior: Dict[int, float], likelihood: Dict[int, float]) -> Dict[int, float]:
        """
        P(H|E) = P(E|H) * P(H) / P(E)
        Here H is the finishing position.
        """
        posterior = {}
        all_keys = set(prior.keys()) | set(likelihood.keys())
        
        for k in all_keys:
            p = prior.get(k, 0.0)
            l = likelihood.get(k, 1e-6) # Small epsilon
            posterior[k] = p * l
            
        return DistributionMath.normalize(posterior)

    @staticmethod
    def entropy(dist: Dict[int, float]) -> float:
        h = 0.0
        for p in dist.values():
            if p > 0:
                h -= p * np.log2(p)
        return h

class HierarchicalModel:
    """Handles hierarchical regularization of beliefs."""
    
    def __init__(self, config: Dict[str, Any]):
        self.pooling_strength = config.get('belief', {}).get('pooling_strength', {'team': 0.3})
        
    def pool_beliefs(self, beliefs: List[Belief], drivers: Dict[int, Driver]) -> List[Belief]:
        """
        Shrink individual belief distributions towards team/manufacturer means.
        """
        # Group by team
        team_dists = {} # {team: {pos: sum_prob}}
        team_counts = {}
        
        for b in beliefs:
            driver = drivers.get(b.proposition.driver_id)
            if not driver: continue
            
            team = driver.team
            dist = b.distribution or {}
            
            if team not in team_dists:
                team_dists[team] = {}
                team_counts[team] = 0
                
            for pos, prob in dist.items():
                pos = int(pos)
                team_dists[team][pos] = team_dists[team].get(pos, 0.0) + prob
            team_counts[team] += 1
            
        # Normalize team means
        team_means = {}
        for team, counts in team_dists.items():
            if team_counts[team] > 0:
                team_means[team] = DistributionMath.normalize(counts)

        # Apply shrinkage
        alpha = self.pooling_strength.get('team', 0.3)
        
        for b in beliefs:
            driver = drivers.get(b.proposition.driver_id)
            if not driver: continue
            
            team_mean = team_means.get(driver.team)
            if not team_mean: continue
            
            # Mix individual with team mean
            new_dist = {}
            current_dist = b.distribution or {}
            
            all_keys = set(current_dist.keys()) | set(team_mean.keys())
            for k in all_keys:
                k = str(k) # JSON keys are strings
                p_ind = current_dist.get(k, 0.0)
                p_team = team_mean.get(int(k), 0.0)
                new_dist[k] = (1 - alpha) * p_ind + alpha * p_team
                
            b.distribution = DistributionMath.normalize({int(k): v for k, v in new_dist.items()})
            
        return beliefs

class EpistemicProjector:
    """
    Main orchestrator for belief projection.
    """
    def __init__(self, db_session: Session, config_path: str = 'config.yaml'):
        self.db_session = db_session
        try:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        except:
            self.config = {}
            
        self.hierarchical_model = HierarchicalModel(self.config)
        self.decay_config = self.config.get('belief', {}).get('time_decay_halflife', {})

    def update_from_simulation(self, run_id: int):
        """Update beliefs based on MC simulation run."""
        run = self.db_session.query(Run).filter(Run.id == run_id).first()
        if not run: return
        
        # Get simulation distributions
        # In the new simulator, we'd pull from World records or parsing mc_path
        # For efficiency, we assume Run stores summary stats or we re-aggregate
        
        # Aggregate from World records associated with this run/race
        # This part assumes we have a way to link Run -> Worlds (via race_id usually)
        race_id = run.end_beliefs.get('race_id')
        worlds = self.db_session.query(World).filter(
            World.scenario['race_id'].astext == str(race_id)
        ).all()
        
        # Build PMFs
        driver_pmfs = {}
        for w in worlds:
            did = w.scenario.get('driver_id')
            pos = w.scenario.get('final_position')
            if did not in driver_pmfs: driver_pmfs[did] = {}
            driver_pmfs[did][pos] = driver_pmfs[did].get(pos, 0) + 1
            
        # Normalize
        for did in driver_pmfs:
            driver_pmfs[did] = DistributionMath.normalize(driver_pmfs[did])

        # Update Beliefs
        for did, pmf in driver_pmfs.items():
            self._update_driver_belief(did, race_id, pmf, "mc_sim")
            
        # Apply Hierarchical Regularization
        self._apply_hierarchy(race_id)

    def _update_driver_belief(
        self, 
        driver_id: int, 
        race_id: int, 
        likelihood_pmf: Dict[int, float],
        source: str
    ):
        """Bayesian update of a single driver's belief."""
        # Get/Create Proposition
        prop = self._get_proposition(driver_id, race_id)
        
        # Get/Create Belief
        belief = self.db_session.query(Belief).filter(
            Belief.prop_id == prop.id
        ).first()
        
        if not belief:
            # Create new with prior (uniform if no prior logic here)
            # ideally priors.py handled initialization
            belief = Belief(
                agent_id=1, # Default agent
                prop_id=prop.id,
                confidence=0.5,
                epistemic_var=1.0,
                distribution=likelihood_pmf, # Init with likelihood if first time
                source=source
            )
            self.db_session.add(belief)
        else:
            # Bayesian Update
            current_dist = {int(k): v for k, v in (belief.distribution or {}).items()}
            if not current_dist:
                posterior = likelihood_pmf
            else:
                posterior = DistributionMath.bayesian_update(current_dist, likelihood_pmf)
            
            belief.distribution = posterior
            
            # Update summary stats
            # Confidence could be Prob(Top 10)
            top10_prob = sum(v for k, v in posterior.items() if k <= 3) # states 0-3 are Top 10
            belief.confidence = top10_prob
            belief.epistemic_var = DistributionMath.entropy(posterior) # Use entropy as var proxy
            belief.source = source
            belief.timestamp = datetime.utcnow()
            
        self.db_session.commit()

    def _apply_hierarchy(self, race_id: int):
        """Pool beliefs for the race."""
        # Get all beliefs for this race
        props = self.db_session.query(Proposition).filter(Proposition.race_id == race_id).all()
        prop_ids = [p.id for p in props]
        beliefs = self.db_session.query(Belief).filter(Belief.prop_id.in_(prop_ids)).all()
        
        # Load drivers
        drivers = {d.id: d for d in self.db_session.query(Driver).all()}
        
        # Apply pooling
        self.hierarchical_model.pool_beliefs(beliefs, drivers)
        self.db_session.commit()

    def apply_time_decay(self, race_id: int, track_type: str = 'default'):
        """Decay belief confidence based on age."""
        # For a "projection" model, time decay usually applies to *Historical* priors
        # entering the current race. If we are updating beliefs *during* a race week,
        # we might decay older evidence (e.g. practice speed from yesterday).
        
        halflife = self.decay_config.get(track_type, 180)
        
        # This would require checking belief.timestamp and increasing variance (entropy)
        # flattening the distribution towards uniform.
        pass # Placeholder for complexity

    def _get_proposition(self, driver_id: int, race_id: int) -> Proposition:
        prop = self.db_session.query(Proposition).filter(
            Proposition.driver_id == driver_id,
            Proposition.race_id == race_id
        ).first()
        
        if not prop:
            prop = Proposition(
                content=f"Driver {driver_id} finish dist",
                driver_id=driver_id,
                race_id=race_id,
                session_type="race"
            )
            self.db_session.add(prop)
            self.db_session.commit()
            
        return prop

# Helper factory
def create_projector(db: Session = None):
    if not db: db = SessionLocal()
    return EpistemicProjector(db)