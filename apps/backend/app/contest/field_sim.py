"""
Field lineup simulation for DFS contest modeling.

This module implements ownership-based field lineup generation for simulating
opponent behavior in DFS contests. It uses Dirichlet-multinomial sampling to
generate realistic field lineups that respect DraftKings constraints.

Key features:
- Dirichlet-multinomial sampling for ownership allocation
- Salary cap constraint enforcement
- Vectorized NumPy operations for efficiency
- Lineup score calculation from driver scores
"""

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


def dirichlet_multinomial_sample(
    ownership: np.ndarray,
    n_samples: int,
    n_draws: int,
    alpha: float = 1.0
) -> np.ndarray:
    """
    Sample from Dirichlet-multinomial distribution.

    The Dirichlet-multinomial distribution models the probability of counts
    for each category when sampling from a population with uncertain proportions.
    It's more flexible than standard multinomial as it accounts for uncertainty
    in ownership estimates.

    Args:
        ownership: Array of ownership percentages (sums to 100)
        n_samples: Number of samples to generate
        n_draws: Number of draws per sample (e.g., 6 drivers per lineup)
        alpha: Concentration parameter (lower = more variance, higher = less variance)

    Returns:
        Array of shape (n_samples, len(ownership)) with counts for each driver

    Example:
        >>> ownership = np.array([20, 15, 12, 10, 8, 7, 6, 5, 5, 4, 4, 4])
        >>> samples = dirichlet_multinomial_sample(ownership, n_samples=100, n_draws=6)
        >>> print(samples.shape)
        (100, 12)
        >>> print(samples.sum(axis=1))  # Each sample sums to 6
        array([6, 6, 6, ..., 6, 6, 6])
    """
    # Normalize ownership to probabilities
    ownership_prob = ownership / ownership.sum()

    n_drivers = len(ownership)

    # Draw concentration parameters for each sample
    # This introduces uncertainty in ownership proportions
    alphas = ownership_prob * alpha

    # For computational efficiency, we approximate Dirichlet-multinomial
    # by adding small noise to ownership and sampling from multinomial
    # This is much faster than full Dirichlet-multinomial sampling

    # Add small noise to ownership for each sample
    # Shape: (n_samples, n_drivers)
    noise = np.random.gamma(
        shape=alphas,
        scale=1.0,
        size=(n_samples, n_drivers)
    )

    # Renormalize to probabilities
    noisy_probs = noise / noise.sum(axis=1, keepdims=True)

    # Sample from multinomial for each set of probabilities
    samples = np.array([
        np.random.multinomial(n_draws, probs)
        for probs in noisy_probs
    ])

    return samples


class FieldLineupSampler:
    """
    Sample field lineups from ownership estimates.

    This class generates realistic opponent lineups for contest simulation
    by sampling from ownership distributions. It enforces DraftKings
    constraints (6 drivers, $50K salary cap) to generate valid lineups.

    Usage:
        >>> ownership = np.array([20, 15, 12, 10, 8, 7, 6, 5, 5, 4, 4, 4])
        >>> driver_pool = [
        ...     {'driver_id': 1, 'salary': 9500, 'projected_points': 45},
        ...     {'driver_id': 2, 'salary': 9200, 'projected_points': 43},
        ...     # ... more drivers
        ... ]
        >>> sampler = FieldLineupSampler(ownership, driver_pool, salary_cap=50000, n_drivers=6)
        >>> lineups = sampler.sample_lineups_with_constraints(100)
        >>> print(f"Generated {len(lineups)} valid lineups")
    """

    def __init__(
        self,
        ownership: np.ndarray,
        driver_pool: List[Dict],
        salary_cap: int = 50000,
        n_drivers: int = 6
    ):
        """
        Initialize field lineup sampler.

        Args:
            ownership: Array of ownership percentages (sums to 100)
            driver_pool: List of driver dicts with keys:
                - driver_id: int
                - salary: int
                - projected_points: float (optional)
            salary_cap: DraftKings salary cap (default 50K)
            n_drivers: Number of drivers per lineup (default 6)

        Raises:
            ValueError: If inputs are invalid
        """
        # Validate inputs
        ownership_array = np.asarray(ownership, dtype=float)

        if len(ownership_array) != len(driver_pool):
            raise ValueError(
                f"Ownership array length ({len(ownership_array)}) must match "
                f"driver_pool length ({len(driver_pool)})"
            )

        if len(ownership_array) < n_drivers:
            raise ValueError(
                f"Need at least {n_drivers} drivers, got {len(ownership_array)}"
            )

        if salary_cap <= 0:
            raise ValueError(f"Salary cap must be positive, got {salary_cap}")

        if n_drivers <= 0:
            raise ValueError(f"Number of drivers must be positive, got {n_drivers}")

        # Validate driver pool structure
        required_keys = {'driver_id', 'salary'}
        for i, driver in enumerate(driver_pool):
            if not isinstance(driver, dict):
                raise ValueError(f"Driver {i} must be a dict, got {type(driver)}")

            missing_keys = required_keys - driver.keys()
            if missing_keys:
                raise ValueError(
                    f"Driver {i} missing required keys: {missing_keys}"
                )

        # Normalize ownership to sum to 100
        self.ownership = ownership_array / ownership_array.sum() * 100

        # Create driver_id to index mapping
        self.driver_ids = np.array([d['driver_id'] for d in driver_pool])
        self.salaries = np.array([d['salary'] for d in driver_pool])

        # Optional projected points
        self.projected_points = np.array([
            d.get('projected_points', 0.0)
            for d in driver_pool
        ])

        self.salary_cap = salary_cap
        self.n_drivers = n_drivers
        self.n_total_drivers = len(driver_pool)

        logger.info(
            f"Initialized FieldLineupSampler: "
            f"{self.n_total_drivers} drivers, "
            f"salary_cap=${salary_cap}, "
            f"n_drivers={n_drivers}"
        )

    def sample_lineups(self, n_lineups: int) -> List[List[int]]:
        """
        Sample driver compositions using Dirichlet-multinomial distribution.

        This method generates lineup compositions based on ownership percentages.
        Each lineup has exactly n_drivers slots, with drivers sampled according
        to their ownership probabilities.

        Note: This method does NOT enforce salary cap constraints.
        Use sample_lineups_with_constraints() for salary-aware sampling.

        Args:
            n_lineups: Number of lineups to sample

        Returns:
            List of driver_id lists (each inner list has n_drivers driver_ids)

        Example:
            >>> sampler = FieldLineupSampler(ownership, driver_pool)
            >>> lineups = sampler.sample_lineups(10)
            >>> print(len(lineups))
            10
            >>> print(len(lineups[0]))
            6
        """
        if n_lineups <= 0:
            raise ValueError(f"n_lineups must be positive, got {n_lineups}")

        logger.debug(f"Sampling {n_lineups} lineups from ownership")

        # Sample driver compositions using Dirichlet-multinomial
        compositions = dirichlet_multinomial_sample(
            self.ownership,
            n_samples=n_lineups,
            n_draws=self.n_drivers,
            alpha=1.0  # Moderate uncertainty in ownership
        )

        # Convert compositions to driver_id lists
        lineups = []
        for composition in compositions:
            # Find drivers with positive counts
            driver_indices = np.where(composition > 0)[0]

            # For each driver with count > 0, add them to lineup that many times
            lineup = []
            for idx in driver_indices:
                count = int(composition[idx])
                lineup.extend([self.driver_ids[idx]] * count)

            # Ensure exactly n_drivers drivers
            # (multinomial should guarantee this, but validate)
            if len(lineup) != self.n_drivers:
                logger.warning(
                    f"Lineup has {len(lineup)} drivers, expected {self.n_drivers}. "
                    f"Composition: {composition}"
                )
                # Pad or truncate to n_drivers
                if len(lineup) < self.n_drivers:
                    # Add lowest-owned drivers to fill
                    remaining = self.n_drivers - len(lineup)
                    sorted_indices = np.argsort(self.ownership)
                    for idx in sorted_indices[:remaining]:
                        lineup.append(self.driver_ids[idx])
                else:
                    # Truncate to n_drivers
                    lineup = lineup[:self.n_drivers]

            lineups.append(lineup)

        logger.debug(f"Sampled {len(lineups)} lineups")

        return lineups

    def _check_salary_constraint(self, lineup: List[int]) -> bool:
        """
        Check if lineup satisfies salary cap constraint.

        Args:
            lineup: List of driver_ids

        Returns:
            True if lineup salary <= salary_cap, False otherwise
        """
        # Find indices for driver_ids
        lineup_indices = np.where(np.isin(self.driver_ids, lineup))[0]

        # Calculate total salary
        total_salary = self.salaries[lineup_indices].sum()

        return total_salary <= self.salary_cap

    def sample_lineups_with_constraints(
        self,
        n_lineups: int,
        max_attempts: int = 100
    ) -> List[List[int]]:
        """
        Sample lineups that satisfy salary cap constraint.

        This method generates ownership-based lineups and filters to those
        that satisfy the salary cap constraint. If insufficient valid lineups
        are found, it resamples up to max_attempts.

        Args:
            n_lineups: Number of valid lineups to generate
            max_attempts: Maximum resampling attempts (default 100)

        Returns:
            List of valid driver_id lists

        Example:
            >>> sampler = FieldLineupSampler(ownership, driver_pool, salary_cap=50000)
            >>> lineups = sampler.sample_lineups_with_constraints(100)
            >>> print(f"Generated {len(lineups)} valid lineups")
            >>> # Check first lineup
            >>> print(lineups[0])
            [1, 5, 8, 12, 15, 20]
        """
        if n_lineups <= 0:
            raise ValueError(f"n_lineups must be positive, got {n_lineups}")

        logger.info(
            f"Sampling {n_lineups} lineups with salary constraint "
            f"(cap=${self.salary_cap})"
        )

        valid_lineups = []
        total_sampled = 0
        attempts = 0

        # Oversample to account for salary constraint filtering
        # Oversampling factor depends on how restrictive the cap is
        oversample_factor = 3

        while len(valid_lineups) < n_lineups and attempts < max_attempts:
            # Sample candidate lineups
            n_to_sample = (n_lineups - len(valid_lineups)) * oversample_factor

            candidate_lineups = self.sample_lineups(n_to_sample)
            total_sampled += len(candidate_lineups)

            # Filter to valid lineups
            for lineup in candidate_lineups:
                if self._check_salary_constraint(lineup):
                    valid_lineups.append(lineup)

                if len(valid_lineups) >= n_lineups:
                    break

            attempts += 1

            logger.debug(
                f"Attempt {attempts}: {len(valid_lineups)}/{n_lineups} valid lineups"
            )

        # Truncate to n_lineups if we got more
        valid_lineups = valid_lineups[:n_lineups]

        success_rate = len(valid_lineups) / total_sampled if total_sampled > 0 else 0

        logger.info(
            f"Generated {len(valid_lineups)}/{n_lineups} valid lineups "
            f"(success rate: {success_rate:.1%}, "
            f"total sampled: {total_sampled})"
        )

        if len(valid_lineups) < n_lineups:
            logger.warning(
                f"Could only generate {len(valid_lineups)}/{n_lineups} valid lineups "
                f"after {max_attempts} attempts. "
                f"Consider relaxing salary cap or checking driver pool."
            )

        return valid_lineups

    def compute_lineup_scores(
        self,
        driver_scores: np.ndarray,
        lineups: Optional[List[List[int]]] = None
    ) -> np.ndarray:
        """
        Sum driver scores for each lineup.

        Args:
            driver_scores: Array of driver scores for this scenario (n_drivers,)
                Must align with ownership array (same driver order)
            lineups: List of driver_id lists (optional). If None, uses last
                sampled lineups or generates new ones.

        Returns:
            Array of lineup scores (n_lineups,)

        Raises:
            ValueError: If driver_scores length doesn't match driver pool

        Example:
            >>> driver_scores = np.array([45, 42, 38, 35, 32, 30, 28, 25, 22, 20, 18, 15])
            >>> lineups = sampler.sample_lineups_with_constraints(10)
            >>> scores = sampler.compute_lineup_scores(driver_scores, lineups)
            >>> print(f"Lineup scores: {scores}")
            [245.2, 238.7, 251.3, ..., 230.5]
        """
        driver_scores_array = np.asarray(driver_scores, dtype=float)

        if len(driver_scores_array) != self.n_total_drivers:
            raise ValueError(
                f"driver_scores length ({len(driver_scores_array)}) must match "
                f"driver pool length ({self.n_total_drivers})"
            )

        if lineups is None:
            # Generate lineups if not provided
            logger.warning("No lineups provided, generating new lineups")
            lineups = self.sample_lineups_with_constraints(100)

        logger.debug(f"Computing scores for {len(lineups)} lineups")

        # Compute score for each lineup
        lineup_scores = np.zeros(len(lineups))

        for i, lineup in enumerate(lineups):
            # Find indices for driver_ids in this lineup
            lineup_indices = np.where(np.isin(self.driver_ids, lineup))[0]

            # Sum driver scores
            lineup_scores[i] = driver_scores_array[lineup_indices].sum()

        return lineup_scores

    def compute_lineup_salary(self, lineup: List[int]) -> int:
        """
        Calculate total salary for a lineup.

        Args:
            lineup: List of driver_ids

        Returns:
            Total salary for the lineup

        Example:
            >>> lineup = [1, 5, 8, 12, 15, 20]
            >>> salary = sampler.compute_lineup_salary(lineup)
            >>> print(f"Lineup salary: ${salary}")
            $48500
        """
        # Find indices for driver_ids
        lineup_indices = np.where(np.isin(self.driver_ids, lineup))[0]

        # Calculate total salary
        total_salary = self.salaries[lineup_indices].sum()

        return int(total_salary)

    def get_lineup_details(self, lineup: List[int]) -> Dict[str, any]:
        """
        Get detailed information about a lineup.

        Args:
            lineup: List of driver_ids

        Returns:
            Dict with keys:
                - driver_ids: List of driver IDs
                - salaries: Array of salaries for each driver
                - projected_points: Array of projected points (if available)
                - total_salary: Total salary
                - total_projected_points: Total projected points (if available)

        Example:
            >>> lineup = [1, 5, 8, 12, 15, 20]
            >>> details = sampler.get_lineup_details(lineup)
            >>> print(f"Total salary: ${details['total_salary']}")
            $48500
        """
        # Find indices for driver_ids
        lineup_indices = np.where(np.isin(self.driver_ids, lineup))[0]

        # Extract lineup information
        salaries = self.salaries[lineup_indices]
        projected_points = self.projected_points[lineup_indices]

        details = {
            'driver_ids': lineup,
            'salaries': salaries,
            'projected_points': projected_points if np.any(projected_points) else None,
            'total_salary': int(salaries.sum()),
            'total_projected_points': float(projected_points.sum()) if np.any(projected_points) else None
        }

        return details

    def __repr__(self) -> str:
        return (
            f"FieldLineupSampler("
            f"n_drivers={self.n_total_drivers}, "
            f"salary_cap=${self.salary_cap}, "
            f"lineup_size={self.n_drivers})"
        )
