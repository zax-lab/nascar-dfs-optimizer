"""
Property-based tests for constraint invariants.

This module tests the constraint compilation system using property-based
testing to validate invariants across many examples.
"""
import pytest
from hypothesis import given, strategies as st
from typing import Dict, List
from unittest.mock import Mock
import tempfile
import os

from app.constraints.models import ConstraintSpec, DriverConstraints, TrackConstraints
from app.constraints.compiler import ConstraintCompiler
from app.constraints.versioning import version_from_constraints, create_run_config, save_run_config, load_run_config


# Property-based tests for DriverConstraints
@given(
    driver_id=st.text(min_size=1),
    skill=st.floats(min_value=0.0, max_value=1.0),
    aggression=st.floats(min_value=0.0, max_value=1.0),
    shadow_risk=st.floats(min_value=0.0, max_value=1.0),
    min_laps=st.integers(min_value=0, max_value=200),
    max_laps=st.integers(min_value=0, max_value=200)
)
def test_driver_constraints_valid_values(driver_id, skill, aggression, shadow_risk, min_laps, max_laps):
    """Test that DriverConstraints accepts valid values."""
    # Ensure min_laps <= max_laps
    if min_laps > max_laps:
        min_laps, max_laps = max_laps, min_laps

    dc = DriverConstraints(
        driver_id=driver_id,
        skill=skill,
        aggression=aggression,
        shadow_risk=shadow_risk,
        min_laps_led=min_laps,
        max_laps_led=max_laps,
        veto_rules=[]
    )

    assert dc.driver_id == driver_id
    assert dc.skill == skill
    assert dc.aggression == aggression
    assert dc.shadow_risk == shadow_risk
    assert dc.min_laps_led == min_laps
    assert dc.max_laps_led == max_laps


@given(st.floats(min_value=1.1, max_value=2.0))
def test_driver_constraints_rejects_invalid_skill(skill):
    """Test that DriverConstraints rejects skill > 1.0."""
    with pytest.raises(ValueError, match="skill must be in \\[0, 1\\]"):
        DriverConstraints(
            driver_id="test",
            skill=skill,
            aggression=0.5,
            shadow_risk=0.5,
            min_laps_led=0,
            max_laps_led=100
        )


@given(st.integers(min_value=-100, max_value=-1))
def test_driver_constraints_rejects_negative_min_laps(min_laps):
    """Test that DriverConstraints rejects negative min_laps_led."""
    with pytest.raises(ValueError, match="min_laps_led must be >= 0"):
        DriverConstraints(
            driver_id="test",
            skill=0.5,
            aggression=0.5,
            shadow_risk=0.5,
            min_laps_led=min_laps,
            max_laps_led=100
        )


# Property-based tests for TrackConstraints
@given(
    track_id=st.text(min_size=1),
    difficulty=st.floats(min_value=0.0, max_value=1.0),
    aggression_factor=st.floats(min_value=0.0, max_value=1.0),
    caution_rate=st.floats(min_value=0.0, max_value=1.0)
)
def test_track_constraints_valid_values(track_id, difficulty, aggression_factor, caution_rate):
    """Test that TrackConstraints accepts valid values."""
    tc = TrackConstraints(
        track_id=track_id,
        difficulty=difficulty,
        aggression_factor=aggression_factor,
        caution_rate=caution_rate,
        pit_window_laps=[35, 70, 105]
    )

    assert tc.track_id == track_id
    assert tc.difficulty == difficulty
    assert tc.aggression_factor == aggression_factor
    assert tc.caution_rate == caution_rate


@given(st.floats(min_value=1.1, max_value=2.0))
def test_track_constraints_rejects_invalid_difficulty(difficulty):
    """Test that TrackConstraints rejects difficulty > 1.0."""
    with pytest.raises(ValueError, match="difficulty must be in \\[0, 1\\]"):
        TrackConstraints(
            track_id="test",
            difficulty=difficulty,
            aggression_factor=0.5,
            caution_rate=0.05
        )


# Property-based tests for ConstraintSpec
def test_constraint_spec_immutability():
    """Test that ConstraintSpec is immutable (frozen dataclass)."""
    spec = ConstraintSpec(
        slate_id="test",
        compiled_at="2024-01-01T00:00:00",
        drivers={"d1": DriverConstraints("d1", 0.5, 0.5, 0.5, 0, 100, [])},
        tracks={"t1": TrackConstraints("t1", 0.5, 0.5, 0.05, [35, 70])},
        version="1.0"
    )

    # Frozen dataclass prevents replacing attribute references
    from dataclasses import FrozenInstanceError
    with pytest.raises(FrozenInstanceError):
        spec.drivers = {}

    with pytest.raises(FrozenInstanceError):
        spec.tracks = {}

    with pytest.raises(FrozenInstanceError):
        spec.version = "2.0"

    # Note: The frozen dataclass prevents attribute reassignment,
    # but nested mutable objects (dicts) can still be modified.
    # The hash is computed once at creation time, which is the key guarantee.


def test_constraint_spec_hash_determinism():
    """Test that ConstraintSpec produces deterministic hash."""
    spec1 = ConstraintSpec(
        slate_id="test",
        compiled_at="2024-01-01T00:00:00",
        drivers={"d1": DriverConstraints("d1", 0.5, 0.5, 0.5, 0, 100, [])},
        tracks={"t1": TrackConstraints("t1", 0.5, 0.5, 0.05, [35, 70])},
        version="1.0"
    )

    spec2 = ConstraintSpec(
        slate_id="test",
        compiled_at="2024-01-01T00:00:00",
        drivers={"d1": DriverConstraints("d1", 0.5, 0.5, 0.5, 0, 100, [])},
        tracks={"t1": TrackConstraints("t1", 0.5, 0.5, 0.05, [35, 70])},
        version="1.0"
    )

    assert spec1.hash == spec2.hash, "Same spec should produce same hash"


def test_constraint_spec_get_driver_constraints():
    """Test get_driver_constraints method."""
    spec = ConstraintSpec(
        slate_id="test",
        compiled_at="2024-01-01T00:00:00",
        drivers={"d1": DriverConstraints("d1", 0.5, 0.5, 0.5, 0, 100, [])},
        tracks={"t1": TrackConstraints("t1", 0.5, 0.5, 0.05, [35, 70])},
        version="1.0"
    )

    dc = spec.get_driver_constraints("d1")
    assert dc.driver_id == "d1"
    assert dc.skill == 0.5

    with pytest.raises(KeyError, match="Driver d2 not found"):
        spec.get_driver_constraints("d2")


# Property-based tests for versioning
def test_version_from_constraints_determinism():
    """Test that version_from_constraints is deterministic."""
    spec = ConstraintSpec(
        slate_id="test",
        compiled_at="2024-01-01T00:00:00",
        drivers={"d1": DriverConstraints("d1", 0.5, 0.5, 0.5, 0, 100, [])},
        tracks={"t1": TrackConstraints("t1", 0.5, 0.5, 0.05, [35, 70])},
        version="1.0"
    )

    v1 = version_from_constraints(spec)
    v2 = version_from_constraints(spec)

    assert v1 == v2
    assert len(v1) == 64  # SHA-256 hex digest


def test_run_config_round_trip():
    """Test that RunConfig can be saved and loaded."""
    spec = ConstraintSpec(
        slate_id="test",
        compiled_at="2024-01-01T00:00:00",
        drivers={"d1": DriverConstraints("d1", 0.5, 0.5, 0.5, 0, 100, [])},
        tracks={"t1": TrackConstraints("t1", 0.5, 0.5, 0.05, [35, 70])},
        version="1.0"
    )

    config = create_run_config(spec, {"n_scenarios": 100}, 42)

    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        path = f.name

    try:
        save_run_config(config, path)
        loaded = load_run_config(path)

        assert loaded.run_id == config.run_id
        assert loaded.constraint_spec_hash == config.constraint_spec_hash
        assert loaded.random_seed == config.random_seed
        assert loaded.sim_params == config.sim_params
    finally:
        os.unlink(path)


def test_run_config_validation():
    """Test that RunConfig validates inputs."""
    spec = ConstraintSpec(
        slate_id="test",
        compiled_at="2024-01-01T00:00:00",
        drivers={"d1": DriverConstraints("d1", 0.5, 0.5, 0.5, 0, 100, [])},
        tracks={"t1": TrackConstraints("t1", 0.5, 0.5, 0.05, [35, 70])},
        version="1.0"
    )

    # Negative n_scenarios should fail
    with pytest.raises(ValueError, match="n_scenarios must be positive"):
        create_run_config(spec, {"n_scenarios": -10}, 42)

    # Negative random_seed should fail
    with pytest.raises(ValueError, match="random_seed must be a positive integer"):
        create_run_config(spec, {"n_scenarios": 100}, -5)


# Performance test for batch query compilation
def test_batch_query_performance():
    """Test that batch query compilation is fast."""
    from app.ontology import OntologyDriver

    # Create mock OntologyDriver
    mock_neo4j_driver = Mock()
    mock_ontology = Mock(spec=OntologyDriver)
    mock_ontology._driver = mock_neo4j_driver

    # Mock batch query for 40 drivers
    # Use a factory function to avoid closure issues
    def make_driver_record(i):
        data = {
            'driver_id': f'driver_{i}',
            'skill': 0.5,
            'aggression': 0.5,
            'shadow_risk': 0.5,
            'veto_rules': []
        }
        return Mock(**{'__getitem__': lambda self, key, d=data: d[key]})

    records = [make_driver_record(i) for i in range(40)]

    mock_result = Mock()
    mock_result.records = records
    mock_neo4j_driver.execute_query = Mock(return_value=mock_result)

    compiler = ConstraintCompiler(mock_ontology)

    import time
    start = time.time()
    drivers = compiler.compile_driver_constraints([f"driver_{i}" for i in range(40)])
    duration = time.time() - start

    assert len(drivers) == 40
    assert duration < 0.1, f"Batch query too slow: {duration*1000:.2f}ms (should be <100ms)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
