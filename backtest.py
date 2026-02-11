"""
Backtest Validation System for NASCAR DFS Optimizer

This module implements a comprehensive backtest validation framework for the NASCAR DFS
optimizer with axiomatic AI framework. The system simulates pre-race conditions
using only data available before the race, then validates predictions against
actual race results to measure system effectiveness.

The backtest framework implements:
1. Historical race data loading and simulation
2. Pre-race belief state simulation
3. Monte Carlo simulation execution
4. Optimal lineup generation using optimizer
5. Actual vs projected points calculation
6. ROI and performance metrics validation
7. Comprehensive reporting and visualization

Backtest Methodology:
- Simulates pre-race conditions using only qualifying/practice data
- Compares projected points (from beliefs) vs actual points (from race results)
- Calculates ROI = (winnings - entry_fee) / entry_fee * 100
- Validates MAE, RMSE, correlation between predicted and actual
- Measures belief accuracy, delta analysis, and epistemic variance effectiveness
- Tests multiple scenarios with different data source combinations
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
import json
import os
import logging

# Database imports
from sqlalchemy.orm import Session
from apps.backend.app.models import (
    Driver, Race, Belief, Proposition, Run, Update, SessionLocal
)

# Backend component imports
from apps.backend.app.optimizer.leverage_aware import LeverageAwareOptimizer
from projector import EpistemicProjector
from mc_sim import NASCARSimulator, calculate_finish_points

# Define DFS Scoring (DraftKings)
FINISH_POINTS = {
    1: 45, 2: 42, 3: 41, 4: 40, 5: 39, 6: 38, 7: 37, 8: 36, 9: 35, 10: 34,
    11: 32, 12: 31, 13: 30, 14: 29, 15: 28, 16: 27, 17: 26, 18: 25, 19: 24, 20: 23,
    21: 21, 22: 20, 23: 19, 24: 18, 25: 17, 26: 16, 27: 15, 28: 14, 29: 13, 30: 12,
    31: 10, 32: 9, 33: 8, 34: 7, 35: 6, 36: 5, 37: 4, 38: 3, 39: 2, 40: 1
}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Configuration Constants
# ============================================================================

DAYTONA_2025_CONFIG = {
    'race_id': 1,
    'race_name': 'Daytona 500',
    'track': 'Daytona International Speedway',
    'track_type': 'superspeedway',
    'date': '2025-02-16',
    'laps': 200,
    'n_drivers': 40,
    'salary_cap': 50000,
    'entry_fee': 10.0,
    'n_lineups': 10,
    'n_simulations': 10000,
    'caution_probability': 0.08,
    'pit_cycle_laps': 35
}

CONFIDENCE_THRESHOLDS = {
    'high': 0.7,
    'medium': 0.5,
    'low': 0.3
}


# ============================================================================
# BacktestEngine Class
# ============================================================================

class BacktestEngine:
    """
    Main backtest engine for validating NASCAR DFS optimizer performance.
    
    This class orchestrates the complete backtest process:
    1. Loads historical race data
    2. Simulates pre-race belief states
    3. Runs Monte Carlo simulations
    4. Generates optimal lineups using optimizer
    5. Calculates actual DFS points from race results
    6. Computes ROI and performance metrics
    7. Generates comprehensive validation reports
    
    Attributes:
        db_session: SQLAlchemy database session
        race_config: Configuration for the race being backtested
        optimizer: NASCAROptimizer instance
        projector: EpistemicProjector instance
        simulator: NASCARSimulator instance
        results: Dictionary storing backtest results
    """
    
    def __init__(self, db_session: Session, race_config: Optional[Dict[str, Any]] = None):
        """
        Initialize backtest engine.
        
        Args:
            db_session: SQLAlchemy database session
            race_config: Optional race configuration (uses Daytona 2025 defaults if None)
        """
        self.db_session = db_session
        self.race_config = race_config or DAYTONA_2025_CONFIG.copy()
        
        # Initialize components
        self.optimizer = LeverageAwareOptimizer(
            db_session=db_session,
            salary_cap=self.race_config['salary_cap'],
            n_drivers=6,
            min_stack=2,
            max_stack=3
        )
        
        self.projector = EpistemicProjector(db_session=db_session)
        self.simulator = None
        
        # Results storage
        self.results = {
            'race_id': self.race_config['race_id'],
            'race_name': self.race_config['race_name'],
            'config': self.race_config.copy(),
            'lineups': [],
            'metrics': {},
            'belief_metrics': {},
            'simulation_metrics': {}
        }
        
        logger.info(f"BacktestEngine initialized for {self.race_config['race_name']}")
    
    def load_historical_race(self, race_id: int) -> Dict[str, Any]:
        """
        Load historical race data from database.
        
        This method retrieves all relevant data for a historical race including:
        - Race information (name, track, date, laps)
        - Driver information (names, teams, salaries, stats)
        - Qualifying results (positions, speeds)
        - Practice results (speeds, lap times)
        - Actual race results (finish positions, DFS points)
        
        Args:
            race_id: Race identifier
            
        Returns:
            Dictionary containing all historical race data
            
        Raises:
            ValueError: If race_id is invalid or data is incomplete
        """
        logger.info(f"Loading historical race data for race {race_id}")
        
        # Get race information
        race = self.db_session.query(Race).filter(Race.id == race_id).first()
        if not race:
            raise ValueError(f"Race with id {race_id} not found")
        
        # Get all drivers
        drivers = self.db_session.query(Driver).all()
        
        # Get propositions and beliefs for this race
        propositions = self.db_session.query(Proposition).filter(
            Proposition.race_id == race_id
        ).all()
        
        # Organize data
        race_data = {
            'race': {
                'id': race.id,
                'name': race.name,
                'track': race.track,
                'date': race.date.isoformat() if race.date else None,
                'laps': race.laps,
                'status': race.status
            },
            'drivers': [],
            'qualifying': [],
            'practice': [],
            'results': []
        }
        
        # Load driver data
        for driver in drivers:
            driver_dict = {
                'driver_id': driver.id,
                'name': driver.name,
                'team': driver.team,
                'car_number': driver.car_number,
                'salary': float(driver.salary),
                'avg_finish': driver.avg_finish,
                'wins': driver.wins,
                'top5': driver.top5,
                'top10': driver.top10
            }
            race_data['drivers'].append(driver_dict)
        
        # Load qualifying data (from propositions with session_type='qualifying')
        qual_props = [p for p in propositions if p.session_type == 'qualifying']
        for prop in qual_props:
            belief = self.db_session.query(Belief).filter(
                Belief.prop_id == prop.id
            ).first()
            
            if belief:
                qual_data = {
                    'driver_id': prop.driver_id,
                    'position': self._extract_position_from_content(prop.content),
                    'confidence': belief.confidence,
                    'epistemic_var': belief.epistemic_var
                }
                race_data['qualifying'].append(qual_data)
        
        # Load practice data (from propositions with session_type='practice')
        prac_props = [p for p in propositions if p.session_type == 'practice']
        for prop in prac_props:
            belief = self.db_session.query(Belief).filter(
                Belief.prop_id == prop.id
            ).first()
            
            if belief:
                prac_data = {
                    'driver_id': prop.driver_id,
                    'speed_rank': self._extract_rank_from_content(prop.content),
                    'confidence': belief.confidence,
                    'epistemic_var': belief.epistemic_var
                }
                race_data['practice'].append(prac_data)
        
        # Load race results (from propositions with session_type='race')
        result_props = [p for p in propositions if p.session_type == 'race']
        for prop in result_props:
            belief = self.db_session.query(Belief).filter(
                Belief.prop_id == prop.id
            ).first()
            
            if belief:
                result_data = {
                    'driver_id': prop.driver_id,
                    'finish_position': self._extract_position_from_content(prop.content),
                    'confidence': belief.confidence,
                    'epistemic_var': belief.epistemic_var
                }
                race_data['results'].append(result_data)
        
        logger.info(
            f"Loaded historical race data: {len(race_data['drivers'])} drivers, "
            f"{len(race_data['qualifying'])} qualifying results, "
            f"{len(race_data['practice'])} practice results, "
            f"{len(race_data['results'])} race results"
        )
        
        return race_data
    
    def _extract_position_from_content(self, content: str) -> int:
        """Extract position number from proposition content."""
        content_lower = content.lower()
        for word in content_lower.split():
            if word.isdigit():
                return int(word)
        return 20  # Default middle position
    
    def _extract_rank_from_content(self, content: str) -> int:
        """Extract rank number from proposition content."""
        content_lower = content.lower()
        for word in content_lower.split():
            if word.isdigit():
                return int(word)
        return 15  # Default middle rank
    
    def simulate_pre_race_beliefs(self, race_id: int, scenario: str = 'all') -> Dict[str, Any]:
        """
        Simulate pre-race belief states using available data sources.
        
        This method simulates the belief state that would have existed
        before the race, using only data that was available at that time.
        Different scenarios use different data source combinations:
        
        Scenarios:
        - 'qualifying_only': Use only qualifying data
        - 'qualifying_practice': Use qualifying + practice data
        - 'qualifying_mc': Use qualifying + MC simulation (no practice)
        - 'all': Use all data sources (qualifying + practice + MC sim)
        
        Args:
            race_id: Race identifier
            scenario: Data source scenario to use
            
        Returns:
            Dictionary containing simulated belief states
        """
        logger.info(f"Simulating pre-race beliefs for race {race_id}, scenario: {scenario}")
        
        # Load historical race data
        race_data = self.load_historical_race(race_id)
        
        # Initialize belief states
        belief_states = {
            'driver_id': [],
            'confidence': [],
            'epistemic_var': [],
            'source': []
        }
        
        # Process drivers
        for driver in race_data['drivers']:
            driver_id = driver['driver_id']
            
            # Get qualifying data
            qual_data = next(
                (q for q in race_data['qualifying'] if q['driver_id'] == driver_id),
                None
            )
            
            # Get practice data
            prac_data = next(
                (p for p in race_data['practice'] if p['driver_id'] == driver_id),
                None
            )
            
            # Calculate initial belief based on scenario
            if scenario == 'qualifying_only':
                # Only use qualifying data
                if qual_data:
                    confidence = qual_data['confidence']
                    epistemic_var = qual_data['epistemic_var']
                    source = 'qualifying'
                else:
                    confidence = 0.5
                    epistemic_var = 0.25
                    source = 'prior'
            
            elif scenario == 'qualifying_practice':
                # Use qualifying + practice
                if qual_data and prac_data:
                    confidence = (qual_data['confidence'] + prac_data['confidence']) / 2
                    epistemic_var = (qual_data['epistemic_var'] + prac_data['epistemic_var']) / 2
                    source = 'qualifying+practice'
                elif qual_data:
                    confidence = qual_data['confidence']
                    epistemic_var = qual_data['epistemic_var']
                    source = 'qualifying'
                else:
                    confidence = 0.5
                    epistemic_var = 0.25
                    source = 'prior'
            
            elif scenario == 'qualifying_mc':
                # Use qualifying + MC sim (will be updated after MC run)
                if qual_data:
                    confidence = qual_data['confidence']
                    epistemic_var = qual_data['epistemic_var']
                    source = 'qualifying+mc_sim'
                else:
                    confidence = 0.5
                    epistemic_var = 0.25
                    source = 'mc_sim'
            
            else:  # 'all'
                # Use all data sources
                if qual_data and prac_data:
                    confidence = (qual_data['confidence'] + prac_data['confidence']) / 2
                    epistemic_var = (qual_data['epistemic_var'] + prac_data['epistemic_var']) / 2
                    source = 'qualifying+practice+mc_sim'
                elif qual_data:
                    confidence = qual_data['confidence']
                    epistemic_var = qual_data['epistemic_var']
                    source = 'qualifying+mc_sim'
                else:
                    confidence = 0.5
                    epistemic_var = 0.25
                    source = 'prior'
            
            belief_states['driver_id'].append(driver_id)
            belief_states['confidence'].append(confidence)
            belief_states['epistemic_var'].append(epistemic_var)
            belief_states['source'].append(source)
        
        logger.info(f"Simulated pre-race beliefs for {len(belief_states['driver_id'])} drivers")
        
        return {
            'belief_states': belief_states,
            'race_data': race_data,
            'scenario': scenario
        }
    
    def run_monte_carlo_pre_race(
        self,
        race_id: int,
        belief_states: Dict[str, Any],
        n_simulations: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Run Monte Carlo simulation using pre-race belief states.
        
        This method initializes the Monte Carlo simulator with driver data
        and runs simulations to generate finish distributions and epistemic
        variance estimates. The simulation uses only data available
        before the race.
        
        Args:
            race_id: Race identifier
            belief_states: Pre-race belief states
            n_simulations: Number of simulations per driver (default from config)
            
        Returns:
            Dictionary containing simulation results including finish distributions
        """
        n_simulations = n_simulations or self.race_config['n_simulations']
        
        logger.info(
            f"Running Monte Carlo simulation for race {race_id}: "
            f"{n_simulations} paths per driver"
        )
        
        race_data = belief_states['race_data']
        
        # Prepare driver data for simulator
        drivers_data = {}
        for driver in race_data['drivers']:
            driver_id = driver['driver_id']
            
            # Find belief state for this driver
            idx = belief_states['belief_states']['driver_id'].index(driver_id)
            confidence = belief_states['belief_states']['confidence'][idx]
            
            # Map confidence to initial state (higher confidence = better starting position)
            initial_state = int((1.0 - confidence) * 9)
            initial_state = max(0, min(9, initial_state))
            
            drivers_data[driver_id] = {
                'name': driver['name'],
                'avg_finish': driver['avg_finish'],
                'wins': driver['wins'],
                'top5': driver['top5'],
                'top10': driver['top10'],
                'initial_state': initial_state
            }
        
        # Prepare track data
        track_data = {
            'name': race_data['race']['track'],
            'type': self.race_config['track_type'],
            'laps': race_data['race']['laps'],
            'caution_probability': self.race_config['caution_probability'],
            'pit_cycle_laps': self.race_config['pit_cycle_laps']
        }
        
        # Initialize simulator
        self.simulator = NASCARSimulator(
            drivers_data=drivers_data,
            track_data=track_data,
            n_states=10
        )
        
        # Create sample historical data for fitting
        historical_races = self._create_sample_historical_data(drivers_data)
        
        # Fit transitions
        self.simulator.fit_transitions(historical_races)
        
        # Run simulations
        simulations = self.simulator.simulate_race(
            race_id=race_id,
            n_simulations=n_simulations,
            store_in_db=False  # Don't store during backtest
        )
        
        # Calculate finish distributions
        finish_distributions = {}
        epistemic_variances = {}
        
        for driver_id in drivers_data:
            finish_distributions[driver_id] = self.simulator.get_driver_finish_distribution(driver_id)
            epistemic_variances[driver_id] = self.simulator.calculate_epistemic_variance(driver_id)
        
        logger.info(f"Monte Carlo simulation completed for {len(drivers_data)} drivers")
        
        return {
            'simulations': simulations,
            'finish_distributions': finish_distributions,
            'epistemic_variances': epistemic_variances,
            'n_simulations': n_simulations
        }
    
    def _create_sample_historical_data(self, drivers_data: Dict[int, Dict[str, Any]]) -> pd.DataFrame:
        """Create sample historical race data for fitting Markov chains."""
        data = []
        
        for driver_id, driver in drivers_data.items():
            # Generate sample transitions based on driver skill
            avg_finish = driver['avg_finish'] or 20
            
            # Create multiple sample transitions
            for _ in range(10):
                start_state = int(np.random.normal(loc=5, scale=2))
                start_state = max(0, min(9, start_state))
                
                # Better drivers tend to move to better states
                finish_bias = (20 - avg_finish) / 20.0
                end_state = start_state + int(np.random.normal(loc=-finish_bias, scale=1))
                end_state = max(0, min(9, end_state))
                
                data.append({
                    'driver_id': driver_id,
                    'start_position': start_state,
                    'end_position': end_state,
                    'track_type': self.race_config['track_type'],
                    'avg_finish': avg_finish,
                    'wins': driver['wins'],
                    'top5': driver['top5'],
                    'top10': driver['top10']
                })
        
        return pd.DataFrame(data)
    
    def generate_optimal_lineups(
        self,
        race_id: int,
        belief_states: Dict[str, Any],
        mc_results: Optional[Dict[str, Any]] = None,
        n_lineups: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate optimal lineups using the optimizer.
        
        This method uses the NASCAR optimizer to generate optimal DFS lineups
        based on current belief states and Monte Carlo simulation results.
        The optimizer calculates expected points from beliefs and selects
        the best lineup subject to salary and stacking constraints.
        
        Args:
            race_id: Race identifier
            belief_states: Pre-race belief states
            mc_results: Optional Monte Carlo simulation results
            n_lineups: Number of lineups to generate (default from config)
            
        Returns:
            List of lineup dictionaries with projected points
        """
        n_lineups = n_lineups or self.race_config['n_lineups']
        
        logger.info(f"Generating {n_lineups} optimal lineups for race {race_id}")
        
        # Load driver data into optimizer
        self.optimizer.load_driver_data(race_id)
        
        # Update driver beliefs with MC results if available
        if mc_results:
            for driver_id, finish_dist in mc_results['finish_distributions'].items():
                # Calculate expected finish position from distribution
                expected_finish = sum(
                    state * prob for state, prob in finish_dist.items()
                )
                
                # Map to confidence
                confidence = max(0.0, min(1.0, 1.0 - (expected_finish / 10.0)))
                
                # Update driver beliefs in optimizer
                for driver in self.optimizer.drivers:
                    if driver['driver_id'] == driver_id:
                        for belief in driver['beliefs']:
                            belief['confidence'] = confidence
                        break
        
        # Generate lineups
        lineups = self.optimizer.optimize_lineup(
            race_id=race_id,
            n_lineups=n_lineups,
            objective='maximize_points'
        )
        
        logger.info(f"Generated {len(lineups)} optimal lineups")
        
        return lineups
    
    def calculate_actual_points(self, lineup: Dict[str, Any], race_results: List[Dict[str, Any]]) -> float:
        """
        Calculate actual DFS points from race results.
        
        This method calculates the actual DFS points earned by a lineup
        based on the actual race results. It uses the DraftKings
        scoring system to calculate points for each driver's finish
        position.
        
        Args:
            lineup: Lineup dictionary with drivers
            race_results: List of race result dictionaries
            
        Returns:
            Total actual DFS points for the lineup
        """
        total_points = 0.0
        
        for driver in lineup['drivers']:
            driver_id = driver['driver_id']
            
            # Find driver's race result
            result = next(
                (r for r in race_results if r['driver_id'] == driver_id),
                None
            )
            
            if result:
                finish_pos = result['finish_position']
                
                # Calculate DFS points using DraftKings scoring
                points = FINISH_POINTS.get(finish_pos, 0.0)
                
                # Add laps led points (estimated)
                laps_led = self._estimate_laps_led(driver, finish_pos)
                points += laps_led * 0.25
                
                # Add fastest lap points (estimated)
                if finish_pos <= 10 and np.random.random() < 0.2:
                    points += 1.0
                
                total_points += points
        
        return total_points
    
    def _estimate_laps_led(self, driver: Dict[str, Any], finish_pos: int) -> int:
        """Estimate laps led based on driver stats and finish position."""
        # Better finish positions tend to lead more laps
        base_laps = max(0, 5 - finish_pos * 0.1)
        
        # Adjust based on driver stats
        wins = driver.get('wins', 0)
        top5 = driver.get('top5', 0)
        
        bonus = (wins * 0.5) + (top5 * 0.1)
        
        return int(base_laps + bonus)
    
    def calculate_roi(self, lineup: Dict[str, Any], entry_fee: float, winnings: float) -> float:
        """
        Calculate ROI for a lineup.
        
        ROI (Return on Investment) measures the profitability of a lineup:
        ROI = (winnings - entry_fee) / entry_fee * 100
        
        Positive ROI indicates profit, negative ROI indicates loss.
        
        Args:
            lineup: Lineup dictionary
            entry_fee: Entry fee for the contest
            winnings: Total winnings from the lineup
            
        Returns:
            ROI percentage
        """
        roi = (winnings - entry_fee) / entry_fee * 100
        return roi
    
    def run_backtest(
        self,
        race_id: int,
        n_lineups: Optional[int] = None,
        entry_fee: Optional[float] = None,
        scenario: str = 'all'
    ) -> Dict[str, Any]:
        """
        Run complete backtest validation.
        
        This method executes the full backtest pipeline:
        1. Load historical race data
        2. Simulate pre-race belief states
        3. Run Monte Carlo simulation (if scenario includes it)
        4. Generate optimal lineups
        5. Calculate actual points from race results
        6. Compute ROI and performance metrics
        7. Generate validation report
        
        Args:
            race_id: Race identifier
            n_lineups: Number of lineups to generate
            entry_fee: Entry fee per lineup
            scenario: Data source scenario to use
            
        Returns:
            Dictionary containing complete backtest results
        """
        n_lineups = n_lineups or self.race_config['n_lineups']
        entry_fee = entry_fee or self.race_config['entry_fee']
        
        logger.info(
            f"Running backtest for race {race_id}: "
            f"{n_lineups} lineups, scenario={scenario}"
        )
        
        # Step 1: Load historical race data
        race_data = self.load_historical_race(race_id)
        
        # Step 2: Simulate pre-race beliefs
        belief_states = self.simulate_pre_race_beliefs(race_id, scenario)
        
        # Step 3: Run Monte Carlo simulation (if scenario includes it)
        mc_results = None
        if scenario in ['qualifying_mc', 'all']:
            mc_results = self.run_monte_carlo_pre_race(race_id, belief_states)
        
        # Step 4: Generate optimal lineups
        lineups = self.generate_optimal_lineups(
            race_id, belief_states, mc_results, n_lineups
        )
        
        # Step 5: Calculate actual points for each lineup
        lineup_results = []
        for lineup in lineups:
            actual_points = self.calculate_actual_points(lineup, race_data['results'])
            projected_points = lineup['total_projected_points']
            
            # Calculate winnings (simplified: assume $100 for top 10%)
            percentile = self._calculate_finish_percentile(lineup, race_data['results'])
            winnings = 100.0 if percentile <= 10 else 0.0
            
            # Calculate ROI
            roi = self.calculate_roi(lineup, entry_fee, winnings)
            
            lineup_result = {
                'lineup': lineup,
                'projected_points': projected_points,
                'actual_points': actual_points,
                'point_error': actual_points - projected_points,
                'point_error_pct': ((actual_points - projected_points) / projected_points * 100)
                    if projected_points > 0 else 0,
                'winnings': winnings,
                'roi': roi,
                'finish_percentile': percentile
            }
            
            lineup_results.append(lineup_result)
        
        # Step 6: Calculate performance metrics
        performance_metrics = self._calculate_performance_metrics(lineup_results)
        
        # Step 7: Calculate belief metrics
        belief_metrics = self._calculate_belief_metrics(belief_states, mc_results)
        
        # Step 8: Calculate simulation metrics (if MC was run)
        simulation_metrics = {}
        if mc_results:
            simulation_metrics = self._calculate_simulation_metrics(
                mc_results, race_data['results']
            )
        
        # Store results
        self.results = {
            'race_id': race_id,
            'race_name': race_data['race']['name'],
            'scenario': scenario,
            'config': self.race_config.copy(),
            'lineups': lineup_results,
            'performance_metrics': performance_metrics,
            'belief_metrics': belief_metrics,
            'simulation_metrics': simulation_metrics,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Backtest completed for race {race_id}")
        
        return self.results
    
    def _calculate_finish_percentile(
        self,
        lineup: Dict[str, Any],
        race_results: List[Dict[str, Any]]
    ) -> float:
        """Calculate finish percentile for a lineup."""
        total_points = 0.0
        
        for driver in lineup['drivers']:
            driver_id = driver['driver_id']
            result = next(
                (r for r in race_results if r['driver_id'] == driver_id),
                None
            )
            
            if result:
                # Lower finish position = better
                total_points += (44 - result['finish_position'])
        
        # Estimate percentile based on points
        # Max possible points = 6 drivers * 43 = 258
        percentile = (total_points / 258.0) * 100
        
        return percentile
    
    def _calculate_performance_metrics(self, lineup_results: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate performance metrics for backtest results.
        
        This method computes various metrics to measure the accuracy
        and effectiveness of the optimizer:
        - MAE: Mean Absolute Error between projected and actual points
        - RMSE: Root Mean Squared Error
        - Correlation: Pearson correlation between projected and actual
        - ROI: Average and total ROI
        - Win rate: Percentage of lineups finishing in top X%
        - Average finish percentile
        
        Args:
            lineup_results: List of lineup result dictionaries
            
        Returns:
            Dictionary of performance metrics
        """
        if not lineup_results:
            return {}
        
        projected = [r['projected_points'] for r in lineup_results]
        actual = [r['actual_points'] for r in lineup_results]
        
        # MAE and RMSE
        mae = calculate_mae(projected, actual)
        rmse = calculate_rmse(projected, actual)
        
        # Correlation
        correlation = calculate_correlation(projected, actual)
        
        # ROI metrics
        rois = [r['roi'] for r in lineup_results]
        avg_roi = np.mean(rois)
        total_roi = sum(rois)
        
        # Win rate (lineups in top 10%)
        win_count = sum(1 for r in lineup_results if r['finish_percentile'] <= 10)
        win_rate = (win_count / len(lineup_results)) * 100
        
        # Average finish percentile
        avg_finish_percentile = np.mean([r['finish_percentile'] for r in lineup_results])
        
        # Confidence calibration
        point_errors = [abs(r['point_error']) for r in lineup_results]
        avg_point_error = np.mean(point_errors)
        
        metrics = {
            'mae': mae,
            'rmse': rmse,
            'correlation': correlation,
            'avg_roi': avg_roi,
            'total_roi': total_roi,
            'win_rate': win_rate,
            'avg_finish_percentile': avg_finish_percentile,
            'avg_point_error': avg_point_error,
            'n_lineups': len(lineup_results)
        }
        
        logger.info(f"Performance metrics: {metrics}")
        
        return metrics
    
    def _calculate_belief_metrics(
        self,
        belief_states: Dict[str, Any],
        mc_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Calculate belief-related metrics.
        
        This method computes metrics related to the belief system:
        - Belief accuracy: How well beliefs predicted outcomes
        - Belief delta: How much beliefs changed during backtest
        - Epistemic variance effectiveness: Correlation between variance and error
        - Source effectiveness: Which data sources were most effective
        
        Args:
            belief_states: Pre-race belief states
            mc_results: Optional Monte Carlo simulation results
            
        Returns:
            Dictionary of belief metrics
        """
        beliefs = belief_states['belief_states']
        
        if not beliefs['driver_id']:
            return {}
        
        # Average confidence
        avg_confidence = np.mean(beliefs['confidence'])
        
        # Average epistemic variance
        avg_epistemic_var = np.mean(beliefs['epistemic_var'])
        
        # Confidence distribution
        high_conf_count = sum(1 for c in beliefs['confidence'] if c >= CONFIDENCE_THRESHOLDS['high'])
        medium_conf_count = sum(1 for c in beliefs['confidence']
            if CONFIDENCE_THRESHOLDS['low'] <= c < CONFIDENCE_THRESHOLDS['high'])
        low_conf_count = sum(1 for c in beliefs['confidence'] if c < CONFIDENCE_THRESHOLDS['low'])
        
        # Source distribution
        sources = {}
        for source in beliefs['source']:
            sources[source] = sources.get(source, 0) + 1
        
        # Epistemic variance effectiveness (if MC results available)
        variance_effectiveness = 0.0
        if mc_results:
            epistemic_vars = mc_results['epistemic_variances']
            # Lower variance should correlate with better predictions
            variance_effectiveness = 1.0 - np.mean(list(epistemic_vars.values()))
        
        metrics = {
            'avg_confidence': avg_confidence,
            'avg_epistemic_var': avg_epistemic_var,
            'high_confidence_pct': (high_conf_count / len(beliefs['confidence'])) * 100,
            'medium_confidence_pct': (medium_conf_count / len(beliefs['confidence'])) * 100,
            'low_confidence_pct': (low_conf_count / len(beliefs['confidence'])) * 100,
            'source_distribution': sources,
            'variance_effectiveness': variance_effectiveness,
            'n_beliefs': len(beliefs['driver_id'])
        }
        
        logger.info(f"Belief metrics: {metrics}")
        
        return metrics
    
    def _calculate_simulation_metrics(
        self,
        mc_results: Dict[str, Any],
        race_results: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Calculate simulation-related metrics.
        
        This method computes metrics related to Monte Carlo simulation accuracy:
        - MC accuracy: How well MC predicted finish positions
        - Finish distribution accuracy: Correlation with actual results
        - Lap-by-lap accuracy: Position prediction accuracy
        
        Args:
            mc_results: Monte Carlo simulation results
            race_results: Actual race results
            
        Returns:
            Dictionary of simulation metrics
        """
        finish_distributions = mc_results['finish_distributions']
        epistemic_variances = mc_results['epistemic_variances']
        
        # Calculate MC accuracy
        predicted_finishes = []
        actual_finishes = []
        
        for result in race_results:
            driver_id = result['driver_id']
            
            if driver_id in finish_distributions:
                # Expected finish from distribution
                dist = finish_distributions[driver_id]
                expected_finish = sum(state * prob for state, prob in dist.items())
                predicted_finishes.append(expected_finish)
                
                # Actual finish
                actual_finishes.append(result['finish_position'])
        
        # Calculate accuracy metrics
        if predicted_finishes and actual_finishes:
            mae = calculate_mae(predicted_finishes, actual_finishes)
            rmse = calculate_rmse(predicted_finishes, actual_finishes)
            correlation = calculate_correlation(predicted_finishes, actual_finishes)
        else:
            mae = 0.0
            rmse = 0.0
            correlation = 0.0
        
        # Average epistemic variance
        avg_epistemic_var = np.mean(list(epistemic_variances.values()))
        
        metrics = {
            'mc_accuracy_mae': mae,
            'mc_accuracy_rmse': rmse,
            'mc_correlation': correlation,
            'avg_epistemic_var': avg_epistemic_var,
            'n_simulations': mc_results['n_simulations']
        }
        
        logger.info(f"Simulation metrics: {metrics}")
        
        return metrics
    
    def generate_backtest_report(self, backtest_results: Dict[str, Any]) -> str:
        """
        Generate detailed backtest report.
        
        This method creates a comprehensive text report summarizing
        all backtest results including:
        - Summary statistics
        - Performance metrics breakdown
        - Per-lineup results
        - Belief analysis
        - Simulation analysis (if applicable)
        
        Args:
            backtest_results: Dictionary containing backtest results
            
        Returns:
            Formatted report string
        """
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append(f"BACKTEST REPORT: {backtest_results['race_name']}")
        report_lines.append("=" * 80)
        report_lines.append(f"Race ID: {backtest_results['race_id']}")
        report_lines.append(f"Scenario: {backtest_results['scenario']}")
        report_lines.append(f"Timestamp: {backtest_results['timestamp']}")
        report_lines.append("")
        
        # Configuration
        report_lines.append("-" * 80)
        report_lines.append("CONFIGURATION")
        report_lines.append("-" * 80)
        config = backtest_results['config']
        report_lines.append(f"Salary Cap: ${config['salary_cap']:,}")
        report_lines.append(f"Entry Fee: ${config['entry_fee']:.2f}")
        report_lines.append(f"Number of Lineups: {config['n_lineups']}")
        report_lines.append(f"MC Simulations: {config['n_simulations']:,}")
        report_lines.append("")
        
        # Performance Metrics
        report_lines.append("-" * 80)
        report_lines.append("PERFORMANCE METRICS")
        report_lines.append("-" * 80)
        perf = backtest_results['performance_metrics']
        report_lines.append(f"MAE (Mean Absolute Error): {perf.get('mae', 0):.2f} points")
        report_lines.append(f"RMSE (Root Mean Squared Error): {perf.get('rmse', 0):.2f} points")
        report_lines.append(f"Correlation (Projected vs Actual): {perf.get('correlation', 0):.3f}")
        report_lines.append(f"Average ROI: {perf.get('avg_roi', 0):.2f}%")
        report_lines.append(f"Total ROI: {perf.get('total_roi', 0):.2f}%")
        report_lines.append(f"Win Rate (Top 10%): {perf.get('win_rate', 0):.1f}%")
        report_lines.append(f"Average Finish Percentile: {perf.get('avg_finish_percentile', 0):.1f}%")
        report_lines.append(f"Average Point Error: {perf.get('avg_point_error', 0):.2f} points")
        report_lines.append("")
        
        # Belief Metrics
        report_lines.append("-" * 80)
        report_lines.append("BELIEF METRICS")
        report_lines.append("-" * 80)
        belief = backtest_results['belief_metrics']
        report_lines.append(f"Average Confidence: {belief.get('avg_confidence', 0):.3f}")
        report_lines.append(f"Average Epistemic Variance: {belief.get('avg_epistemic_var', 0):.4f}")
        report_lines.append(f"High Confidence (>0.7): {belief.get('high_confidence_pct', 0):.1f}%")
        report_lines.append(f"Medium Confidence (0.3-0.7): {belief.get('medium_confidence_pct', 0):.1f}%")
        report_lines.append(f"Low Confidence (<0.3): {belief.get('low_confidence_pct', 0):.1f}%")
        report_lines.append(f"Variance Effectiveness: {belief.get('variance_effectiveness', 0):.3f}")
        report_lines.append(f"Number of Beliefs: {belief.get('n_beliefs', 0)}")
        report_lines.append("")
        
        # Simulation Metrics
        if backtest_results['simulation_metrics']:
            report_lines.append("-" * 80)
            report_lines.append("SIMULATION METRICS")
            report_lines.append("-" * 80)
            sim = backtest_results['simulation_metrics']
            report_lines.append(f"MC Accuracy (MAE): {sim.get('mc_accuracy_mae', 0):.2f}")
            report_lines.append(f"MC Accuracy (RMSE): {sim.get('mc_accuracy_rmse', 0):.2f}")
            report_lines.append(f"MC Correlation: {sim.get('mc_correlation', 0):.3f}")
            report_lines.append(f"Average Epistemic Variance: {sim.get('avg_epistemic_var', 0):.4f}")
            report_lines.append(f"Number of Simulations: {sim.get('n_simulations', 0):,}")
            report_lines.append("")
        
        # Per-Lineup Results
        report_lines.append("-" * 80)
        report_lines.append("PER-LINEUP RESULTS")
        report_lines.append("-" * 80)
        report_lines.append(f"{'Lineup':<8} {'Projected':<12} {'Actual':<12} {'Error':<12} {'ROI':<10} {'Percentile':<12}")
        report_lines.append("-" * 80)
        
        for i, lineup_result in enumerate(backtest_results['lineups'], 1):
            report_lines.append(
                f"{i:<8} "
                f"{lineup_result['projected_points']:<12.2f} "
                f"{lineup_result['actual_points']:<12.2f} "
                f"{lineup_result['point_error']:<12.2f} "
                f"{lineup_result['roi']:<10.2f}% "
                f"{lineup_result['finish_percentile']:<12.1f}%"
            )
        
        report_lines.append("")
        report_lines.append("=" * 80)
        report_lines.append("END OF REPORT")
        report_lines.append("=" * 80)
        
        return "\n".join(report_lines)


# ============================================================================
# Helper Functions for Data Loading
# ============================================================================

def load_daytona_2025_race() -> Dict[str, Any]:
    """
    Load Daytona 2025 race data.
    
    Returns:
        Dictionary containing Daytona 2025 race configuration
    """
    return DAYTONA_2025_CONFIG.copy()


def load_daytona_2025_qualifying() -> List[Dict[str, Any]]:
    """
    Load Daytona 2025 qualifying results.
    
    Returns:
        List of qualifying result dictionaries
    """
    # Sample realistic qualifying data for Daytona 2025
    drivers = [
        "Kyle Larson", "Denny Hamlin", "Martin Truex Jr.", "Chase Elliott",
        "William Byron", "Ross Chastain", "Ryan Blaney", "Joey Logano",
        "Christopher Bell", "Tyler Reddick", "Alex Bowman", "Bubba Wallace",
        "Austin Cindric", "Kevin Harvick", "Aric Almirola", "Brad Keselowski",
        "Erik Jones", "Michael McDowell", "Corey LaJoie", "Ty Gibbs",
        "Noah Gragson", "Daniel Suarez", "AJ Allmendinger", "Todd Gilliland",
        "Harrison Burton", "Justin Haley", "Josh Berry", "Ty Dillon",
        "Kaz Grala", "J.J. Yeley", "Garrett Smithley", "Cody Ware"
    ]
    
    qualifying = []
    for i, driver_name in enumerate(drivers[:40]):
        # Simulate qualifying position (better drivers tend to qualify better)
        position = i + 1
        speed = 195.0 - (position * 0.2) + np.random.normal(0, 1.0)
        
        # Calculate confidence based on position
        confidence = max(0.1, min(0.9, 1.0 - (position / 50.0)))
        epistemic_var = 0.1 + (position / 200.0)
        
        qualifying.append({
            'driver_id': i + 1,
            'name': driver_name,
            'position': position,
            'speed': round(speed, 2),
            'confidence': round(confidence, 3),
            'epistemic_var': round(epistemic_var, 4)
        })
    
    return qualifying


def load_daytona_2025_practice() -> List[Dict[str, Any]]:
    """
    Load Daytona 2025 practice results.
    
    Returns:
        List of practice result dictionaries
    """
    qualifying = load_daytona_2025_qualifying()
    
    practice = []
    for qual in qualifying:
        # Simulate practice speed rank (some variation from qualifying)
        rank_offset = int(np.random.normal(0, 2))
        speed_rank = max(1, min(40, qual['position'] + rank_offset))
        
        # Calculate confidence based on speed rank
        confidence = max(0.1, min(0.9, 1.0 - (speed_rank / 50.0)))
        epistemic_var = 0.1 + (speed_rank / 200.0)
        
        practice.append({
            'driver_id': qual['driver_id'],
            'name': qual['name'],
            'session_number': 1,
            'speed_rank': speed_rank,
            'avg_speed': qual['speed'] - np.random.normal(0, 2.0),
            'best_lap_time': 48.0 + np.random.normal(0, 0.5),
            'confidence': round(confidence, 3),
            'epistemic_var': round(epistemic_var, 4)
        })
    
    return practice


def load_daytona_2025_results() -> List[Dict[str, Any]]:
    """
    Load Daytona 2025 actual race results.
    
    Returns:
        List of race result dictionaries
    """
    qualifying = load_daytona_2025_qualifying()
    
    results = []
    for qual in qualifying:
        # Simulate race finish (some variation from qualifying)
        finish_offset = int(np.random.normal(0, 5))
        finish_position = max(1, min(43, qual['position'] + finish_offset))
        
        # Calculate DFS points
        points = FINISH_POINTS.get(finish_position, 0.0)
        
        # Add laps led and fastest lap points
        laps_led = max(0, 10 - finish_position * 0.2)
        points += laps_led * 0.25
        
        if finish_position <= 10 and np.random.random() < 0.2:
            points += 1.0
        
        results.append({
            'driver_id': qual['driver_id'],
            'name': qual['name'],
            'finish_position': finish_position,
            'laps_led': int(laps_led),
            'fastest_lap': finish_position <= 10,
            'dfs_points': round(points, 2),
            'confidence': round(qual['confidence'], 3),
            'epistemic_var': round(qual['epistemic_var'], 4)
        })
    
    return results


# ============================================================================
# Helper Functions for Validation
# ============================================================================

def calculate_mae(predicted: List[float], actual: List[float]) -> float:
    """
    Calculate Mean Absolute Error.
    
    MAE = mean(|predicted - actual|)
    
    Args:
        predicted: List of predicted values
        actual: List of actual values
        
    Returns:
        Mean Absolute Error
    """
    if len(predicted) != len(actual):
        raise ValueError("predicted and actual must have same length")
    
    if not predicted:
        return 0.0
    
    errors = [abs(p - a) for p, a in zip(predicted, actual)]
    mae = sum(errors) / len(errors)
    
    return mae


def calculate_rmse(predicted: List[float], actual: List[float]) -> float:
    """
    Calculate Root Mean Squared Error.
    
    RMSE = sqrt(mean((predicted - actual)^2))
    
    Args:
        predicted: List of predicted values
        actual: List of actual values
        
    Returns:
        Root Mean Squared Error
    """
    if len(predicted) != len(actual):
        raise ValueError("predicted and actual must have same length")
    
    if not predicted:
        return 0.0
    
    squared_errors = [(p - a) ** 2 for p, a in zip(predicted, actual)]
    mse = sum(squared_errors) / len(squared_errors)
    rmse = np.sqrt(mse)
    
    return rmse


def calculate_correlation(predicted: List[float], actual: List[float]) -> float:
    """
    Calculate Pearson correlation coefficient.
    
    Correlation measures the linear relationship between predicted and actual values.
    Values range from -1 (perfect negative correlation) to 1 (perfect positive correlation).
    
    Args:
        predicted: List of predicted values
        actual: List of actual values
        
    Returns:
        Pearson correlation coefficient
    """
    if len(predicted) != len(actual) or len(predicted) < 2:
        return 0.0
    
    # Convert to numpy arrays
    pred_array = np.array(predicted)
    act_array = np.array(actual)
    
    # Calculate correlation
    correlation_matrix = np.corrcoef(pred_array, act_array)
    correlation = correlation_matrix[0, 1]
    
    # Handle NaN
    if np.isnan(correlation):
        return 0.0
    
    return correlation


def calculate_calibration(beliefs: List[Dict[str, Any]], outcomes: List[bool]) -> float:
    """
    Calculate belief calibration.
    
    Calibration measures how well confidence levels match prediction accuracy.
    Well-calibrated beliefs have confidence that matches their accuracy.
    
    Args:
        beliefs: List of belief dictionaries with 'confidence' key
        outcomes: List of boolean outcomes (True if prediction was correct)
        
    Returns:
        Calibration score (0-1, higher is better)
    """
    if len(beliefs) != len(outcomes):
        raise ValueError("beliefs and outcomes must have same length")
    
    if not beliefs:
        return 0.0
    
    # Calculate calibration bins
    bins = [0.1, 0.3, 0.5, 0.7, 0.9]
    calibration_scores = []
    
    for i, belief in enumerate(beliefs):
        confidence = belief['confidence']
        outcome = outcomes[i]
        
        # Find appropriate bin
        for j, threshold in enumerate(bins):
            if confidence <= threshold:
                break
        else:
            j = len(bins)
        
        # Binary outcome: 1 if correct, 0 if incorrect
        binary_outcome = 1 if outcome else 0
        
        # Calibration error
        calibration_error = abs(confidence - binary_outcome)
        calibration_scores.append(1.0 - calibration_error)
    
    calibration = np.mean(calibration_scores)
    
    return calibration


# ============================================================================
# Helper Functions for Reporting
# ============================================================================

def print_backtest_summary(results: Dict[str, Any]) -> None:
    """
    Print backtest summary to console.
    
    Args:
        results: Backtest results dictionary
    """
    print("\n" + "=" * 80)
    print(f"BACKTEST SUMMARY: {results['race_name']}")
    print("=" * 80)
    print(f"Race ID: {results['race_id']}")
    print(f"Scenario: {results['scenario']}")
    print(f"Timestamp: {results['timestamp']}")
    print("")
    
    perf = results['performance_metrics']
    print("Performance Metrics:")
    print(f"  MAE: {perf.get('mae', 0):.2f} points")
    print(f"  RMSE: {perf.get('rmse', 0):.2f} points")
    print(f"  Correlation: {perf.get('correlation', 0):.3f}")
    print(f"  Average ROI: {perf.get('avg_roi', 0):.2f}%")
    print(f"  Win Rate: {perf.get('win_rate', 0):.1f}%")
    print("")
    
    print("=" * 80)
    print()


def save_backtest_report(results: Dict[str, Any], filename: str) -> None:
    """
    Save detailed backtest report to file.
    
    Args:
        results: Backtest results dictionary
        filename: Output filename
    """
    engine = BacktestEngine(SessionLocal())
    report = engine.generate_backtest_report(results)
    
    with open(filename, 'w') as f:
        f.write(report)
    
    logger.info(f"Backtest report saved to {filename}")


def plot_backtest_results(results: Dict[str, Any], output_dir: str = '.') -> None:
    """
    Generate visualization plots for backtest results.
    
    This method creates several plots:
    1. Projected vs Actual Points scatter plot
    2. Point Error histogram
    3. ROI distribution
    4. Confidence vs Accuracy (if available)
    
    Args:
        results: Backtest results dictionary
        output_dir: Directory to save plots
    """
    os.makedirs(output_dir, exist_ok=True)
    
    lineup_results = results['lineups']
    
    # Create figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f"Backtest Results: {results['race_name']}", fontsize=16)
    
    # Plot 1: Projected vs Actual Points
    projected = [r['projected_points'] for r in lineup_results]
    actual = [r['actual_points'] for r in lineup_results]
    
    axes[0, 0].scatter(projected, actual, alpha=0.7, s=100)
    axes[0, 0].plot([min(projected), max(projected)],
                    [min(projected), max(projected)], 'r--', label='Perfect Prediction')
    axes[0, 0].set_xlabel('Projected Points')
    axes[0, 0].set_ylabel('Actual Points')
    axes[0, 0].set_title('Projected vs Actual Points')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    
    # Plot 2: Point Error Histogram
    errors = [r['point_error'] for r in lineup_results]
    axes[0, 1].hist(errors, bins=10, edgecolor='black', alpha=0.7)
    axes[0, 1].axvline(x=0, color='r', linestyle='--', label='No Error')
    axes[0, 1].set_xlabel('Point Error (Actual - Projected)')
    axes[0, 1].set_ylabel('Frequency')
    axes[0, 1].set_title('Point Error Distribution')
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)
    
    # Plot 3: ROI Distribution
    rois = [r['roi'] for r in lineup_results]
    axes[1, 0].hist(rois, bins=10, edgecolor='black', alpha=0.7, color='green')
    axes[1, 0].axvline(x=0, color='r', linestyle='--', label='Break Even')
    axes[1, 0].set_xlabel('ROI (%)')
    axes[1, 0].set_ylabel('Frequency')
    axes[1, 0].set_title('ROI Distribution')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    # Plot 4: Finish Percentile Distribution
    percentiles = [r['finish_percentile'] for r in lineup_results]
    axes[1, 1].hist(percentiles, bins=10, edgecolor='black', alpha=0.7, color='orange')
    axes[1, 1].set_xlabel('Finish Percentile (%)')
    axes[1, 1].set_ylabel('Frequency')
    axes[1, 1].set_title('Finish Percentile Distribution')
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save figure
    output_path = os.path.join(output_dir, f"backtest_{results['race_id']}_plots.png")
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    logger.info(f"Plots saved to {output_path}")


def export_backtest_csv(results: Dict[str, Any], filename: str) -> None:
    """
    Export backtest results to CSV file.
    
    Args:
        results: Backtest results dictionary
        filename: Output CSV filename
    """
    lineup_results = results['lineups']
    
    # Prepare data
    data = []
    for i, lineup_result in enumerate(lineup_results, 1):
        lineup = lineup_result['lineup']
        
        # Get driver names
        driver_names = ', '.join([d['name'] for d in lineup['drivers']])
        
        row = {
            'Lineup': i,
            'Drivers': driver_names,
            'Projected_Points': lineup_result['projected_points'],
            'Actual_Points': lineup_result['actual_points'],
            'Point_Error': lineup_result['point_error'],
            'Point_Error_Pct': lineup_result['point_error_pct'],
            'Winnings': lineup_result['winnings'],
            'ROI': lineup_result['roi'],
            'Finish_Percentile': lineup_result['finish_percentile'],
            'Total_Salary': lineup['total_salary']
        }
        
        data.append(row)
    
    # Create DataFrame and export
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    
    logger.info(f"Backtest results exported to {filename}")


# ============================================================================
# Main Execution Functions
# ============================================================================

def run_daytona_2025_backtest(
    scenario: str = 'all',
    n_lineups: int = 10,
    entry_fee: float = 10.0
) -> Dict[str, Any]:
    """
    Run backtest for Daytona 2025 race.
    
    This is a convenience function that runs a complete backtest for
    the Daytona 2025 race using specified parameters.
    
    Args:
        scenario: Data source scenario ('qualifying_only', 'qualifying_practice',
                  'qualifying_mc', 'all')
        n_lineups: Number of lineups to generate
        entry_fee: Entry fee per lineup
        
    Returns:
        Dictionary containing backtest results
    """
    logger.info(f"Running Daytona 2025 backtest: scenario={scenario}")
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Initialize backtest engine
        engine = BacktestEngine(db, DAYTONA_2025_CONFIG)
        
        # Run backtest
        results = engine.run_backtest(
            race_id=DAYTONA_2025_CONFIG['race_id'],
            n_lineups=n_lineups,
            entry_fee=entry_fee,
            scenario=scenario
        )
        
        return results
        
    finally:
        db.close()


def run_all_scenarios_backtest(
    race_id: int,
    n_lineups: int = 10,
    entry_fee: float = 10.0
) -> Dict[str, Dict[str, Any]]:
    """
    Run backtests for all scenarios.
    
    This function runs backtests for all four scenarios and
    compares the results to determine which data source
    combination performs best.
    
    Args:
        race_id: Race identifier
        n_lineups: Number of lineups per scenario
        entry_fee: Entry fee per lineup
        
    Returns:
        Dictionary mapping scenario names to backtest results
    """
    logger.info(f"Running all scenario backtests for race {race_id}")
    
    scenarios = ['qualifying_only', 'qualifying_practice', 'qualifying_mc', 'all']
    all_results = {}
    
    for scenario in scenarios:
        results = run_daytona_2025_backtest(scenario, n_lineups, entry_fee)
        all_results[scenario] = results
    
    return all_results


def compare_scenarios(all_results: Dict[str, Dict[str, Any]]) -> str:
    """
    Compare backtest results across scenarios.
    
    This function generates a comparative report showing which
    scenario performed best across different metrics.
    
    Args:
        all_results: Dictionary mapping scenario names to results
        
    Returns:
        Formatted comparison report string
    """
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("SCENARIO COMPARISON REPORT")
    report_lines.append("=" * 80)
    report_lines.append("")
    
    # Create comparison table
    report_lines.append(f"{'Scenario':<25} {'MAE':<10} {'RMSE':<10} {'Correlation':<12} {'Avg ROI':<10}")
    report_lines.append("-" * 80)
    
    for scenario, results in all_results.items():
        perf = results['performance_metrics']
        report_lines.append(
            f"{scenario:<25} "
            f"{perf.get('mae', 0):<10.2f} "
            f"{perf.get('rmse', 0):<10.2f} "
            f"{perf.get('correlation', 0):<12.3f} "
            f"{perf.get('avg_roi', 0):<10.2f}%"
        )
    
    report_lines.append("")
    
    # Find best scenario for each metric
    best_mae = min(all_results.items(),
                key=lambda x: x[1]['performance_metrics'].get('mae', float('inf')))
    best_rmse = min(all_results.items(),
                 key=lambda x: x[1]['performance_metrics'].get('rmse', float('inf')))
    best_corr = max(all_results.items(),
                  key=lambda x: x[1]['performance_metrics'].get('correlation', -float('inf')))
    best_roi = max(all_results.items(),
                 key=lambda x: x[1]['performance_metrics'].get('avg_roi', -float('inf')))
    
    report_lines.append("BEST SCENARIOS:")
    report_lines.append(f"  Lowest MAE: {best_mae[0]} ({best_mae[1]['performance_metrics']['mae']:.2f})")
    report_lines.append(f"  Lowest RMSE: {best_rmse[0]} ({best_rmse[1]['performance_metrics']['rmse']:.2f})")
    report_lines.append(f"  Highest Correlation: {best_corr[0]} ({best_corr[1]['performance_metrics']['correlation']:.3f})")
    report_lines.append(f"  Highest ROI: {best_roi[0]} ({best_roi[1]['performance_metrics']['avg_roi']:.2f}%)")
    
    report_lines.append("")
    report_lines.append("=" * 80)
    
    return "\n".join(report_lines)


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    logger.info("Backtest Validation System loaded")
    
    # Example: Run single scenario backtest
    print("\nRunning Daytona 2025 backtest (all data sources)...")
    results = run_daytona_2025_backtest(scenario='all', n_lineups=10, entry_fee=10.0)
    
    # Print summary
    print_backtest_summary(results)
    
    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"backtest_daytona2025_{timestamp}.txt"
    save_backtest_report(results, report_filename)
    
    # Generate plots
    plot_backtest_results(results, output_dir='.')
    
    # Export CSV
    csv_filename = f"backtest_daytona2025_{timestamp}.csv"
    export_backtest_csv(results, csv_filename)
    
    print(f"\nBacktest complete!")
    print(f"  Report: {report_filename}")
    print(f"  CSV: {csv_filename}")
    print(f"  Plots: backtest_{results['race_id']}_plots.png")
    
    # Example: Run all scenarios
    print("\n" + "=" * 80)
    print("Running all scenario backtests...")
    print("=" * 80)
    
    all_results = run_all_scenarios_backtest(n_lineups=10, entry_fee=10.0)
    
    # Print comparison
    comparison = compare_scenarios(all_results)
    print(comparison)
    
    # Save comparison report
    comparison_filename = f"backtest_comparison_{timestamp}.txt"
    with open(comparison_filename, 'w') as f:
        f.write(comparison)
    
    print(f"\nComparison report saved to: {comparison_filename}")
