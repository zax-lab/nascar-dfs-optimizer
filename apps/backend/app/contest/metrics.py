"""
Contest metrics calculation utilities for DFS analysis.

This module provides functions for computing key contest metrics from
simulation results, including ROI, cash percentage, win probability,
and portfolio-level statistics.

Key features:
- ROI calculation with confidence intervals
- Cash percentage with standard error
- Win probability (top 1%) computation
- Portfolio-level aggregation
- Pretty-printed contest reports
"""

import logging
from typing import Dict, List, Any, Union

import numpy as np

logger = logging.getLogger(__name__)


def compute_roi(
    payouts: np.ndarray,
    buyin: float
) -> Dict[str, float]:
    """
    Calculate ROI and confidence intervals from payout distribution.

    Args:
        payouts: Array of payout amounts from simulations
        buyin: Contest buy-in amount

    Returns:
        Dict with keys:
            - roi: Expected return on investment (percentage)
            - roi_std: Standard deviation of ROI (percentage)
            - roi_lower_5: 5th percentile ROI (percentage)
            - roi_upper_95: 95th percentile ROI (percentage)

    Example:
        >>> payouts = np.array([0, 0, 100, 0, 50, 200, 0, 0])
        >>> roi = compute_roi(payouts, buyin=20.0)
        >>> print(f"ROI: {roi['roi']:.2f}% ± {roi['roi_std']:.2f}%")
        ROI: 56.25% ± 112.50%
    """
    if buyin <= 0:
        raise ValueError(f"buyin must be positive, got {buyin}")

    payouts_array = np.asarray(payouts, dtype=float)

    # Calculate ROI for each simulation
    roi_per_sim = (payouts_array - buyin) / buyin * 100

    # Compute statistics
    roi_mean = float(roi_per_sim.mean())
    roi_std = float(roi_per_sim.std())
    roi_lower_5 = float(np.percentile(roi_per_sim, 5))
    roi_upper_95 = float(np.percentile(roi_per_sim, 95))

    result = {
        'roi': roi_mean,
        'roi_std': roi_std,
        'roi_lower_5': roi_lower_5,
        'roi_upper_95': roi_upper_95
    }

    logger.debug(
        f"ROI: {roi_mean:.2f}% ± {roi_std:.2f}% "
        f"(5th: {roi_lower_5:.2f}%, 95th: {roi_upper_95:.2f}%)"
    )

    return result


def compute_cash_pct(cashed: np.ndarray) -> Dict[str, float]:
    """
    Calculate cash percentage and standard error.

    Args:
        cashed: Boolean array indicating whether lineup cashed in each simulation

    Returns:
        Dict with keys:
            - cash_pct: Cash percentage (0-100)
            - cash_se: Standard error of cash percentage
            - n_simulations: Number of simulations

    Example:
        >>> cashed = np.array([True, False, True, False, True])
        >>> cash = compute_cash_pct(cashed)
        >>> print(f"Cash%: {cash['cash_pct']:.2f}% ± {cash['cash_se']:.2f}%")
        Cash%: 60.00% ± 21.91%
    """
    cashed_array = np.asarray(cashed, dtype=bool)
    n = len(cashed_array)

    if n == 0:
        raise ValueError("cashed array must not be empty")

    # Calculate cash percentage
    cash_pct = float(cashed_array.mean() * 100)

    # Calculate standard error: sqrt(p * (1-p) / n)
    p = cashed_array.mean()
    cash_se = float(np.sqrt(p * (1 - p) / n) * 100)

    result = {
        'cash_pct': cash_pct,
        'cash_se': cash_se,
        'n_simulations': n
    }

    logger.debug(f"Cash%: {cash_pct:.2f}% ± {cash_se:.2f}% (n={n})")

    return result


def compute_win_prob(top_1_pct: np.ndarray) -> Dict[str, float]:
    """
    Calculate win probability (top 1% finish) and standard error.

    Args:
        top_1_pct: Boolean array indicating whether lineup finished in top 1%

    Returns:
        Dict with keys:
            - win_prob: Win probability (0-100)
            - win_se: Standard error of win probability
            - n_simulations: Number of simulations

    Example:
        >>> top_1_pct = np.array([True, False, False, False, False])
        >>> win = compute_win_prob(top_1_pct)
        >>> print(f"Win%: {win['win_prob']:.2f}% ± {win['win_se']:.2f}%")
        Win%: 20.00% ± 17.89%
    """
    top_1_array = np.asarray(top_1_pct, dtype=bool)
    n = len(top_1_array)

    if n == 0:
        raise ValueError("top_1_pct array must not be empty")

    # Calculate win percentage
    win_prob = float(top_1_array.mean() * 100)

    # Calculate standard error: sqrt(p * (1-p) / n)
    p = top_1_array.mean()
    win_se = float(np.sqrt(p * (1 - p) / n) * 100)

    result = {
        'win_prob': win_prob,
        'win_se': win_se,
        'n_simulations': n
    }

    logger.debug(f"Win%: {win_prob:.2f}% ± {win_se:.2f}% (n={n})")

    return result


def compute_portfolio_metrics(
    ranks: np.ndarray,
    payouts: np.ndarray,
    cashed: np.ndarray,
    top_1_pct: np.ndarray,
    buyin: float
) -> Dict[str, Any]:
    """
    Compute all metrics for a portfolio of lineups.

    Aggregates individual metrics and adds portfolio-level statistics.

    Args:
        ranks: Array of ranks (n_lineups, n_sims)
        payouts: Array of payouts (n_lineups, n_sims)
        cashed: Boolean array of cashed status (n_lineups, n_sims)
        top_1_pct: Boolean array of top-1% status (n_lineups, n_sims)
        buyin: Contest buy-in amount

    Returns:
        Dict with all metrics:
            - roi: Expected ROI (percentage)
            - roi_std: ROI standard deviation (percentage)
            - roi_lower_5: 5th percentile ROI (percentage)
            - roi_upper_95: 95th percentile ROI (percentage)
            - cash_pct: Cash percentage (percentage)
            - cash_se: Cash percentage standard error (percentage)
            - win_prob: Win probability (percentage)
            - win_se: Win probability standard error (percentage)
            - best_rank: Best rank across all simulations
            - worst_rank: Worst rank across all simulations
            - avg_rank: Average rank across all simulations
            - best_payout: Best payout across all simulations
            - total_entries: Total number of lineup entries

    Example:
        >>> ranks = np.random.randint(1, 1000, size=(5, 1000))
        >>> payouts = np.where(ranks <= 250, np.random.uniform(0, 100000, size=(5, 1000)), 0)
        >>> cashed = ranks <= 250
        >>> top_1_pct = ranks <= 10
        >>> metrics = compute_portfolio_metrics(ranks, payouts, cashed, top_1_pct, buyin=20.0)
        >>> print(f"ROI: {metrics['roi']:.2f}%")
    """
    # Flatten arrays for aggregation
    ranks_flat = ranks.flatten()
    payouts_flat = payouts.flatten()
    cashed_flat = cashed.flatten()
    top_1_flat = top_1_pct.flatten()

    # Compute individual metrics
    roi_result = compute_roi(payouts_flat, buyin)
    cash_result = compute_cash_pct(cashed_flat)
    win_result = compute_win_prob(top_1_flat)

    # Compute portfolio-level statistics
    best_rank = int(ranks_flat.min())
    worst_rank = int(ranks_flat.max())
    avg_rank = float(ranks_flat.mean())
    best_payout = float(payouts_flat.max())
    total_entries = ranks.shape[0] * ranks.shape[1]

    # Aggregate all results
    result = {
        **roi_result,
        **cash_result,
        **win_result,
        'best_rank': best_rank,
        'worst_rank': worst_rank,
        'avg_rank': avg_rank,
        'best_payout': best_payout,
        'total_entries': total_entries
    }

    logger.info(
        f"Portfolio metrics: "
        f"ROI={result['roi']:.2f}%, "
        f"Cash%={result['cash_pct']:.2f}%, "
        f"Win%={result['win_prob']:.2f}%, "
        f"best_rank={result['best_rank']}, "
        f"best_payout=${result['best_payout']:.2f}"
    )

    return result


def compute_per_lineup_metrics(
    ranks: np.ndarray,
    payouts: np.ndarray,
    cashed: np.ndarray,
    top_1_pct: np.ndarray,
    buyin: float
) -> List[Dict[str, Any]]:
    """
    Compute metrics for each lineup separately.

    Args:
        ranks: Array of ranks (n_lineups, n_sims)
        payouts: Array of payouts (n_lineups, n_sims)
        cashed: Boolean array of cashed status (n_lineups, n_sims)
        top_1_pct: Boolean array of top-1% status (n_lineups, n_sims)
        buyin: Contest buy-in amount

    Returns:
        List of dicts, one per lineup, with keys:
            - lineup_idx: Lineup index
            - roi: Expected ROI (percentage)
            - cash_pct: Cash percentage (percentage)
            - win_prob: Win probability (percentage)
            - avg_rank: Average rank
            - best_payout: Best payout

    Example:
        >>> metrics = compute_per_lineup_metrics(ranks, payouts, cashed, top_1_pct, 20.0)
        >>> for m in metrics:
        ...     print(f"Lineup {m['lineup_idx']}: ROI={m['roi']:.2f}%")
    """
    n_lineups = ranks.shape[0]
    metrics_list = []

    for i in range(n_lineups):
        # Compute metrics for this lineup
        roi_result = compute_roi(payouts[i], buyin)
        cash_result = compute_cash_pct(cashed[i])
        win_result = compute_win_prob(top_1_pct[i])

        lineup_metrics = {
            'lineup_idx': i,
            'roi': roi_result['roi'],
            'cash_pct': cash_result['cash_pct'],
            'win_prob': win_result['win_prob'],
            'avg_rank': float(ranks[i].mean()),
            'best_payout': float(payouts[i].max())
        }

        metrics_list.append(lineup_metrics)

    return metrics_list


def print_contest_report(metrics: Dict[str, Any], buyin: float = 20.0) -> None:
    """
    Pretty-print contest metrics report.

    Args:
        metrics: Dict from compute_portfolio_metrics
        buyin: Contest buy-in amount (for display)

    Example:
        >>> metrics = compute_portfolio_metrics(ranks, payouts, cashed, top_1_pct, 20.0)
        >>> print_contest_report(metrics)
        ========================================
        CONTEST SIMULATION RESULTS
        ========================================
        ...
    """
    print("\n" + "=" * 50)
    print("CONTEST SIMULATION RESULTS")
    print("=" * 50)

    # ROI section
    print("\nReturn on Investment (ROI):")
    print(f"  Expected ROI:    {metrics['roi']:>7.2f}%")
    print(f"  Std Dev:         {metrics['roi_std']:>7.2f}%")
    print(f"  90% CI:          [{metrics['roi_lower_5']:>7.2f}%, {metrics['roi_upper_95']:>7.2f}%]")

    # Cash percentage section
    print("\nCash Percentage:")
    print(f"  Cash Rate:       {metrics['cash_pct']:>7.2f}%")
    print(f"  Std Error:       {metrics['cash_se']:>7.2f}%")

    # Win probability section
    print("\nWin Probability (Top 1%):")
    print(f"  Win Rate:        {metrics['win_prob']:>7.2f}%")
    print(f"  Std Error:       {metrics['win_se']:>7.2f}%")

    # Portfolio statistics section
    print("\nPortfolio Statistics:")
    print(f"  Best Rank:       {metrics['best_rank']:>7d}")
    print(f"  Worst Rank:      {metrics['worst_rank']:>7d}")
    print(f"  Average Rank:    {metrics['avg_rank']:>7.1f}")
    print(f"  Best Payout:     ${metrics['best_payout']:>7.2f}")
    print(f"  Total Entries:   {metrics['total_entries']:>7d}")

    # Expected value
    ev = metrics['roi'] / 100 * buyin + buyin
    print(f"\nExpected Value:   ${ev:>7.2f} (buyin: ${buyin:.2f})")

    print("\n" + "=" * 50)


def print_lineup_comparison(metrics_list: List[Dict[str, Any]]) -> None:
    """
    Pretty-print comparison of multiple lineups.

    Args:
        metrics_list: List of dicts from compute_per_lineup_metrics

    Example:
        >>> metrics = compute_per_lineup_metrics(ranks, payouts, cashed, top_1_pct, 20.0)
        >>> print_lineup_comparison(metrics)
        ========================================
        LINEUP COMPARISON
        ========================================
        Lineup |   ROI% | Cash% | Win% | AvgRank | BestPayout
        -------|--------|-------|------|--------|-----------
             0 |  12.50 | 25.00 |  2.50 |   450.2 |   $100.00
             1 |  -5.00 | 20.00 |  1.00 |   520.1 |    $50.00
        ...
    """
    print("\n" + "=" * 70)
    print("LINEUP COMPARISON")
    print("=" * 70)
    print(f"{'Lineup':>7} | {'ROI%':>6} | {'Cash%':>5} | {'Win%':>4} | {'AvgRank':>7} | {'BestPayout':>10}")
    print("-" * 70)

    for m in metrics_list:
        print(
            f"{m['lineup_idx']:>7} | "
            f"{m['roi']:>6.2f} | "
            f"{m['cash_pct']:>5.2f} | "
            f"{m['win_prob']:>4.2f} | "
            f"{m['avg_rank']:>7.1f} | "
            f"${m['best_payout']:>9.2f}"
        )

    print("=" * 70)


def format_metrics_summary(metrics: Dict[str, Any]) -> str:
    """
    Format metrics as a compact summary string.

    Args:
        metrics: Dict from compute_portfolio_metrics

    Returns:
        Formatted summary string

    Example:
        >>> metrics = compute_portfolio_metrics(ranks, payouts, cashed, top_1_pct, 20.0)
        >>> summary = format_metrics_summary(metrics)
        >>> print(summary)
        ROI: 12.50%, Cash%: 25.00%, Win%: 2.50%, AvgRank: 450.2
    """
    summary = (
        f"ROI: {metrics['roi']:.2f}%, "
        f"Cash%: {metrics['cash_pct']:.2f}%, "
        f"Win%: {metrics['win_prob']:.2f}%, "
        f"AvgRank: {metrics['avg_rank']:.1f}"
    )

    return summary


def compare_lineups(
    metrics_list: List[Dict[str, Any]],
    metric: str = 'roi'
) -> List[Dict[str, Any]]:
    """
    Compare lineups by a specific metric and return sorted list.

    Args:
        metrics_list: List of dicts from compute_per_lineup_metrics
        metric: Metric to sort by ('roi', 'cash_pct', 'win_prob', 'avg_rank', 'best_payout')

    Returns:
        Sorted list of metrics dicts (best first)

    Example:
        >>> metrics = compute_per_lineup_metrics(ranks, payouts, cashed, top_1_pct, 20.0)
        >>> best_by_roi = compare_lineups(metrics, metric='roi')
        >>> print(f"Best lineup by ROI: {best_by_roi[0]['lineup_idx']}")
    """
    valid_metrics = {'roi', 'cash_pct', 'win_prob', 'avg_rank', 'best_payout'}

    if metric not in valid_metrics:
        raise ValueError(
            f"Invalid metric: {metric}. Must be one of: {valid_metrics}"
        )

    # Sort by metric (descending for most, ascending for avg_rank)
    reverse = metric != 'avg_rank'
    sorted_list = sorted(metrics_list, key=lambda x: x[metric], reverse=reverse)

    return sorted_list


def compute_sharpe_ratio(
    payouts: np.ndarray,
    buyin: float,
    risk_free_rate: float = 0.0
) -> Dict[str, float]:
    """
    Calculate Sharpe ratio for contest returns.

    Sharpe ratio measures risk-adjusted returns:
    (mean_return - risk_free_rate) / std_return

    Args:
        payouts: Array of payout amounts from simulations
        buyin: Contest buy-in amount
        risk_free_rate: Risk-free rate (as decimal, e.g., 0.02 for 2%)

    Returns:
        Dict with keys:
            - sharpe_ratio: Sharpe ratio
            - mean_return: Mean return (decimal)
            - std_return: Standard deviation of return (decimal)

    Example:
        >>> payouts = np.array([0, 0, 100, 0, 50, 200, 0, 0])
        >>> sharpe = compute_sharpe_ratio(payouts, buyin=20.0)
        >>> print(f"Sharpe ratio: {sharpe['sharpe_ratio']:.3f}")
    """
    if buyin <= 0:
        raise ValueError(f"buyin must be positive, got {buyin}")

    payouts_array = np.asarray(payouts, dtype=float)

    # Calculate returns
    returns = (payouts_array - buyin) / buyin

    # Compute statistics
    mean_return = float(returns.mean())
    std_return = float(returns.std())

    # Avoid division by zero
    if std_return == 0:
        sharpe_ratio = 0.0 if mean_return <= risk_free_rate else float('inf')
    else:
        sharpe_ratio = (mean_return - risk_free_rate) / std_return

    result = {
        'sharpe_ratio': sharpe_ratio,
        'mean_return': mean_return,
        'std_return': std_return
    }

    logger.debug(f"Sharpe ratio: {sharpe_ratio:.3f}")

    return result
