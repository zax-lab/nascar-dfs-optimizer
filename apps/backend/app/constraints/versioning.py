"""
Run configuration versioning for reproducible simulation/optimization runs.

This module provides versioning and persistence for run configurations,
enabling reproducible simulation and optimization runs with frozen constraints.

Key concepts:
- Deterministic hashing of ConstraintSpec for versioning
- RunConfig captures all parameters for a simulation/optimization run
- Save/load functionality for run configuration persistence
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
from datetime import datetime
import hashlib
import json
import logging

from app.constraints.models import ConstraintSpec

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunConfig:
    """
    Immutable run configuration for reproducible simulation/optimization.

    Captures all parameters needed to reproduce a simulation or optimization run,
    including the constraint specification hash and simulation parameters.

    Attributes:
        run_id: Unique run identifier (timestamp + constraint spec hash)
        constraint_spec_hash: SHA-256 hash of the ConstraintSpec used
        sim_params: Simulation parameters (n_scenarios, field_size, race_length, etc.)
        created_at: ISO timestamp of run config creation
        random_seed: Random seed for reproducible randomness
    """
    run_id: str
    constraint_spec_hash: str
    sim_params: Dict[str, Any]
    created_at: str
    random_seed: int

    def __post_init__(self):
        """Validate run configuration after initialization."""
        # Validate random_seed is positive integer
        if not isinstance(self.random_seed, int) or self.random_seed <= 0:
            raise ValueError(
                f"random_seed must be a positive integer, got {self.random_seed}"
            )

        # Validate sim_params has required fields
        required_fields = ["n_scenarios"]
        for field in required_fields:
            if field not in self.sim_params:
                raise ValueError(f"sim_params missing required field: {field}")

        # Validate n_scenarios is positive
        if self.sim_params["n_scenarios"] <= 0:
            raise ValueError(
                f"sim_params.n_scenarios must be positive, got {self.sim_params['n_scenarios']}"
            )


def version_from_constraints(spec: ConstraintSpec) -> str:
    """
    Compute deterministic version hash from constraint specification.

    Serializes the constraint spec to JSON with sorted keys and computes
    SHA-256 hash. The same spec always produces the same hash.

    Args:
        spec: ConstraintSpec to version

    Returns:
        SHA-256 hex digest as version string

    Example:
        >>> spec = ConstraintSpec(...)
        >>> version = version_from_constraints(spec)
        >>> assert len(version) == 64  # SHA-256 hex digest
    """
    # Serialize constraint spec to dict (already has computed hash)
    spec_dict = {
        "slate_id": spec.slate_id,
        "drivers": {
            driver_id: {
                "skill": dc.skill,
                "aggression": dc.aggression,
                "shadow_risk": dc.shadow_risk,
                "min_laps_led": dc.min_laps_led,
                "max_laps_led": dc.max_laps_led,
                "veto_rules": sorted(dc.veto_rules),
            }
            for driver_id, dc in sorted(spec.drivers.items())
        },
        "tracks": {
            track_id: {
                "difficulty": tc.difficulty,
                "aggression_factor": tc.aggression_factor,
                "caution_rate": tc.caution_rate,
                "pit_window_laps": tc.pit_window_laps,
            }
            for track_id, tc in sorted(spec.tracks.items())
        },
    }

    # Serialize to JSON with sorted keys for determinism
    json_str = json.dumps(spec_dict, sort_keys=True)

    # Compute SHA-256 hash
    version_hash = hashlib.sha256(json_str.encode()).hexdigest()

    logger.debug(f"Computed version hash: {version_hash[:16]}...")
    return version_hash


def create_run_config(
    spec: ConstraintSpec,
    sim_params: Dict[str, Any],
    random_seed: Optional[int] = None
) -> RunConfig:
    """
    Create a run configuration from constraint specification and simulation parameters.

    Computes constraint spec hash and generates run_id for the configuration.

    Args:
        spec: ConstraintSpec for this run
        sim_params: Simulation parameters dictionary
            - n_scenarios (required): Number of scenarios to generate
            - field_size (optional): DFS field size
            - race_length (optional): Race length in laps
        random_seed: Random seed for reproducibility (default: current timestamp)

    Returns:
        Frozen RunConfig with computed run_id

    Example:
        >>> spec = ConstraintSpec(...)
        >>> config = create_run_config(spec, {"n_scenarios": 1000}, 42)
        >>> print(config.run_id)
    """
    # Compute constraint spec hash
    constraint_spec_hash = version_from_constraints(spec)

    # Generate random seed if not provided
    if random_seed is None:
        random_seed = int(datetime.utcnow().timestamp())

    # Generate run_id from timestamp + constraint hash
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    run_id = f"run_{timestamp}_{constraint_spec_hash[:8]}"

    # Create run config
    config = RunConfig(
        run_id=run_id,
        constraint_spec_hash=constraint_spec_hash,
        sim_params=sim_params,
        created_at=datetime.utcnow().isoformat() + "Z",
        random_seed=random_seed
    )

    logger.info(
        f"Created run config {run_id} with constraint hash {constraint_spec_hash[:16]}... "
        f"and seed {random_seed}"
    )

    return config


def save_run_config(config: RunConfig, path: str) -> None:
    """
    Save run configuration to JSON file.

    Serializes the run configuration to JSON with pretty formatting
    and writes to the specified path.

    Args:
        config: RunConfig to save
        path: File path to save to

    Raises:
        IOError: If file cannot be written

    Example:
        >>> config = create_run_config(spec, {"n_scenarios": 1000}, 42)
        >>> save_run_config(config, "/path/to/config.json")
    """
    try:
        # Convert to dict for JSON serialization
        config_dict = asdict(config)

        # Write to file with pretty formatting
        with open(path, "w") as f:
            json.dump(config_dict, f, indent=2, sort_keys=True)

        logger.info(f"Saved run config {config.run_id} to {path}")

    except Exception as e:
        logger.error(f"Failed to save run config to {path}: {e}")
        raise IOError(f"Failed to save run config: {e}")


def load_run_config(path: str) -> RunConfig:
    """
    Load run configuration from JSON file.

    Reads and deserializes a run configuration from the specified path,
    validating the constraint_spec_hash format.

    Args:
        path: File path to load from

    Returns:
        RunConfig loaded from file

    Raises:
        IOError: If file cannot be read
        ValueError: If config is invalid

    Example:
        >>> config = load_run_config("/path/to/config.json")
        >>> print(config.run_id)
    """
    try:
        # Read from file
        with open(path, "r") as f:
            config_dict = json.load(f)

        # Validate constraint_spec_hash format
        constraint_hash = config_dict.get("constraint_spec_hash", "")
        if len(constraint_hash) != 64:
            raise ValueError(
                f"Invalid constraint_spec_hash format: expected 64 chars, got {len(constraint_hash)}"
            )

        # Reconstruct RunConfig
        config = RunConfig(**config_dict)

        logger.info(f"Loaded run config {config.run_id} from {path}")

        return config

    except FileNotFoundError:
        logger.error(f"Run config file not found: {path}")
        raise IOError(f"Run config file not found: {path}")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in run config file {path}: {e}")
        raise ValueError(f"Invalid JSON in run config file: {e}")
    except Exception as e:
        logger.error(f"Failed to load run config from {path}: {e}")
        raise
