"""
Tail metrics computation for conditional-upside optimization.

This module provides efficient, stable tail metric calculations for scenario-based
portfolio optimization, including:
- Conditional Value at Risk (CVaR) using Rockafellar-Uryasev formulation
- Top X% outcome metrics (tournament equity)
- Conditional upside (tail mean vs. overall mean)
- Adaptive scenario count thresholds for stability

Key design principles:
1. Use np.partition() for O(n) tail selection (NOT np.sort which is O(n log n))
2. Standard Rockafellar-Uryasev CVaR formulation (zeta + tail_slack mean)
3. Adaptive scenario counts prevent instability from insufficient samples
4. Bootstrap stability validation detects unreliable tail estimates

Reference: Rockafellar & Uryasev (2000) "Optimization of Conditional Value-at-Risk"
"""
import logging
from dataclasses import dataclass
from typing import Dict, Optional, Callable

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TailMetrics:
    """
    Tail risk metrics for scenario-based portfolio optimization.

    Attributes:
        VaR: Value at Risk (worst outcome in tail region)
        CVaR: Conditional Value at Risk (mean of tail region)
        top_X_pct: Best outcome in tail region (Top X% performance)
        conditional_upside: CVaR - overall_mean (tail premium vs. average)
        alpha: Tail quantile used (e.g., 0.99 for top 1%)
    """
    VaR: float
    CVaR: float
    top_X_pct: float
    conditional_upside: float
    alpha: float


def compute_cvar(
    scenario_points: np.ndarray,
    alpha: float = 0.99,
) -> float:
    """
    Compute Conditional Value at Risk (CVaR) using Rockafellar-Uryasev formulation.

    CVaR is the expected value in the worst (1-alpha) proportion of scenarios.
    For tournament optimization, we use alpha > 0.5 to focus on top-tail outcomes.

    This implementation uses np.partition() for O(n) performance, avoiding the
    O(n log n) cost of np.sort().

    Args:
        scenario_points: Array of portfolio points per scenario, shape (n_scenarios,)
        alpha: Tail quantile (e.g., 0.99 for top 1%, 0.95 for top 5%)

    Returns:
        CVaR: Mean of outcomes in the top (1-alpha) proportion

    Raises:
        ValueError: If scenario_points is empty or alpha is not in [0, 1]

    Examples:
        >>> scenarios = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        >>> compute_cvar(scenarios, alpha=0.90)  # Top 10% (top 1 scenario)
        10.0
        >>> compute_cvar(scenarios, alpha=0.80)  # Top 20% (top 2 scenarios)
        9.5
    """
    if len(scenario_points) == 0:
        raise ValueError("scenario_points cannot be empty")

    if not 0 <= alpha <= 1:
        raise ValueError(f"alpha must be in [0, 1], got {alpha}")

    # Handle edge cases
    if alpha == 1.0:
        return float(np.max(scenario_points))
    if alpha == 0.0:
        return float(np.min(scenario_points))

    # Number of scenarios in the tail
    n_scenarios = len(scenario_points)
    k = max(1, int((1 - alpha) * n_scenarios))

    # Use np.partition for O(n) selection of top k elements
    # np.partition(arr, -k) puts the k-th largest element at position -k
    # with all larger elements to the right
    top_k = np.partition(scenario_points, -k)[-k:]

    # CVaR is the mean of the tail
    cvar = float(np.mean(top_k))

    logger.debug(
        f"CVaR({alpha:.2f}): {cvar:.3f} from {n_scenarios} scenarios, tail size={k}"
    )

    return cvar


def compute_tail_metrics(
    scenario_points: np.ndarray,
    alpha: float = 0.99,
) -> TailMetrics:
    """
    Compute comprehensive tail metrics for scenario-based optimization.

    Calculates:
    - VaR: Value at Risk (worst outcome in tail)
    - CVaR: Conditional Value at Risk (mean of tail)
    - Top X%: Best outcome in tail
    - Conditional upside: CVaR - overall_mean

    Args:
        scenario_points: Array of portfolio points per scenario, shape (n_scenarios,)
        alpha: Tail quantile (e.g., 0.99 for top 1%, 0.95 for top 5%)

    Returns:
        TailMetrics dataclass with all computed metrics

    Raises:
        ValueError: If scenario_points is empty or alpha is not in [0, 1]

    Examples:
        >>> np.random.seed(42)
        >>> scenarios = np.random.randn(1000)
        >>> metrics = compute_tail_metrics(scenarios, alpha=0.99)
        >>> print(f"CVaR: {metrics.CVaR:.3f}")
        >>> print(f"Conditional upside: {metrics.conditional_upside:.3f}")
    """
    if len(scenario_points) == 0:
        raise ValueError("scenario_points cannot be empty")

    if not 0 <= alpha <= 1:
        raise ValueError(f"alpha must be in [0, 1], got {alpha}")

    # Handle edge cases
    if alpha == 1.0:
        max_val = float(np.max(scenario_points))
        mean_val = float(np.mean(scenario_points))
        return TailMetrics(
            VaR=max_val,
            CVaR=max_val,
            top_X_pct=max_val,
            conditional_upside=max_val - mean_val,
            alpha=alpha,
        )

    if alpha == 0.0:
        min_val = float(np.min(scenario_points))
        mean_val = float(np.mean(scenario_points))
        return TailMetrics(
            VaR=min_val,
            CVaR=min_val,
            top_X_pct=min_val,
            conditional_upside=min_val - mean_val,
            alpha=alpha,
        )

    # Number of scenarios in the tail
    n_scenarios = len(scenario_points)
    k = max(1, int((1 - alpha) * n_scenarios))

    # Warn if tail size is too small for stable estimates
    if k < 10:
        logger.warning(
            f"Tail size {k} < 10 - CVaR estimates may be unstable. "
            f"Recommend at least {adaptive_scenario_count(alpha)} scenarios."
        )

    # Use np.partition for O(n) selection of top k elements
    top_k = np.partition(scenario_points, -k)[-k:]

    # Compute metrics
    VaR = float(top_k[0])  # Worst outcome in tail
    CVaR = float(np.mean(top_k))  # Mean of tail
    top_X_pct = float(top_k[-1])  # Best outcome in tail
    overall_mean = float(np.mean(scenario_points))
    conditional_upside = CVaR - overall_mean

    metrics = TailMetrics(
        VaR=VaR,
        CVaR=CVaR,
        top_X_pct=top_X_pct,
        conditional_upside=conditional_upside,
        alpha=alpha,
    )

    logger.info(
        f"Tail metrics (alpha={alpha:.2f}): "
        f"VaR={VaR:.3f}, CVaR={CVaR:.3f}, "
        f"Top {int((1-alpha)*100)}%={top_X_pct:.3f}, "
        f"Conditional upside={conditional_upside:.3f}"
    )

    return metrics


def compute_top_X_metrics(
    scenario_points: np.ndarray,
    quantiles: Optional[list] = None,
) -> Dict[str, float]:
    """
    Compute Top X% metrics for multiple quantiles.

    Args:
        scenario_points: Array of portfolio points per scenario, shape (n_scenarios,)
        quantiles: List of alpha values (default: [0.99, 0.95, 0.90])

    Returns:
        Dict with keys like "Top_1pct", "Top_5pct", "Top_10pct"

    Examples:
        >>> scenarios = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        >>> compute_top_X_metrics(scenarios, [0.90, 0.80])
        {'Top_10pct': 10.0, 'Top_20pct': 9.0}
    """
    if quantiles is None:
        quantiles = [0.99, 0.95, 0.90]

    metrics = {}
    for alpha in quantiles:
        k = max(1, int((1 - alpha) * len(scenario_points)))
        top_k = np.partition(scenario_points, -k)[-k:]
        top_value = float(top_k[-1])  # Best in tail
        # Use round to avoid floating point precision issues
        key = f"Top_{int(round((1-alpha)*100))}pct"
        metrics[key] = top_value

    return metrics


def adaptive_scenario_count(
    target_alpha: float,
    min_tail_samples: int = 100,
) -> int:
    """
    Calculate minimum scenario count for stable tail estimation.

    Rule of thumb: Need at least min_tail_samples in the tail region.
    For alpha=0.99 (top 1%), need at least 100 / 0.01 = 10,000 scenarios.

    This function returns tiered thresholds based on the target alpha:
    - alpha >= 0.99: 10,000 scenarios (for extreme tail estimation)
    - alpha >= 0.95: 2,000 scenarios (for top 5% estimation)
    - alpha >= 0.90: 1,000 scenarios (for top 10% estimation)
    - alpha < 0.90: 500 scenarios (for broader tails)

    Args:
        target_alpha: Target tail quantile (e.g., 0.99 for top 1%)
        min_tail_samples: Minimum samples required in tail region (default: 100)

    Returns:
        Minimum number of scenarios for stable CVaR estimation

    Raises:
        ValueError: If target_alpha is not in [0, 1] or min_tail_samples < 1

    Examples:
        >>> adaptive_scenario_count(0.99)
        10000
        >>> adaptive_scenario_count(0.95)
        2000
        >>> adaptive_scenario_count(0.90)
        1000
        >>> adaptive_scenario_count(0.80, min_tail_samples=50)
        500
    """
    if not 0 <= target_alpha <= 1:
        raise ValueError(f"target_alpha must be in [0, 1], got {target_alpha}")

    if min_tail_samples < 1:
        raise ValueError(f"min_tail_samples must be >= 1, got {min_tail_samples}")

    # Calculate required scenarios based on formula
    # Need at least min_tail_samples in the (1 - alpha) tail region
    required_scenarios = int(np.ceil(min_tail_samples / (1 - target_alpha)))

    # Apply tiered thresholds
    if target_alpha >= 0.99:
        # Extreme tail (top 1% or less) - need many scenarios
        return max(required_scenarios, 10000)
    elif target_alpha >= 0.95:
        # Top 5% - moderate scenario count
        return max(required_scenarios, 2000)
    elif target_alpha >= 0.90:
        # Top 10% - lower scenario count
        return max(required_scenarios, 1000)
    else:
        # Broader tails - can use fewer scenarios
        return max(required_scenarios, 500)


def validate_tail_stability(
    scenarios: np.ndarray,
    optimize_fn: Callable[[np.ndarray], list],
    alpha: float = 0.99,
    n_bootstrap: int = 10,
) -> Dict[str, any]:
    """
    Validate tail metric stability using bootstrap resampling.

    Performs bootstrap resampling of scenarios to assess the stability
    of CVaR estimates. High coefficient of variation (CV) or low
    lineup consistency indicates unstable tail estimates.

    Args:
        scenarios: Array of scenario outcomes, shape (n_scenarios,)
        optimize_fn: Function that takes scenarios and returns lineup scores
        alpha: Tail quantile for CVaR calculation (default: 0.99)
        n_bootstrap: Number of bootstrap iterations (default: 10)

    Returns:
        Dict with:
        - cvar_cv: Coefficient of variation of CVaR across bootstrap samples
        - lineup_consistency: Fraction of bootstrap samples with same top lineup
        - stable: Boolean indicating if estimates are stable (CV < 0.2 and consistency > 0.7)
        - cvar_values: Array of CVaR values from each bootstrap sample

    Raises:
        ValueError: If scenarios is empty or n_bootstrap < 2

    Examples:
        >>> np.random.seed(42)
        >>> scenarios = np.random.randn(10000)
        >>> def dummy_optimize(s): return list(range(6))
        >>> stability = validate_tail_stability(scenarios, dummy_optimize, n_bootstrap=5)
        >>> print(f"Stable: {stability['stable']}, CV: {stability['cvar_cv']:.3f}")
    """
    if len(scenarios) == 0:
        raise ValueError("scenarios cannot be empty")

    if n_bootstrap < 2:
        raise ValueError(f"n_bootstrap must be >= 2, got {n_bootstrap}")

    n_scenarios = len(scenarios)
    cvar_values = []
    lineup_rankings = []

    # Perform bootstrap resampling
    for i in range(n_bootstrap):
        # Resample scenarios with replacement
        bootstrap_sample = np.random.choice(scenarios, size=n_scenarios, replace=True)

        # Compute CVaR for this bootstrap sample
        bootstrap_cvar = compute_cvar(bootstrap_sample, alpha=alpha)
        cvar_values.append(bootstrap_cvar)

        # Get lineup ranking from optimize function
        ranking = optimize_fn(bootstrap_sample)
        lineup_rankings.append(tuple(ranking))

    # Calculate coefficient of variation (CV = std / mean)
    cvar_values = np.array(cvar_values)
    cvar_mean = float(np.mean(cvar_values))
    cvar_std = float(np.std(cvar_values, ddof=1))

    # Avoid division by zero
    if cvar_mean != 0:
        cvar_cv = cvar_std / abs(cvar_mean)
    else:
        cvar_cv = float('inf')

    # Calculate lineup consistency
    # Fraction of bootstrap samples that produce the same top lineup
    most_common_ranking = max(set(lineup_rankings), key=lineup_rankings.count)
    lineup_consistency = lineup_rankings.count(most_common_ranking) / n_bootstrap

    # Determine stability
    stable = (cvar_cv < 0.2) and (lineup_consistency > 0.7)

    # Log warnings if unstable
    if not stable:
        logger.warning(
            f"Unstable tail estimates detected: "
            f"CVaR CV={cvar_cv:.3f} (threshold: 0.2), "
            f"Lineup consistency={lineup_consistency:.3f} (threshold: 0.7). "
            f"Recommend increasing scenario count to {adaptive_scenario_count(alpha)}."
        )

    result = {
        'cvar_cv': cvar_cv,
        'lineup_consistency': lineup_consistency,
        'stable': stable,
        'cvar_values': cvar_values,
        'cvar_mean': cvar_mean,
        'cvar_std': cvar_std,
    }

    logger.info(
        f"Tail stability (alpha={alpha:.2f}): "
        f"CV={cvar_cv:.3f}, Consistency={lineup_consistency:.3f}, Stable={stable}"
    )

    return result
