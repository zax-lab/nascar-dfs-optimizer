"""
CVaR Objective Builders for MILP Optimization

This module implements Conditional Value at Risk (CVaR) objective builders using
the Rockafellar-Uryasev formulation for mixed-integer linear programming (MILP).
CVaR optimization enables direct targeting of top-tail outcomes (tournament equity)
rather than mean points for NASCAR DFS portfolio optimization.

Rockafellar-Uryasev Formulation:
    CVaR_α(X) = max_ζ { ζ + (1/[(1-α)S]) Σ_{k=1}^S max(0, points_k - ζ) }

Where:
    - ζ (zeta): Value at Risk threshold (VaR)
    - u_k: Auxiliary variables for tail slack (max(0, points_k - ζ))
    - α (alpha): Tail quantile (e.g., 0.99 for top 1%)
    - S: Number of scenarios
    - points_k: Portfolio points in scenario k

This formulation linearizes the conditional expectation calculation, making CVaR
optimization tractable for MILP solvers like PuLP + CBC.

References:
    - Rockafellar & Uryasev (2000): "Optimization of Conditional Value-at-Risk"
    - 03-RESEARCH.md: Pattern 1 - Rockafellar-Uryasev CVaR MILP Formulation
"""

import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass

import numpy as np
from pulp import LpProblem, LpVariable, lpSum, LpAffineExpression

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class CVaRVariables:
    """
    Container for CVaR auxiliary variables from Rockafellar-Uryasev formulation.

    Attributes:
        zeta: Value at Risk threshold variable (continuous, unbounded)
        u: Dict mapping scenario index k -> tail slack variable u_k
        alpha: Tail quantile used (e.g., 0.99 for top 1%)
        n_scenarios: Number of scenarios
    """
    zeta: LpVariable
    u: Dict[int, LpVariable]
    alpha: float
    n_scenarios: int


def build_cvar_objective(
    prob: LpProblem,
    scenarios: np.ndarray,
    x: Dict[int, LpVariable],
    alpha: float = 0.99,
    var_prefix: str = ""
) -> LpAffineExpression:
    """
    Build CVaR objective using Rockafellar-Uryasev formulation for MAXIMIZATION.

    For maximizing the upper tail (tournament upside), we use the upper CVaR:
    CVaR_α = max_ζ { ζ + (1/[(1-α)S]) Σ_{k=1}^S max(0, points_k - ζ) }

    Where:
    - ζ (zeta): Value at Risk threshold (VaR) for the upper tail
    - u_k: Auxiliary variables for tail upside (max(0, points_k - ζ))
    - α (alpha): Upper tail quantile (e.g., 0.99 for top 1%)
    - S: Number of scenarios
    - points_k: Portfolio points in scenario k

    This formulation linearizes the conditional expectation calculation, making CVaR
    optimization tractable for MILP solvers like PuLP + CBC.

    Args:
        prob: PuLP problem to add variables/constraints to
        scenarios: ndarray (n_scenarios, n_drivers) with DFS points per scenario
        x: Dict mapping driver_id -> binary selection variable
        alpha: Upper tail quantile (e.g., 0.99 for top 1%, 0.95 for top 5%)
        var_prefix: Prefix for variable names (useful for Multi-CVaR to avoid conflicts)

    Returns:
        PuLP expression for CVaR objective (to be maximized)

    Raises:
        ValueError: If scenarios is empty or alpha is not in (0, 1)

    Example:
        >>> prob = LpProblem("CVaR_Portfolio", LpMaximize)
        >>> scenarios = np.random.randn(100, 5)  # 100 scenarios, 5 drivers
        >>> x = {i: LpVariable(f"driver_{i}", cat="Binary") for i in range(5)}
        >>> cvar_expr = build_cvar_objective(prob, scenarios, x, alpha=0.99)
        >>> prob += cvar_expr, "CVaR_Objective"
        >>> prob.solve()
    """
    # Validate inputs
    if scenarios.size == 0:
        raise ValueError("scenarios array cannot be empty")

    if not (0 < alpha < 1):
        raise ValueError(f"alpha must be in (0, 1), got {alpha}")

    # Extract dimensions
    n_scenarios, n_drivers = scenarios.shape

    logger.info(
        f"Building CVaR({alpha*100:.0f}%) objective: "
        f"{n_scenarios} scenarios, {n_drivers} drivers"
    )

    # Create CVaR auxiliary variables
    # zeta: Value at Risk threshold (continuous, bounded by scenario range)
    # Calculate bounds for zeta based on min/max scenario points
    min_scenario = float(scenarios.min())
    max_scenario = float(scenarios.max())
    min_possible_points = min_scenario * n_drivers  # Lower bound (all drivers min)
    max_possible_points = max_scenario * n_drivers  # Upper bound (all drivers max)

    zeta_name = f"{var_prefix}zeta" if var_prefix else "zeta"
    zeta = LpVariable(
        zeta_name,
        lowBound=min_possible_points,
        upBound=max_possible_points,
        cat="Continuous"
    )

    # u_k: Tail slack variables (non-negative)
    # u_k >= scenario_points_k - zeta
    u = {}
    for k in range(n_scenarios):
        u_name = f"{var_prefix}tail_slack_{k}" if var_prefix else f"tail_slack_{k}"
        u[k] = LpVariable(u_name, lowBound=0, cat="Continuous")

    # Compute portfolio points per scenario
    # scenario_points[k] = sum_i scenarios[k, i] * x[i]
    scenario_points = {}
    for k in range(n_scenarios):
        scenario_points[k] = lpSum(
            scenarios[k, i] * x[i] for i in range(n_drivers)
        )

    # Add CVaR constraints: u_k >= scenario_points_k - zeta, u_k >= 0
    # The u_k >= 0 constraint is enforced by lowBound=0 in LpVariable
    for k in range(n_scenarios):
        constraint_name = (
            f"{var_prefix}Tail_Slack_{k}" if var_prefix else f"Tail_Slack_{k}"
        )
        prob += u[k] >= scenario_points[k] - zeta, constraint_name

    # Build and return CVaR objective expression
    # CVaR = zeta + (1 / [(1-alpha) * S]) * sum(u_k)
    denominator = (1 - alpha) * n_scenarios
    cvar_expr = zeta + lpSum(u[k] for k in range(n_scenarios)) / denominator

    logger.debug(
        f"CVaR objective created: {n_scenarios} tail slack variables, "
        f"denominator={denominator:.2f}"
    )

    return cvar_expr


def add_cvar_constraints(
    prob: LpProblem,
    scenarios: np.ndarray,
    x: Dict[int, LpVariable],
    alpha: float = 0.99,
    var_prefix: str = ""
) -> Tuple[LpVariable, Dict[int, LpVariable], LpAffineExpression]:
    """
    Add CVaR constraints to problem and return variables (alternative API).

    This function provides the same core logic as build_cvar_objective() but
    returns the variables explicitly, allowing manual combination of multiple
    CVaR objectives for Multi-CVaR optimization.

    Args:
        prob: PuLP problem to add variables/constraints to
        scenarios: ndarray (n_scenarios, n_drivers) with DFS points per scenario
        x: Dict mapping driver_id -> binary selection variable
        alpha: Tail quantile (e.g., 0.99 for top 1%)
        var_prefix: Prefix for variable names (useful for Multi-CVaR)

    Returns:
        Tuple of (zeta, u, cvar_expr):
            - zeta: Value at Risk variable
            - u: Dict mapping scenario index -> tail slack variable
            - cvar_expr: PuLP expression for CVaR objective

    Example:
        >>> prob = LpProblem("Multi_CVaR", LpMaximize)
        >>> scenarios = np.random.randn(100, 5)
        >>> x = {i: LpVariable(f"driver_{i}", cat="Binary") for i in range(5)}
        >>> zeta_99, u_99, cvar_99 = add_cvar_constraints(prob, scenarios, x, 0.99, "cvar99_")
        >>> zeta_95, u_95, cvar_95 = add_cvar_constraints(prob, scenarios, x, 0.95, "cvar95_")
        >>> prob += 0.7 * cvar_99 + 0.3 * cvar_95, "Multi_CVaR_Objective"
    """
    # Validate inputs
    if scenarios.size == 0:
        raise ValueError("scenarios array cannot be empty")

    if not (0 < alpha < 1):
        raise ValueError(f"alpha must be in (0, 1), got {alpha}")

    # Extract dimensions
    n_scenarios, n_drivers = scenarios.shape

    # Create CVaR auxiliary variables
    # Calculate bounds for zeta based on min/max scenario values
    min_scenario = float(scenarios.min())
    max_scenario = float(scenarios.max())
    min_possible_points = min_scenario * n_drivers  # Lower bound
    max_possible_points = max_scenario * n_drivers  # Upper bound

    zeta_name = f"{var_prefix}zeta" if var_prefix else "zeta"
    zeta = LpVariable(
        zeta_name,
        lowBound=min_possible_points,
        upBound=max_possible_points,
        cat="Continuous"
    )

    u = {}
    for k in range(n_scenarios):
        u_name = f"{var_prefix}tail_slack_{k}" if var_prefix else f"tail_slack_{k}"
        u[k] = LpVariable(u_name, lowBound=0, cat="Continuous")

    # Compute portfolio points per scenario
    scenario_points = {}
    for k in range(n_scenarios):
        scenario_points[k] = lpSum(
            scenarios[k, i] * x[i] for i in range(n_drivers)
        )

    # Add CVaR constraints
    for k in range(n_scenarios):
        constraint_name = (
            f"{var_prefix}Tail_Slack_{k}" if var_prefix else f"Tail_Slack_{k}"
        )
        prob += u[k] >= scenario_points[k] - zeta, constraint_name

    # Build CVaR objective expression
    denominator = (1 - alpha) * n_scenarios
    cvar_expr = zeta + lpSum(u[k] for k in range(n_scenarios)) / denominator

    return zeta, u, cvar_expr


def build_multi_cvar_objective(
    prob: LpProblem,
    scenarios: np.ndarray,
    x: Dict[int, LpVariable],
    alphas: List[float] = [0.99, 0.95],
    weights: List[float] = [0.7, 0.3]
) -> LpAffineExpression:
    """
    Build Multi-CVaR objective for stability.

    Combines CVaR at multiple quantiles to stabilize estimation while preserving
    tail focus. Multi-CVaR addresses the instability of single-quantile CVaR
    optimization when scenario counts are limited.

    Typical weights: 70% CVaR(99%) + 30% CVaR(95%)
    - Literature recommends 60-80% weight on extreme quantile
    - Higher weight on moderate quantile (95%) improves stability
    - Higher weight on extreme quantile (99%) preserves tail focus

    Args:
        prob: PuLP problem to add variables/constraints to
        scenarios: ndarray (n_scenarios, n_drivers) with DFS points
        x: Dict mapping driver_id -> binary selection variable
        alphas: List of tail quantiles (e.g., [0.99, 0.95])
        weights: List of weights for each quantile (must sum to 1.0)

    Returns:
        PuLP expression for weighted Multi-CVaR objective

    Raises:
        ValueError: If len(alphas) != len(weights) or weights don't sum to 1.0

    Example:
        >>> prob = LpProblem("Multi_CVaR_Portfolio", LpMaximize)
        >>> scenarios = np.random.randn(100, 5)
        >>> x = {i: LpVariable(f"driver_{i}", cat="Binary") for i in range(5)}
        >>> multi_cvar = build_multi_cvar_objective(
        ...     prob, scenarios, x,
        ...     alphas=[0.99, 0.95],
        ...     weights=[0.7, 0.3]
        ... )
        >>> prob += multi_cvar, "Multi_CVaR_Objective"
    """
    # Validate inputs
    if len(alphas) != len(weights):
        raise ValueError(
            f"len(alphas)={len(alphas)} must equal len(weights)={len(weights)}"
        )

    total_weight = sum(weights)
    if not (0.99 <= total_weight <= 1.01):  # Allow small floating point errors
        raise ValueError(
            f"weights must sum to 1.0, got {total_weight:.4f}"
        )

    if scenarios.size == 0:
        raise ValueError("scenarios array cannot be empty")

    n_scenarios, n_drivers = scenarios.shape

    logger.info(
        f"Building Multi-CVaR objective: {len(alphas)} quantiles, "
        f"weights={weights}, alphas={alphas}"
    )

    # Build CVaR objective for each quantile
    cvar_exprs = []
    for i, alpha in enumerate(alphas):
        # Use unique variable names for each quantile
        var_prefix = f"cvar_{int(alpha*100)}_"

        # Build CVaR objective for this quantile
        cvar_expr = build_cvar_objective(
            prob, scenarios, x, alpha=alpha, var_prefix=var_prefix
        )
        cvar_exprs.append(cvar_expr)

    # Combine objectives with weights
    multi_cvar = lpSum(
        weights[i] * cvar_exprs[i]
        for i in range(len(alphas))
    )

    logger.debug(
        f"Multi-CVaR objective created: "
        f"{'+'.join(f'{w:.2f}*CVaR({a*100:.0f}%)' for w, a in zip(weights, alphas))}"
    )

    return multi_cvar


def compute_scenario_points(
    scenarios: np.ndarray,
    driver_selection: List[int]
) -> np.ndarray:
    """
    Compute portfolio points per scenario for a given driver selection.

    Helper function to calculate scenario points after optimization, useful for
    post-hoc validation and analysis.

    Args:
        scenarios: ndarray (n_scenarios, n_drivers) with DFS points per scenario
        driver_selection: List of selected driver indices

    Returns:
        ndarray (n_scenarios,) with portfolio points per scenario

    Example:
        >>> scenarios = np.random.randn(100, 5)
        >>> selected = [0, 2, 4]  # Selected drivers 0, 2, 4
        >>> points = compute_scenario_points(scenarios, selected)
        >>> print(f"Mean points: {points.mean():.2f}")
        >>> print(f"CVaR(99%): {compute_cvar(points, 0.99):.2f}")
    """
    if scenarios.size == 0:
        raise ValueError("scenarios array cannot be empty")

    if not driver_selection:
        raise ValueError("driver_selection cannot be empty")

    # Sum driver points for each scenario
    # points[k] = sum_i scenarios[k, driver_selection[i]]
    scenario_points = scenarios[:, driver_selection].sum(axis=1)

    return scenario_points


# Import compute_cvar from tail_metrics for post-hoc validation
# This will be implemented in Phase 3 Plan 01
def compute_cvar(scenario_points: np.ndarray, alpha: float = 0.99) -> float:
    """
    Compute CVaR from scenario points (post-hoc validation).

    This is a simple implementation for post-hoc validation. For the full
    tail metrics module with adaptive scenario counts and stability validation,
    see tail_metrics.py (Phase 3 Plan 01).

    Args:
        scenario_points: ndarray (n_scenarios,) with portfolio points per scenario
        alpha: Tail quantile (e.g., 0.99 for top 1%)

    Returns:
        CVaR value (float)
    """
    if scenario_points.size == 0:
        raise ValueError("scenario_points array cannot be empty")

    if not (0 < alpha < 1):
        raise ValueError(f"alpha must be in (0, 1), got {alpha}")

    n_scenarios = len(scenario_points)
    # For top 1% (alpha=0.99), we want the top 1% of scenarios
    # k = ceil((1 - alpha) * n_scenarios) to ensure we get at least 1 scenario
    k = max(1, int(np.ceil((1 - alpha) * n_scenarios)))

    # Use np.partition for O(n) performance
    # Get top k scenarios (largest values)
    top_k_points = np.partition(scenario_points, -k)[-k:]
    cvar = top_k_points.mean()

    return cvar


def build_upper_tail_cvar_objective(
    prob: LpProblem,
    scenarios: np.ndarray,
    x: Dict[int, LpVariable],
    alpha: float = 0.99,
    var_prefix: str = "cvar"
) -> LpAffineExpression:
    """
    Build CVaR objective for upper-tail maximization (tournament upside).

    Reformulates Rockafellar-Uryasev for bounded maximization:
    - Bounds zeta variable to prevent unbounded optimization
    - Maximizes expected value of top (1-alpha) scenarios

    The standard Rockafellar-Uryasev CVaR formulation is designed for risk
    minimization (downside tail), where zeta can be unbounded below. When
    maximizing CVaR for upside tournament outcomes, the unbounded zeta variable
    causes optimization to fail with "Unbounded" status. This formulation adds
    explicit bounds to zeta based on the min/max possible portfolio points.

    Args:
        prob: PuLP problem instance
        scenarios: (n_scenarios, n_drivers) matrix of driver points per scenario
        x: Dict mapping driver_id to binary selection variables
        alpha: Tail quantile (e.g., 0.99 for top 1%)
        var_prefix: Prefix for variable names

    Returns:
        LpAffineExpression for CVaR objective (maximize this)

    Raises:
        ValueError: If scenarios is empty or alpha is not in (0, 1)

    Example:
        >>> prob = LpProblem("Upper_Tail_CVaR", LpMaximize)
        >>> scenarios = np.random.randn(1000, 10) * 10 + 100
        >>> x = {i: LpVariable(f"d{i}", cat="Binary") for i in range(10)}
        >>> obj = build_upper_tail_cvar_objective(prob, scenarios, x, alpha=0.99)
        >>> prob += obj
        >>> prob.solve()
    """
    # Validate inputs
    if scenarios.size == 0:
        raise ValueError("scenarios array cannot be empty")

    if not (0 < alpha < 1):
        raise ValueError(f"alpha must be in (0, 1), got {alpha}")

    n_scenarios, n_drivers = scenarios.shape

    logger.info(
        f"Building upper-tail CVaR({alpha*100:.0f}%) objective: "
        f"{n_scenarios} scenarios, {n_drivers} drivers"
    )

    # Bounded zeta: upper-tail CVaR cannot exceed max possible points
    # Max points: best lineup with all drivers at max scenario points
    max_driver_points = float(scenarios.max())
    max_lineup_points = max_driver_points * n_drivers
    min_lineup_points = float(scenarios.min())

    # Calculate maximum possible excess (for u_k upper bounds)
    # u_k represents excess over threshold, max excess is max_lineup_points - min_lineup_points
    max_excess = max_lineup_points - min_lineup_points

    # Zeta bounded between min and max possible lineup points
    # This prevents unbounded optimization when maximizing CVaR
    zeta = LpVariable(
        f"{var_prefix}_zeta",
        lowBound=min_lineup_points,
        upBound=max_lineup_points,
        cat="Continuous"
    )

    logger.debug(
        f"Created bounded zeta variable: [{min_lineup_points:.2f}, {max_lineup_points:.2f}]"
    )

    # Tail slack variables with upper bounds to prevent unbounded growth
    # For maximization, u_k needs both lower AND upper bounds
    u = {
        k: LpVariable(
            f"{var_prefix}_u_{k}",
            lowBound=0,
            upBound=max_excess,
            cat="Continuous"
        )
        for k in range(n_scenarios)
    }

    # Portfolio points per scenario
    scenario_points = {}
    for k in range(n_scenarios):
        scenario_points[k] = lpSum(
            scenarios[k, i] * x[driver_id]
            for i, driver_id in enumerate(x.keys())
        )

    # CVaR constraints for upper-tail: u_k >= scenario_points_k - zeta
    # This formulation captures upside tail scenarios (points above threshold)
    # The upper bound on u_k prevents unbounded optimization
    for k in range(n_scenarios):
        prob += u[k] >= scenario_points[k] - zeta, f"{var_prefix}_tail_slack_{k}"

    # CVaR objective: zeta + mean(tail_slack) for top (1-alpha) scenarios
    # For upper-tail maximization, we use the standard Rockafellar-Uryasev formula
    # with bounded zeta to prevent unbounded optimization
    denominator = (1 - alpha) * n_scenarios
    cvar_objective = zeta + lpSum(u[k] for k in range(n_scenarios)) / denominator

    logger.debug(
        f"Upper-tail CVaR objective created: {n_scenarios} tail slack variables, "
        f"denominator={denominator:.2f}"
    )

    return cvar_objective


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    logger.info("CVaR Objectives module loaded")

    # Example: Build CVaR objective
    from pulp import LpProblem, LpMaximize, LpVariable

    prob = LpProblem("Example_CVaR", LpMaximize)
    np.random.seed(42)
    scenarios = np.random.randn(100, 5)  # 100 scenarios, 5 drivers
    x = {i: LpVariable(f"driver_{i}", cat="Binary") for i in range(5)}

    cvar_expr = build_cvar_objective(prob, scenarios, x, alpha=0.99)
    prob += cvar_expr, "CVaR_Objective"

    logger.info(f"Created CVaR objective with {len(prob.variables())} variables")
    logger.info(f"Added {len(prob.constraints)} constraints")
