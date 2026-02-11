"""
Monte Carlo contest simulation for DFS GPP modeling.

This module implements contest simulation infrastructure that models opponent
behavior through ownership-based field generation and computes contest outcomes
(ROI, Cash%, win probability) using payout-aware scoring.

Key features:
- Monte Carlo simulation across race scenarios
- Ownership-based field lineup sampling
- Payout curve integration for contest winnings
- Vectorized NumPy operations for efficiency
- Contest metrics (ROI, cash%, win probability)
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Union

import numpy as np

from apps.backend.app.contest.field_sim import FieldLineupSampler
from apps.backend.app.contest.payout_curve import PayoutCurveFitter

logger = logging.getLogger(__name__)


@dataclass
class ContestResult:
    """
    Result of a single contest simulation.

    Attributes:
        my_rank: Finishing position (1-indexed, 1 = best)
        my_payout: Payout amount in dollars
        my_score: My lineup's DFS score
        winning_score: Winning lineup's score
        field_size: Total number of lineups in contest
        cashed: Whether lineup cashed (typically top 25%)
        top_1_pct: Whether lineup finished in top 1%

    Example:
        >>> result = ContestResult(
        ...     my_rank=150,
        ...     my_payout=0.0,
        ...     my_score=145.5,
        ...     winning_score=182.3,
        ...     field_size=1000,
        ...     cashed=False,
        ...     top_1_pct=False
        ... )
        >>> print(f"Finished {result.my_rank}th with {result.my_score} points")
    """
    my_rank: int
    my_payout: float
    my_score: float
    winning_score: float
    field_size: int
    cashed: bool
    top_1_pct: bool


class ContestSimulator:
    """
    Monte Carlo contest simulator for DFS GPPs.

    Simulates contest outcomes by:
    1. Sampling field lineups from ownership distributions
    2. Scoring all lineups against simulated race scenarios
    3. Applying payout curves to determine winnings
    4. Aggregating results to compute ROI, Cash%, win probability

    Uses vectorized NumPy operations for performance.

    Usage:
        >>> ownership = np.array([20, 15, 12, 10, 8, 7, 6, 5, 5, 4, 4, 4])
        >>> driver_pool = [
        ...     {'driver_id': i+1, 'salary': 8000 + i*200, 'projected_points': 45 - i*2}
        ...     for i in range(12)
        ... ]
        >>> field_sampler = FieldLineupSampler(ownership, driver_pool)
        >>>
        >>> # Fit payout curve
        >>> ranks = np.array([1, 2, 3, 5, 10, 20, 50, 100])
        >>> payouts = np.array([100000, 50000, 30000, 15000, 5000, 2000, 500, 200])
        >>> payout_curve = PayoutCurveFitter()
        >>> payout_curve.fit(ranks, payouts)
        >>>
        >>> # Create simulator
        >>> simulator = ContestSimulator(
        ...     field_sampler=field_sampler,
        ...     payout_curve=payout_curve,
        ...     field_size=1000,
        ...     n_scenarios=100,
        ...     n_contest_sims=100
        ... )
        >>>
        >>> # Simulate contest
        >>> my_score = 150.0
        >>> driver_scores = np.random.gamma(20, 2, size=(100, 12))
        >>> result = simulator.simulate_contest(my_score, driver_scores[0])
        >>> print(f"Rank: {result.my_rank}, Payout: ${result.my_payout:.2f}")
    """

    # Define payout structure types
    PAYOUT_STANDARD_GPP = 'standard_gpp'
    PAYOUT_CASH = 'cash'
    PAYOUT_DOUBLE_UP = 'double_up'

    def __init__(
        self,
        field_sampler: FieldLineupSampler,
        payout_curve: Optional[PayoutCurveFitter] = None,
        field_size: int = 1000,
        n_scenarios: int = 1000,
        n_contest_sims: int = 100,
        default_payout_structure: str = PAYOUT_STANDARD_GPP
    ):
        """
        Initialize contest simulator.

        Args:
            field_sampler: FieldLineupSampler instance for generating field lineups
            payout_curve: Optional fitted PayoutCurveFitter. If None, uses default structure
            field_size: Number of lineups in the contest
            n_scenarios: Number of race outcome scenarios to simulate
            n_contest_sims: Number of contest simulations per scenario
            default_payout_structure: Which default payout curve to use if no curve provided
                - 'standard_gpp': Top 25% cash, power-law payout decay
                - 'cash': Top 50% cash, linear payout decay
                - 'double_up': Top 45% double payout (2x buyin)

        Raises:
            ValueError: If inputs are invalid
        """
        if not isinstance(field_sampler, FieldLineupSampler):
            raise ValueError(
                f"field_sampler must be FieldLineupSampler instance, "
                f"got {type(field_sampler)}"
            )

        if payout_curve is not None and not isinstance(payout_curve, PayoutCurveFitter):
            raise ValueError(
                f"payout_curve must be PayoutCurveFitter instance or None, "
                f"got {type(payout_curve)}"
            )

        if field_size <= 0:
            raise ValueError(f"field_size must be positive, got {field_size}")

        if n_scenarios <= 0:
            raise ValueError(f"n_scenarios must be positive, got {n_scenarios}")

        if n_contest_sims <= 0:
            raise ValueError(f"n_contest_sims must be positive, got {n_contest_sims}")

        if default_payout_structure not in [
            self.PAYOUT_STANDARD_GPP,
            self.PAYOUT_CASH,
            self.PAYOUT_DOUBLE_UP
        ]:
            raise ValueError(
                f"Invalid default_payout_structure: {default_payout_structure}. "
                f"Must be one of: {self.PAYOUT_STANDARD_GPP}, {self.PAYOUT_CASH}, "
                f"{self.PAYOUT_DOUBLE_UP}"
            )

        self.field_sampler = field_sampler
        self.payout_curve = payout_curve
        self.field_size = field_size
        self.n_scenarios = n_scenarios
        self.n_contest_sims = n_contest_sims
        self.default_payout_structure = default_payout_structure

        logger.info(
            f"Initialized ContestSimulator: "
            f"field_size={field_size}, "
            f"n_scenarios={n_scenarios}, "
            f"n_contest_sims={n_contest_sims}, "
            f"payout_curve={'fitted' if payout_curve else 'default'}"
        )

    def _apply_default_payout_structure(
        self,
        rank: int,
        buyin: float = 20.0
    ) -> float:
        """
        Apply default payout structure based on rank.

        Args:
            rank: Finishing position (1-indexed)
            buyin: Contest buy-in amount

        Returns:
            Payout amount
        """
        if self.default_payout_structure == self.PAYOUT_STANDARD_GPP:
            # Top 25% cash, power-law decay
            cash_cutoff = int(self.field_size * 0.25)
            if rank > cash_cutoff:
                return 0.0

            # Power-law payout: payout ∝ rank^(-1.5)
            # Scale so 1st place wins 1000x buyin
            payout = buyin * 1000 * (rank ** -1.5)

        elif self.default_payout_structure == self.PAYOUT_CASH:
            # Top 50% cash, linear decay to 1.1x buyin
            cash_cutoff = int(self.field_size * 0.50)
            if rank > cash_cutoff:
                return 0.0

            # Linear from 2x buyin (1st) to 1.1x buyin (cutoff)
            payout_ratio = 2.0 - (rank - 1) / cash_cutoff * 0.9
            payout = buyin * payout_ratio

        elif self.default_payout_structure == self.PAYOUT_DOUBLE_UP:
            # Top 45% double payout
            cash_cutoff = int(self.field_size * 0.45)
            if rank > cash_cutoff:
                return 0.0

            payout = buyin * 2.0

        else:
            # Fallback: no payout
            payout = 0.0

        return float(payout)

    def simulate_contest(
        self,
        my_lineup_score: float,
        scenario_driver_scores: np.ndarray,
        buyin: float = 20.0
    ) -> ContestResult:
        """
        Simulate a single contest outcome.

        Samples field lineup scores, combines with my score, determines rank
        and payout, and returns contest result.

        Args:
            my_lineup_score: My lineup's DFS score
            scenario_driver_scores: Driver scores for this scenario (n_drivers,)
            buyin: Contest buy-in amount (default 20.0)

        Returns:
            ContestResult with rank, payout, cash status, etc.

        Example:
            >>> my_score = 150.0
            >>> driver_scores = np.random.gamma(20, 2, size=12)
            >>> result = simulator.simulate_contest(my_score, driver_scores)
            >>> print(f"Rank: {result.my_rank}, Cashed: {result.cashed}")
        """
        # Sample field lineup scores
        # Generate field lineups and compute their scores
        field_lineups = self.field_sampler.sample_lineups_with_constraints(
            self.field_size - 1  # Exclude my lineup
        )

        field_scores = self.field_sampler.compute_lineup_scores(
            scenario_driver_scores,
            field_lineups
        )

        # Combine my score with field scores
        all_scores = np.concatenate([
            [my_lineup_score],
            field_scores
        ])

        # Calculate my rank (1-indexed, higher score = better rank)
        # Use argsort for efficiency: higher score = lower rank number
        # argsort returns indices that would sort the array
        sorted_indices = np.argsort(-all_scores)  # Negative for descending
        my_rank = np.where(sorted_indices == 0)[0][0] + 1  # +1 for 1-indexed

        # Determine payout
        if self.payout_curve is not None:
            # Use fitted payout curve
            my_payout = self.payout_curve.predict(np.array([my_rank]))[0]
        else:
            # Use default payout structure
            my_payout = self._apply_default_payout_structure(my_rank, buyin)

        # Check if cashed (typically top 25%)
        cash_cutoff = int(self.field_size * 0.25)
        cashed = my_rank <= cash_cutoff

        # Check if top 1% (top 10 positions in 1000-entry contest)
        top_1_cutoff = int(self.field_size * 0.01)
        top_1_pct = my_rank <= top_1_cutoff

        # Winning score
        winning_score = all_scores[sorted_indices[0]]

        result = ContestResult(
            my_rank=int(my_rank),
            my_payout=float(my_payout),
            my_score=float(my_lineup_score),
            winning_score=float(winning_score),
            field_size=self.field_size,
            cashed=cashed,
            top_1_pct=top_1_pct
        )

        logger.debug(
            f"Contest sim: rank={result.my_rank}, "
            f"payout=${result.my_payout:.2f}, "
            f"cashed={result.cashed}, "
            f"top_1%={result.top_1_pct}"
        )

        return result

    def simulate_portfolio(
        self,
        my_lineup_scores: np.ndarray,
        scenario_driver_scores: np.ndarray,
        buyin: float = 20.0
    ) -> Dict[str, np.ndarray]:
        """
        Simulate contest outcomes for a portfolio of lineups.

        Runs Monte Carlo simulations across scenarios and contest iterations,
        computing ranks, payouts, cash status, and top-1% status for each lineup.

        Args:
            my_lineup_scores: Scores for my lineups (n_lineups,)
            scenario_driver_scores: Driver scores for each scenario (n_scenarios, n_drivers)
            buyin: Contest buy-in amount (default 20.0)

        Returns:
            Dict with arrays of results:
                - ranks: (n_lineups, n_scenarios * n_contest_sims)
                - payouts: (n_lineups, n_scenarios * n_contest_sims)
                - cashed: (n_lineups, n_scenarios * n_contest_sims)
                - top_1_pct: (n_lineups, n_scenarios * n_contest_sims)

        Example:
            >>> my_scores = np.array([150, 145, 140])
            >>> driver_scores = np.random.gamma(20, 2, size=(100, 12))
            >>> results = simulator.simulate_portfolio(my_scores, driver_scores)
            >>> print(f"Average rank: {results['ranks'].mean()}")
        """
        n_lineups = len(my_lineup_scores)
        n_sims = self.n_scenarios * self.n_contest_sims

        logger.info(
            f"Simulating portfolio: {n_lineups} lineups, "
            f"{self.n_scenarios} scenarios x {self.n_contest_sims} contest sims = {n_sims} total"
        )

        # Pre-allocate results arrays
        ranks = np.zeros((n_lineups, n_sims), dtype=int)
        payouts = np.zeros((n_lineups, n_sims))
        cashed = np.zeros((n_lineups, n_sims), dtype=bool)
        top_1_pct = np.zeros((n_lineups, n_sims), dtype=bool)

        sim_idx = 0

        for scenario_idx in range(self.n_scenarios):
            driver_scores = scenario_driver_scores[scenario_idx]

            # Run multiple contest simulations per scenario
            for contest_sim in range(self.n_contest_sims):
                for lineup_idx, my_score in enumerate(my_lineup_scores):
                    result = self.simulate_contest(my_score, driver_scores, buyin)

                    ranks[lineup_idx, sim_idx] = result.my_rank
                    payouts[lineup_idx, sim_idx] = result.my_payout
                    cashed[lineup_idx, sim_idx] = result.cashed
                    top_1_pct[lineup_idx, sim_idx] = result.top_1_pct

                sim_idx += 1

            # Log progress every 10% of scenarios
            if (scenario_idx + 1) % max(1, self.n_scenarios // 10) == 0:
                progress = (scenario_idx + 1) / self.n_scenarios * 100
                logger.debug(f"Portfolio simulation progress: {progress:.0f}%")

        logger.info(
            f"Completed {n_sims} contest simulations for {n_lineups} lineups"
        )

        return {
            'ranks': ranks,
            'payouts': payouts,
            'cashed': cashed,
            'top_1_pct': top_1_pct
        }

    def compute_contest_metrics(
        self,
        results: Dict[str, np.ndarray],
        buyin: float = 20.0
    ) -> Dict[str, float]:
        """
        Compute contest-level metrics from simulation results.

        Calculates ROI, cash percentage, win probability, and risk metrics
        from Monte Carlo simulation results.

        Args:
            results: Results from simulate_portfolio with keys:
                - ranks: (n_lineups, n_sims)
                - payouts: (n_lineups, n_sims)
                - cashed: (n_lineups, n_sims)
                - top_1_pct: (n_lineups, n_sims)
            buyin: Contest buy-in amount (default 20.0)

        Returns:
            Dict with metrics:
                - roi: Expected return on investment (percentage)
                - roi_std: Standard deviation of ROI
                - cash_pct: Probability of cashing (percentage)
                - win_prob: Probability of top 1% finish (percentage)
                - ev: Expected value in dollars
                - avg_rank: Average finish position

        Example:
            >>> results = simulator.simulate_portfolio(my_scores, driver_scores)
            >>> metrics = simulator.compute_contest_metrics(results)
            >>> print(f"ROI: {metrics['roi']:.2f}%")
            >>> print(f"Cash%: {metrics['cash_pct']:.2f}%")
        """
        payouts = results['payouts']
        cashed = results['cashed']
        top_1_pct = results['top_1_pct']
        ranks = results['ranks']

        # Average across simulations for each lineup
        avg_payout = payouts.mean(axis=1)  # (n_lineups,)
        cash_rate = cashed.mean(axis=1).astype(float)  # (n_lineups,)
        win_rate = top_1_pct.mean(axis=1).astype(float)  # (n_lineups,)
        avg_rank = ranks.mean(axis=1).astype(float)  # (n_lineups,)

        # Compute ROI and EV
        roi = (avg_payout - buyin) / buyin * 100  # Percentage
        roi_std = (payouts.std(axis=1) / buyin * 100)  # ROI std
        ev = avg_payout  # Expected value in $

        # Aggregate across lineups (mean)
        metrics = {
            'roi': float(roi.mean()),
            'roi_std': float(roi_std.mean()),
            'cash_pct': float(cash_rate.mean() * 100),
            'win_prob': float(win_rate.mean() * 100),
            'ev': float(ev.mean()),
            'avg_rank': float(avg_rank.mean())
        }

        logger.info(
            f"Contest metrics: "
            f"ROI={metrics['roi']:.2f}% ± {metrics['roi_std']:.2f}%, "
            f"Cash%={metrics['cash_pct']:.2f}%, "
            f"Win%={metrics['win_prob']:.2f}%, "
            f"EV=${metrics['ev']:.2f}"
        )

        return metrics

    def simulate_single_lineup_distribution(
        self,
        my_lineup_score: float,
        scenario_driver_scores: np.ndarray,
        buyin: float = 20.0
    ) -> Dict[str, Union[float, np.ndarray]]:
        """
        Simulate distribution of outcomes for a single lineup.

        Runs multiple contest simulations across scenarios and returns
        detailed statistics on outcome distribution.

        Args:
            my_lineup_score: My lineup's DFS score
            scenario_driver_scores: Driver scores for each scenario (n_scenarios, n_drivers)
            buyin: Contest buy-in amount (default 20.0)

        Returns:
            Dict with statistics:
                - mean_rank: Average finish position
                - median_rank: Median finish position
                - best_rank: Best finish position
                - worst_rank: Worst finish position
                - mean_payout: Average payout
                - median_payout: Median payout
                - cash_pct: Percentage of simulations cashed
                - win_pct: Percentage of top-1% finishes
                - roi: Expected ROI (percentage)
                - all_ranks: Array of all rank outcomes
                - all_payouts: Array of all payout outcomes

        Example:
            >>> my_score = 150.0
            >>> driver_scores = np.random.gamma(20, 2, size=(100, 12))
            >>> stats = simulator.simulate_single_lineup_distribution(my_score, driver_scores)
            >>> print(f"Mean rank: {stats['mean_rank']:.1f}")
            >>> print(f"Cash%: {stats['cash_pct']:.2f}%")
        """
        # Run simulations for single lineup (convert to array)
        my_scores_array = np.array([my_lineup_score])

        results = self.simulate_portfolio(
            my_scores_array,
            scenario_driver_scores,
            buyin
        )

        # Extract results for this lineup
        ranks = results['ranks'][0]  # (n_sims,)
        payouts = results['payouts'][0]  # (n_sims,)
        cashed = results['cashed'][0]  # (n_sims,)
        top_1_pct = results['top_1_pct'][0]  # (n_sims,)

        # Compute statistics
        stats = {
            'mean_rank': float(ranks.mean()),
            'median_rank': float(np.median(ranks)),
            'best_rank': int(ranks.min()),
            'worst_rank': int(ranks.max()),
            'mean_payout': float(payouts.mean()),
            'median_payout': float(np.median(payouts)),
            'cash_pct': float(cashed.mean() * 100),
            'win_pct': float(top_1_pct.mean() * 100),
            'roi': float((payouts.mean() - buyin) / buyin * 100),
            'all_ranks': ranks,
            'all_payouts': payouts
        }

        logger.info(
            f"Single lineup distribution: "
            f"mean_rank={stats['mean_rank']:.1f}, "
            f"cash%={stats['cash_pct']:.2f}%, "
            f"ROI={stats['roi']:.2f}%"
        )

        return stats

    def __repr__(self) -> str:
        return (
            f"ContestSimulator("
            f"field_size={self.field_size}, "
            f"n_scenarios={self.n_scenarios}, "
            f"n_contest_sims={self.n_contest_sims}, "
            f"payout_curve={'fitted' if self.payout_curve else 'default'})"
        )
