"""MCMC lineup optimizer using JAX for local Apple Silicon computation."""

import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
import numpy as np

# JAX imports for Apple Silicon optimization
import jax
import jax.numpy as jnp
from jax import random, jit, vmap

logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    """Result of MCMC optimization for a single lineup."""

    drivers: List[Dict[str, Any]]
    total_projected_points: float
    total_salary: int
    total_value: float
    risk_score: float
    lineup_score: float


class MCMCLineupOptimizer:
    """MCMC-based lineup optimizer using JAX for local computation on Apple Silicon.

    This optimizer uses Markov Chain Monte Carlo sampling to explore the lineup
    space and find high-quality lineups that satisfy DraftKings constraints.

    Key features:
    - JAX-based computation for Apple Silicon performance
    - Configurable MCMC iterations (default 1000, max 5000)
    - Temperature-based sampling for exploration/exploitation tradeoff
    - Salary cap constraint enforcement ($50,000 for DraftKings)
    - 6-driver lineup size constraint
    - Progress callback for real-time UI updates
    - Cancellation support for user interruption

    Attributes:
        default_iterations: Default number of MCMC iterations
        max_iterations: Maximum allowed iterations
        temperature: MCMC temperature parameter
        salary_cap: DraftKings salary cap
        lineup_size: Number of drivers per lineup
    """

    def __init__(
        self,
        default_iterations: int = 1000,
        max_iterations: int = 5000,
        temperature: float = 1.0,
        salary_cap: int = 50000,
        lineup_size: int = 6,
    ):
        """Initialize MCMC lineup optimizer.

        Args:
            default_iterations: Default MCMC iterations (default 1000)
            max_iterations: Maximum iterations allowed (default 5000)
            temperature: MCMC temperature for sampling (default 1.0)
            salary_cap: Salary cap constraint (default 50000)
            lineup_size: Number of drivers per lineup (default 6)
        """
        self.default_iterations = default_iterations
        self.max_iterations = max_iterations
        self.temperature = temperature
        self.salary_cap = salary_cap
        self.lineup_size = lineup_size

        # JAX configuration for Apple Silicon
        # Use CPU backend (Metal GPU support is experimental)
        jax.config.update("jax_platform_name", "cpu")

        logger.info(
            f"MCMCLineupOptimizer initialized: "
            f"iterations={default_iterations}, temperature={temperature}, "
            f"salary_cap=${salary_cap}, lineup_size={lineup_size}"
        )

    def optimize(
        self,
        drivers: List[Dict[str, Any]],
        num_lineups: int = 20,
        salary_cap: Optional[int] = None,
        iterations: Optional[int] = None,
        constraints: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[int, int, float], None]] = None,
        cancellation_check: Optional[Callable[[], bool]] = None,
    ) -> List[Dict[str, Any]]:
        """Optimize lineups using MCMC sampling.

        Args:
            drivers: List of driver dictionaries with keys:
                - driver_id: str or int
                - name: str
                - team: str
                - salary: int
                - projected_points: float
                - value_score: float (optional)
            num_lineups: Number of lineups to generate (default 20)
            salary_cap: Salary cap override (default: self.salary_cap)
            iterations: MCMC iterations override (default: self.default_iterations)
            constraints: Additional constraints dict (optional)
                - min_stack: int - minimum drivers from same team
                - max_stack: int - maximum drivers from same team
                - exclude_drivers: List[str] - driver IDs to exclude
            progress_callback: Callback for progress updates
                Signature: callback(current_iteration, total_iterations, best_score)
            cancellation_check: Callable that returns True if optimization should stop

        Returns:
            List of lineup dictionaries, each containing:
                - drivers: List of selected driver dicts
                - total_projected_points: float
                - total_salary: int
                - total_value: float
                - risk_score: float
                - lineup_score: float

        Raises:
            ValueError: If insufficient drivers or invalid parameters
            CancellationError: If optimization is cancelled
        """
        if not drivers:
            raise ValueError("No drivers provided for optimization")

        if len(drivers) < self.lineup_size:
            raise ValueError(
                f"Insufficient drivers: {len(drivers)} < {self.lineup_size}"
            )

        # Use defaults if not specified
        salary_cap = salary_cap or self.salary_cap
        iterations = iterations or self.default_iterations
        iterations = min(iterations, self.max_iterations)

        constraints = constraints or {}

        logger.info(
            f"Starting MCMC optimization: {num_lineups} lineups, "
            f"{iterations} iterations, {len(drivers)} drivers"
        )

        # Prepare driver data for JAX
        driver_data = self._prepare_driver_data(drivers, constraints)

        # Run MCMC optimization
        results = self._mcmc_optimize(
            driver_data=driver_data,
            num_lineups=num_lineups,
            salary_cap=salary_cap,
            iterations=iterations,
            constraints=constraints,
            progress_callback=progress_callback,
            cancellation_check=cancellation_check,
        )

        logger.info(f"MCMC optimization complete: {len(results)} lineups generated")
        return results

    def _prepare_driver_data(
        self,
        drivers: List[Dict[str, Any]],
        constraints: Dict[str, Any],
    ) -> Dict[str, jnp.ndarray]:
        """Prepare driver data as JAX arrays for efficient computation.

        Args:
            drivers: List of driver dictionaries
            constraints: Constraints dict

        Returns:
            Dictionary of JAX arrays with driver data
        """
        n_drivers = len(drivers)

        # Extract arrays
        salaries = jnp.array([d["salary"] for d in drivers], dtype=jnp.float32)
        projected_points = jnp.array(
            [d.get("projected_points", 0.0) for d in drivers], dtype=jnp.float32
        )
        value_scores = jnp.array(
            [d.get("value_score", 0.0) for d in drivers], dtype=jnp.float32
        )

        # Team encoding for stacking constraints
        teams = [d.get("team", "Unknown") for d in drivers]
        unique_teams = list(set(teams))
        team_to_idx = {team: idx for idx, team in enumerate(unique_teams)}
        team_indices = jnp.array([team_to_idx[team] for team in teams], dtype=jnp.int32)

        # Handle excluded drivers
        exclude_drivers = constraints.get("exclude_drivers", [])
        available_mask = jnp.ones(n_drivers, dtype=jnp.bool_)
        for i, driver in enumerate(drivers):
            if driver.get("driver_id") in exclude_drivers:
                available_mask = available_mask.at[i].set(False)

        return {
            "n_drivers": n_drivers,
            "salaries": salaries,
            "projected_points": projected_points,
            "value_scores": value_scores,
            "team_indices": team_indices,
            "n_teams": len(unique_teams),
            "available_mask": available_mask,
            "drivers": drivers,  # Keep original for reference
        }

    def _mcmc_optimize(
        self,
        driver_data: Dict[str, jnp.ndarray],
        num_lineups: int,
        salary_cap: int,
        iterations: int,
        constraints: Dict[str, Any],
        progress_callback: Optional[Callable[[int, int, float], None]],
        cancellation_check: Optional[Callable[[], bool]],
    ) -> List[Dict[str, Any]]:
        """Run MCMC optimization to find optimal lineups.

        Args:
            driver_data: Prepared driver data as JAX arrays
            num_lineups: Number of lineups to generate
            salary_cap: Salary cap constraint
            iterations: Number of MCMC iterations
            constraints: Additional constraints
            progress_callback: Progress callback
            cancellation_check: Cancellation check

        Returns:
            List of optimized lineups
        """
        n_drivers = driver_data["n_drivers"]

        # Initialize random key for reproducibility
        key = random.PRNGKey(42)

        # Track best lineups found
        best_lineups = []
        best_scores = []

        # MCMC parameters
        min_stack = constraints.get("min_stack", 0)
        max_stack = constraints.get("max_stack", 6)

        # Progress tracking
        progress_interval = max(1, iterations // 100)  # Update every 1%
        best_score_so_far = 0.0

        for iteration in range(iterations):
            # Check for cancellation
            if cancellation_check and cancellation_check():
                raise CancellationError("Optimization cancelled by user")

            # Generate candidate lineup
            key, subkey = random.split(key)
            candidate = self._generate_candidate_lineup(
                key=subkey,
                driver_data=driver_data,
                salary_cap=salary_cap,
                min_stack=min_stack,
                max_stack=max_stack,
            )

            if candidate is None:
                continue

            # Calculate lineup score
            score = self._calculate_lineup_score(candidate, driver_data)

            # Update best score tracking
            if score > best_score_so_far:
                best_score_so_far = score

            # MCMC acceptance criterion (Metropolis-Hastings)
            # Accept if better, or with probability based on temperature
            if len(best_lineups) < num_lineups:
                # Fill initial population
                lineup_dict = self._create_lineup_dict(candidate, driver_data, score)
                best_lineups.append(lineup_dict)
                best_scores.append(score)
            else:
                # Replace worst if better
                min_idx = int(jnp.argmin(jnp.array(best_scores)))
                if score > best_scores[min_idx]:
                    lineup_dict = self._create_lineup_dict(
                        candidate, driver_data, score
                    )
                    best_lineups[min_idx] = lineup_dict
                    best_scores[min_idx] = score

            # Progress callback
            if progress_callback and iteration % progress_interval == 0:
                progress_callback(iteration, iterations, float(best_score_so_far))

        # Final progress update
        if progress_callback:
            progress_callback(iterations, iterations, float(best_score_so_far))

        # Sort by score descending
        sorted_indices = sorted(
            range(len(best_lineups)), key=lambda i: best_scores[i], reverse=True
        )

        return [best_lineups[i] for i in sorted_indices]

    def _generate_candidate_lineup(
        self,
        key: jnp.ndarray,
        driver_data: Dict[str, jnp.ndarray],
        salary_cap: int,
        min_stack: int,
        max_stack: int,
    ) -> Optional[jnp.ndarray]:
        """Generate a candidate lineup using greedy randomized selection.

        Args:
            key: JAX random key
            driver_data: Driver data
            salary_cap: Salary cap
            min_stack: Minimum stack size
            max_stack: Maximum stack size

        Returns:
            Array of selected driver indices, or None if invalid
        """
        n_drivers = driver_data["n_drivers"]
        salaries = driver_data["salaries"]
        projected_points = driver_data["projected_points"]
        team_indices = driver_data["team_indices"]
        available_mask = driver_data["available_mask"]

        # Greedy randomized construction
        selected = []
        remaining_cap = salary_cap
        available = set(int(i) for i in range(n_drivers) if available_mask[i])

        # Track team counts for stacking
        team_counts = {}

        max_attempts = 100
        attempts = 0

        while len(selected) < self.lineup_size and attempts < max_attempts:
            attempts += 1

            # Find affordable drivers
            affordable = [i for i in available if int(salaries[i]) <= remaining_cap]

            if not affordable:
                break

            # Calculate selection probabilities based on projected points
            points = jnp.array([projected_points[i] for i in affordable])

            # Add some randomness (temperature)
            probs = jnp.exp(points / self.temperature)
            probs = probs / jnp.sum(probs)

            # Sample driver
            key, subkey = random.split(key)
            idx = int(random.choice(subkey, jnp.array(affordable), p=probs))

            # Check stacking constraints
            team_idx = int(team_indices[idx])
            new_team_count = team_counts.get(team_idx, 0) + 1

            if new_team_count > max_stack:
                # Remove this driver and try again
                available.discard(idx)
                continue

            # Accept driver
            selected.append(idx)
            remaining_cap -= int(salaries[idx])
            available.discard(idx)
            team_counts[team_idx] = new_team_count

        # Validate lineup
        if len(selected) != self.lineup_size:
            return None

        # Check min stacking constraint
        if min_stack > 0:
            max_team_count = max(team_counts.values()) if team_counts else 0
            if max_team_count < min_stack:
                return None

        return jnp.array(selected, dtype=jnp.int32)

    def _calculate_lineup_score(
        self,
        candidate: jnp.ndarray,
        driver_data: Dict[str, jnp.ndarray],
    ) -> float:
        """Calculate score for a candidate lineup.

        Args:
            candidate: Array of selected driver indices
            driver_data: Driver data

        Returns:
            Lineup score (higher is better)
        """
        projected_points = driver_data["projected_points"]
        value_scores = driver_data["value_scores"]

        # Total projected points
        total_points = float(jnp.sum(projected_points[candidate]))

        # Total value score
        total_value = float(jnp.sum(value_scores[candidate]))

        # Combined score with value weighting
        score = total_points + 0.1 * total_value

        return score

    def _create_lineup_dict(
        self,
        candidate: jnp.ndarray,
        driver_data: Dict[str, jnp.ndarray],
        score: float,
    ) -> Dict[str, Any]:
        """Create lineup dictionary from candidate indices.

        Args:
            candidate: Array of selected driver indices
            driver_data: Driver data
            score: Lineup score

        Returns:
            Lineup dictionary
        """
        drivers = driver_data["drivers"]
        salaries = driver_data["salaries"]
        projected_points = driver_data["projected_points"]
        value_scores = driver_data["value_scores"]

        selected_drivers = [drivers[int(i)] for i in candidate]

        total_salary = int(jnp.sum(salaries[candidate]))
        total_points = float(jnp.sum(projected_points[candidate]))
        total_value = float(jnp.sum(value_scores[candidate]))

        # Simple risk score based on variance of projected points
        points_array = projected_points[candidate]
        risk_score = float(jnp.std(points_array) * 10)

        return {
            "drivers": selected_drivers,
            "total_projected_points": round(total_points, 2),
            "total_salary": total_salary,
            "total_value": round(total_value, 2),
            "risk_score": round(risk_score, 2),
            "lineup_score": round(score, 2),
        }


class CancellationError(Exception):
    """Raised when optimization is cancelled by user."""

    pass
