"""
Skeleton Narrative data structures for race scenario generation.

This module defines the core data structures for representing race scenarios,
including race-flow regimes, driver outcomes, and conservation metadata.

The Skeleton Narrative concept treats a race as mostly quiet (coarse granularity)
until something happens (incident/caution triggers fine granularity). This module
provides the data contracts for scenario generation and serialization.
"""
import json
import logging
import uuid
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional

# PyArrow and pandas for serialization
try:
    import pyarrow.parquet as pq
    import pandas as pd
    PARQUET_AVAILABLE = True
except ImportError:
    PARQUET_AVAILABLE = False
    pq = None
    pd = None

logger = logging.getLogger(__name__)


class PitStrategy(Enum):
    """
    Pit strategy enum representing driver approach to pit stops.

    Attributes:
        AGGRESSIVE: Early pit stops, prioritize track position over fuel/tires
        STANDARD: Pit around median lap window, balanced approach
        CONSERVATIVE: Late pit stops, prioritize fuel and tire conservation
    """
    AGGRESSIVE = "aggressive"
    STANDARD = "standard"
    CONSERVATIVE = "conservative"


@dataclass(frozen=True)
class RaceFlowRegime:
    """
    Race-flow regime representing the macro-level pattern of a race scenario.

    The regime captures the high-level characteristics of how a race unfolds,
    including caution frequency, pit strategy patterns, and risk factors.

    Attributes:
        n_cautions: Number of caution periods in the race (0-10)
        pit_strategy: Dominant pit strategy pattern for this scenario
        fuel_window_risk: Probability of fuel mileage race (0-1)
        late_race_chaos: Probability of late-race incidents (0-1)

    Example:
        >>> regime = RaceFlowRegime(
        ...     n_cautions=5,
        ...     pit_strategy=PitStrategy.STANDARD,
        ...     fuel_window_risk=0.3,
        ...     late_race_chaos=0.4
        ... )
        >>> assert regime.n_cautions == 5
    """
    n_cautions: int
    pit_strategy: PitStrategy
    fuel_window_risk: float
    late_race_chaos: float

    def __post_init__(self):
        """Validate race-flow regime invariants."""
        # Caution count must be non-negative and bounded
        if self.n_cautions < 0:
            raise ValueError(f"n_cautions must be >= 0, got {self.n_cautions}")
        if self.n_cautions > 10:
            raise ValueError(f"n_cautions must be <= 10, got {self.n_cautions}")

        # Risk probabilities must be in [0, 1]
        if not 0.0 <= self.fuel_window_risk <= 1.0:
            raise ValueError(
                f"fuel_window_risk must be in [0.0, 1.0], got {self.fuel_window_risk}"
            )
        if not 0.0 <= self.late_race_chaos <= 1.0:
            raise ValueError(
                f"late_race_chaos must be in [0.0, 1.0], got {self.late_race_chaos}"
            )


@dataclass(frozen=True)
class DriverOutcome:
    """
    Outcome for a single driver in a race scenario.

    Contains all DFS-relevant components for a driver: dominator metrics
    (laps led, fastest laps), finishing outcomes, and incident status.

    Attributes:
        driver_id: Unique identifier for the driver
        laps_led: Total laps led by this driver (0-race_length)
        fastest_laps: Number of fastest laps recorded (0-green_flag_laps)
        finish_position: Final finishing position (1-field_size, 40 for DNF)
        place_differential: Position change (finish - start, negative = gained spots)
        incident: Whether driver was involved in an incident
        dnf_lap: Lap of DNF if applicable, None if finished

    Example:
        >>> outcome = DriverOutcome(
        ...     driver_id="driver_123",
        ...     laps_led=50,
        ...     fastest_laps=10,
        ...     finish_position=5,
        ...     place_differential=-5,  # Gained 5 positions
        ...     incident=False,
        ...     dnf_lap=None
        ... )
    """
    driver_id: str
    laps_led: int
    fastest_laps: int
    finish_position: int
    place_differential: int
    incident: bool
    dnf_lap: Optional[int] = None

    def __post_init__(self):
        """Validate driver outcome invariants."""
        # Laps led cannot be negative
        if self.laps_led < 0:
            raise ValueError(f"laps_led must be >= 0, got {self.laps_led}")

        # Fastest laps cannot be negative
        if self.fastest_laps < 0:
            raise ValueError(f"fastest_laps must be >= 0, got {self.fastest_laps}")

        # Finish position must be positive
        if self.finish_position < 1:
            raise ValueError(f"finish_position must be >= 1, got {self.finish_position}")

        # If DNF, dnf_lap must be provided
        if self.finish_position == 40 and self.dnf_lap is None:
            raise ValueError("DNF (finish_position=40) requires dnf_lap")

        # If not DNF, dnf_lap should be None
        if self.finish_position != 40 and self.dnf_lap is not None:
            raise ValueError("dnf_lap should only be set for DNF (finish_position=40)")

        # DNF lap must be positive if provided
        if self.dnf_lap is not None and self.dnf_lap < 1:
            raise ValueError(f"dnf_lap must be >= 1, got {self.dnf_lap}")


@dataclass(frozen=True)
class ConservationMetadata:
    """
    Metadata about conservation constraint validation for a scenario.

    This data structure tracks whether the scenario respects physical
    conservation laws (laps led, fastest laps) and provides veto reasons
    if validation fails.

    Attributes:
        total_laps_led: Sum of all driver laps_led (must ≤ race_length)
        total_fastest_laps: Sum of all driver fastest_laps (must ≤ green_flag_laps)
        green_flag_laps: Total green flag laps in the race
        validation_passed: True if all conservation constraints satisfied
        veto_reasons: List of human-readable veto reasons (empty if valid)

    Example:
        >>> metadata = ConservationMetadata(
        ...     total_laps_led=200,
        ...     total_fastest_laps=50,
        ...     green_flag_laps=180,
        ...     validation_passed=True,
        ...     veto_reasons=[]
        ... )
    """
    total_laps_led: int
    total_fastest_laps: int
    green_flag_laps: int
    validation_passed: bool
    veto_reasons: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate conservation metadata invariants."""
        # Totals cannot be negative
        if self.total_laps_led < 0:
            raise ValueError(f"total_laps_led must be >= 0, got {self.total_laps_led}")
        if self.total_fastest_laps < 0:
            raise ValueError(
                f"total_fastest_laps must be >= 0, got {self.total_fastest_laps}"
            )

        # Green flag laps must be non-negative
        if self.green_flag_laps < 0:
            raise ValueError(
                f"green_flag_laps must be >= 0, got {self.green_flag_laps}"
            )

        # Validation passed should be consistent with veto reasons
        if self.validation_passed and self.veto_reasons:
            logger.warning(
                "ConservationMetadata has validation_passed=True but veto_reasons is non-empty. "
                "Clearing veto_reasons."
            )
            # Convert to list to modify frozen dataclass
            object.__setattr__(self, 'veto_reasons', [])


@dataclass(frozen=True)
class ScenarioComponents:
    """
    Complete race scenario with all driver outcomes and metadata.

    This is the primary data structure for scenario generation. It contains
    the race-flow regime, all driver outcomes, and conservation validation
    metadata.

    Attributes:
        scenario_id: Unique identifier for this scenario (UUID or hash)
        regime: Race-flow regime for this scenario
        driver_outcomes: Dictionary mapping driver_id to DriverOutcome
        conservation_metadata: Conservation validation results

    Example:
        >>> scenario = ScenarioComponents(
        ...     scenario_id="scenario_abc123",
        ...     regime=RaceFlowRegime(n_cautions=5, pit_strategy=PitStrategy.STANDARD, ...),
        ...     driver_outcomes={"driver_123": DriverOutcome(...)},
        ...     conservation_metadata=ConservationMetadata(...)
        ... )
    """
    scenario_id: str
    regime: RaceFlowRegime
    driver_outcomes: Dict[str, DriverOutcome]
    conservation_metadata: ConservationMetadata

    def __post_init__(self):
        """Validate scenario components invariants."""
        # Must have at least one driver
        if not self.driver_outcomes:
            raise ValueError("Scenario must have at least one driver outcome")

        # Validate all driver outcomes exist
        for driver_id, outcome in self.driver_outcomes.items():
            if not isinstance(outcome, DriverOutcome):
                raise ValueError(
                    f"Driver {driver_id} outcome must be DriverOutcome, "
                    f"got {type(outcome)}"
                )
            if driver_id != outcome.driver_id:
                raise ValueError(
                    f"Driver ID mismatch: dict key '{driver_id}' != "
                    f"outcome.driver_id '{outcome.driver_id}'"
                )


def serialize_scenario(scenario: ScenarioComponents) -> dict:
    """
    Convert ScenarioComponents to JSON-serializable dictionary.

    Args:
        scenario: ScenarioComponents to serialize

    Returns:
        Dictionary with primitive types only (JSON-serializable)

    Example:
        >>> scenario = ScenarioComponents(...)
        >>> data = serialize_scenario(scenario)
        >>> import json
        >>> json.dumps(data)  # Should not raise TypeError
    """
    # Use dataclasses.asdict to convert nested dataclasses
    data = asdict(scenario)

    # Convert PitStrategy enum to string
    if 'regime' in data and 'pit_strategy' in data['regime']:
        data['regime']['pit_strategy'] = data['regime']['pit_strategy'].value

    # Convert DriverOutcome dataclasses to dicts
    if 'driver_outcomes' in data:
        for driver_id, outcome in data['driver_outcomes'].items():
            # outcome is already a dict from asdict
            pass

    logger.debug(f"Serialized scenario {scenario.scenario_id}")
    return data


def deserialize_scenario(data: dict) -> ScenarioComponents:
    """
    Reconstruct ScenarioComponents from dictionary.

    Args:
        data: Dictionary from serialize_scenario

    Returns:
        Reconstructed ScenarioComponents

    Raises:
        ValueError: If data is invalid or missing required fields

    Example:
        >>> data = serialize_scenario(scenario)
        >>> reconstructed = deserialize_scenario(data)
        >>> assert reconstructed.scenario_id == scenario.scenario_id
    """
    # Validate required fields
    required_fields = ['scenario_id', 'regime', 'driver_outcomes', 'conservation_metadata']
    for field_name in required_fields:
        if field_name not in data:
            raise ValueError(f"Missing required field: {field_name}")

    # Convert regime dict back to RaceFlowRegime
    regime_data = data['regime']
    # Convert pit_strategy string back to enum
    if 'pit_strategy' in regime_data:
        if isinstance(regime_data['pit_strategy'], str):
            regime_data['pit_strategy'] = PitStrategy(regime_data['pit_strategy'])
    regime = RaceFlowRegime(**regime_data)

    # Convert driver outcomes back to DriverOutcome
    driver_outcomes = {}
    for driver_id, outcome_data in data['driver_outcomes'].items():
        # Handle dnf_lap conversion (None vs present)
        if 'dnf_lap' in outcome_data and outcome_data['dnf_lap'] is None:
            # Keep as None
            pass
        driver_outcomes[driver_id] = DriverOutcome(**outcome_data)

    # Convert conservation metadata back to ConservationMetadata
    conservation_metadata = ConservationMetadata(**data['conservation_metadata'])

    # Reconstruct ScenarioComponents
    scenario = ScenarioComponents(
        scenario_id=data['scenario_id'],
        regime=regime,
        driver_outcomes=driver_outcomes,
        conservation_metadata=conservation_metadata
    )

    logger.debug(f"Deserialized scenario {scenario.scenario_id}")
    return scenario


def serialize_scenarios_to_parquet(
    scenarios: List[ScenarioComponents],
    path: str
) -> None:
    """
    Serialize list of scenarios to Parquet file.

    This function converts scenarios to a pandas DataFrame and writes
    to Parquet format for efficient storage and retrieval.

    Args:
        scenarios: List of ScenarioComponents to serialize
        path: Output file path for Parquet file

    Raises:
        ImportError: If PyArrow or pandas not available
        ValueError: If scenarios list is empty

    Example:
        >>> scenarios = [scenario1, scenario2, scenario3]
        >>> serialize_scenarios_to_parquet(scenarios, '/tmp/scenarios.parquet')
    """
    if not PARQUET_AVAILABLE:
        raise ImportError(
            "PyArrow and pandas required for Parquet serialization. "
            "Install with: pip install pyarrow pandas"
        )

    if not scenarios:
        raise ValueError("Cannot serialize empty scenarios list")

    # Convert scenarios to list of dicts
    records = []
    for scenario in scenarios:
        data = serialize_scenario(scenario)

        # Flatten regime into top-level fields
        regime = data.pop('regime')
        data['n_cautions'] = regime['n_cautions']
        data['pit_strategy'] = regime['pit_strategy']
        data['fuel_window_risk'] = regime['fuel_window_risk']
        data['late_race_chaos'] = regime['late_race_chaos']

        # Flatten conservation_metadata
        metadata = data.pop('conservation_metadata')
        data['total_laps_led'] = metadata['total_laps_led']
        data['total_fastest_laps'] = metadata['total_fastest_laps']
        data['green_flag_laps'] = metadata['green_flag_laps']
        data['validation_passed'] = metadata['validation_passed']
        # Convert veto_reasons list to JSON string for safe storage
        data['veto_reasons'] = json.dumps(metadata['veto_reasons'])

        # Driver outcomes as nested JSON string
        data['driver_outcomes'] = json.dumps(data['driver_outcomes'])

        records.append(data)

    # Create DataFrame
    df = pd.DataFrame(records)

    # Write to Parquet
    df.to_parquet(path, index=False, engine='pyarrow')

    logger.info(f"Serialized {len(scenarios)} scenarios to {path}")


def deserialize_scenarios_from_parquet(path: str) -> List[ScenarioComponents]:
    """
    Deserialize scenarios from Parquet file.

    Args:
        path: Path to Parquet file

    Returns:
        List of ScenarioComponents

    Raises:
        ImportError: If PyArrow or pandas not available
        ValueError: If file is invalid or scenarios cannot be reconstructed

    Example:
        >>> scenarios = deserialize_scenarios_from_parquet('/tmp/scenarios.parquet')
        >>> assert len(scenarios) > 0
    """
    if not PARQUET_AVAILABLE:
        raise ImportError(
            "PyArrow and pandas required for Parquet deserialization. "
            "Install with: pip install pyarrow pandas"
        )

    # Read Parquet file
    df = pd.read_parquet(path, engine='pyarrow')

    scenarios = []
    for _, row in df.iterrows():
        # Reconstruct regime
        regime = RaceFlowRegime(
            n_cautions=int(row['n_cautions']),
            pit_strategy=PitStrategy(row['pit_strategy']),
            fuel_window_risk=float(row['fuel_window_risk']),
            late_race_chaos=float(row['late_race_chaos'])
        )

        # Reconstruct driver outcomes from JSON
        driver_outcomes_data = json.loads(row['driver_outcomes'])
        driver_outcomes = {}
        for driver_id, outcome_data in driver_outcomes_data.items():
            driver_outcomes[driver_id] = DriverOutcome(**outcome_data)

        # Reconstruct conservation metadata
        # Parse veto_reasons from JSON string back to list
        veto_reasons_str = row['veto_reasons']
        if veto_reasons_str and veto_reasons_str != '[]':
            try:
                veto_reasons = json.loads(veto_reasons_str)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse veto_reasons JSON: {veto_reasons_str}")
                veto_reasons = []
        else:
            veto_reasons = []

        conservation_metadata = ConservationMetadata(
            total_laps_led=int(row['total_laps_led']),
            total_fastest_laps=int(row['total_fastest_laps']),
            green_flag_laps=int(row['green_flag_laps']),
            validation_passed=bool(row['validation_passed']),
            veto_reasons=veto_reasons
        )

        # Reconstruct scenario
        scenario = ScenarioComponents(
            scenario_id=str(row['scenario_id']),
            regime=regime,
            driver_outcomes=driver_outcomes,
            conservation_metadata=conservation_metadata
        )
        scenarios.append(scenario)

    logger.info(f"Deserialized {len(scenarios)} scenarios from {path}")
    return scenarios
