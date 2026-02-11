"""
Contest simulation and payout modeling module.

This module provides infrastructure for modeling DraftKings GPP payout structures
and simulating contest outcomes for NASCAR DFS optimization.

Key components:
- FieldLineupSampler: Ownership-based field lineup generation with Dirichlet-multinomial sampling
- ContestSimulator: Monte Carlo contest simulation with payout-aware scoring
- PayoutCurveFitter: Fits parametric models (power-law, exponential) to historical payout data
- PowerLawPayoutCurve: Power-law decay model (payout = a * rank^(-b))
- ExponentialPayoutCurve: Exponential decay model (payout = a * exp(-b * rank))
- Contest metrics: ROI, cash%, win probability calculation utilities
- Contest Pydantic models: Data validation for contest structures

The contest simulation approach enables:
1. Ownership-based field lineup modeling (Dirichlet-multinomial sampling)
2. Monte Carlo simulation across race scenarios (vectorized NumPy operations)
3. Payout-aware contest outcome calculation (ROI, cash%, win probability)
4. Portfolio-level metrics aggregation and comparison
"""

from apps.backend.app.contest.payout_curve import (
    PayoutCurveFitter,
    PowerLawPayoutCurve,
    ExponentialPayoutCurve,
    load_historical_payouts,
    fit_payout_curves_by_tier,
    get_payout_curve_for_contest,
    interpolate_payout_for_rank,
)

from apps.backend.app.contest.field_sim import (
    FieldLineupSampler,
    dirichlet_multinomial_sample,
)

from apps.backend.app.contest.contest_sim import (
    ContestSimulator,
    ContestResult,
)

from apps.backend.app.contest.metrics import (
    compute_roi,
    compute_cash_pct,
    compute_win_prob,
    compute_portfolio_metrics,
    compute_per_lineup_metrics,
    print_contest_report,
    print_lineup_comparison,
    format_metrics_summary,
    compare_lineups,
    compute_sharpe_ratio,
)

__all__ = [
    # Payout curve (from Plan 04-03)
    "PayoutCurveFitter",
    "PowerLawPayoutCurve",
    "ExponentialPayoutCurve",
    "load_historical_payouts",
    "fit_payout_curves_by_tier",
    "get_payout_curve_for_contest",
    "interpolate_payout_for_rank",
    # Field simulation (from Plan 04-04)
    "FieldLineupSampler",
    "dirichlet_multinomial_sample",
    # Contest simulation (from Plan 04-04)
    "ContestSimulator",
    "ContestResult",
    # Contest metrics (from Plan 04-04)
    "compute_roi",
    "compute_cash_pct",
    "compute_win_prob",
    "compute_portfolio_metrics",
    "compute_per_lineup_metrics",
    "print_contest_report",
    "print_lineup_comparison",
    "format_metrics_summary",
    "compare_lineups",
    "compute_sharpe_ratio",
]
