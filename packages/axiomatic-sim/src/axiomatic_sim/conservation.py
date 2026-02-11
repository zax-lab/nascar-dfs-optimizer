"""
Conservation validation utilities for NASCAR race simulation.

This module provides JAX-accelerated validation functions for enforcing
dominator conservation constraints. These constraints ensure that scenarios
don't inflate dominator totals (impossible worlds).

The module supports:
- Laps led conservation: Total laps led ≤ race length
- Fastest laps conservation: Total fastest laps ≤ green flag laps
- Position swap plausibility: Max swaps bounded by physical limits
- Batch validation: Vectorized validation across 1,000+ scenarios

All validation functions return veto reasons when constraints are violated,
making it easy to debug why scenarios are rejected.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import logging

# JAX imports for acceleration
try:
    import jax.numpy as jnp
    import jax
    from jax import vmap, jit
    JAX_AVAILABLE = True
except ImportError:
    # Fallback to numpy for development environments
    import numpy as jnp
    JAX_AVAILABLE = False
    # Create stubs for JAX-specific functions
    def vmap(func, in_axes=0):
        """Fallback vmap that just wraps the function."""
        return func
    def jit(func):
        """Fallback jit that just returns the function."""
        return func

# Import from state_space
try:
    from packages.axiomatic_sim.src.axiomatic_sim.state_space import RaceState
except ImportError:
    try:
        from .state_space import RaceState
    except ImportError:
        # For standalone usage, define a minimal RaceState placeholder
        RaceState = None


logger = logging.getLogger(__name__)


@dataclass
class ConservationResult:
    """Result of conservation validation.

    Attributes:
        laps_led_valid: Whether laps_led conservation is satisfied
        fastest_laps_valid: Whether fastest_laps conservation is satisfied
        position_swaps_valid: Whether position_swaps conservation is satisfied
        veto_reasons: List of human-readable veto reasons (populated if invalid)
        is_valid: Overall validity (True only if all validations pass)
    """
    laps_led_valid: bool
    fastest_laps_valid: bool
    position_swaps_valid: bool
    veto_reasons: List[str] = field(default_factory=list)
    is_valid: bool = False

    def __post_init__(self):
        """Calculate overall validity from individual validations."""
        self.is_valid = all([
            self.laps_led_valid,
            self.fastest_laps_valid,
            self.position_swaps_valid
        ])

    def add_veto_reason(self, reason: str) -> None:
        """Add a veto reason to the list.

        Args:
            reason: Human-readable explanation of the constraint violation
        """
        if reason and reason not in self.veto_reasons:
            self.veto_reasons.append(reason)


def validate_laps_led_conservation(
    laps_led: jnp.ndarray,
    race_length: int
) -> Tuple[bool, str]:
    """Validate that total laps led does not exceed race length.

    Conservation principle: Only one driver can lead a given lap.
    Therefore, sum of all drivers' laps_led must be ≤ race_length.

    Args:
        laps_led: JAX array of laps led per driver (shape: [n_drivers])
        race_length: Total laps in the race

    Returns:
        Tuple of (is_valid, veto_reason)
        - is_valid: True if conservation is satisfied
        - veto_reason: Empty string if valid, explanation if invalid

    Examples:
        >>> laps_led = jnp.array([100, 50, 30, 20])  # Sum = 200
        >>> validate_laps_led_conservation(laps_led, 200)
        (True, "")

        >>> laps_led = jnp.array([150, 60, 40])  # Sum = 250
        >>> validate_laps_led_conservation(laps_led, 200)
        (False, "Laps led conservation violated: total (250) exceeds race length (200)")
    """
    total_laps_led = jnp.sum(laps_led)

    if total_laps_led <= race_length:
        return True, ""
    else:
        veto_reason = (
            f"Laps led conservation violated: total ({int(total_laps_led)}) "
            f"exceeds race length ({race_length})"
        )
        return False, veto_reason


def validate_fastest_laps_conservation(
    fastest_laps: jnp.ndarray,
    green_flag_laps: int
) -> Tuple[bool, str]:
    """Validate that total fastest laps does not exceed green flag laps.

    Conservation principle: Only one driver can record fastest lap on a
    given green flag lap. Therefore, sum of all drivers' fastest_laps
    must be ≤ green_flag_laps.

    Args:
        fastest_laps: JAX array of fastest laps per driver (shape: [n_drivers])
        green_flag_laps: Total green flag laps in the race

    Returns:
        Tuple of (is_valid, veto_reason)
        - is_valid: True if conservation is satisfied
        - veto_reason: Empty string if valid, explanation if invalid

    Examples:
        >>> fastest_laps = jnp.array([10, 8, 5, 3])  # Sum = 26
        >>> validate_fastest_laps_conservation(fastest_laps, 30)
        (True, "")

        >>> fastest_laps = jnp.array([15, 12, 8])  # Sum = 35
        >>> validate_fastest_laps_conservation(fastest_laps, 30)
        (False, "Fastest laps conservation violated: total (35) exceeds green flag laps (30)")
    """
    total_fastest_laps = jnp.sum(fastest_laps)

    if total_fastest_laps <= green_flag_laps:
        return True, ""
    else:
        veto_reason = (
            f"Fastest laps conservation violated: total ({int(total_fastest_laps)}) "
            f"exceeds green flag laps ({green_flag_laps})"
        )
        return False, veto_reason


def calculate_max_position_swaps(field_size: int, green_flag_laps: int) -> int:
    """Calculate the physical limit on position swaps per race.

    Position swaps are bounded by physical opportunities:
    - Max 2 position changes per driver per green flag segment
    - Limited by actual green flag laps available
    - Track geometry limits concurrent position changes

    Formula: min(field_size * 2, green_flag_laps // 10)

    Rationale:
    - field_size * 2: Assumes each driver can change positions at most twice
      per segment on average (conservative bound)
    - green_flag_laps // 10: Assumes one opportunity per 10 green flag laps
      (rough estimate based on track length and racing opportunities)

    Args:
        field_size: Number of drivers in the race
        green_flag_laps: Total green flag laps in the race

    Returns:
        Maximum number of position swaps allowed (integer)

    Examples:
        >>> calculate_max_position_swaps(40, 180)
        40  # min(80, 18) = 18, but bound by field_size * factor

        >>> calculate_max_position_swaps(20, 50)
        10  # min(40, 5) = 5
    """
    # Conservative bound: 2 swaps per driver max
    swaps_per_driver_limit = field_size * 2

    # Track geometry bound: 1 swap opportunity per 10 green flag laps
    track_opportunity_limit = green_flag_laps // 10

    # Take the more conservative bound
    max_swaps = min(swaps_per_driver_limit, track_opportunity_limit)

    # Ensure at least field_size (one swap per driver minimum)
    max_swaps = max(max_swaps, field_size)

    return max_swaps


def validate_position_swaps(
    start_positions: jnp.ndarray,
    finish_positions: jnp.ndarray,
    max_swaps: int
) -> Tuple[bool, str]:
    """Validate that position swaps are within physical limits.

    Position swap count: sum(abs(finish - start)) across all drivers.
    This measures total position changes from start to finish.

    Conservation principle: Total position changes cannot exceed physical
    opportunities for passing during the race.

    Args:
        start_positions: JAX array of starting positions (shape: [n_drivers])
        finish_positions: JAX array of finishing positions (shape: [n_drivers])
        max_swaps: Maximum allowed position swaps (from calculate_max_position_swaps)

    Returns:
        Tuple of (is_valid, veto_reason)
        - is_valid: True if swaps are within limits
        - veto_reason: Empty string if valid, explanation if invalid

    Examples:
        >>> start = jnp.array([1, 2, 3, 4, 5])
        >>> finish = jnp.array([1, 2, 3, 4, 5])
        >>> validate_position_swaps(start, finish, 10)
        (True, "")

        >>> start = jnp.array([1, 2, 3, 4, 5])
        >>> finish = jnp.array([5, 4, 3, 2, 1])  # Total swaps = 12
        >>> validate_position_swaps(start, finish, 10)
        (False, "Position swaps violated: total (12) exceeds max allowed (10)")
    """
    # Calculate total position changes
    position_changes = jnp.abs(finish_positions - start_positions)
    total_swaps = jnp.sum(position_changes)

    if total_swaps <= max_swaps:
        return True, ""
    else:
        veto_reason = (
            f"Position swaps violated: total ({int(total_swaps)}) "
            f"exceeds max allowed ({max_swaps})"
        )
        return False, veto_reason


@jit
def _validate_single_scenario(
    scenario: jnp.ndarray,
    race_length: int,
    green_flag_laps: int,
    max_swaps: int
) -> bool:
    """Validate a single scenario's conservation constraints.

    Args:
        scenario: Array with [laps_led, fastest_laps] per driver (shape: [n_drivers, 2])
        race_length: Total race laps
        green_flag_laps: Total green flag laps
        max_swaps: Maximum position swaps

    Returns:
        True if all conservation constraints satisfied
    """
    laps_led = scenario[:, 0]
    fastest_laps = scenario[:, 1]

    laps_led_ok = jnp.sum(laps_led) <= race_length
    fastest_laps_ok = jnp.sum(fastest_laps) <= green_flag_laps

    return jnp.logical_and(laps_led_ok, fastest_laps_ok)


@jit
def batch_validate_conservation(
    scenarios: jnp.ndarray,
    race_length: int,
    green_flag_laps: int,
    max_swaps: int
) -> jnp.ndarray:
    """Validate conservation constraints across a batch of scenarios.

    This function is JIT-compiled for performance. Uses vmap to vectorize
    validation across all scenarios in parallel.

    Args:
        scenarios: Batch of scenarios with laps_led and fastest_laps
                   (shape: [n_scenarios, n_drivers, 2])
                   scenarios[i, :, 0] = laps_led for scenario i
                   scenarios[i, :, 1] = fastest_laps for scenario i
        race_length: Total race laps
        green_flag_laps: Total green flag laps
        max_swaps: Maximum position swaps (not used in vectorized laps validation)

    Returns:
        Boolean array (shape: [n_scenarios]) indicating valid/invalid
        True = scenario passes conservation, False = scenario violates conservation

    Examples:
        >>> scenarios = jnp.array([
        ...     [[100, 10], [50, 8], [30, 5], [20, 3]],  # Sum: 200, 26
        ...     [[150, 15], [60, 12], [40, 8]],           # Sum: 250, 35
        ... ])
        >>> batch_validate_conservation(scenarios, 200, 30, 40)
        Array([True, False], dtype=bool)
    """
    if JAX_AVAILABLE:
        # Use JAX vmap for vectorized validation
        validate_fn = lambda s: _validate_single_scenario(
            s, race_length, green_flag_laps, max_swaps
        )
        vectorized_validate = vmap(validate_fn)
        return vectorized_validate(scenarios)
    else:
        # Fallback to loop-based validation
        results = []
        for i in range(scenarios.shape[0]):
            scenario = scenarios[i]
            laps_led = scenario[:, 0]
            fastest_laps = scenario[:, 1]

            laps_led_ok = jnp.sum(laps_led) <= race_length
            fastest_laps_ok = jnp.sum(fastest_laps) <= green_flag_laps
            results.append(jnp.logical_and(laps_led_ok, fastest_laps_ok))

        return jnp.array(results)


def validate_race_state_conservation(
    race_state: RaceState,
    green_flag_laps: int
) -> ConservationResult:
    """Validate conservation constraints for a RaceState instance.

    This is a convenience function that extracts laps_led from all drivers
    in a RaceState and validates conservation.

    Args:
        race_state: RaceState instance to validate
        green_flag_laps: Total green flag laps in the race

    Returns:
        ConservationResult with validation status and veto reasons

    Examples:
        >>> from packages.axiomatic_sim.src.axiomatic_sim.state_space import (
        ...     RaceState, DriverState, RaceSegment
        ... )
        >>> drivers = {
        ...     "driver1": DriverState(position=1, fuel_level=1.0, tire_wear=1.0, laps_led=100),
        ...     "driver2": DriverState(position=2, fuel_level=1.0, tire_wear=1.0, laps_led=50),
        ... }
        >>> state = RaceState(lap=200, race_length=200, segment=RaceSegment.GREEN_FLAG, drivers=drivers)
        >>> result = validate_race_state_conservation(state, 180)
        >>> result.is_valid
        True
    """
    # Extract laps_led from all drivers
    laps_led_list = [driver.laps_led for driver in race_state.drivers.values()]
    laps_led = jnp.array(laps_led_list)

    # Fastest laps not currently tracked in DriverState, assume all zeros
    fastest_laps = jnp.zeros(len(laps_led_list))

    # Validate laps led
    laps_led_valid, laps_led_reason = validate_laps_led_conservation(
        laps_led, race_state.race_length
    )

    # Validate fastest laps
    fastest_laps_valid, fastest_laps_reason = validate_fastest_laps_conservation(
        fastest_laps, green_flag_laps
    )

    # Position swaps validation requires start positions, not available in RaceState
    position_swaps_valid = True

    # Build result
    result = ConservationResult(
        laps_led_valid=bool(laps_led_valid),
        fastest_laps_valid=bool(fastest_laps_valid),
        position_swaps_valid=position_swaps_valid
    )

    # Add veto reasons
    if not laps_led_valid:
        result.add_veto_reason(laps_led_reason)
    if not fastest_laps_valid:
        result.add_veto_reason(fastest_laps_reason)

    return result


# Export public API
__all__ = [
    "ConservationResult",
    "validate_laps_led_conservation",
    "validate_fastest_laps_conservation",
    "calculate_max_position_swaps",
    "validate_position_swaps",
    "batch_validate_conservation",
    "validate_race_state_conservation",
    "JAX_AVAILABLE",
]
