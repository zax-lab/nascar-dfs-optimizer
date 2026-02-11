"""
Exposure management for NASCAR DFS portfolio optimization.

This module implements exposure bookkeeping and constraints to prevent overexposure
to specific drivers or teams across a portfolio of lineups.

Exposure management is critical for portfolio risk control:
- Prevents >50% of lineups from containing the same driver
- Prevents >70% of lineups from over-indexing to the same team
- Tracks cumulative usage as lineups are generated iteratively
"""

import logging
from typing import Dict, List

from pulp import LpProblem, lpSum, LpVariable

logger = logging.getLogger(__name__)


def add_exposure_constraints(
    prob: LpProblem,
    x: Dict[int, LpVariable],
    exposure_book: Dict[int, int],
    n_lineups_generated: int,
    max_driver_exposure: float = 0.5,
    max_team_exposure: float = 0.7,
    driver_data: List[Dict] = None,
) -> None:
    """
    Add exposure constraints to prevent overexposure across portfolio.

    Exposure constraints are applied iteratively as lineups are generated:
    - If driver exposure >= max_driver_exposure, force exclusion from next lineup
    - If team exposure >= max_team_exposure, exclude all drivers from that team

    This approach ensures no driver or team dominates the portfolio, which is
    critical for tournament diversification and risk management.

    Args:
        prob: PuLP problem to add constraints to
        x: Dict mapping driver_id -> binary selection variable
        exposure_book: Dict mapping driver_id -> usage count so far
        n_lineups_generated: Number of lineups already generated
        max_driver_exposure: Max fraction of portfolios containing a driver (default 0.5 = 50%)
        max_team_exposure: Max fraction of portfolios from same team (default 0.7 = 70%)
        driver_data: Optional list of driver dicts with team key for team exposure

    Example:
        >>> from pulp import LpProblem, LpVariable, LpMaximize
        >>> prob = LpProblem("Test_Exposure", LpMaximize)
        >>> drivers = [
        ...     {"driver_id": i, "salary": 8000, "team": f"team_{i%3}"}
        ...     for i in range(10)
        ... ]
        >>> x = {d["driver_id"]: LpVariable(f"d_{i}", cat="Binary") for i in range(10)}
        >>> exposure_book = {0: 5, 1: 3}  # Driver 0 used 5 times, driver 1 used 3 times
        >>> add_exposure_constraints(
        ...     prob, x, exposure_book,
        ...     n_lineups_generated=10,
        ...     max_driver_exposure=0.5
        ... )
        >>> # Driver 0 will be excluded (5/10 = 50% exposure at limit)
    """
    if n_lineups_generated == 0:
        logger.debug("No lineups generated yet, skipping exposure constraints")
        return

    logger.debug(
        f"Adding exposure constraints: {len(exposure_book)} tracked drivers, "
        f"{n_lineups_generated} lineups generated"
    )

    # Driver-level exposure constraints
    excluded_drivers = []
    for driver_id, count in exposure_book.items():
        if driver_id not in x:
            continue

        current_exposure = count / n_lineups_generated

        if current_exposure >= max_driver_exposure:
            # Driver at max exposure, force exclusion
            prob += x[driver_id] == 0, f"Exclude_Overexposed_Driver_{driver_id}"
            excluded_drivers.append(driver_id)
            logger.debug(
                f"Excluding driver {driver_id}: "
                f"exposure {current_exposure:.1%} >= {max_driver_exposure:.1%}"
            )

    if excluded_drivers:
        logger.info(f"Excluded {len(excluded_drivers)} overexposed drivers")

    # Team-level exposure constraints (if driver_data provided)
    if driver_data:
        # Group drivers by team
        teams = {}
        for driver in driver_data:
            team = driver["team"]
            if team not in teams:
                teams[team] = []
            teams[team].append(driver["driver_id"])

        # Check team exposure
        excluded_teams = []
        for team, team_drivers in teams.items():
            team_usage = sum(exposure_book.get(did, 0) for did in team_drivers)
            current_exposure = team_usage / n_lineups_generated

            if current_exposure >= max_team_exposure:
                # Team at max exposure, exclude all drivers
                excluded_count = 0
                for driver_id in team_drivers:
                    if driver_id in x:
                        prob += (
                            x[driver_id] == 0,
                            f"Exclude_Overexposed_Team_{sanitize_team_name(team)}_{driver_id}"
                        )
                        excluded_count += 1

                excluded_teams.append((team, current_exposure, excluded_count))
                logger.debug(
                    f"Excluded {excluded_count} drivers from team '{team}': "
                    f"exposure {current_exposure:.1%} >= {max_team_exposure:.1%}"
                )

        if excluded_teams:
            logger.info(
                f"Excluded drivers from {len(excluded_teams)} overexposed teams: "
                f"{[t[0] for t in excluded_teams]}"
            )


def update_exposure_book(
    exposure_book: Dict[int, int],
    lineup: List[int]
) -> Dict[int, int]:
    """
    Update exposure book with new lineup.

    Increments usage count for each driver in the lineup. This is called
    after each lineup is generated to track cumulative exposure.

    Args:
        exposure_book: Current exposure counts (driver_id -> usage count)
        lineup: List of driver_ids in the new lineup

    Returns:
        Updated exposure book (new dict, does not modify input)

    Example:
        >>> book = {0: 5, 1: 3}
        >>> new_book = update_exposure_book(book, [0, 2, 4])
        >>> print(new_book)
        {0: 6, 1: 3, 2: 1, 4: 1}
    """
    new_book = exposure_book.copy()

    for driver_id in lineup:
        new_book[driver_id] = new_book.get(driver_id, 0) + 1

    logger.debug(
        f"Updated exposure book: {len(lineup)} drivers, "
        f"total tracked drivers: {len(new_book)}"
    )

    return new_book


def compute_exposure_metrics(
    exposure_book: Dict[int, int],
    n_lineups: int
) -> Dict[str, any]:
    """
    Compute exposure summary metrics for a portfolio.

    Provides statistics on driver exposure across the portfolio, useful for
    validation and reporting.

    Args:
        exposure_book: Dict mapping driver_id -> usage count
        n_lineups: Total number of lineups in portfolio

    Returns:
        Dict with keys:
            - max_exposure: Maximum driver exposure (fraction)
            - max_exposure_driver: Driver ID with max exposure
            - avg_exposure: Average exposure across tracked drivers
            - n_tracked_drivers: Number of drivers in exposure book
            - exposure_distribution: Dict of driver_id -> exposure fraction

    Example:
        >>> book = {0: 5, 1: 3, 2: 2}
        >>> metrics = compute_exposure_metrics(book, n_lineups=10)
        >>> print(f"Max exposure: {metrics['max_exposure']:.1%}")
        Max exposure: 50.0%
    """
    if n_lineups == 0:
        return {
            "max_exposure": 0.0,
            "max_exposure_driver": None,
            "avg_exposure": 0.0,
            "n_tracked_drivers": 0,
            "exposure_distribution": {},
        }

    if not exposure_book:
        return {
            "max_exposure": 0.0,
            "max_exposure_driver": None,
            "avg_exposure": 0.0,
            "n_tracked_drivers": 0,
            "exposure_distribution": {},
        }

    # Compute exposure fractions
    exposure_distribution = {
        driver_id: count / n_lineups
        for driver_id, count in exposure_book.items()
    }

    # Find max exposure
    max_exposure_driver = max(exposure_book, key=exposure_book.get)
    max_exposure = exposure_book[max_exposure_driver] / n_lineups

    # Compute average exposure
    avg_exposure = sum(exposure_book.values()) / (len(exposure_book) * n_lineups)

    metrics = {
        "max_exposure": max_exposure,
        "max_exposure_driver": max_exposure_driver,
        "avg_exposure": avg_exposure,
        "n_tracked_drivers": len(exposure_book),
        "exposure_distribution": exposure_distribution,
    }

    logger.debug(
        f"Exposure metrics: max={max_exposure:.1%} (driver {max_exposure_driver}), "
        f"avg={avg_exposure:.1%}, tracked={len(exposure_book)} drivers"
    )

    return metrics


def check_exposure_limits(
    exposure_book: Dict[int, int],
    n_lineups: int,
    max_driver_exposure: float = 0.5,
    max_team_exposure: float = 0.7,
    driver_data: List[Dict] = None
) -> Dict[str, any]:
    """
    Check if any drivers or teams exceed exposure limits.

    Validation function to check if the current exposure book violates any
    limits. Useful for post-hoc validation of a generated portfolio.

    Args:
        exposure_book: Dict mapping driver_id -> usage count
        n_lineups: Total number of lineups
        max_driver_exposure: Maximum allowed driver exposure
        max_team_exposure: Maximum allowed team exposure
        driver_data: Optional list of driver dicts with team key

    Returns:
        Dict with keys:
            - compliant (bool): True if all exposures within limits
            - violations (list): List of violation descriptions
            - overexposed_drivers (list): List of (driver_id, exposure) tuples
            - overexposed_teams (list): List of (team_name, exposure) tuples

    Example:
        >>> book = {0: 8, 1: 3, 2: 2}
        >>> check = check_exposure_limits(book, n_lineups=10, max_driver_exposure=0.5)
        >>> if not check["compliant"]:
        ...     print(f"Violations: {check['violations']}")
    """
    violations = []
    overexposed_drivers = []
    overexposed_teams = []

    if n_lineups == 0:
        return {
            "compliant": True,
            "violations": [],
            "overexposed_drivers": [],
            "overexposed_teams": [],
        }

    # Check driver-level exposure
    for driver_id, count in exposure_book.items():
        exposure = count / n_lineups
        if exposure > max_driver_exposure:
            violations.append(
                f"Driver {driver_id}: {exposure:.1%} exposure "
                f"exceeds limit {max_driver_exposure:.1%}"
            )
            overexposed_drivers.append((driver_id, exposure))

    # Check team-level exposure (if driver_data provided)
    if driver_data:
        # Group drivers by team
        teams = {}
        for driver in driver_data:
            team = driver["team"]
            if team not in teams:
                teams[team] = []
            teams[team].append(driver["driver_id"])

        # Check team exposure
        for team, team_drivers in teams.items():
            team_usage = sum(exposure_book.get(did, 0) for did in team_drivers)
            exposure = team_usage / n_lineups

            if exposure > max_team_exposure:
                violations.append(
                    f"Team '{team}': {exposure:.1%} exposure "
                    f"exceeds limit {max_team_exposure:.1%}"
                )
                overexposed_teams.append((team, exposure))

    compliant = len(violations) == 0

    if not compliant:
        logger.warning(
            f"Exposure limit violations detected: {len(violations)} violations, "
            f"{len(overexposed_drivers)} drivers, {len(overexposed_teams)} teams"
        )

    return {
        "compliant": compliant,
        "violations": violations,
        "overexposed_drivers": overexposed_drivers,
        "overexposed_teams": overexposed_teams,
    }


def sanitize_team_name(team_name: str) -> str:
    """
    Sanitize team name for use in PuLP constraint names.

    PuLP constraint names must be valid Python identifiers.
    """
    sanitized = "".join(c if c.isalnum() else "_" for c in team_name)
    while "__" in sanitized:
        sanitized = sanitized.replace("__", "_")
    return sanitized


if __name__ == "__main__":
    # Example usage and basic tests
    logging.basicConfig(level=logging.INFO)

    logger.info("Exposure management module loaded")

    # Example: Update exposure book
    book = {0: 5, 1: 3}
    new_book = update_exposure_book(book, [0, 2, 4])
    logger.info(f"Updated exposure book: {new_book}")

    # Example: Compute exposure metrics
    metrics = compute_exposure_metrics(new_book, n_lineups=10)
    logger.info(
        f"Exposure metrics: max={metrics['max_exposure']:.1%}, "
        f"avg={metrics['avg_exposure']:.1%}"
    )

    # Example: Check exposure limits
    check = check_exposure_limits(new_book, n_lineups=10, max_driver_exposure=0.5)
    logger.info(f"Exposure check: compliant={check['compliant']}")
