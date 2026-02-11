"""
DraftKings NASCAR DFS compliance constraints.

This module implements DraftKings NASCAR Classic rule constraints for portfolio optimization:
- Roster size: Exactly 6 drivers
- Salary cap: $50,000 total
- Team stacking: 2-3 drivers per team (min_stack to max_stack)

These constraints are applied to each lineup in the portfolio to ensure DraftKings compliance.
"""

import logging
from typing import Dict, List, Any

from pulp import LpProblem, lpSum, LpVariable

logger = logging.getLogger(__name__)


def add_dk_compliance_constraints(
    prob: LpProblem,
    x: Dict[int, LpVariable],
    driver_data: List[Dict[str, Any]],
    salary_cap: int = 50000,
    n_drivers: int = 6,
    min_stack: int = 2,
    max_stack: int = 3,
) -> None:
    """
    Add DraftKings NASCAR Classic constraints to optimization problem.

    Enforces three key DraftKings rules:
    1. Select exactly n_drivers (6) drivers
    2. Total salary must not exceed salary_cap ($50,000)
    3. Team stacking: min_stack (2) to max_stack (3) drivers per team

    Note: The min_stack constraint is enforced via exposure bookkeeping in
    portfolio generation, not as a hard constraint here. This allows the
    optimizer flexibility during lineup generation while ensuring final
    lineups meet the minimum stacking requirement.

    Args:
        prob: PuLP problem to add constraints to
        x: Dict mapping driver_id -> binary selection variable
        driver_data: List of driver dicts with salary, team keys
        salary_cap: Maximum total salary (default $50,000)
        n_drivers: Number of drivers to select (default 6)
        min_stack: Minimum drivers from same team (default 2)
        max_stack: Maximum drivers from same team (default 3)

    Raises:
        ValueError: If driver_data is empty or required keys are missing

    Example:
        >>> from pulp import LpProblem, LpVariable, LpMaximize
        >>> prob = LpProblem("Test_DK", LpMaximize)
        >>> drivers = [
        ...     {"driver_id": 1, "salary": 8000, "team": "Hendrick"},
        ...     {"driver_id": 2, "salary": 7500, "team": "Joe Gibbs"},
        ... ]
        >>> x = {d["driver_id"]: LpVariable(f"d_{d['driver_id']}", cat="Binary")
        ...      for d in drivers}
        >>> add_dk_compliance_constraints(prob, x, drivers)
        >>> print(f"Added {len(prob.constraints)} constraints")
    """
    if not driver_data:
        raise ValueError("driver_data cannot be empty")

    # Validate driver_data has required keys
    required_keys = {"driver_id", "salary", "team"}
    for driver in driver_data:
        missing_keys = required_keys - driver.keys()
        if missing_keys:
            raise ValueError(
                f"Driver {driver.get('driver_id', 'unknown')} "
                f"missing keys: {missing_keys}"
            )

    logger.debug(
        f"Adding DK compliance constraints: "
        f"{len(driver_data)} drivers, salary_cap=${salary_cap}, "
        f"n_drivers={n_drivers}, stacking={min_stack}-{max_stack}"
    )

    # Constraint 1: Roster size - select exactly n_drivers
    prob += lpSum(x.values()) == n_drivers, "Select_Exactly_N_Drivers"
    logger.debug(f"Added roster size constraint: select exactly {n_drivers} drivers")

    # Constraint 2: Salary cap - total salary <= salary_cap
    prob += (
        lpSum(d["salary"] * x[d["driver_id"]] for d in driver_data) <= salary_cap,
        f"Salary_Cap_{salary_cap}",
    )
    logger.debug(f"Added salary cap constraint: total salary <= ${salary_cap}")

    # Constraint 3: Team stacking - max_stack per team
    # Group drivers by team
    teams = {}
    for driver in driver_data:
        team = driver["team"]
        if team not in teams:
            teams[team] = []
        teams[team].append(driver)

    # Add stacking constraints for each team with enough drivers
    for team, team_drivers in teams.items():
        if len(team_drivers) >= min_stack:
            # Only apply stacking constraints if team has enough drivers
            team_selection = lpSum(
                x[d["driver_id"]] for d in team_drivers
            )

            # Max constraint: at most max_stack drivers from this team
            prob += (
                team_selection <= max_stack,
                f"Max_{max_stack}_From_Team_{sanitize_constraint_name(team)}",
            )

            # Min constraint: if any driver from this team is selected,
            # select at least min_stack drivers from this team
            # This is a semi-continuous constraint: team_selection = 0 or team_selection >= min_stack
            # We model this as: team_selection >= min_stack * y_team, where y_team is binary
            # and team_selection <= max_stack * y_team (implicitly enforced by max_stack)
            # For simplicity, we use: team_selection >= min_stack * (1 if any selected else 0)
            # Implemented as: team_selection >= min_stack * indicator
            # where indicator = 1 if any driver from team is selected

            # Create auxiliary binary variable for team selection
            y_team = LpVariable(f"select_team_{sanitize_constraint_name(team)}", cat="Binary")

            # If y_team = 1, then team_selection >= min_stack
            # If y_team = 0, then team_selection = 0 (no drivers from this team)
            # Link y_team to team_selection:
            # team_selection >= min_stack * y_team (if team selected, need at least min_stack)
            # team_selection <= max_stack * y_team (if team not selected, cannot select drivers)
            # But the second constraint is already implied by team_selection <= max_stack

            # However, we need to link y_team to individual driver selections:
            # y_team >= x[i] for all drivers i in team (if any driver selected, y_team = 1)
            for driver in team_drivers:
                prob += (
                    y_team >= x[driver["driver_id"]],
                    f"Link_Team_Indicator_{sanitize_constraint_name(team)}_{driver['driver_id']}"
                )

            # If y_team = 1, need at least min_stack drivers
            prob += (
                team_selection >= min_stack * y_team,
                f"Min_{min_stack}_From_Team_{sanitize_constraint_name(team)}_If_Selected"
            )

            logger.debug(
                f"Added team stacking constraints: "
                f"min {min_stack}, max {max_stack} from team '{team}' "
                f"({len(team_drivers)} drivers available)"
            )


def validate_dk_lineup(
    lineup: List[int],
    driver_data: List[Dict[str, Any]],
    salary_cap: int = 50000,
    n_drivers: int = 6,
    min_stack: int = 2,
    max_stack: int = 3,
) -> Dict[str, Any]:
    """
    Validate lineup against DraftKings NASCAR Classic rules.

    Performs comprehensive validation of a lineup to ensure it meets all
    DraftKings requirements. Returns detailed error information for debugging.

    Validation checks:
    1. Roster size: Exactly n_drivers (6)
    2. Salary cap: Total salary <= salary_cap ($50,000)
    3. Team stacking: min_stack (2) to max_stack (3) drivers per team
    4. No duplicate drivers in lineup

    Args:
        lineup: List of driver_ids in the lineup
        driver_data: List of driver dicts with salary, team keys
        salary_cap: Maximum total salary (default $50,000)
        n_drivers: Required roster size (default 6)
        min_stack: Minimum drivers from same team (default 2)
        max_stack: Maximum drivers from same team (default 3)

    Returns:
        Dict with keys:
            - valid (bool): True if lineup passes all checks
            - errors (list[str]): List of error messages (empty if valid)

    Example:
        >>> drivers = [
        ...     {"driver_id": 1, "salary": 8000, "team": "Hendrick"},
        ...     {"driver_id": 2, "salary": 7500, "team": "Joe Gibbs"},
        ... ]
        >>> validation = validate_dk_lineup([1, 2, 3, 4, 5, 6], drivers)
        >>> if validation["valid"]:
        ...     print("Lineup is valid")
        >>> else:
        ...     print(f"Errors: {validation['errors']}")
    """
    errors = []

    # Build lookup dicts for validation
    driver_lookup = {d["driver_id"]: d for d in driver_data}

    # Check 1: Roster size
    if len(lineup) != n_drivers:
        errors.append(
            f"Roster size violation: {len(lineup)} drivers, "
            f"expected exactly {n_drivers}"
        )

    # Check 2: No duplicates
    if len(set(lineup)) != len(lineup):
        duplicates = [d for d in lineup if lineup.count(d) > 1]
        errors.append(f"Duplicate drivers in lineup: {set(duplicates)}")

    # Check 3: All driver_ids exist in driver_data
    missing_drivers = [d for d in lineup if d not in driver_lookup]
    if missing_drivers:
        errors.append(f"Unknown driver_ids in lineup: {missing_drivers}")

    # Check 4: Salary cap (only if lineup has valid drivers)
    if lineup and all(d in driver_lookup for d in lineup):
        total_salary = sum(driver_lookup[d]["salary"] for d in lineup)
        if total_salary > salary_cap:
            errors.append(
                f"Salary cap violation: ${total_salary:,}, "
                f"maximum allowed ${salary_cap:,}"
            )

    # Check 5: Team stacking (only if lineup has valid drivers)
    if lineup and all(d in driver_lookup for d in lineup):
        team_counts = {}
        for driver_id in lineup:
            team = driver_lookup[driver_id]["team"]
            team_counts[team] = team_counts.get(team, 0) + 1

        for team, count in team_counts.items():
            if count < min_stack:
                errors.append(
                    f"Team stacking violation: '{team}' has {count} driver(s), "
                    f"minimum required {min_stack}"
                )
            if count > max_stack:
                errors.append(
                    f"Team stacking violation: '{team}' has {count} driver(s), "
                    f"maximum allowed {max_stack}"
                )

    valid = len(errors) == 0

    if not valid:
        logger.warning(f"Lineup validation failed with {len(errors)} errors: {errors}")
    else:
        logger.debug("Lineup validation passed")

    return {"valid": valid, "errors": errors}


def sanitize_constraint_name(team_name: str) -> str:
    """
    Sanitize team name for use in PuLP constraint names.

    PuLP constraint names must be valid Python identifiers (alphanumeric and underscores).
    This function replaces spaces and special characters with underscores.

    Args:
        team_name: Raw team name (e.g., "Joe Gibbs Racing")

    Returns:
        Sanitized team name (e.g., "Joe_Gibbs_Racing")
    """
    # Replace spaces and special chars with underscores
    sanitized = "".join(c if c.isalnum() else "_" for c in team_name)
    # Collapse multiple underscores
    while "__" in sanitized:
        sanitized = sanitized.replace("__", "_")
    return sanitized


def compute_lineup_salary(
    lineup: List[int],
    driver_data: List[Dict[str, Any]]
) -> int:
    """
    Compute total salary for a lineup.

    Helper function to calculate the total salary of a lineup for validation
    or display purposes.

    Args:
        lineup: List of driver_ids
        driver_data: List of driver dicts with salary key

    Returns:
        Total salary (int)

    Raises:
        ValueError: If any driver_id is not found in driver_data
    """
    driver_lookup = {d["driver_id"]: d for d in driver_data}

    try:
        total_salary = sum(driver_lookup[driver_id]["salary"] for driver_id in lineup)
    except KeyError as e:
        raise ValueError(f"Driver ID {e.args[0]} not found in driver_data")

    return total_salary


def compute_team_distribution(
    lineup: List[int],
    driver_data: List[Dict[str, Any]]
) -> Dict[str, int]:
    """
    Compute team distribution for a lineup.

    Helper function to count how many drivers from each team are in the lineup.
    Useful for validation and debugging.

    Args:
        lineup: List of driver_ids
        driver_data: List of driver dicts with team key

    Returns:
        Dict mapping team name -> driver count

    Raises:
        ValueError: If any driver_id is not found in driver_data
    """
    driver_lookup = {d["driver_id"]: d for d in driver_data}

    team_counts = {}
    for driver_id in lineup:
        try:
            team = driver_lookup[driver_id]["team"]
        except KeyError:
            raise ValueError(f"Driver ID {driver_id} not found in driver_data")

        team_counts[team] = team_counts.get(team, 0) + 1

    return team_counts


if __name__ == "__main__":
    # Example usage and basic tests
    logging.basicConfig(level=logging.INFO)

    logger.info("DraftKings rules module loaded")

    # Example: Add constraints to a problem
    from pulp import LpProblem, LpVariable, LpMaximize

    # Mock driver data
    drivers = [
        {"driver_id": i, "salary": 7500 + i * 100, "team": f"team_{i % 3}"}
        for i in range(10)
    ]

    # Create problem
    prob = LpProblem("Example_DK", LpMaximize)
    x = {d["driver_id"]: LpVariable(f"d_{d['driver_id']}", cat="Binary") for d in drivers}

    # Add constraints
    add_dk_compliance_constraints(prob, x, drivers)
    logger.info(f"Added {len(prob.constraints)} DK compliance constraints")

    # Example: Validate a lineup
    test_lineup = [0, 1, 2, 3, 4, 5]
    validation = validate_dk_lineup(test_lineup, drivers)
    logger.info(f"Lineup validation: valid={validation['valid']}")
    if not validation["valid"]:
        logger.error(f"Validation errors: {validation['errors']}")
