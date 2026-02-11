"""
Portfolio diversity constraints for NASCAR DFS optimization.

This module implements correlation-based diversity constraints to ensure generated
lineups are sufficiently different from each other. Diversity is critical for
tournament portfolios to maximize coverage of different race outcomes.

Key concepts:
- Jaccard similarity: Measures lineup overlap (intersection / union)
- Correlation penalty: Soft penalty for selecting drivers from previous lineups
- Portfolio correlation: Aggregate similarity metrics across all lineups
"""

import logging
from typing import Dict, List, Any

import numpy as np
from pulp import LpProblem, lpSum, LpVariable

logger = logging.getLogger(__name__)


def add_correlation_penalty(
    prob: LpProblem,
    x: Dict[int, LpVariable],
    previous_lineups: List[Dict],
    correlation_weight: float = 0.1,
) -> float:
    """
    Add correlation penalty to encourage lineup diversity.

    Applies a soft penalty that reduces the objective value when selecting drivers
    that frequently appear in previous lineups. This encourages the optimizer to
    explore different driver combinations for diversity.

    The penalty is: correlation_weight * sum(overlap with each previous lineup)

    This is a soft constraint (penalty) rather than a hard constraint, allowing
    the optimizer to trade off diversity vs. CVaR optimization.

    Args:
        prob: PuLP problem to add penalty to
        x: Dict mapping driver_id -> binary selection variable
        previous_lineups: List of previous lineup dicts with "drivers" key
        correlation_weight: Penalty strength (default 0.1 = 10% penalty per overlap)

    Returns:
        Correlation penalty expression (to subtract from objective)

    Example:
        >>> from pulp import LpProblem, LpVariable, LpMaximize
        >>> prob = LpProblem("Test_Diversity", LpMaximize)
        >>> drivers = [i for i in range(10)]
        >>> x = {i: LpVariable(f"d_{i}", cat="Binary") for i in drivers}
        >>> previous = [{"drivers": [0, 1, 2, 3, 4, 5]}]
        >>> penalty = add_correlation_penalty(prob, x, previous, correlation_weight=0.1)
        >>> # Objective should be: cvar_objective - penalty
    """
    if not previous_lineups:
        logger.debug("No previous lineups, no correlation penalty")
        return 0.0

    penalty = 0

    for prev_lineup in previous_lineups:
        # Get drivers from previous lineup
        prev_drivers = prev_lineup.get("drivers", [])

        if not prev_drivers:
            continue

        # Count overlap with previous lineup
        overlap = lpSum(
            x[driver_id]
            for driver_id in prev_drivers
            if driver_id in x
        )

        penalty += overlap

    total_penalty = correlation_weight * penalty

    logger.debug(
        f"Correlation penalty: {len(previous_lineups)} previous lineups, "
        f"weight={correlation_weight}, penalty_value={total_penalty}"
    )

    return total_penalty


def compute_pairwise_similarity(
    lineup1: List[int],
    lineup2: List[int]
) -> float:
    """
    Compute Jaccard similarity between two lineups.

    Jaccard similarity measures the overlap between two sets:
        Jaccard(A, B) = |A ∩ B| / |A ∪ B|

    Values range from 0 (no overlap) to 1 (identical lineups).

    Args:
        lineup1: List of driver_ids in first lineup
        lineup2: List of driver_ids in second lineup

    Returns:
        Jaccard similarity (float between 0 and 1)

    Example:
        >>> sim = compute_pairwise_similarity([0, 1, 2, 3, 4, 5], [0, 1, 2, 6, 7, 8])
        >>> print(f"Similarity: {sim:.3f}")
        Similarity: 0.333
    """
    set1 = set(lineup1)
    set2 = set(lineup2)

    intersection = len(set1 & set2)
    union = len(set1 | set2)

    if union == 0:
        return 0.0

    similarity = intersection / union

    logger.debug(
        f"Pairwise similarity: intersection={intersection}, "
        f"union={union}, similarity={similarity:.3f}"
    )

    return similarity


def compute_portfolio_correlation(
    lineups: List[Dict[str, Any]]
) -> Dict[str, any]:
    """
    Compute pairwise correlation metrics for a portfolio.

    Calculates aggregate similarity metrics across all pairs of lineups in the
    portfolio. Higher correlations indicate less diversity (more similar lineups).

    Metrics computed:
    - avg_similarity: Mean Jaccard similarity across all pairs
    - max_similarity: Maximum Jaccard similarity (most similar pair)
    - min_similarity: Minimum Jaccard similarity (most diverse pair)
    - most_similar_pair: Indices of the most similar pair
    - n_pairs: Total number of pairwise comparisons

    Args:
        lineups: List of lineup dicts with "drivers" key

    Returns:
        Dict with correlation metrics

    Example:
        >>> lineups = [
        ...     {"drivers": [0, 1, 2, 3, 4, 5]},
        ...     {"drivers": [0, 1, 2, 6, 7, 8]},
        ...     {"drivers": [3, 4, 5, 6, 7, 8]},
        ... ]
        >>> corr = compute_portfolio_correlation(lineups)
        >>> print(f"Avg similarity: {corr['avg_similarity']:.3f}")
        Avg similarity: 0.333
    """
    n = len(lineups)

    if n < 2:
        logger.debug("Less than 2 lineups, no correlation to compute")
        return {
            "avg_similarity": 0.0,
            "max_similarity": 0.0,
            "min_similarity": 0.0,
            "most_similar_pair": None,
            "least_similar_pair": None,
            "n_pairs": 0,
        }

    similarities = []
    most_similar = (0.0, None, None)  # (similarity, lineup_i, lineup_j)
    least_similar = (1.0, None, None)  # (similarity, lineup_i, lineup_j)

    # Compute pairwise similarities
    for i in range(n):
        for j in range(i + 1, n):
            sim = compute_pairwise_similarity(
                lineups[i]["drivers"],
                lineups[j]["drivers"]
            )
            similarities.append(sim)

            # Track most similar pair
            if sim > most_similar[0]:
                most_similar = (sim, i, j)

            # Track least similar pair
            if sim < least_similar[0]:
                least_similar = (sim, i, j)

    # Compute aggregate metrics
    avg_similarity = float(np.mean(similarities))
    max_similarity = float(np.max(similarities))
    min_similarity = float(np.min(similarities))

    logger.info(
        f"Portfolio correlation: n={n}, pairs={len(similarities)}, "
        f"avg={avg_similarity:.3f}, max={max_similarity:.3f}, min={min_similarity:.3f}"
    )

    return {
        "avg_similarity": avg_similarity,
        "max_similarity": max_similarity,
        "min_similarity": min_similarity,
        "most_similar_pair": most_similar[1:],
        "least_similar_pair": least_similar[1:],
        "n_pairs": len(similarities),
    }


def compute_similarity_matrix(
    lineups: List[Dict[str, Any]]
) -> np.ndarray:
    """
    Compute full similarity matrix for a portfolio.

    Creates an n x n matrix where element [i, j] is the Jaccard similarity
    between lineup i and lineup j. The diagonal is 1.0 (identical).

    Useful for visualization and clustering analysis.

    Args:
        lineups: List of lineup dicts with "drivers" key

    Returns:
        n x n numpy array of similarities

    Example:
        >>> lineups = [
        ...     {"drivers": [0, 1, 2, 3, 4, 5]},
        ...     {"drivers": [0, 1, 2, 6, 7, 8]},
        ... ]
        >>> matrix = compute_similarity_matrix(lineups)
        >>> print(matrix)
        [[1.   0.333]
         [0.333 1.  ]]
    """
    n = len(lineups)

    if n == 0:
        return np.array([])

    # Initialize matrix with zeros
    matrix = np.zeros((n, n))

    # Fill diagonal with 1.0 (identical)
    np.fill_diagonal(matrix, 1.0)

    # Compute pairwise similarities
    for i in range(n):
        for j in range(i + 1, n):
            sim = compute_pairwise_similarity(
                lineups[i]["drivers"],
                lineups[j]["drivers"]
            )
            matrix[i, j] = sim
            matrix[j, i] = sim  # Symmetric

    logger.debug(f"Computed similarity matrix: {n}x{n}")

    return matrix


def find_most_diverse_subset(
    lineups: List[Dict[str, Any]],
    n_select: int
) -> List[int]:
    """
    Find the most diverse subset of lineups using greedy selection.

    Iteratively selects the lineup that minimizes average similarity to the
    already-selected lineups. This is useful for reducing a large portfolio
    to a smaller, more diverse set.

    Args:
        lineups: List of lineup dicts with "drivers" key
        n_select: Number of lineups to select

    Returns:
        List of indices of the most diverse lineups

    Example:
        >>> lineups = [{"drivers": [...]}, ...]  # 20 lineups
        >>> diverse_indices = find_most_diverse_subset(lineups, n_select=5)
        >>> print(f"Most diverse lineups: {diverse_indices}")
    """
    if n_select >= len(lineups):
        return list(range(len(lineups)))

    if n_select <= 0:
        return []

    # Start with a random lineup
    import random
    selected = [random.randint(0, len(lineups) - 1)]
    remaining = set(range(len(lineups))) - set(selected)

    # Greedy selection
    for _ in range(n_select - 1):
        if not remaining:
            break

        # Find the lineup that minimizes avg similarity to selected
        best_idx = None
        best_avg_sim = float('inf')

        for idx in remaining:
            # Compute avg similarity to all selected lineups
            sims = [
                compute_pairwise_similarity(
                    lineups[idx]["drivers"],
                    lineups[sel_idx]["drivers"]
                )
                for sel_idx in selected
            ]
            avg_sim = np.mean(sims)

            if avg_sim < best_avg_sim:
                best_avg_sim = avg_sim
                best_idx = idx

        if best_idx is not None:
            selected.append(best_idx)
            remaining.remove(best_idx)

    logger.info(
        f"Selected {len(selected)} most diverse lineups from {len(lineups)} "
        f"(avg similarity: {best_avg_sim:.3f})"
    )

    return selected


if __name__ == "__main__":
    # Example usage and basic tests
    logging.basicConfig(level=logging.INFO)

    logger.info("Diversity constraints module loaded")

    # Example: Compute pairwise similarity
    sim = compute_pairwise_similarity([0, 1, 2, 3, 4, 5], [0, 1, 2, 6, 7, 8])
    logger.info(f"Jaccard similarity: {sim:.3f}")

    # Example: Compute portfolio correlation
    lineups = [
        {"drivers": [0, 1, 2, 3, 4, 5]},
        {"drivers": [0, 1, 2, 6, 7, 8]},
        {"drivers": [3, 4, 5, 6, 7, 8]},
    ]
    corr = compute_portfolio_correlation(lineups)
    logger.info(
        f"Portfolio correlation: avg={corr['avg_similarity']:.3f}, "
        f"max={corr['max_similarity']:.3f}"
    )

    # Example: Similarity matrix
    matrix = compute_similarity_matrix(lineups)
    logger.info(f"Similarity matrix:\n{matrix}")
