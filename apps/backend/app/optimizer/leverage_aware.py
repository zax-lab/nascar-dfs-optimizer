"""
Leverage-aware optimizer for NASCAR DFS portfolio generation.

This module extends the existing NASCAROptimizer with ownership-based leverage
optimization to generate lineups that differentiate from the field by targeting
low-ownership drivers while maintaining CVaR optimization.

Key features:
- Leverage score calculation based on ownership differentiation
- Ownership constraints (max per driver, min low-ownership drivers)
- Regime-aware allocation across race-flow scenarios
- Integration with existing CVaR portfolio optimizer
"""
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class LeverageMetrics:
    """
    Leverage metrics for a lineup.

    Attributes:
        avg_ownership: Average ownership percentage in lineup
        max_ownership: Maximum ownership percentage in lineup
        total_ownership: Sum of ownership percentages
        low_ownership_count: Number of drivers with <10% ownership
        leverage_score: Leverage differentiation score (higher = more differentiated)
    """
    avg_ownership: float
    max_ownership: float
    total_ownership: float
    low_ownership_count: int
    leverage_score: float


class LeverageAwareOptimizer:
    """
    Leverage-aware optimizer for NASCAR DFS lineups.

    Extends portfolio optimization with ownership-based leverage to generate
    lineups that maximize differentiation from the field while preserving
    CVaR tail optimization.

    Usage:
        >>> optimizer = LeverageAwareOptimizer(
        ...     ownership=np.array([20, 15, 12, 10, 8, 7]),
        ...     leverage_penalty=0.5,
        ...     max_ownership_per_driver=0.3
        ... )
        >>> lineups = optimizer.optimize_lineup_with_leverage(
        ...     driver_data,
        ...     scenarios,
        ...     salary_cap=50000,
        ...     n_drivers=6
        ... )
    """

    def __init__(
        self,
        ownership: np.ndarray,
        leverage_penalty: float = 0.5,
        max_ownership_per_driver: float = 0.3,
        min_low_ownership_drivers: int = 2,
        max_total_ownership: float = 3.0
    ):
        """
        Initialize leverage-aware optimizer.

        Args:
            ownership: Array of ownership percentages for each driver (0-100)
            leverage_penalty: Weight for ownership penalty in objective (0-1)
            max_ownership_per_driver: Max ownership fraction for any single driver (0-1)
            min_low_ownership_drivers: Minimum number of drivers with <10% ownership
            max_total_ownership: Max sum of ownership fractions in lineup

        Raises:
            ValueError: If inputs are invalid
        """
        # Validate ownership array
        ownership_array = np.asarray(ownership, dtype=float)
        if len(ownership_array) == 0:
            raise ValueError("ownership array cannot be empty")

        if not np.all((ownership_array >= 0) & (ownership_array <= 100)):
            raise ValueError("ownership percentages must be in range [0, 100]")

        # Validate parameters
        if not (0.0 <= leverage_penalty <= 1.0):
            raise ValueError(f"leverage_penalty must be in [0, 1], got {leverage_penalty}")

        if not (0.0 <= max_ownership_per_driver <= 1.0):
            raise ValueError(
                f"max_ownership_per_driver must be in [0, 1], got {max_ownership_per_driver}"
            )

        if min_low_ownership_drivers < 0 or min_low_ownership_drivers > 6:
            raise ValueError(
                f"min_low_ownership_drivers must be in [0, 6], got {min_low_ownership_drivers}"
            )

        if max_total_ownership < 0:
            raise ValueError(
                f"max_total_ownership must be non-negative, got {max_total_ownership}"
            )

        self.ownership = ownership_array / 100.0  # Convert to fractions
        self.leverage_penalty = leverage_penalty
        self.max_ownership_per_driver = max_ownership_per_driver
        self.min_low_ownership_drivers = min_low_ownership_drivers
        self.max_total_ownership = max_total_ownership

        logger.info(
            f"Initialized LeverageAwareOptimizer: "
            f"n_drivers={len(ownership)}, "
            f"leverage_penalty={leverage_penalty:.2f}, "
            f"max_ownership={max_ownership_per_driver:.1%}"
        )

    def calculate_leverage_score(
        self,
        driver_indices: List[int],
        salary: Optional[int] = None
    ) -> LeverageMetrics:
        """
        Calculate leverage metrics for a lineup.

        Leverage score measures differentiation from the field based on ownership.
        Higher scores indicate more differentiation (lower ownership lineups).

        Args:
            driver_indices: Indices of drivers in lineup
            salary: Optional total salary for logging

        Returns:
            LeverageMetrics with ownership statistics
        """
        if not driver_indices:
            raise ValueError("driver_indices cannot be empty")

        # Get ownership for drivers in lineup
        lineup_ownership = self.ownership[driver_indices]

        # Calculate ownership metrics
        avg_ownership = lineup_ownership.mean() * 100  # Convert back to percentage
        max_ownership = lineup_ownership.max() * 100
        total_ownership = lineup_ownership.sum() * 100

        # Count low-ownership drivers (<10%)
        low_ownership_count = (lineup_ownership < 0.10).sum()

        # Calculate leverage score
        # Higher score = more differentiated from field
        # Score = (1 - avg_ownership_fraction) * (1 + low_ownership_bonus)
        avg_ownership_fraction = lineup_ownership.mean()
        low_ownership_bonus = low_ownership_count * 0.1
        leverage_score = (1 - avg_ownership_fraction) * (1 + low_ownership_bonus) * 100

        metrics = LeverageMetrics(
            avg_ownership=float(avg_ownership),
            max_ownership=float(max_ownership),
            total_ownership=float(total_ownership),
            low_ownership_count=int(low_ownership_count),
            leverage_score=float(leverage_score)
        )

        logger.debug(
            f"Leverage metrics: avg={metrics.avg_ownership:.1f}%, "
            f"max={metrics.max_ownership:.1f}%, "
            f"low_ownership={metrics.low_ownership_count}, "
            f"score={metrics.leverage_score:.1f}"
        )

        return metrics

    def check_ownership_constraints(
        self,
        driver_indices: List[int]
    ) -> Dict[str, bool]:
        """
        Check if lineup satisfies ownership constraints.

        Args:
            driver_indices: Indices of drivers in lineup

        Returns:
            Dict with constraint satisfaction status
        """
        metrics = self.calculate_leverage_score(driver_indices)

        # Check max ownership per driver
        max_ownership_ok = metrics.max_ownership / 100 <= self.max_ownership_per_driver

        # Check min low-ownership drivers
        min_low_ownership_ok = metrics.low_ownership_count >= self.min_low_ownership_drivers

        # Check max total ownership
        max_total_ownership_ok = metrics.total_ownership / 100 <= self.max_total_ownership

        return {
            'max_ownership_per_driver': max_ownership_ok,
            'min_low_ownership_drivers': min_low_ownership_ok,
            'max_total_ownership': max_total_ownership_ok,
            'all_satisfied': max_ownership_ok and min_low_ownership_ok and max_total_ownership_ok
        }

    def calculate_leverage_penalty(
        self,
        driver_indices: List[int]
    ) -> float:
        """
        Calculate leverage penalty for optimization objective.

        Higher ownership = higher penalty (discourages high-ownership lineups).

        Args:
            driver_indices: Indices of drivers in lineup

        Returns:
            Penalty value to subtract from objective
        """
        metrics = self.calculate_leverage_score(driver_indices)

        # Penalty = leverage_penalty * (1 - leverage_score/100)
        # Lower leverage score = higher penalty
        penalty = self.leverage_penalty * (1 - metrics.leverage_score / 100)

        return penalty

    def optimize_lineup_with_leverage(
        self,
        driver_data: List[Dict[str, Any]],
        scenarios: np.ndarray,
        salary_cap: int = 50000,
        n_drivers: int = 6,
        n_lineups: int = 1,
        random_seed: int = 42
    ) -> List[Dict[str, Any]]:
        """
        Generate leverage-optimized lineups.

        This is a simplified implementation that uses portfolio generator
        with ownership-aware modifications. For production use, integrate
        with the full portfolio_generator module.

        Args:
            driver_data: List of driver dicts with salary, team, etc.
            scenarios: Scenario matrix (n_scenarios, n_drivers)
            salary_cap: Salary cap constraint
            n_drivers: Number of drivers per lineup
            n_lineups: Number of lineups to generate
            random_seed: Random seed for reproducibility

        Returns:
            List of lineup dicts with leverage metrics
        """
        logger.info(
            f"Generating {n_lineups} leverage-optimized lineups "
            f"with {len(driver_data)} drivers"
        )

        # Import portfolio generator
        try:
            from app.portfolio_generator import generate_portfolio
        except ImportError:
            logger.error("portfolio_generator not available")
            return []

        # Wrap scenarios in function for portfolio generator
        def scenario_fn(n):
            return scenarios[:min(n, len(scenarios))]

        # Generate base portfolios
        # Note: This doesn't include leverage penalty in objective yet
        # For full implementation, need to modify portfolio generator
        lineups = []
        attempts = 0
        max_attempts = 10

        while len(lineups) < n_lineups and attempts < max_attempts:
            try:
                # Generate portfolio with different random seeds
                portfolio = generate_portfolio(
                    race_id=f"leverage_{len(lineups)}",
                    driver_data=driver_data,
                    scenario_fn=scenario_fn,
                    n_lineups=max(1, n_lineups - len(lineups)),
                    n_scenarios=len(scenarios),
                    salary_cap=salary_cap,
                    n_drivers=n_drivers,
                    random_seed=random_seed + attempts,
                    correlation_weight=0.2  # Increase diversity
                )

                # Add leverage metrics to each lineup
                for lineup in portfolio:
                    # Check ownership constraints
                    driver_indices = lineup['drivers']
                    constraints_ok = self.check_ownership_constraints(driver_indices)

                    # Filter lineups that don't satisfy constraints
                    if constraints_ok['all_satisfied']:
                        # Calculate leverage metrics
                        metrics = self.calculate_leverage_score(driver_indices)

                        # Add leverage metrics to lineup
                        lineup_with_leverage = {
                            **lineup,
                            'avg_ownership': metrics.avg_ownership,
                            'max_ownership': metrics.max_ownership,
                            'total_ownership': metrics.total_ownership,
                            'leverage_score': metrics.leverage_score,
                            'low_ownership_count': metrics.low_ownership_count
                        }
                        lineups.append(lineup_with_leverage)

            except Exception as e:
                logger.warning(f"Portfolio generation attempt {attempts} failed: {e}")

            attempts += 1

        logger.info(f"Generated {len(lineups)} leverage-optimized lineups")
        return lineups

    def generate_regime_aware_portfolio(
        self,
        driver_data: List[Dict[str, Any]],
        scenarios: np.ndarray,
        regimes: List[str],
        salary_cap: int = 50000,
        n_drivers: int = 6,
        n_lineups_per_regime: int = 3
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate regime-aware portfolio with leverage optimization.

        Allocates lineups across race-flow regimes (dominator, chaos, fuel_mileage)
        with ownership-aware leverage optimization for each regime.

        Args:
            driver_data: List of driver dicts
            scenarios: Scenario matrix (n_scenarios, n_drivers)
            regimes: List of regime labels for each scenario
            salary_cap: Salary cap constraint
            n_drivers: Number of drivers per lineup
            n_lineups_per_regime: Number of lineups to generate per regime

        Returns:
            Dict mapping regime names to lists of lineups
        """
        logger.info(
            f"Generating regime-aware portfolio: {n_lineups_per_regime} lineups per regime"
        )

        # Group scenarios by regime
        regime_scenarios = {}
        for regime in ['dominator', 'chaos', 'fuel_mileage']:
            regime_mask = np.array([r == regime for r in regimes])
            regime_scenarios[regime] = scenarios[regime_mask]

        # Generate lineups for each regime
        portfolio_by_regime = {}
        for regime, regime_scenario_matrix in regime_scenarios.items():
            if len(regime_scenario_matrix) == 0:
                logger.warning(f"No scenarios for regime '{regime}', skipping")
                continue

            logger.info(
                f"Generating {n_lineups_per_regime} lineups for '{regime}' regime "
                f"({len(regime_scenario_matrix)} scenarios)"
            )

            regime_lineups = self.optimize_lineup_with_leverage(
                driver_data=driver_data,
                scenarios=regime_scenario_matrix,
                salary_cap=salary_cap,
                n_drivers=n_drivers,
                n_lineups=n_lineups_per_regime,
                random_seed=hash(regime) % 1000  # Deterministic seed per regime
            )

            # Add regime label to lineups
            for lineup in regime_lineups:
                lineup['regime'] = regime

            portfolio_by_regime[regime] = regime_lineups

        total_lineups = sum(len(lineups) for lineups in portfolio_by_regime.values())
        logger.info(f"Generated {total_lineups} lineups across {len(portfolio_by_regime)} regimes")

        return portfolio_by_regime

    def __repr__(self) -> str:
        return (
            f"LeverageAwareOptimizer("
            f"n_drivers={len(self.ownership)}, "
            f"leverage_penalty={self.leverage_penalty:.2f}, "
            f"max_ownership={self.max_ownership_per_driver:.1%})"
        )
