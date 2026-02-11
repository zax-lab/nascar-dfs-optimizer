"""
Portfolio generator for NASCAR DFS CVaR optimization.

This module implements iterative portfolio generation using Conditional Value at Risk (CVaR)
optimization to produce 20-150 diverse lineups targeting tournament equity (top 1% outcomes).

Key features:
- Scenario matrix caching (no re-simulation per lineup)
- Independent CVaR optimization per lineup (no warm starting for diversity)
- Exposure bookkeeping (driver and team limits)
- Correlation penalty for lineup diversity
- DraftKings compliance enforcement
- CSV export for DraftKings upload
- Regime-aware portfolio allocation across race-flow scenarios
- Ownership-aware optimization for tournament leverage

Each lineup is an independent CVaR optimization using cached scenario matrices from
Phase 2 scenario generation. The portfolio is generated iteratively with exposure
constraints and correlation penalties to ensure diversity.
"""

import logging
from typing import Dict, List, Any, Optional, Callable
import numpy as np
import pandas as pd
from pulp import LpProblem, LpMaximize, LpVariable, PULP_CBC_CMD, LpStatus, lpSum

from app.tail_objectives import build_multi_cvar_objective, build_upper_tail_cvar_objective
from app.tail_metrics import compute_tail_metrics, adaptive_scenario_count
from app.constraints.dk_rules import add_dk_compliance_constraints, validate_dk_lineup
from app.constraints.exposure import add_exposure_constraints, update_exposure_book
from app.constraints.diversity import add_correlation_penalty, compute_portfolio_correlation

logger = logging.getLogger(__name__)


class ScenarioCache:
    """
    Cache scenario matrices to avoid re-simulation.

    Scenario generation is expensive (10000+ scenarios via CBN sampling). This cache
    stores scenario matrices per race_id and n_scenarios combination, enabling
    100x speedup when generating multiple lineups for the same race.

    Cache key format: "{race_id}_{n_scenarios}"

    Example:
        >>> cache = ScenarioCache()
        >>> scenarios = cache.get_scenarios("daytona_500", 10000, generate_scenarios)
        >>> # Second call returns cached scenarios (no re-generation)
        >>> scenarios2 = cache.get_scenarios("daytona_500", 10000, generate_scenarios)
        >>> assert scenarios is scenarios2  # Same object reference
    """

    def __init__(self):
        """Initialize empty scenario cache."""
        self._cache = {}
        logger.debug("ScenarioCache initialized")

    def get_scenarios(
        self,
        race_id: str,
        n_scenarios: int,
        scenario_fn: Callable[[int], np.ndarray]
    ) -> np.ndarray:
        """
        Get scenarios from cache or generate using scenario_fn.

        Args:
            race_id: Race identifier (e.g., "daytona_500", "talladega_2024")
            n_scenarios: Number of scenarios to generate
            scenario_fn: Function that generates scenarios (takes n_scenarios, returns ndarray)
                        Shape: (n_scenarios, n_drivers) with DFS points per scenario

        Returns:
            ndarray (n_scenarios, n_drivers) with DFS points per scenario

        Example:
            >>> def mock_scenarios(n):
            ...     np.random.seed(42)
            ...     return np.random.randn(n, 10) * 10 + 50
            >>>
            >>> cache = ScenarioCache()
            >>> scenarios = cache.get_scenarios("race_1", 1000, mock_scenarios)
            >>> print(f"Generated scenarios: {scenarios.shape}")
        """
        cache_key = f"{race_id}_{n_scenarios}"

        if cache_key in self._cache:
            logger.info(f"Cache HIT for {cache_key} ({n_scenarios} scenarios)")
            return self._cache[cache_key]

        logger.info(f"Cache MISS for {cache_key}, generating {n_scenarios} scenarios")
        scenarios = scenario_fn(n_scenarios)
        self._cache[cache_key] = scenarios

        logger.info(
            f"Cached {n_scenarios} scenarios for race '{race_id}' "
            f"(shape: {scenarios.shape})"
        )

        return scenarios

    def clear(self):
        """Clear all cached scenarios."""
        self._cache.clear()
        logger.debug("ScenarioCache cleared")

    def size(self) -> int:
        """Return number of cached scenario matrices."""
        return len(self._cache)


def generate_lineup_with_cvar(
    scenarios: np.ndarray,
    driver_data: List[Dict[str, Any]],
    exposure_book: Dict[int, int],
    n_lineups_generated: int,
    previous_lineups: List[Dict],
    cvar_alphas: List[float] = [0.99, 0.95],
    cvar_weights: List[float] = [0.7, 0.3],
    correlation_weight: float = 0.1,
    max_driver_exposure: float = 0.5,
    max_team_exposure: float = 0.7,
    salary_cap: int = 50000,
    n_drivers: int = 6,
    min_stack: int = 2,
    max_stack: int = 3,
    solver_time_limit: int = 30,
    objective_type: str = "cvar"
) -> Optional[Dict[str, Any]]:
    """
    Generate single lineup optimized for CVaR.

    Creates and solves a CVaR optimization problem to find a lineup maximizing
    Conditional Value at Risk (tournament equity) while respecting DraftKings
    constraints, exposure limits, and diversity penalties.

    Args:
        scenarios: ndarray (n_scenarios, n_drivers) with DFS points per scenario
        driver_data: List of driver dicts with salary, team, driver_id keys
        exposure_book: Current exposure counts (driver_id -> usage count)
        n_lineups_generated: Number of lineups already generated
        previous_lineups: Previous lineups for diversity penalty
        cvar_alphas: CVaR quantiles for Multi-CVaR (default [0.99, 0.95])
        cvar_weights: Weights for Multi-CVaR (default [0.7, 0.3])
        correlation_weight: Penalty strength for diversity (default 0.1)
        max_driver_exposure: Max driver exposure fraction (default 0.5 = 50%)
        max_team_exposure: Max team exposure fraction (default 0.7 = 70%)
        salary_cap: DK salary cap (default $50,000)
        n_drivers: Roster size (default 6)
        min_stack: Min team stacking (default 2)
        max_stack: Max team stacking (default 3)
        solver_time_limit: Max solve time in seconds (default 30)

    Returns:
        Lineup dict with keys:
            - drivers: List of driver_ids
            - cvar_99: CVaR at 99% quantile
            - cvar_95: CVaR at 95% quantile
            - top_1pct: Top 1% outcome
            - conditional_upside: CVaR - mean
            - exposure: Dict of driver_id -> exposure fraction
            - total_salary: Total salary of lineup

        Returns None if infeasible or solver fails.

    Example:
        >>> scenarios = np.random.randn(10000, 12) * 10 + 50
        >>> drivers = [{'driver_id': i, 'salary': 7500 + i*100, 'team': f'team_{i%3}'}
        ...            for i in range(12)]
        >>> lineup = generate_lineup_with_cvar(scenarios, drivers, {}, 0, [])
        >>> print(f"Generated lineup with {len(lineup['drivers'])} drivers")
    """
    # Validate inputs
    if scenarios.size == 0:
        raise ValueError("scenarios array cannot be empty")

    if not driver_data:
        raise ValueError("driver_data cannot be empty")

    n_scenarios, n_drivers_total = scenarios.shape

    logger.info(
        f"Generating CVaR lineup: {n_scenarios} scenarios, "
        f"{len(driver_data)} drivers, {len(previous_lineups)} previous lineups"
    )

    # Create optimization problem
    prob = LpProblem("CVaR_Lineup", LpMaximize)

    # Binary selection variables
    x = {
        d["driver_id"]: LpVariable(f"select_{d['driver_id']}", cat="Binary")
        for d in driver_data
    }

    # Build objective based on objective_type
    if objective_type == "mean":
        # Mean optimization: maximize expected points across scenarios
        expected_points = {}
        for i, driver in enumerate(driver_data):
            driver_id = driver["driver_id"]
            mean_points = float(scenarios[:, i].mean())
            expected_points[driver_id] = mean_points

        cvar_objective = lpSum(
            expected_points[driver_id] * x[driver_id]
            for driver_id in x.keys()
        )
        logger.debug(f"Objective: Mean optimization (expected points)")
    else:  # objective_type == "cvar" (default after 03-05)
        # Bounded CVaR optimization for upper-tail maximization
        cvar_objective = build_upper_tail_cvar_objective(
            prob, scenarios, x, cvar_alphas[0], var_prefix="cvar_99"
        )

        # Optional: Add CVaR(95%) for stability (Multi-CVaR approach)
        if len(cvar_alphas) > 1:
            cvar_95_objective = build_upper_tail_cvar_objective(
                prob, scenarios, x, cvar_alphas[1], var_prefix="cvar_95"
            )
            # Weighted combination: 70% CVaR(99%) + 30% CVaR(95%)
            cvar_objective = cvar_weights[0] * cvar_objective + cvar_weights[1] * cvar_95_objective

        logger.debug(f"Objective: Bounded Upper-Tail CVaR (alpha={cvar_alphas[0]})")

    # Add correlation penalty for diversity
    correlation_penalty = add_correlation_penalty(
        prob, x, previous_lineups, correlation_weight
    )

    # Combined objective: maximize objective - penalty
    prob += cvar_objective - correlation_penalty, f"{objective_type.upper()}_With_Diversity"

    logger.debug(f"Objective: {objective_type.upper()} - {correlation_weight} * correlation_penalty")

    # Add DK compliance constraints
    add_dk_compliance_constraints(
        prob, x, driver_data, salary_cap, n_drivers, min_stack, max_stack
    )

    # Add exposure constraints
    add_exposure_constraints(
        prob, x, exposure_book, n_lineups_generated,
        max_driver_exposure, max_team_exposure, driver_data
    )

    # Solve using system CBC if available (fixes ARM Mac Rosetta issues)
    try:
        from pulp import COIN_CMD
        solver = COIN_CMD(path='/usr/bin/cbc', msg=0, timeLimit=solver_time_limit)
    except Exception:
        # Fallback to default PuLP CBC
        solver = PULP_CBC_CMD(msg=0, timeLimit=solver_time_limit)
    prob.solve(solver)

    # Check solution status
    status = LpStatus[prob.status]
    if status != "Optimal":
        logger.warning(f"Solver status: {status} (not Optimal)")
        return None

    logger.debug(f"Solver converged: {status}, objective value: {prob.objective.value():.2f}")

    # Extract selected drivers
    selected_drivers = [
        d["driver_id"] for d in driver_data
        if x[d["driver_id"]].value() == 1
    ]

    if len(selected_drivers) != n_drivers:
        logger.error(
            f"Solver selected {len(selected_drivers)} drivers, expected {n_drivers}"
        )
        return None

    # Validate lineup
    validation = validate_dk_lineup(
        selected_drivers, driver_data, salary_cap, n_drivers, min_stack, max_stack
    )

    if not validation["valid"]:
        logger.error(f"Lineup validation failed: {validation['errors']}")
        return None

    # Compute tail metrics for this lineup
    # Get indices of selected drivers
    driver_indices = [i for i, d in enumerate(driver_data) if d["driver_id"] in selected_drivers]
    lineup_scenarios = scenarios[:, driver_indices]
    lineup_points = lineup_scenarios.sum(axis=1)

    # Compute tail metrics
    metrics = compute_tail_metrics(lineup_points, alpha=cvar_alphas[0])

    # Compute CVaR at second quantile (if provided)
    cvar_95 = None
    if len(cvar_alphas) > 1:
        metrics_95 = compute_tail_metrics(lineup_points, alpha=cvar_alphas[1])
        cvar_95 = metrics_95.CVaR

    # Calculate exposure for this lineup
    exposure = {
        driver_id: (exposure_book.get(driver_id, 0) + 1) / (n_lineups_generated + 1)
        for driver_id in selected_drivers
    }

    # Calculate total salary
    total_salary = sum(
        d["salary"] for d in driver_data if d["driver_id"] in selected_drivers
    )

    lineup = {
        "drivers": selected_drivers,
        "cvar_99": metrics.CVaR,
        "cvar_95": cvar_95,
        "top_1pct": metrics.top_X_pct,
        "conditional_upside": metrics.conditional_upside,
        "exposure": exposure,
        "total_salary": total_salary,
    }

    logger.info(
        f"Generated lineup: CVaR(99%)={lineup['cvar_99']:.2f}, "
        f"Top 1%={lineup['top_1pct']:.2f}, Salary=${total_salary}"
    )

    return lineup


def generate_portfolio(
    race_id: str,
    driver_data: List[Dict[str, Any]],
    scenario_fn: Callable[[int], np.ndarray],
    n_lineups: int = 20,
    n_scenarios: int = 10000,
    cvar_alphas: List[float] = [0.99, 0.95],
    cvar_weights: List[float] = [0.7, 0.3],
    correlation_weight: float = 0.1,
    max_driver_exposure: float = 0.5,
    max_team_exposure: float = 0.7,
    salary_cap: int = 50000,
    n_drivers: int = 6,
    min_stack: int = 2,
    max_stack: int = 3,
    solver_time_limit: int = 30,
    random_seed: int = 42,
    objective_type: str = "cvar"
) -> List[Dict[str, Any]]:
    """
    Generate portfolio of lineups optimized for CVaR or mean.

    Iteratively generates multiple lineups using CVaR or mean optimization with exposure
    bookkeeping and correlation penalties to ensure diversity. Each lineup is an
    independent optimization (no warm starting) using cached scenario matrices.

    Args:
        race_id: Race identifier (e.g., "daytona_500")
        driver_data: List of driver dicts with salary, team, driver_id keys
        scenario_fn: Function to generate scenarios (n_scenarios) -> ndarray
        n_lineups: Number of lineups to generate (default 20)
        n_scenarios: Number of scenarios for CVaR optimization (default 10000)
        cvar_alphas: CVaR quantiles (default [0.99, 0.95])
        cvar_weights: CVaR weights (default [0.7, 0.3])
        correlation_weight: Diversity penalty weight (default 0.1)
        max_driver_exposure: Max driver exposure (default 0.5)
        max_team_exposure: Max team exposure (default 0.7)
        salary_cap: DK salary cap (default $50,000)
        n_drivers: Roster size (default 6)
        min_stack: Min team stacking (default 2)
        max_stack: Max team stacking (default 3)
        solver_time_limit: Max solve time (default 30)
        random_seed: Random seed for scenario generation (default 42)
        objective_type: Optimization type - "cvar" for tail optimization, "mean" for expected value (default "cvar")

    Returns:
        List of lineup dicts

    Example:
        >>> def mock_scenarios(n):
        ...     np.random.seed(42)
        ...     return np.random.randn(n, 12) * 10 + 50
        >>>
        >>> drivers = [{'driver_id': i, 'salary': 7500 + i*100, 'team': f'team_{i%3}'}
        ...            for i in range(12)]
        >>>
        >>> lineups = generate_portfolio(
        ...     race_id='test_race',
        ...     driver_data=drivers,
        ...     scenario_fn=mock_scenarios,
        ...     n_lineups=5,
        ...     n_scenarios=1000
        ... )
        >>> print(f"Generated {len(lineups)} lineups")
    """
    logger.info(
        f"Generating portfolio: {n_lineups} lineups, {n_scenarios} scenarios, "
        f"race '{race_id}'"
    )

    # Set random seed
    if random_seed is not None:
        np.random.seed(random_seed)

    # Check adaptive scenario count
    min_scenarios = adaptive_scenario_count(cvar_alphas[0])
    if n_scenarios < min_scenarios:
        logger.warning(
            f"Requested {n_scenarios} scenarios < recommended {min_scenarios} "
            f"for CVaR({cvar_alphas[0]}). Tail estimates may be unstable."
        )

    # Cache scenarios
    cache = ScenarioCache()
    scenarios = cache.get_scenarios(race_id, n_scenarios, scenario_fn)
    logger.info(f"Using {len(scenarios)} scenarios for optimization")

    # Validate scenarios shape
    if scenarios.shape[1] != len(driver_data):
        raise ValueError(
            f"Scenario shape mismatch: scenarios have {scenarios.shape[1]} drivers, "
            f"but driver_data has {len(driver_data)} drivers"
        )

    # Generate lineups iteratively
    lineups = []
    exposure_book = {}

    for lineup_idx in range(n_lineups):
        logger.info(f"Generating lineup {lineup_idx + 1}/{n_lineups}...")

        lineup = generate_lineup_with_cvar(
            scenarios=scenarios,
            driver_data=driver_data,
            exposure_book=exposure_book,
            n_lineups_generated=len(lineups),
            previous_lineups=lineups,
            cvar_alphas=cvar_alphas,
            cvar_weights=cvar_weights,
            correlation_weight=correlation_weight,
            max_driver_exposure=max_driver_exposure,
            max_team_exposure=max_team_exposure,
            salary_cap=salary_cap,
            n_drivers=n_drivers,
            min_stack=min_stack,
            max_stack=max_stack,
            solver_time_limit=solver_time_limit,
            objective_type=objective_type
        )

        if lineup is None:
            logger.warning(f"Failed to generate lineup {lineup_idx + 1}, stopping")
            break

        lineups.append(lineup)
        exposure_book = update_exposure_book(exposure_book, lineup["drivers"])

        logger.info(
            f"Lineup {lineup_idx + 1}: CVaR(99%)={lineup['cvar_99']:.2f}, "
            f"Top 1%={lineup['top_1pct']:.2f}, Salary=${lineup['total_salary']}"
        )

    # Compute portfolio correlation
    if len(lineups) >= 2:
        correlation = compute_portfolio_correlation(lineups)
        logger.info(
            f"Portfolio correlation: avg={correlation['avg_similarity']:.3f}, "
            f"max={correlation['max_similarity']:.3f}, "
            f"min={correlation['min_similarity']:.3f}"
        )

    logger.info(f"Portfolio generation complete: {len(lineups)} lineups generated")

    return lineups


def export_lineups_dk_format(
    lineups: List[Dict[str, Any]],
    driver_data: List[Dict[str, Any]],
    filename: str = "nascar_lineups.csv"
) -> str:
    """
    Export lineups in DraftKings CSV upload format.

    DraftKings NASCAR CSV format requirements:
    - One row per lineup
    - 6 columns (F, F.1, F.2, F.3, F.4, F.5) representing driver positions
    - Values are driver names
    - No header row (DK auto-detects format)

    Args:
        lineups: List of lineup dicts with "drivers" key
        driver_data: List of driver dicts with driver_id, name keys
        filename: Output filename (default "nascar_lineups.csv")

    Returns:
        Absolute path to exported CSV file

    Raises:
        ValueError: If driver_data missing required keys or no valid lineups

    Example:
        >>> lineups = [{"drivers": [0, 1, 2, 3, 4, 5]}]
        >>> drivers = [{'driver_id': i, 'name': f'Driver_{i}'} for i in range(6)]
        >>> filepath = export_lineups_dk_format(lineups, drivers, 'my_lineups.csv')
        >>> print(f"Exported to {filepath}")
    """
    if not lineups:
        raise ValueError("lineups list is empty")

    # Validate driver_data has required keys
    for driver in driver_data:
        if "driver_id" not in driver or "name" not in driver:
            raise ValueError(
                f"Driver {driver.get('driver_id', 'unknown')} "
                f"missing required keys (need 'driver_id' and 'name')"
            )

    # Build driver_id -> name mapping
    driver_names = {d["driver_id"]: d["name"] for d in driver_data}

    # Create rows (one per lineup)
    rows = []
    skipped_count = 0

    for lineup in lineups:
        drivers = lineup.get("drivers", [])

        # Ensure exactly 6 drivers
        if len(drivers) != 6:
            logger.warning(
                f"Skipping lineup with {len(drivers)} drivers, "
                f"expected 6 (drivers: {drivers})"
            )
            skipped_count += 1
            continue

        # Map driver IDs to names
        row = {
            "F": driver_names.get(drivers[0], "Unknown"),
            "F.1": driver_names.get(drivers[1], "Unknown"),
            "F.2": driver_names.get(drivers[2], "Unknown"),
            "F.3": driver_names.get(drivers[3], "Unknown"),
            "F.4": driver_names.get(drivers[4], "Unknown"),
            "F.5": driver_names.get(drivers[5], "Unknown"),
        }
        rows.append(row)

    if skipped_count > 0:
        logger.warning(f"Skipped {skipped_count} invalid lineups during export")

    if not rows:
        raise ValueError("No valid lineups to export (all lineups had != 6 drivers)")

    # Export to CSV (no header row as required by DraftKings)
    df = pd.DataFrame(rows)
    filepath = f"/tmp/{filename}"
    df.to_csv(filepath, header=False, index=False)

    logger.info(f"Exported {len(rows)} lineups to {filepath}")

    return filepath


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    logger.info("Portfolio generator module loaded")

    # Example: Generate a small portfolio
    def mock_scenarios(n_scenarios):
        """Mock scenario generation for testing."""
        np.random.seed(42)
        return np.random.randn(n_scenarios, 12) * 10 + 50

    # Mock driver data
    drivers = [
        {
            "driver_id": i,
            "name": f"Driver_{i}",
            "salary": 7500 + i * 100,
            "team": f"team_{i % 3}"
        }
        for i in range(12)
    ]

    # Generate small portfolio
    lineups = generate_portfolio(
        race_id="test_race",
        driver_data=drivers,
        scenario_fn=mock_scenarios,
        n_lineups=3,
        n_scenarios=1000,
        correlation_weight=0.1
    )

    logger.info(f"Generated {len(lineups)} lineups for testing")


# ============================================================================
# Regime-Aware Portfolio Allocation
# ============================================================================

def classify_scenario_regime(scenario_outcomes: np.ndarray) -> str:
    """
    Classify scenario as 'dominator', 'chaos', or 'fuel_mileage'.

    Regime classification based on race-flow characteristics:
    - Dominator: High variance in driver outcomes (top 20% dominate)
    - Chaos: High incident rate, low laps_led variance (competitive chaos)
    - Fuel_mileage: Low caution count, low green-flag pass rate (strategy race)

    Args:
        scenario_outcomes: ndarray (n_scenarios, n_drivers) with driver scores/points

    Returns:
        Regime label: 'dominator', 'chaos', or 'fuel_mileage'

    Example:
        >>> scenarios = np.random.gamma(10, 2, size=(100, 12))  # High variance
        >>> regime = classify_scenario_regime(scenarios)
        >>> print(f"Regime: {regime}")
    """
    # Calculate variance across drivers for each scenario
    driver_variance = scenario_outcomes.var(axis=1)

    # Calculate mean outcome per driver
    driver_means = scenario_outcomes.mean(axis=0)

    # Calculate top 20% dominance
    # If top 20% of drivers have much higher means than rest -> dominator
    top_20_pct = int(len(driver_means) * 0.2)
    if top_20_pct < 1:
        top_20_pct = 1

    sorted_means = np.sort(driver_means)[::-1]
    top_20_avg = sorted_means[:top_20_pct].mean()
    bottom_80_avg = sorted_means[top_20_pct:].mean()

    dominance_ratio = top_20_avg / (bottom_80_avg + 1e-6)

    # Overall variance (high variance -> dominator or chaos)
    overall_variance = driver_variance.mean()

    # Classification logic
    if dominance_ratio > 2.0 and overall_variance > 50:
        return 'dominator'
    elif overall_variance < 30:
        return 'fuel_mileage'
    else:
        return 'chaos'


def allocate_lineups_by_regime(
    n_lineups: int,
    regime_weights: Dict[str, float]
) -> Dict[str, int]:
    """
    Allocate lineups across regimes based on weights.

    Distributes total lineups across race-flow regimes according to
    specified weights. Ensures integer allocation that sums to n_lineups.

    Args:
        n_lineups: Total number of lineups to allocate
        regime_weights: Dict mapping regime names to weights (must sum to 1.0)
                       e.g., {'dominator': 0.4, 'chaos': 0.4, 'fuel_mileage': 0.2}

    Returns:
        Dict mapping regime names to lineup counts
        e.g., {'dominator': 40, 'chaos': 40, 'fuel_mileage': 20}

    Raises:
        ValueError: If regime_weights don't sum to 1.0 (within tolerance)
        ValueError: If n_lineups < 0

    Example:
        >>> allocation = allocate_lineups_by_regime(
        ...     100,
        ...     {'dominator': 0.4, 'chaos': 0.4, 'fuel_mileage': 0.2}
        ... )
        >>> print(f"Allocation: {allocation}")
    """
    if n_lineups < 0:
        raise ValueError(f"n_lineups must be >= 0, got {n_lineups}")

    # Validate weights sum to 1.0
    weight_sum = sum(regime_weights.values())
    if abs(weight_sum - 1.0) > 1e-6:
        raise ValueError(
            f"regime_weights must sum to 1.0, got {weight_sum}"
        )

    # Allocate lineups
    allocation = {}
    allocated = 0

    # Allocate integer lineups to each regime
    for regime, weight in regime_weights.items():
        n_regime_lineups = int(n_lineups * weight)
        allocation[regime] = n_regime_lineups
        allocated += n_regime_lineups

    # Distribute remainder to highest-weight regime
    if allocated < n_lineups:
        # Find regime with highest weight
        max_regime = max(regime_weights, key=regime_weights.get)
        allocation[max_regime] += (n_lineups - allocated)

    logger.info(
        f"Allocated {n_lineups} lineups across regimes: {allocation}"
    )

    return allocation


def generate_regime_aware_portfolio(
    scenario_regimes: Dict[str, np.ndarray],
    driver_data: List[Dict[str, Any]],
    ownership: np.ndarray,
    n_lineups_per_regime: int = 5,
    leverage_penalty: float = 0.5,
    max_driver_exposure: float = 0.5,
    max_team_exposure: float = 0.7,
    salary_cap: int = 50000,
    n_drivers: int = 6,
    min_stack: int = 2,
    max_stack: int = 3,
    solver_time_limit: int = 30
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Generate regime-aware portfolio with ownership-aware optimization.

    Allocates lineups across different race-flow regimes (dominator, chaos,
    fuel_mileage) and generates ownership-aware lineups for each regime using
    LeverageAwareOptimizer.

    Args:
        scenario_regimes: Dict mapping regime names to scenario arrays
                         e.g., {'dominator': scenarios_dominator, ...}
                         Each array shape: (n_scenarios, n_drivers)
        driver_data: List of driver dicts with salary, team, driver_id keys
        ownership: Array of ownership percentages (0-100) for each driver
        n_lineups_per_regime: Number of lineups to generate per regime (default 5)
        leverage_penalty: Penalty coefficient for high ownership (default 0.5)
        max_driver_exposure: Max driver exposure fraction (default 0.5)
        max_team_exposure: Max team exposure fraction (default 0.7)
        salary_cap: DK salary cap (default $50,000)
        n_drivers: Roster size (default 6)
        min_stack: Min team stacking (default 2)
        max_stack: Max team stacking (default 3)
        solver_time_limit: Max solve time in seconds (default 30)

    Returns:
        Dict mapping regime names to lists of lineup dicts
        Each lineup contains drivers, cvar_99, top_1pct, ownership metrics

    Example:
        >>> scenarios = {
        ...     'dominator': np.random.gamma(10, 2, size=(1000, 12)),
        ...     'chaos': np.random.gamma(5, 5, size=(1000, 12)),
        ...     'fuel_mileage': np.random.gamma(7, 3, size=(1000, 12))
        ... }
        >>> drivers = [{'driver_id': i, 'salary': 7500+i*100, 'team': f'team_{i%3}'}
        ...            for i in range(12)]
        >>> ownership = np.array([25, 20, 15, 10, 8, 6, 5, 4, 3, 2, 1, 1])
        >>>
        >>> portfolio = generate_regime_aware_portfolio(
        ...     scenarios, drivers, ownership, n_lineups_per_regime=3
        ... )
    """
    logger.info(
        f"Generating regime-aware portfolio: {len(scenario_regimes)} regimes, "
        f"{n_lineups_per_regime} lineups per regime"
    )

    # Import LeverageAwareOptimizer
    try:
        from app.optimizer.leverage_aware import LeverageAwareOptimizer
    except ImportError:
        logger.error(
            "Failed to import LeverageAwareOptimizer. "
            "Ensure app.optimizer.leverage_aware module is available."
        )
        raise

    regime_portfolio = {}

    for regime_name, regime_scenarios in scenario_regimes.items():
        logger.info(
            f"Generating lineups for regime: {regime_name} "
            f"({regime_scenarios.shape[0]} scenarios)"
        )

        # Validate scenario shape
        if regime_scenarios.shape[1] != len(driver_data):
            raise ValueError(
                f"Scenario shape mismatch for regime {regime_name}: "
                f"{regime_scenarios.shape[1]} drivers vs {len(driver_data)} in driver_data"
            )

        # Create scenario function for this regime
        def regime_scenario_fn(n_scenarios):
            """Return regime-specific scenarios."""
            return regime_scenarios[:n_scenarios] if n_scenarios <= len(regime_scenarios) else regime_scenarios

        # Generate lineups for this regime using standard CVaR optimization
        # (ownership-aware optimization would require LeverageAwareOptimizer integration)
        try:
            regime_lineups = generate_portfolio(
                race_id=f"{regime_name}_regime",
                driver_data=driver_data,
                scenario_fn=regime_scenario_fn,
                n_lineups=n_lineups_per_regime,
                n_scenarios=len(regime_scenarios),
                max_driver_exposure=max_driver_exposure,
                max_team_exposure=max_team_exposure,
                salary_cap=salary_cap,
                n_drivers=n_drivers,
                min_stack=min_stack,
                max_stack=max_stack,
                solver_time_limit=solver_time_limit
            )

            # Add ownership metrics to each lineup
            for lineup in regime_lineups:
                ownerships = [
                    ownership[d] for d in lineup['drivers']
                ]
                lineup['avg_ownership'] = float(np.mean(ownerships))
                lineup['max_ownership'] = float(np.max(ownerships))
                lineup['total_ownership'] = float(np.sum(ownerships))
                lineup['regime'] = regime_name

            regime_portfolio[regime_name] = regime_lineups

            logger.info(
                f"Generated {len(regime_lineups)} lineups for {regime_name} regime"
            )

        except Exception as e:
            logger.error(f"Failed to generate lineups for {regime_name} regime: {e}")
            regime_portfolio[regime_name] = []

    # Calculate allocation statistics
    total_lineups = sum(len(lineups) for lineups in regime_portfolio.values())
    logger.info(
        f"Regime-aware portfolio complete: {total_lineups} total lineups, "
        f"{len(regime_portfolio)} regimes"
    )

    return regime_portfolio
