"""
Immutable constraint specification models.

This module provides frozen dataclasses for constraint specifications compiled
from Neo4j. These models ensure immutability and validation of constraint data.

Key concepts:
- Frozen dataclasses prevent mutation after creation
- Validation in __post_init__ ensures data integrity
- Hash computation enables versioning and reproducibility
"""
from dataclasses import dataclass, field
from typing import Dict, List
import hashlib
import json


@dataclass(frozen=True)
class DriverConstraints:
    """
    Immutable driver constraint specification.

    Attributes:
        driver_id: Unique driver identifier
        skill: Driver skill level (0-1)
        aggression: Aggression level (0-1)
        shadow_risk: Risk of poor performance (0-1)
        min_laps_led: Minimum laps this driver can lead (0+)
        max_laps_led: Maximum laps this driver can lead (>= min_laps_led)
        veto_rules: List of veto rule identifiers for this driver
    """
    driver_id: str
    skill: float
    aggression: float
    shadow_risk: float
    min_laps_led: int
    max_laps_led: int
    veto_rules: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate driver constraints after initialization."""
        # Validate skill, aggression, shadow_risk are in [0, 1]
        if not 0.0 <= self.skill <= 1.0:
            raise ValueError(f"Driver {self.driver_id}: skill must be in [0, 1], got {self.skill}")
        if not 0.0 <= self.aggression <= 1.0:
            raise ValueError(f"Driver {self.driver_id}: aggression must be in [0, 1], got {self.aggression}")
        if not 0.0 <= self.shadow_risk <= 1.0:
            raise ValueError(f"Driver {self.driver_id}: shadow_risk must be in [0, 1], got {self.shadow_risk}")

        # Validate laps led constraints
        if self.min_laps_led < 0:
            raise ValueError(f"Driver {self.driver_id}: min_laps_led must be >= 0, got {self.min_laps_led}")
        if self.max_laps_led < self.min_laps_led:
            raise ValueError(
                f"Driver {self.driver_id}: max_laps_led ({self.max_laps_led}) "
                f"must be >= min_laps_led ({self.min_laps_led})"
            )

        # Validate veto_rules is a list (frozen dataclass needs explicit check)
        if not isinstance(self.veto_rules, list):
            raise ValueError(f"Driver {self.driver_id}: veto_rules must be a list")


@dataclass(frozen=True)
class TrackConstraints:
    """
    Immutable track constraint specification.

    Attributes:
        track_id: Unique track identifier
        difficulty: Track difficulty (0-1)
        aggression_factor: How much aggression matters at this track (0-1)
        caution_rate: Probability of caution per lap (0-1)
        pit_window_laps: Standard pit window lap numbers
    """
    track_id: str
    difficulty: float
    aggression_factor: float
    caution_rate: float
    pit_window_laps: List[int] = field(default_factory=lambda: [35, 70, 105, 140, 175])

    def __post_init__(self):
        """Validate track constraints after initialization."""
        # Validate difficulty, aggression_factor, caution_rate are in [0, 1]
        if not 0.0 <= self.difficulty <= 1.0:
            raise ValueError(f"Track {self.track_id}: difficulty must be in [0, 1], got {self.difficulty}")
        if not 0.0 <= self.aggression_factor <= 1.0:
            raise ValueError(
                f"Track {self.track_id}: aggression_factor must be in [0, 1], got {self.aggression_factor}"
            )
        if not 0.0 <= self.caution_rate <= 1.0:
            raise ValueError(f"Track {self.track_id}: caution_rate must be in [0, 1], got {self.caution_rate}")

        # Validate pit_window_laps is sorted and positive
        if not isinstance(self.pit_window_laps, list):
            raise ValueError(f"Track {self.track_id}: pit_window_laps must be a list")

        if len(self.pit_window_laps) > 0:
            if self.pit_window_laps != sorted(self.pit_window_laps):
                raise ValueError(f"Track {self.track_id}: pit_window_laps must be sorted")
            if any(lap < 0 for lap in self.pit_window_laps):
                raise ValueError(f"Track {self.track_id}: pit_window_laps must be non-negative")


@dataclass(frozen=True)
class ConstraintSpec:
    """
    Immutable constraint specification for a slate.

    This is the compiled artifact from Neo4j that replaces live database
    queries in simulation/optimization loops.

    Attributes:
        slate_id: Unique slate identifier
        compiled_at: ISO timestamp of when spec was compiled
        drivers: Dictionary mapping driver_id to DriverConstraints
        tracks: Dictionary mapping track_id to TrackConstraints
        version: Version string for this spec
        hash: SHA-256 hash of constraint data for versioning
    """
    slate_id: str
    compiled_at: str
    drivers: Dict[str, DriverConstraints]
    tracks: Dict[str, TrackConstraints]
    version: str
    hash: str = field(default="")

    def __post_init__(self):
        """Compute hash from constraints and validate."""
        # Compute deterministic hash from driver and track constraints
        hash_input = {
            "drivers": {
                driver_id: {
                    "skill": constraints.skill,
                    "aggression": constraints.aggression,
                    "shadow_risk": constraints.shadow_risk,
                    "min_laps_led": constraints.min_laps_led,
                    "max_laps_led": constraints.max_laps_led,
                    "veto_rules": sorted(constraints.veto_rules),
                }
                for driver_id, constraints in sorted(self.drivers.items())
            },
            "tracks": {
                track_id: {
                    "difficulty": constraints.difficulty,
                    "aggression_factor": constraints.aggression_factor,
                    "caution_rate": constraints.caution_rate,
                    "pit_window_laps": constraints.pit_window_laps,
                }
                for track_id, constraints in sorted(self.tracks.items())
            },
        }

        # Compute SHA-256 hash
        json_str = json.dumps(hash_input, sort_keys=True)
        hash_value = hashlib.sha256(json_str.encode()).hexdigest()

        # Set hash using object.__setattr__ for frozen dataclass
        object.__setattr__(self, "hash", hash_value)

    def get_driver_constraints(self, driver_id: str) -> DriverConstraints:
        """
        Get driver constraints by driver_id.

        Args:
            driver_id: Driver identifier

        Returns:
            DriverConstraints for the specified driver

        Raises:
            KeyError: If driver_id not found in spec
        """
        if driver_id not in self.drivers:
            raise KeyError(f"Driver {driver_id} not found in constraint spec for slate {self.slate_id}")
        return self.drivers[driver_id]

    def get_track_constraints(self, track_id: str) -> TrackConstraints:
        """
        Get track constraints by track_id.

        Args:
            track_id: Track identifier

        Returns:
            TrackConstraints for the specified track

        Raises:
            KeyError: If track_id not found in spec
        """
        if track_id not in self.tracks:
            raise KeyError(f"Track {track_id} not found in constraint spec for slate {self.slate_id}")
        return self.tracks[track_id]
