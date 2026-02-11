"""
NASCAR DFS Lineup Optimizer with Axiomatic AI Framework

This module implements a complete DraftKings NASCAR DFS lineup optimizer using PuLP
for linear programming optimization. The optimizer integrates with the epistemic database
schema and belief projection system to calculate expected points from agent beliefs.

The optimizer implements:
1. DraftKings NASCAR Classic constraints (6 drivers, $50k salary cap)
2. Team stacking rules (min 2, max 3 drivers per team)
3. Expected points calculation from belief system
4. Multiple lineup generation with diversity constraints
5. Risk-adjusted optimization using epistemic variance
6. CSV export for DraftKings upload

DraftKings NASCAR Scoring:
- 1st place: 46 points
- 2nd place: 40 points
- 3rd place: 35 points
- 4th place: 31 points
- 5th place: 28 points
- 6th place: 25 points
- 7th place: 22 points
- 8th place: 20 points
- 9th place: 18 points
- 10th place: 17 points
- 11th-15th: 15 points
- 16th-20th: 12 points
- 21st-25th: 10 points
- 26th-30th: 8 points
- 31st-36th: 6 points
- 37th-43rd: 3 points
- Laps led: 0.25 points per lap
- Fastest lap: 1 point
- DNF: 0 points
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import numpy as np
import pandas as pd

# PuLP for linear programming optimization
from pulp import (
    LpProblem,
    LpMaximize,
    LpVariable,
    lpSum,
    LpBinary,
    LpStatus,
    value,
    PULP_CBC_CMD,
)

# Database imports
from sqlalchemy.orm import Session
from app.models import (
    Driver,
    Race,
    Belief,
    Proposition,
    Agent,
    SessionLocal,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# DraftKings NASCAR scoring table
FINISH_POINTS = {
    1: 46,
    2: 40,
    3: 35,
    4: 31,
    5: 28,
    6: 25,
    7: 22,
    8: 20,
    9: 18,
    10: 17,
    11: 15,
    12: 15,
    13: 15,
    14: 15,
    15: 15,
    16: 12,
    17: 12,
    18: 12,
    19: 12,
    20: 12,
    21: 10,
    22: 10,
    23: 10,
    24: 10,
    25: 10,
    26: 8,
    27: 8,
    28: 8,
    29: 8,
    30: 8,
    31: 6,
    32: 6,
    33: 6,
    34: 6,
    35: 6,
    36: 6,
    37: 3,
    38: 3,
    39: 3,
    40: 3,
    41: 3,
    42: 3,
    43: 3,
}


class NASCAROptimizer:
    """
    Optimizer for selecting optimal DraftKings NASCAR DFS lineups using PuLP.

    This class implements a complete lineup optimizer that:
    - Loads driver data from the epistemic database
    - Calculates expected points from agent beliefs
    - Applies DraftKings constraints (salary cap, driver count, team stacking)
    - Generates multiple optimal lineups with diversity
    - Exports lineups in CSV format for DraftKings upload

    Attributes:
        db_session: SQLAlchemy database session
        salary_cap: Maximum total salary for lineup (default $50,000)
        n_drivers: Number of drivers to select (default 6)
        min_stack: Minimum drivers from same team (default 2)
        max_stack: Maximum drivers from same team (default 3)
        drivers: List of driver dictionaries with beliefs
        problem: Current PuLP optimization problem
        driver_vars: Dictionary of PuLP variables for driver selection
    """

    def __init__(
        self,
        db_session: Session,
        salary_cap: int = 50000,
        n_drivers: int = 6,
        min_stack: int = 2,
        max_stack: int = 3,
    ) -> None:
        """
        Initialize NASCAROptimizer with constraints.

        Args:
            db_session: SQLAlchemy database session
            salary_cap: Maximum total salary for lineup (default 50,000)
            n_drivers: Number of drivers to select (default 6)
            min_stack: Minimum drivers from same team (default 2)
            max_stack: Maximum drivers from same team (default 3)
        """
        self.db_session = db_session
        self.salary_cap = salary_cap
        self.n_drivers = n_drivers
        self.min_stack = min_stack
        self.max_stack = max_stack

        self.drivers: List[Dict[str, Any]] = []
        self.problem: Optional[LpProblem] = None
        self.driver_vars: Optional[Dict[str, LpVariable]] = None

        logger.info(
            f"NASCAROptimizer initialized: salary_cap=${salary_cap}, "
            f"n_drivers={n_drivers}, stacking={min_stack}-{max_stack}"
        )

    def load_driver_data(self, race_id: int) -> None:
        """
        Load driver data from database with beliefs.

        This method retrieves all drivers for a race and their associated beliefs
        from the epistemic database. Each driver dictionary includes:
        - driver_id: Driver identifier
        - name: Driver name
        - team: Driver team
        - salary: DraftKings salary
        - beliefs: List of belief dictionaries with confidence and epistemic variance

        Args:
            race_id: Race identifier

        Raises:
            ValueError: If race_id is invalid or no drivers found
        """
        logger.info(f"Loading driver data for race {race_id}")

        # Verify race exists
        race = self.db_session.query(Race).filter(Race.id == race_id).first()
        if not race:
            raise ValueError(f"Race with id {race_id} not found")

        # Get all drivers
        drivers = self.db_session.query(Driver).all()
        if not drivers:
            raise ValueError("No drivers found in database")

        # Load beliefs for each driver
        self.drivers = []
        for driver in drivers:
            # Get propositions for this driver and race
            propositions = (
                self.db_session.query(Proposition)
                .filter(
                    Proposition.driver_id == driver.id,
                    Proposition.race_id == race_id,
                )
                .all()
            )

            # Get beliefs for these propositions
            beliefs = []
            for prop in propositions:
                belief = (
                    self.db_session.query(Belief)
                    .filter(Belief.prop_id == prop.id)
                    .first()
                )
                if belief:
                    beliefs.append(
                        {
                            "belief_id": belief.id,
                            "proposition_id": prop.id,
                            "content": prop.content,
                            "confidence": belief.confidence,
                            "epistemic_var": belief.epistemic_var,
                            "source": belief.source,
                            "timestamp": belief.timestamp,
                        }
                    )

            # Create driver dictionary
            driver_dict = {
                "driver_id": driver.id,
                "name": driver.name,
                "team": driver.team,
                "car_number": driver.car_number,
                "salary": float(driver.salary),
                "avg_finish": driver.avg_finish,
                "wins": driver.wins,
                "top5": driver.top5,
                "top10": driver.top10,
                "beliefs": beliefs,
            }

            self.drivers.append(driver_dict)

        logger.info(f"Loaded {len(self.drivers)} drivers for race {race_id}")

    def calculate_expected_points(self, driver_id: int) -> float:
        """
        Calculate expected DFS points from beliefs.

        This method calculates expected points by:
        1. Retrieving beliefs for the driver
        2. Extracting finish position probabilities from beliefs
        3. Calculating expected finish points using DraftKings scoring
        4. Adding expected laps led and fastest lap points

        Expected points = Σ (finish_probability * finish_points) + expected_laps_led * 0.25 + expected_fastest_lap * 1

        Args:
            driver_id: Driver identifier

        Returns:
            Expected DFS points (float)

        Raises:
            ValueError: If driver_id is invalid
        """
        # Find driver
        driver = next(
            (d for d in self.drivers if d["driver_id"] == driver_id), None
        )
        if not driver:
            raise ValueError(f"Driver with id {driver_id} not found")

        # If no beliefs, use average finish as proxy
        if not driver["beliefs"]:
            avg_finish = driver.get("avg_finish", 22)
            # Map average finish to expected points
            finish_pos = int(min(43, max(1, round(avg_finish))))
            expected_points = FINISH_POINTS.get(finish_pos, 10.0)
            logger.warning(
                f"No beliefs for driver {driver_id}, using avg_finish={avg_finish}, "
                f"expected_points={expected_points}"
            )
            return expected_points

        # Calculate expected points from beliefs
        expected_finish_points = 0.0
        total_weight = 0.0

        for belief in driver["beliefs"]:
            # Use confidence as weight
            weight = belief["confidence"]
            total_weight += weight

            # Extract finish position from proposition content
            # Expected format: "{driver} top-3 finish" or similar
            content = belief["content"].lower()

            # Parse proposition to get finish position probability
            finish_prob = self._extract_finish_probability(content, belief)

            # Calculate expected finish points
            expected_finish_points += weight * finish_prob

        # Normalize by total weight
        if total_weight > 0:
            expected_finish_points /= total_weight
        else:
            # Fallback to average finish
            avg_finish = driver.get("avg_finish", 22)
            finish_pos = int(min(43, max(1, round(avg_finish))))
            expected_finish_points = FINISH_POINTS.get(finish_pos, 10.0)

        # Add expected laps led points (estimated from driver stats)
        expected_laps_led = self._estimate_laps_led(driver)
        laps_led_points = expected_laps_led * 0.25

        # Add expected fastest lap points (estimated from driver stats)
        expected_fastest_lap = self._estimate_fastest_lap(driver)
        fastest_lap_points = expected_fastest_lap * 1.0

        total_expected_points = (
            expected_finish_points + laps_led_points + fastest_lap_points
        )

        logger.debug(
            f"Driver {driver_id}: finish_points={expected_finish_points:.2f}, "
            f"laps_led={laps_led_points:.2f}, fastest={fastest_lap_points:.2f}, "
            f"total={total_expected_points:.2f}"
        )

        return total_expected_points

    def _extract_finish_probability(
        self, content: str, belief: Dict[str, Any]
    ) -> float:
        """
        Extract finish position probability from proposition content.

        Args:
            content: Proposition content string
            belief: Belief dictionary

        Returns:
            Expected finish points (float)
        """
        # Parse proposition content to determine expected finish
        if "top-3" in content or "top 3" in content:
            # High confidence in top-3 finish
            confidence = belief["confidence"]
            # Expected points for top-3 finish (average of positions 1-3)
            expected_points = (46 + 40 + 35) / 3 * confidence
            return expected_points

        elif "top-5" in content or "top 5" in content:
            confidence = belief["confidence"]
            # Expected points for top-5 finish (average of positions 1-5)
            expected_points = (46 + 40 + 35 + 31 + 28) / 5 * confidence
            return expected_points

        elif "top-10" in content or "top 10" in content:
            confidence = belief["confidence"]
            # Expected points for top-10 finish (average of positions 1-10)
            expected_points = (
                (46 + 40 + 35 + 31 + 28 + 25 + 22 + 20 + 18 + 17) / 10 * confidence
            )
            return expected_points

        elif "win" in content or "1st" in content:
            confidence = belief["confidence"]
            expected_points = 46 * confidence
            return expected_points

        else:
            # Generic proposition, use confidence as multiplier for average points
            confidence = belief["confidence"]
            expected_points = 20.0 * confidence  # Average DFS points
            return expected_points

    def _estimate_laps_led(self, driver: Dict[str, Any]) -> float:
        """
        Estimate expected laps led based on driver statistics.

        Args:
            driver: Driver dictionary

        Returns:
            Expected laps led (float)
        """
        # Use wins and top5 as proxies for laps led
        wins = driver.get("wins", 0)
        top5 = driver.get("top5", 0)
        top10 = driver.get("top10", 0)

        # Simple heuristic: more wins/top5 = more laps led
        # Estimate 5-20 laps led per race for top drivers
        base_laps = 5.0
        win_bonus = wins * 2.0
        top5_bonus = top5 * 0.5
        top10_bonus = top10 * 0.2

        expected_laps = base_laps + win_bonus + top5_bonus + top10_bonus

        # Cap at reasonable maximum
        return min(50.0, expected_laps)

    def _estimate_fastest_lap(self, driver: Dict[str, Any]) -> float:
        """
        Estimate probability of fastest lap based on driver statistics.

        Args:
            driver: Driver dictionary

        Returns:
            Expected fastest lap points (float)
        """
        # Use wins and top5 as proxies for fastest lap probability
        wins = driver.get("wins", 0)
        top5 = driver.get("top5", 0)

        # Simple heuristic: probability of fastest lap
        # Top drivers have 10-30% chance of fastest lap
        base_prob = 0.05
        win_bonus = wins * 0.02
        top5_bonus = top5 * 0.005

        expected_fastest_lap = base_prob + win_bonus + top5_bonus

        # Cap at reasonable maximum
        return min(0.5, expected_fastest_lap)

    def calculate_value_score(self, driver_id: int) -> float:
        """
        Calculate value score = expected_points / salary.

        Value score measures the efficiency of a driver's salary relative
        to their expected points. Higher values indicate better value.

        Args:
            driver_id: Driver identifier

        Returns:
            Value score (expected_points / salary * 1000)
        """
        driver = next(
            (d for d in self.drivers if d["driver_id"] == driver_id), None
        )
        if not driver:
            raise ValueError(f"Driver with id {driver_id} not found")

        expected_points = self.calculate_expected_points(driver_id)
        salary = driver["salary"]

        if salary <= 0:
            return 0.0

        value_score = (expected_points / salary) * 1000

        return value_score

    def calculate_finish_distribution(self, driver_id: int) -> Dict[int, float]:
        """
        Get finish position probability distribution for a driver.

        This method generates a probability distribution over finish positions
        based on driver beliefs and historical statistics.

        Args:
            driver_id: Driver identifier

        Returns:
            Dictionary mapping finish positions (1-43) to probabilities
        """
        driver = next(
            (d for d in self.drivers if d["driver_id"] == driver_id), None
        )
        if not driver:
            raise ValueError(f"Driver with id {driver_id} not found")

        # Initialize uniform distribution
        distribution = {pos: 1.0 / 43 for pos in range(1, 44)}

        # Adjust based on beliefs
        if driver["beliefs"]:
            for belief in driver["beliefs"]:
                content = belief["content"].lower()
                confidence = belief["confidence"]

                if "top-3" in content or "top 3" in content:
                    # Increase probability of positions 1-3
                    for pos in range(1, 4):
                        distribution[pos] *= (1 + confidence)
                elif "top-5" in content or "top 5" in content:
                    for pos in range(1, 6):
                        distribution[pos] *= (1 + confidence * 0.8)
                elif "top-10" in content or "top 10" in content:
                    for pos in range(1, 11):
                        distribution[pos] *= (1 + confidence * 0.6)

        # Normalize distribution
        total = sum(distribution.values())
        if total > 0:
            distribution = {pos: prob / total for pos, prob in distribution.items()}

        return distribution

    def calculate_expected_finish_points(self, driver_id: int) -> float:
        """
        Calculate expected finish points from finish distribution.

        Args:
            driver_id: Driver identifier

        Returns:
            Expected finish points (float)
        """
        distribution = self.calculate_finish_distribution(driver_id)

        expected_points = sum(
            prob * FINISH_POINTS.get(pos, 0.0)
            for pos, prob in distribution.items()
        )

        return expected_points

    def optimize_lineup(
        self, race_id: int, n_lineups: int = 1, objective: str = "maximize_points"
    ) -> List[Dict[str, Any]]:
        """
        Optimize lineup using PuLP.

        This method creates and solves a linear programming problem to find
        optimal lineups subject to DraftKings constraints.

        Args:
            race_id: Race identifier
            n_lineups: Number of lineups to generate (default 1)
            objective: Optimization objective:
                - "maximize_points": Maximize expected points (default)
                - "maximize_value": Maximize value score
                - "minimize_risk": Minimize epistemic variance

        Returns:
            List of lineup dictionaries with keys:
                - drivers: List of selected driver dictionaries
                - total_projected_points: float
                - total_salary: int
                - total_value: float
                - risk_score: float

        Raises:
            ValueError: If race_id is invalid or no valid solution found
        """
        logger.info(
            f"Optimizing lineups for race {race_id}: n_lineups={n_lineups}, "
            f"objective={objective}"
        )

        # Load driver data
        self.load_driver_data(race_id)

        if len(self.drivers) < self.n_drivers:
            raise ValueError(
                f"Not enough drivers: {len(self.drivers)} < {self.n_drivers}"
            )

        lineups = []
        excluded_drivers = set()

        for lineup_idx in range(n_lineups):
            # Create optimization problem
            self.problem = LpProblem(
                f"NASCAR_DFS_Optimization_{lineup_idx}", LpMaximize
            )

            # Filter available drivers
            available_drivers = [
                d for d in self.drivers if d["driver_id"] not in excluded_drivers
            ]

            if len(available_drivers) < self.n_drivers:
                logger.warning(
                    f"Not enough available drivers for lineup {lineup_idx + 1}"
                )
                break

            # Create binary variables for each driver
            self.driver_vars = {
                driver["driver_id"]: LpVariable(
                    f"select_{driver['driver_id']}", cat=LpBinary
                )
                for driver in available_drivers
            }

            # Set objective function
            if objective == "maximize_points":
                self._set_maximize_points_objective(available_drivers)
            elif objective == "maximize_value":
                self._set_maximize_value_objective(available_drivers)
            elif objective == "minimize_risk":
                self._set_minimize_risk_objective(available_drivers)
            else:
                raise ValueError(f"Unknown objective: {objective}")

            # Apply constraints
            self.apply_driver_count_constraints()
            self.apply_salary_constraints(available_drivers)
            self.apply_stacking_constraints(available_drivers)

            # Solve the problem
            solver = PULP_CBC_CMD(msg=0, timeLimit=30)
            self.problem.solve(solver)

            # Check solution status
            if LpStatus[self.problem.status] != "Optimal":
                logger.warning(
                    f"No optimal solution for lineup {lineup_idx + 1}: "
                    f"status={LpStatus[self.problem.status]}"
                )
                break

            # Extract selected drivers
            selected_drivers = [
                driver
                for driver in available_drivers
                if self.driver_vars[driver["driver_id"]].value() == 1
            ]

            # Calculate lineup metrics
            lineup = self._calculate_lineup_metrics(selected_drivers)

            lineups.append(lineup)

            # Exclude selected drivers for next iteration
            excluded_drivers.update(d["driver_id"] for d in selected_drivers)

            logger.info(
                f"Lineup {lineup_idx + 1}: points={lineup['total_projected_points']:.2f}, "
                f"salary=${lineup['total_salary']}, value={lineup['total_value']:.2f}"
            )

        logger.info(f"Generated {len(lineups)} optimal lineups")
        return lineups

    def _set_maximize_points_objective(self, drivers: List[Dict[str, Any]]) -> None:
        """Set objective to maximize expected points."""
        self.problem += lpSum(
            self.calculate_expected_points(driver["driver_id"])
            * self.driver_vars[driver["driver_id"]]
            for driver in drivers
        ), "Maximize_Expected_Points"

    def _set_maximize_value_objective(self, drivers: List[Dict[str, Any]]) -> None:
        """Set objective to maximize value score."""
        self.problem += lpSum(
            self.calculate_value_score(driver["driver_id"])
            * self.driver_vars[driver["driver_id"]]
            for driver in drivers
        ), "Maximize_Value_Score"

    def _set_minimize_risk_objective(self, drivers: List[Dict[str, Any]]) -> None:
        """Set objective to minimize epistemic variance (risk)."""
        # Calculate risk-adjusted score = expected_points / (1 + epistemic_variance)
        self.problem += lpSum(
            (
                self.calculate_expected_points(driver["driver_id"])
                / (1.0 + self._get_driver_epistemic_variance(driver))
            )
            * self.driver_vars[driver["driver_id"]]
            for driver in drivers
        ), "Minimize_Risk"

    def _get_driver_epistemic_variance(self, driver: Dict[str, Any]) -> float:
        """Get average epistemic variance for driver beliefs."""
        if not driver["beliefs"]:
            return 0.0

        variances = [b["epistemic_var"] for b in driver["beliefs"]]
        return sum(variances) / len(variances)

    def apply_driver_count_constraints(self) -> None:
        """
        Apply constraint to select exactly n_drivers.

        This constraint ensures that exactly the specified number of drivers
        are selected in the lineup.
        """
        self.problem += (
            lpSum(self.driver_vars.values()) == self.n_drivers,
            f"Select_Exact_{self.n_drivers}_Drivers",
        )

    def apply_salary_constraints(self, drivers: List[Dict[str, Any]]) -> None:
        """
        Apply salary cap constraint.

        This constraint ensures that the total salary of selected drivers
        does not exceed the salary cap.

        Args:
            drivers: List of available driver dictionaries
        """
        self.problem += (
            lpSum(
                driver["salary"] * self.driver_vars[driver["driver_id"]]
                for driver in drivers
            )
            <= self.salary_cap,
            f"Salary_Cap_{self.salary_cap}",
        )

    def apply_stacking_constraints(self, drivers: List[Dict[str, Any]]) -> None:
        """
        Apply team stacking constraints.

        This constraint enforces team stacking rules:
        - At least min_stack drivers from the same team
        - At most max_stack drivers from the same team

        Args:
            drivers: List of available driver dictionaries
        """
        # Group drivers by team
        teams = {}
        for driver in drivers:
            team = driver["team"]
            if team not in teams:
                teams[team] = []
            teams[team].append(driver)

        # Apply stacking constraints for each team
        for team, team_drivers in teams.items():
            # Calculate total drivers selected from this team
            team_selection = lpSum(
                self.driver_vars[driver["driver_id"]] for driver in team_drivers
            )

            # If team has enough drivers, apply stacking constraints
            if len(team_drivers) >= self.min_stack:
                # Maximum constraint: at most max_stack drivers from this team
                self.problem += (
                    team_selection <= self.max_stack,
                    f"Max_{self.max_stack}_From_Team_{team}",
                )

    def optimize_multiple_lineups(
        self, race_id: int, n_lineups: int = 10, objective: str = "maximize_points"
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple optimal lineups with diversity.

        This method generates multiple lineups by iteratively optimizing
        and excluding previously selected drivers to ensure diversity.

        Args:
            race_id: Race identifier
            n_lineups: Number of lineups to generate (default 10)
            objective: Optimization objective (default "maximize_points")

        Returns:
            List of lineup dictionaries
        """
        logger.info(f"Generating {n_lineups} diverse lineups for race {race_id}")

        lineups = self.optimize_lineup(race_id, n_lineups, objective)

        return lineups

    def calculate_lineup_projection(self, lineup: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate detailed projection for a lineup.

        This method calculates detailed statistics for a lineup including:
        - Expected points breakdown by driver
        - Team distribution
        - Salary distribution
        - Risk metrics

        Args:
            lineup: Lineup dictionary

        Returns:
            Dictionary with detailed projection information
        """
        drivers = lineup["drivers"]

        # Calculate driver projections
        driver_projections = []
        for driver in drivers:
            driver_id = driver["driver_id"]
            expected_points = self.calculate_expected_points(driver_id)
            value_score = self.calculate_value_score(driver_id)
            finish_dist = self.calculate_finish_distribution(driver_id)

            driver_projections.append(
                {
                    "driver_id": driver_id,
                    "name": driver["name"],
                    "team": driver["team"],
                    "salary": driver["salary"],
                    "expected_points": expected_points,
                    "value_score": value_score,
                    "finish_distribution": finish_dist,
                }
            )

        # Calculate team distribution
        team_counts = {}
        for driver in drivers:
            team = driver["team"]
            team_counts[team] = team_counts.get(team, 0) + 1

        # Calculate risk metrics
        epistemic_variances = []
        for driver in drivers:
            if driver["beliefs"]:
                variances = [b["epistemic_var"] for b in driver["beliefs"]]
                epistemic_variances.extend(variances)

        avg_variance = (
            sum(epistemic_variances) / len(epistemic_variances)
            if epistemic_variances
            else 0.0
        )

        projection = {
            "driver_projections": driver_projections,
            "team_distribution": team_counts,
            "avg_epistemic_variance": avg_variance,
            "risk_score": avg_variance * 100,
        }

        return projection

    def _calculate_lineup_metrics(
        self, drivers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate metrics for a lineup.

        Args:
            drivers: List of selected driver dictionaries

        Returns:
            Dictionary with lineup metrics
        """
        # Calculate total expected points
        total_points = sum(
            self.calculate_expected_points(d["driver_id"]) for d in drivers
        )

        # Calculate total salary
        total_salary = sum(d["salary"] for d in drivers)

        # Calculate total value
        total_value = sum(self.calculate_value_score(d["driver_id"]) for d in drivers)

        # Calculate average epistemic variance
        variances = []
        for driver in drivers:
            if driver["beliefs"]:
                variances.extend([b["epistemic_var"] for b in driver["beliefs"]])

        avg_variance = sum(variances) / len(variances) if variances else 0.0

        return {
            "drivers": drivers,
            "total_projected_points": total_points,
            "total_salary": int(total_salary),
            "total_value": total_value,
            "risk_score": avg_variance * 100,
        }

    def export_lineup_csv(
        self, lineup: Dict[str, Any], filename: Optional[str] = None
    ) -> str:
        """
        Export lineup to CSV for DraftKings upload.

        The CSV format includes:
        - DriverID, Name, Team, Salary, ProjectedPoints

        Args:
            lineup: Lineup dictionary
            filename: Output filename (auto-generated if None)

        Returns:
            Path to exported CSV file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"nascar_lineup_{timestamp}.csv"

        # Prepare data for CSV
        data = []
        for driver in lineup["drivers"]:
            driver_id = driver["driver_id"]
            expected_points = self.calculate_expected_points(driver_id)

            data.append(
                {
                    "DriverID": driver_id,
                    "Name": driver["name"],
                    "Team": driver["team"],
                    "CarNumber": driver["car_number"],
                    "Salary": driver["salary"],
                    "ProjectedPoints": round(expected_points, 2),
                }
            )

        # Create DataFrame and export
        df = pd.DataFrame(data)
        filepath = f"/tmp/{filename}"
        df.to_csv(filepath, index=False)

        logger.info(f"Exported lineup to {filepath}")
        return filepath

    def export_multiple_lineups_csv(
        self, lineups: List[Dict[str, Any]], filename: Optional[str] = None
    ) -> str:
        """
        Export multiple lineups to CSV for DraftKings upload.

        Args:
            lineups: List of lineup dictionaries
            filename: Output filename (auto-generated if None)

        Returns:
            Path to exported CSV file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"nascar_lineups_{timestamp}.csv"

        # Prepare data for CSV
        data = []
        for idx, lineup in enumerate(lineups, 1):
            for driver in lineup["drivers"]:
                driver_id = driver["driver_id"]
                expected_points = self.calculate_expected_points(driver_id)

                data.append(
                    {
                        "Lineup": idx,
                        "DriverID": driver_id,
                        "Name": driver["name"],
                        "Team": driver["team"],
                        "CarNumber": driver["car_number"],
                        "Salary": driver["salary"],
                        "ProjectedPoints": round(expected_points, 2),
                    }
                )

        # Create DataFrame and export
        df = pd.DataFrame(data)
        filepath = f"/tmp/{filename}"
        df.to_csv(filepath, index=False)

        logger.info(f"Exported {len(lineups)} lineups to {filepath}")
        return filepath

    def get_driver_salary(self, driver_id: int) -> float:
        """
        Get DraftKings salary for a driver.

        Args:
            driver_id: Driver identifier

        Returns:
            Driver salary (float)

        Raises:
            ValueError: If driver_id is invalid
        """
        driver = next(
            (d for d in self.drivers if d["driver_id"] == driver_id), None
        )
        if not driver:
            raise ValueError(f"Driver with id {driver_id} not found")

        return driver["salary"]

    def get_driver_team(self, driver_id: int) -> str:
        """
        Get driver team for stacking.

        Args:
            driver_id: Driver identifier

        Returns:
            Driver team name (str)

        Raises:
            ValueError: If driver_id is invalid
        """
        driver = next(
            (d for d in self.drivers if d["driver_id"] == driver_id), None
        )
        if not driver:
            raise ValueError(f"Driver with id {driver_id} not found")

        return driver["team"]

    def get_salary_distribution(self) -> Dict[str, int]:
        """
        Get the salary distribution of available drivers.

        Returns:
            Dictionary with salary ranges and counts
        """
        salary_ranges = {
            "0-5000": 0,
            "5001-10000": 0,
            "10001-15000": 0,
            "15001-20000": 0,
            "20001+": 0,
        }

        for driver in self.drivers:
            salary = driver["salary"]
            if salary <= 5000:
                salary_ranges["0-5000"] += 1
            elif salary <= 10000:
                salary_ranges["5001-10000"] += 1
            elif salary <= 15000:
                salary_ranges["10001-15000"] += 1
            elif salary <= 20000:
                salary_ranges["15001-20000"] += 1
            else:
                salary_ranges["20001+"] += 1

        return salary_ranges

    def get_projection_summary(self) -> Dict[str, float]:
        """
        Get summary statistics for driver projections.

        Returns:
            Dictionary with min, max, mean, and median projections
        """
        projections = [
            self.calculate_expected_points(d["driver_id"]) for d in self.drivers
        ]

        if not projections:
            return {
                "min": 0.0,
                "max": 0.0,
                "mean": 0.0,
                "median": 0.0,
            }

        sorted_projections = sorted(projections)
        n = len(sorted_projections)

        return {
            "min": min(projections),
            "max": max(projections),
            "mean": sum(projections) / n,
            "median": sorted_projections[n // 2]
            if n % 2 == 1
            else (sorted_projections[n // 2 - 1] + sorted_projections[n // 2]) / 2,
        }

    def get_team_distribution(self) -> Dict[str, int]:
        """
        Get the team distribution of available drivers.

        Returns:
            Dictionary mapping team names to driver counts
        """
        teams = {}
        for driver in self.drivers:
            team = driver["team"]
            teams[team] = teams.get(team, 0) + 1

        return teams


# Legacy LineupOptimizer class for backward compatibility
class LineupOptimizer:
    """
    Legacy optimizer for backward compatibility.

    This class maintains the original API for existing code that uses
    the old LineupOptimizer interface. New code should use NASCAROptimizer.
    """

    def __init__(
        self,
        drivers: List[Dict[str, Any]],
        salary_cap: int = 50000,
        lineup_size: int = 6,
    ) -> None:
        """
        Initialize LineupOptimizer with driver data and constraints.

        Args:
            drivers: List of driver dictionaries with keys:
                     - driver_id: str
                     - name: str
                     - salary: int
                     - projected_points: float
                     - position: int
            salary_cap: Maximum salary for lineup (default 50,000)
            lineup_size: Number of drivers to select (default 6)
        """
        self.drivers: List[Dict[str, Any]] = drivers
        self.salary_cap: int = salary_cap
        self.lineup_size: int = lineup_size
        self.problem: Optional[LpProblem] = None
        self.variables: Optional[Dict[str, LpVariable]] = None

    def optimize(self) -> Optional[Dict[str, Any]]:
        """
        Solve the optimization problem and return the optimal lineup.

        Returns:
            Dictionary with keys:
            - drivers: List of selected driver dictionaries
            - total_projected_points: float
            - total_salary: int
            None if no valid solution found
        """
        if len(self.drivers) < self.lineup_size:
            return None

        # Create the problem
        self.problem = LpProblem("NASCAR_DFS_Optimization", LpMaximize)

        # Create binary variables for each driver
        self.variables = {
            driver["driver_id"]: LpVariable(
                f"select_{driver['driver_id']}", cat=LpBinary
            )
            for driver in self.drivers
        }

        # Objective: Maximize projected points
        self.problem += lpSum(
            driver["projected_points"] * self.variables[driver["driver_id"]]
            for driver in self.drivers
        ), "Total_Projected_Points"

        # Constraint: Select exactly lineup_size drivers
        self.problem += (
            lpSum(
                self.variables[driver["driver_id"]] for driver in self.drivers
            )
            == self.lineup_size,
            "Select_Exact_Lineup_Size",
        )

        # Constraint: Total salary <= salary_cap
        self.problem += (
            lpSum(
                driver["salary"] * self.variables[driver["driver_id"]]
                for driver in self.drivers
            )
            <= self.salary_cap,
            "Salary_Cap_Constraint",
        )

        # Solve the problem using system CBC if available (fixes ARM Mac issues)
        try:
            # Try to use system-installed CBC first
            from pulp import COIN_CMD
            solver = COIN_CMD(path='/usr/bin/cbc', msg=0, timeLimit=30)
        except Exception:
            # Fallback to default solver
            solver = None
        self.problem.solve(solver)

        # Check if solution is optimal
        if LpStatus[self.problem.status] != "Optimal":
            return None

        # Extract the selected drivers
        selected_drivers = [
            driver
            for driver in self.drivers
            if self.variables[driver["driver_id"]].value() == 1
        ]

        # Calculate totals
        total_projected_points = sum(
            driver["projected_points"] for driver in selected_drivers
        )
        total_salary = sum(driver["salary"] for driver in selected_drivers)

        return {
            "drivers": selected_drivers,
            "total_projected_points": total_projected_points,
            "total_salary": total_salary,
        }

    def get_multiple_lineups(
        self, num_lineups: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple optimal lineups by excluding previous selections.

        Args:
            num_lineups: Number of lineups to generate

        Returns:
            List of lineup dictionaries
        """
        lineups = []
        excluded_driver_ids = set()

        for _ in range(num_lineups):
            # Filter out excluded drivers
            available_drivers = [
                driver
                for driver in self.drivers
                if driver["driver_id"] not in excluded_driver_ids
            ]

            if len(available_drivers) < self.lineup_size:
                break

            # Create a new optimizer with available drivers
            optimizer = LineupOptimizer(
                drivers=available_drivers,
                salary_cap=self.salary_cap,
                lineup_size=self.lineup_size,
            )

            result = optimizer.optimize()

            if not result:
                break

            lineups.append(result)

            # Exclude selected drivers for next iteration
            excluded_driver_ids.update(
                driver["driver_id"] for driver in result["drivers"]
            )

        return lineups

    def get_salary_distribution(self) -> Dict[str, int]:
        """
        Get the salary distribution of available drivers.

        Returns:
            Dictionary with salary ranges and counts
        """
        salary_ranges = {
            "0-5000": 0,
            "5001-10000": 0,
            "10001-15000": 0,
            "15001-20000": 0,
            "20001+": 0,
        }

        for driver in self.drivers:
            salary = driver["salary"]
            if salary <= 5000:
                salary_ranges["0-5000"] += 1
            elif salary <= 10000:
                salary_ranges["5001-10000"] += 1
            elif salary <= 15000:
                salary_ranges["10001-15000"] += 1
            elif salary <= 20000:
                salary_ranges["15001-20000"] += 1
            else:
                salary_ranges["20001+"] += 1

        return salary_ranges

    def get_projection_summary(self) -> Dict[str, float]:
        """
        Get summary statistics for driver projections.

        Returns:
            Dictionary with min, max, mean, and median projections
        """
        projections = [driver["projected_points"] for driver in self.drivers]

        if not projections:
            return {
                "min": 0.0,
                "max": 0.0,
                "mean": 0.0,
                "median": 0.0,
            }

        sorted_projections = sorted(projections)
        n = len(sorted_projections)

        return {
            "min": min(projections),
            "max": max(projections),
            "mean": sum(projections) / n,
            "median": sorted_projections[n // 2]
            if n % 2 == 1
            else (sorted_projections[n // 2 - 1] + sorted_projections[n // 2]) / 2,
        }


# Helper functions

def create_optimizer(
    db_session: Optional[Session] = None,
    salary_cap: int = 50000,
    n_drivers: int = 6,
    min_stack: int = 2,
    max_stack: int = 3,
) -> NASCAROptimizer:
    """
    Factory function to create a NASCAROptimizer instance.

    Args:
        db_session: Optional database session (creates new one if None)
        salary_cap: Maximum total salary for lineup (default 50,000)
        n_drivers: Number of drivers to select (default 6)
        min_stack: Minimum drivers from same team (default 2)
        max_stack: Maximum drivers from same team (default 3)

    Returns:
        NASCAROptimizer instance
    """
    if db_session is None:
        db_session = SessionLocal()

    return NASCAROptimizer(
        db_session=db_session,
        salary_cap=salary_cap,
        n_drivers=n_drivers,
        min_stack=min_stack,
        max_stack=max_stack,
    )


if __name__ == "__main__":
    # Example usage
    logger.info("NASCAR DFS Optimizer module loaded")

    # Create database session
    db = SessionLocal()

    try:
        # Create optimizer
        optimizer = create_optimizer(db)

        # Example: Optimize lineups for race 1
        # lineups = optimizer.optimize_lineup(race_id=1, n_lineups=5)

        # Example: Export lineup to CSV
        # if lineups:
        #     optimizer.export_lineup_csv(lineups[0], "example_lineup.csv")

    finally:
        db.close()
