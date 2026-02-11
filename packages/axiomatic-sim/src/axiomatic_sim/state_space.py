"""
State space model for NASCAR race simulation.

This module defines the core types for representing race state and transitions
between race segments (green flag, caution, pit cycles, fuel windows).

The state space is designed to be:
- Immutable: All state updates create new RaceState instances
- Type-safe: Transitions are validated at type-check time
- Composable: Transitions can be chained to build Skeleton Narratives
"""

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Dict, Protocol, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


# Type aliases
DriverId = str


class RaceSegment(Enum):
    """Represents the current segment of a race.

    NASCAR races consist of alternating segments with different rules:
    - GREEN_FLAG: Normal racing conditions, positions change freely
    - CAUTION: Field frozen, safety vehicles on track, no position changes
    - PIT_CYCLE: Green flag pit stop sequence, pitting drivers penalized
    - FUEL_WINDOW: Approaching fuel exhaustion, drivers must pit soon
    """
    GREEN_FLAG = "green_flag"
    CAUTION = "caution"
    PIT_CYCLE = "pit_cycle"
    FUEL_WINDOW = "fuel_window"


@dataclass(frozen=True)
class DriverState:
    """Represents the state of a single driver at a point in time.

    All fields are immutable - updates create new DriverState instances.

    Attributes:
        position: Current running position (1-40, 1 is leader)
        fuel_level: Fraction of fuel remaining (0.0-1.0)
        tire_wear: Fraction of tire life remaining (0.0-1.0)
        laps_led: Total laps led so far in the race
        in_pit: Whether driver is currently on pit road
        dnf: Whether driver has retired from the race (did not finish)
    """
    position: int
    fuel_level: float
    tire_wear: float
    laps_led: int = 0
    in_pit: bool = False
    dnf: bool = False

    def __post_init__(self):
        """Validate driver state invariants."""
        # Position must be positive
        if self.position < 1:
            raise ValueError(f"Position must be >= 1, got {self.position}")

        # Fuel level must be in [0, 1]
        if not 0.0 <= self.fuel_level <= 1.0:
            raise ValueError(
                f"Fuel level must be in [0.0, 1.0], got {self.fuel_level}"
            )

        # Tire wear must be in [0, 1]
        if not 0.0 <= self.tire_wear <= 1.0:
            raise ValueError(
                f"Tire wear must be in [0.0, 1.0], got {self.tire_wear}"
            )

        # Laps led cannot be negative
        if self.laps_led < 0:
            raise ValueError(f"Laps led must be >= 0, got {self.laps_led}")

        # DNF drivers cannot be in pits
        if self.dnf and self.in_pit:
            raise ValueError("DNF driver cannot be in pit")


@dataclass(frozen=True)
class RaceState:
    """Represents the complete state of a race at a point in time.

    This is the core data structure for simulation. All transitions
    create new RaceState instances - mutations are not allowed.

    Attributes:
        lap: Current lap number (1-indexed)
        race_length: Total laps in the race
        segment: Current race segment (GREEN_FLAG, CAUTION, etc.)
        drivers: Mapping of driver_id to DriverState
        active_caution_laps: Laps remaining in caution period (0 if green)
    """
    lap: int
    race_length: int
    segment: RaceSegment
    drivers: Dict[DriverId, DriverState]
    active_caution_laps: int = 0

    def __post_init__(self):
        """Validate race state invariants."""
        # Lap must be positive
        if self.lap < 1:
            raise ValueError(f"Lap must be >= 1, got {self.lap}")

        # Lap cannot exceed race length
        if self.lap > self.race_length:
            raise ValueError(
                f"Lap ({self.lap}) cannot exceed race_length ({self.race_length})"
            )

        # Race length must be positive
        if self.race_length < 1:
            raise ValueError(f"Race length must be >= 1, got {self.race_length}")

        # Must have at least one driver
        if len(self.drivers) < 1:
            raise ValueError("Race must have at least one driver")

        # Active caution laps cannot be negative
        if self.active_caution_laps < 0:
            raise ValueError(
                f"Active caution laps must be >= 0, got {self.active_caution_laps}"
            )

        # If in caution segment, must have active caution laps
        if self.segment == RaceSegment.CAUTION and self.active_caution_laps == 0:
            raise ValueError(
                "CAUTION segment requires active_caution_laps > 0"
            )

        # If not in caution, should not have active caution laps
        if self.segment != RaceSegment.CAUTION and self.active_caution_laps > 0:
            raise ValueError(
                f"Cannot have active_caution_laps > 0 in {self.segment} segment"
            )

        # Validate all driver states
        for driver_id, driver_state in self.drivers.items():
            if not isinstance(driver_state, DriverState):
                raise ValueError(
                    f"Driver {driver_id} must be DriverState, got {type(driver_state)}"
                )

        # Validate position uniqueness (no two drivers can have same position)
        positions = [d.position for d in self.drivers.values() if not d.dnf]
        if len(positions) != len(set(positions)):
            raise ValueError("Positions must be unique among active drivers")


# Type alias for transition functions (defined after RaceState)
TransitionCallable = Callable[[RaceState], RaceState]


class StateTransition(Protocol):
    """Protocol for state transition operators.

    A transition operator transforms a RaceState into a new RaceState.
    All transitions must be pure functions - no side effects, no mutations.

    Example:
        >>> def my_transition(state: RaceState) -> RaceState:
        ...     # Create and return new state
        ...     return dataclasses.replace(state, lap=state.lap + 1)
    """

    def apply(self, state: RaceState) -> RaceState:
        """Apply the transition to create a new state.

        Args:
            state: Current race state

        Returns:
            New race state after applying transition

        Raises:
            ValueError: If transition would violate state invariants
        """
        ...


class TransitionOperator:
    """Base class for state transition operators.

    This provides a common interface for all transitions and enables
    composition of transitions using operator chaining.

    Example:
        >>> transition = TransitionOperator(lambda s: green_flag_transition(s, laps=5))
        >>> new_state = transition.apply(current_state)
    """

    def __init__(self, func: TransitionCallable):
        """Initialize with a transition function.

        Args:
            func: Function that transforms RaceState to RaceState
        """
        self._func = func

    def apply(self, state: RaceState) -> RaceState:
        """Apply the transition function.

        Args:
            state: Current race state

        Returns:
            New race state after applying transition
        """
        return self._func(state)

    def __or__(self, other: 'TransitionOperator') -> 'TransitionOperator':
        """Compose two transitions (left-to-right).

        Example:
            >>> combined = green_flag | caution
            >>> new_state = combined.apply(state)

        Args:
            other: Transition to apply after this one

        Returns:
            New composed transition operator
        """
        def composed(state: RaceState) -> RaceState:
            intermediate = self.apply(state)
            return other.apply(intermediate)

        return TransitionOperator(composed)

    def __repr__(self) -> str:
        """String representation of the transition."""
        return f"TransitionOperator({self._func.__name__})"
