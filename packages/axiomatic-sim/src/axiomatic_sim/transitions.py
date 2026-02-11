"""
Transition operators for NASCAR race simulation.

This module implements concrete state transitions that represent the dynamics
of a NASCAR race: green flag racing, caution periods, pit cycles, and fuel windows.

All transitions are pure functions - they take a RaceState and return a new
RaceState without side effects or mutations.
"""

import logging
import random
from dataclasses import replace
from typing import List, Dict

from axiomatic_sim.state_space import (
    RaceState,
    DriverState,
    RaceSegment,
    DriverId,
)


# Configure logging
logger = logging.getLogger("axiomatic_sim.transitions")


# Constants for transition behavior
FUEL_BURN_PER_LAP = 0.01  # Fuel consumed per lap under green flag
TIRE_WEAR_PER_LAP = 0.02  # Tire wear per lap under green flag
CAUTION_FUEL_BURN = 0.005  # Fuel consumed per lap under caution (slower)
FUEL_THRESHOLD = 0.15  # Fuel level below which driver is in fuel window
POSITION_SWAP_PROBABILITY = 0.1  # Probability of position change per lap


def green_flag_transition(state: RaceState, laps: int = 1) -> RaceState:
    """Apply green flag racing transition for specified number of laps.

    During green flag racing:
    - Lap counter increments
    - Fuel decreases for all drivers
    - Tire wear increases for all drivers
    - Positions may change based on random swaps (binomial distribution)
    - Leader's laps_led increases

    Args:
        state: Current race state
        laps: Number of green flag laps to simulate (default: 1)

    Returns:
        New race state after green flag laps

    Raises:
        ValueError: If transition would violate state invariants
    """
    if laps < 1:
        raise ValueError(f"Laps must be >= 1, got {laps}")

    new_lap = state.lap + laps

    # Check if this would exceed race length
    if new_lap > state.race_length:
        raise ValueError(
            f"Cannot advance to lap {new_lap}, race length is {state.race_length}"
        )

    logger.info(f"Applying green flag transition: laps={laps}, {state.lap} -> {new_lap}")

    # Create new driver states with updated fuel, tire wear, and positions
    new_drivers: Dict[DriverId, DriverState] = {}

    # Get list of active driver IDs (not DNF) for position shuffling
    active_driver_ids = [
        driver_id for driver_id, driver_state in state.drivers.items()
        if not driver_state.dnf
    ]

    # Create position mapping for potential swaps
    positions = {
        driver_id: driver_state.position
        for driver_id, driver_state in state.drivers.items()
        if not driver_state.dnf
    }

    # Apply random position swaps for each lap
    for _ in range(laps):
        # Randomly swap adjacent positions with binomial distribution
        driver_ids_in_order = sorted(positions.keys(), key=lambda d: positions[d])

        for i in range(len(driver_ids_in_order) - 1):
            # Random chance to swap positions
            if random.random() < POSITION_SWAP_PROBABILITY:
                driver_a = driver_ids_in_order[i]
                driver_b = driver_ids_in_order[i + 1]
                positions[driver_a], positions[driver_b] = (
                    positions[driver_b],
                    positions[driver_a],
                )

    # Update each driver's state
    for driver_id, driver_state in state.drivers.items():
        if driver_state.dnf:
            # DNF drivers don't change
            new_drivers[driver_id] = driver_state
            continue

        # Calculate new fuel level
        fuel_burn = FUEL_BURN_PER_LAP * laps
        new_fuel = max(0.0, driver_state.fuel_level - fuel_burn)

        # Calculate new tire wear
        tire_wear = TIRE_WEAR_PER_LAP * laps
        new_tire = max(0.0, driver_state.tire_wear - tire_wear)

        # Update position from the shuffled mapping
        new_position = positions.get(driver_id, driver_state.position)

        # Track laps led for the leader (position 1)
        new_laps_led = driver_state.laps_led
        if new_position == 1:
            new_laps_led += laps

        new_drivers[driver_id] = replace(
            driver_state,
            position=new_position,
            fuel_level=new_fuel,
            tire_wear=new_tire,
            laps_led=new_laps_led,
        )

    # Create and return new race state
    new_state = replace(
        state,
        lap=new_lap,
        drivers=new_drivers,
    )

    logger.debug(f"Green flag transition complete: {len(new_drivers)} drivers updated")

    return new_state


def caution_transition(state: RaceState, caution_laps: int = 3) -> RaceState:
    """Apply caution period transition.

    During caution:
    - Segment changes to CAUTION
    - All positions are frozen (no position changes)
    - Active caution laps counter is set
    - Fuel decreases at slower rate (cars running slower)
    - Drivers in pits complete their pit stops

    Args:
        state: Current race state
        caution_laps: Number of caution laps to simulate (default: 3)

    Returns:
        New race state in caution segment

    Raises:
        ValueError: If transition would violate state invariants
    """
    if caution_laps < 1:
        raise ValueError(f"Caution laps must be >= 1, got {caution_laps}")

    logger.info(
        f"Applying caution transition: caution_laps={caution_laps}, "
        f"segment={state.segment} -> CAUTION"
    )

    # Update drivers: decrease fuel slower, complete pit stops
    new_drivers: Dict[DriverId, DriverState] = {}
    for driver_id, driver_state in state.drivers.items():
        if driver_state.dnf:
            # DNF drivers don't change
            new_drivers[driver_id] = driver_state
            continue

        # Calculate fuel burn (slower under caution)
        fuel_burn = CAUTION_FUEL_BURN * caution_laps
        new_fuel = max(0.0, driver_state.fuel_level - fuel_burn)

        # Complete pit stops if driver was in pits
        new_in_pit = False  # Pit stops complete under caution

        new_drivers[driver_id] = replace(
            driver_state,
            fuel_level=new_fuel,
            in_pit=new_in_pit,
        )

    # Create new race state in caution segment
    new_state = replace(
        state,
        segment=RaceSegment.CAUTION,
        active_caution_laps=caution_laps,
        drivers=new_drivers,
    )

    logger.debug(
        f"Caution transition complete: {len(new_drivers)} drivers, "
        f"{caution_laps} caution laps"
    )

    return new_state


def pit_cycle_transition(state: RaceState, pit_drivers: List[DriverId]) -> RaceState:
    """Apply pit cycle transition.

    During a pit cycle:
    - Segment changes to PIT_CYCLE
    - Pitting drivers reset fuel to 1.0 and tires to 1.0
    - Pitting drivers receive position penalty (drop to rear of field)
    - Non-pitting drivers advance positions to fill gaps

    Args:
        state: Current race state
        pit_drivers: List of driver IDs entering pits

    Returns:
        New race state with pit cycle applied

    Raises:
        ValueError: If transition would violate state invariants
    """
    if not pit_drivers:
        logger.warning("Pit cycle called with empty pit_drivers list")
        # Still allow this - it's valid to have no pitters
        return replace(state, segment=RaceSegment.PIT_CYCLE)

    # Validate all pit drivers exist
    for driver_id in pit_drivers:
        if driver_id not in state.drivers:
            raise ValueError(f"Driver {driver_id} not in race state")

    logger.info(
        f"Applying pit cycle transition: {len(pit_drivers)} drivers pitting, "
        f"segment={state.segment} -> PIT_CYCLE"
    )

    # Get active drivers for position calculation
    active_drivers = {
        driver_id: driver_state
        for driver_id, driver_state in state.drivers.items()
        if not driver_state.dnf
    }

    # Separate pitting and non-pitting drivers
    pitting_set = set(pit_drivers)
    non_pitting_drivers = [
        driver_id for driver_id in active_drivers.keys() if driver_id not in pitting_set
    ]

    # Sort non-pitting drivers by current position
    non_pitting_sorted = sorted(
        non_pitting_drivers, key=lambda d: active_drivers[d].position
    )

    # Assign new positions: non-pitters keep relative order, pitters go to rear
    new_positions: Dict[DriverId, int] = {}

    # Non-pitting drivers fill positions from the front
    for i, driver_id in enumerate(non_pitting_sorted, start=1):
        new_positions[driver_id] = i

    # Pitting drivers fill positions from the rear
    # Determine max field size (including active drivers)
    max_position = len(active_drivers)

    # Sort pitting drivers by their current position (first to pit gets better position)
    pitting_sorted = sorted(
        pit_drivers,
        key=lambda d: active_drivers[d].position if d in active_drivers else 999,
    )

    # Assign rear positions to pitting drivers
    rear_position_start = max_position - len(pitting_sorted) + 1
    for i, driver_id in enumerate(pitting_sorted):
        new_positions[driver_id] = rear_position_start + i

    # Update all drivers
    new_drivers: Dict[DriverId, DriverState] = {}
    for driver_id, driver_state in state.drivers.items():
        if driver_id in pit_drivers:
            # Pitting driver: reset fuel and tires, mark as in pit
            new_drivers[driver_id] = replace(
                driver_state,
                fuel_level=1.0,
                tire_wear=1.0,
                position=new_positions.get(driver_id, driver_state.position),
                in_pit=True,
            )
            logger.debug(
                f"Driver {driver_id} pitted: fuel=1.0, tires=1.0, "
                f"pos={driver_state.position}->{new_positions[driver_id]}"
            )
        elif not driver_state.dnf:
            # Non-pitting driver: update position only
            new_drivers[driver_id] = replace(
                driver_state, position=new_positions.get(driver_id, driver_state.position)
            )
        else:
            # DNF driver: no change
            new_drivers[driver_id] = driver_state

    # Create new race state
    new_state = replace(
        state,
        segment=RaceSegment.PIT_CYCLE,
        drivers=new_drivers,
        active_caution_laps=0,  # Reset caution laps when entering pit cycle
    )

    logger.debug(
        f"Pit cycle complete: {len(pit_drivers)} drivers serviced, "
        f"positions reassigned"
    )

    return new_state


def fuel_window_transition(state: RaceState) -> RaceState:
    """Check if race enters fuel window and update state accordingly.

    Fuel window is triggered when more than 5 drivers have fuel level
    below the FUEL_THRESHOLD (0.15).

    Args:
        state: Current race state

    Returns:
        New race state (may be unchanged if not in fuel window)
    """
    # Count drivers below fuel threshold
    drivers_below_threshold = [
        driver_id
        for driver_id, driver_state in state.drivers.items()
        if not driver_state.dnf and driver_state.fuel_level < FUEL_THRESHOLD
    ]

    # Check if we should enter fuel window
    should_enter_fuel_window = len(drivers_below_threshold) > 5

    if should_enter_fuel_window:
        if state.segment != RaceSegment.FUEL_WINDOW:
            logger.info(
                f"Entering fuel window: {len(drivers_below_threshold)} drivers "
                f"below threshold (>{FUEL_THRESHOLD*100:.0f}%), "
                f"segment={state.segment} -> FUEL_WINDOW"
            )

        return replace(state, segment=RaceSegment.FUEL_WINDOW)
    else:
        logger.debug(
            f"Not in fuel window: {len(drivers_below_threshold)} drivers below threshold"
        )
        # Return unmodified state if not in fuel window
        return state
