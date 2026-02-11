"""
Integration tests for scenario generation pipeline.

This test module validates the end-to-end scenario generation flow:
- Mock CBN creation with ontology priors
- SkeletonNarrative scenario generation
- Kernel post-validation for conservation
- Serialization/deserialization
- Race-flow regime diversity
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import List, Dict

# Import modules to test
import sys
from pathlib import Path

# Add package to path
package_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(package_path))

from axiomatic_sim.scenario_generator import (
    create_mock_cbn,
    SkeletonNarrative,
    generate_scenarios,
)
from axiomatic_sim.cbn import CausalBayesianNetwork
from axiomatic_sim.ontology_constraints import OntologyConstraints
from axiomatic_sim.narrative import (
    RaceFlowRegime,
    ScenarioComponents,
    DriverOutcome,
    ConservationMetadata,
    PitStrategy,
    serialize_scenario,
    deserialize_scenario,
    serialize_scenarios_to_parquet,
    deserialize_scenarios_from_parquet,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_ontology_constraints():
    """Create mock OntologyConstraints with fixed priors."""
    mock_ontology = Mock(spec=OntologyConstraints)
    mock_ontology.get_driver_priors = Mock(return_value={
        'skill': 0.7,
        'aggression': 0.5,
        'shadow_risk': 0.3,
    })
    mock_ontology._track_difficulty_cache = {'test_track': 0.6}
    mock_ontology.get_veto_rules = Mock(return_value=[])

    return mock_ontology


@pytest.fixture
def driver_ids():
    """Provide list of test driver IDs."""
    return [f"driver_{i}" for i in range(1, 41)]


@pytest.fixture
def mock_cbn(mock_ontology_constraints, driver_ids):
    """Create mock CBN with fixed structure."""
    return create_mock_cbn(mock_ontology_constraints, driver_ids)


@pytest.fixture
def mock_kernel():
    """Create mock KernelLogic for testing."""
    mock_kernel = Mock()
    mock_kernel.validate_dominator_conservation = Mock(return_value=MagicMock(
        is_valid=True,
        laps_led_valid=True,
        fastest_laps_valid=True,
        position_swaps_valid=True,
        veto_reasons=[]
    ))
    mock_kernel.field_size = 40
    return mock_kernel


# ============================================================================
# Tests: Task 1 - Scenario Generation Produces Valid Scenarios
# ============================================================================

def test_scenario_generation_produces_valid_scenarios(
    mock_cbn, mock_ontology_constraints, mock_kernel
):
    """Test that generated scenarios pass kernel conservation validation."""
    # Given: Mock CBN, OntologyConstraints, and KernelLogic
    generator = SkeletonNarrative(
        cbn=mock_cbn,
        ontology_constraints=mock_ontology_constraints,
        track_id='test_track',
        field_size=40,
        kernel=mock_kernel,
    )

    # When: Generate 10 scenarios
    scenarios = generator.generate_scenarios(n_scenarios=10)

    # Then: All scenarios should pass kernel conservation validation
    assert len(scenarios) == 10, "Should generate 10 scenarios"

    for scenario in scenarios:
        assert isinstance(scenario, ScenarioComponents), "Should be ScenarioComponents"
        assert scenario.conservation_metadata.validation_passed, \
            "All scenarios should pass kernel validation"
        assert len(scenario.conservation_metadata.veto_reasons) == 0, \
            "Valid scenarios should have no veto reasons"

    # Verify kernel was called for each scenario
    assert mock_kernel.validate_dominator_conservation.call_count == 10, \
        "Kernel should validate each scenario"


# ============================================================================
# Tests: Task 2 - Scenario Count Target Met
# ============================================================================

def test_scenario_count_target_met(
    mock_cbn, mock_ontology_constraints, mock_kernel
):
    """Test that exactly n_scenarios are generated."""
    # Given: Mock CBN, OntologyConstraints, and KernelLogic
    generator = SkeletonNarrative(
        cbn=mock_cbn,
        ontology_constraints=mock_ontology_constraints,
        track_id='test_track',
        field_size=40,
        kernel=mock_kernel,
    )

    # When: Request 100 scenarios
    scenarios = generator.generate_scenarios(n_scenarios=100)

    # Then: Exactly 100 valid scenarios returned
    assert len(scenarios) == 100, "Should generate exactly 100 scenarios"


# ============================================================================
# Tests: Task 3 - Laps Led Conservation
# ============================================================================

def test_laps_led_conservation(mock_cbn, mock_ontology_constraints):
    """Test that laps_led is conserved (sum ≤ race_length)."""
    # Given: Generator without kernel (to test raw generation)
    generator = SkeletonNarrative(
        cbn=mock_cbn,
        ontology_constraints=mock_ontology_constraints,
        track_id='test_track',
        field_size=40,
        kernel=None,  # No kernel for raw generation test
    )

    # When: Generate 10 scenarios
    scenarios = generator.generate_scenarios(n_scenarios=10)

    # Then: Total laps_led ≤ race_length for each scenario
    for scenario in scenarios:
        total_laps_led = sum(
            outcome.laps_led for outcome in scenario.driver_outcomes.values()
        )

        assert total_laps_led <= 200, \
            f"Total laps_led ({total_laps_led}) must be ≤ race_length (200)"
        assert total_laps_led == scenario.conservation_metadata.total_laps_led, \
            "Metadata should match computed total"


# ============================================================================
# Tests: Task 4 - Fastest Laps Conservation
# ============================================================================

def test_fastest_laps_conservation(mock_cbn, mock_ontology_constraints):
    """Test that fastest_laps is conserved (sum ≤ green_flag_laps)."""
    # Given: Generator without kernel
    generator = SkeletonNarrative(
        cbn=mock_cbn,
        ontology_constraints=mock_ontology_constraints,
        track_id='test_track',
        field_size=40,
        kernel=None,
    )

    # When: Generate 10 scenarios
    scenarios = generator.generate_scenarios(n_scenarios=10)

    # Then: Total fastest_laps ≤ green_flag_laps for each scenario
    for scenario in scenarios:
        total_fastest_laps = sum(
            outcome.fastest_laps for outcome in scenario.driver_outcomes.values()
        )
        green_flag_laps = scenario.conservation_metadata.green_flag_laps

        assert total_fastest_laps <= green_flag_laps, \
            f"Total fastest_laps ({total_fastest_laps}) must be ≤ green_flag_laps ({green_flag_laps})"
        assert total_fastest_laps == scenario.conservation_metadata.total_fastest_laps, \
            "Metadata should match computed total"


# ============================================================================
# Tests: Task 5 - Race Flow Regime Diversity
# ============================================================================

def test_race_flow_regime_diversity(mock_cbn, mock_ontology_constraints):
    """Test that race-flow regimes vary across scenarios."""
    # Given: Generator
    generator = SkeletonNarrative(
        cbn=mock_cbn,
        ontology_constraints=mock_ontology_constraints,
        track_id='test_track',
        field_size=40,
        kernel=None,
    )

    # When: Generate 100 scenarios
    scenarios = generator.generate_scenarios(n_scenarios=100)

    # Then: n_cautions should have variance > 0
    caution_counts = [s.regime.n_cautions for s in scenarios]
    unique_caution_counts = set(caution_counts)

    assert len(unique_caution_counts) > 1, \
        "Scenarios should have varied caution counts (variance > 0)"

    # Verify pit strategies also vary
    pit_strategies = [s.regime.pit_strategy for s in scenarios]
    unique_pit_strategies = set(pit_strategies)

    assert len(unique_pit_strategies) >= 2, \
        "Scenarios should use multiple pit strategies"


# ============================================================================
# Tests: Task 6 - Scenario Serialization Roundtrip
# ============================================================================

def test_scenario_serialization_roundtrip():
    """Test that serialize/deserialize preserves all data."""
    # Given: Sample scenario
    regime = RaceFlowRegime(
        n_cautions=5,
        pit_strategy=PitStrategy.STANDARD,
        fuel_window_risk=0.3,
        late_race_chaos=0.4,
    )

    driver_outcomes = {
        "driver_1": DriverOutcome(
            driver_id="driver_1",
            laps_led=50,
            fastest_laps=10,
            finish_position=5,
            place_differential=-5,
            incident=False,
            dnf_lap=None,
        ),
        "driver_2": DriverOutcome(
            driver_id="driver_2",
            laps_led=30,
            fastest_laps=5,
            finish_position=10,
            place_differential=0,
            incident=True,
            dnf_lap=None,
        ),
    }

    conservation_metadata = ConservationMetadata(
        total_laps_led=200,
        total_fastest_laps=50,
        green_flag_laps=180,
        validation_passed=True,
        veto_reasons=[],
    )

    original_scenario = ScenarioComponents(
        scenario_id="test_scenario_123",
        regime=regime,
        driver_outcomes=driver_outcomes,
        conservation_metadata=conservation_metadata,
    )

    # When: Serialize to dict, deserialize back
    serialized = serialize_scenario(original_scenario)
    deserialized = deserialize_scenario(serialized)

    # Then: Deserialized scenario equals original
    assert deserialized.scenario_id == original_scenario.scenario_id, \
        "scenario_id should match"
    assert deserialized.regime.n_cautions == original_scenario.regime.n_cautions, \
        "n_cautions should match"
    assert deserialized.regime.pit_strategy == original_scenario.regime.pit_strategy, \
        "pit_strategy should match"
    assert deserialized.regime.fuel_window_risk == original_scenario.regime.fuel_window_risk, \
        "fuel_window_risk should match"
    assert deserialized.regime.late_race_chaos == original_scenario.regime.late_race_chaos, \
        "late_race_chaos should match"

    # Check driver outcomes
    assert len(deserialized.driver_outcomes) == len(original_scenario.driver_outcomes), \
        "Should have same number of driver outcomes"

    for driver_id in original_scenario.driver_outcomes:
        orig = original_scenario.driver_outcomes[driver_id]
        deser = deserialized.driver_outcomes[driver_id]

        assert deser.driver_id == orig.driver_id
        assert deser.laps_led == orig.laps_led
        assert deser.fastest_laps == orig.fastest_laps
        assert deser.finish_position == orig.finish_position
        assert deser.place_differential == orig.place_differential
        assert deser.incident == orig.incident
        assert deser.dnf_lap == orig.dnf_lap

    # Check conservation metadata
    assert deserialized.conservation_metadata.total_laps_led == \
        original_scenario.conservation_metadata.total_laps_led
    assert deserialized.conservation_metadata.total_fastest_laps == \
        original_scenario.conservation_metadata.total_fastest_laps
    assert deserialized.conservation_metadata.green_flag_laps == \
        original_scenario.conservation_metadata.green_flag_laps
    assert deserialized.conservation_metadata.validation_passed == \
        original_scenario.conservation_metadata.validation_passed


# ============================================================================
# Tests: Task 7 - Kernel Post-Validation Called
# ============================================================================

def test_kernel_post_validation_called(mock_cbn, mock_ontology_constraints, mock_kernel):
    """Test that kernel.validate_dominator_conservation is called for each scenario."""
    # Given: SkeletonNarrative with mock kernel
    generator = SkeletonNarrative(
        cbn=mock_cbn,
        ontology_constraints=mock_ontology_constraints,
        track_id='test_track',
        field_size=40,
        kernel=mock_kernel,
    )

    # When: Generate 10 scenarios
    scenarios = generator.generate_scenarios(n_scenarios=10)

    # Then: kernel.validate_dominator_conservation called for each scenario
    assert mock_kernel.validate_dominator_conservation.call_count == 10, \
        f"Kernel should validate each scenario (expected 10, got {mock_kernel.validate_dominator_conservation.call_count})"

    # Verify the kernel received proper data format
    for call in mock_kernel.validate_dominator_conservation.call_args_list:
        scenario_dict = call[0][0]  # First argument

        # Check required fields
        assert 'laps_led' in scenario_dict, "Should have laps_led"
        assert 'fastest_laps' in scenario_dict, "Should have fastest_laps"
        assert 'start_positions' in scenario_dict, "Should have start_positions"
        assert 'finish_positions' in scenario_dict, "Should have finish_positions"
        assert 'race_length' in scenario_dict, "Should have race_length"
        assert 'green_flag_laps' in scenario_dict, "Should have green_flag_laps"


# ============================================================================
# Tests: create_mock_cbn Function
# ============================================================================

def test_create_mock_cbn_structure(mock_ontology_constraints, driver_ids):
    """Test that create_mock_cbn creates valid CBN structure."""
    # When: Create mock CBN
    cbn = create_mock_cbn(mock_ontology_constraints, driver_ids)

    # Then: Should return CausalBayesianNetwork
    assert isinstance(cbn, CausalBayesianNetwork), \
        "Should return CausalBayesianNetwork instance"

    # Check structure has expected nodes
    for driver_id in driver_ids[:3]:  # Check first 3 drivers
        assert f"{driver_id}_skill" in cbn.structure.nodes, \
            f"Should have {driver_id}_skill node"
        assert f"{driver_id}_laps_led" in cbn.structure.nodes, \
            f"Should have {driver_id}_laps_led node"
        assert f"{driver_id}_fastest_laps" in cbn.structure.nodes, \
            f"Should have {driver_id}_fastest_laps node"
        assert f"{driver_id}_finish_position" in cbn.structure.nodes, \
            f"Should have {driver_id}_finish_position node"
        assert f"{driver_id}_incident" in cbn.structure.nodes, \
            f"Should have {driver_id}_incident node"

    # Check expected edges exist (domain knowledge edges)
    # skill -> laps_led
    assert cbn.structure.has_edge(f"{driver_ids[0]}_skill", f"{driver_ids[0]}_laps_led"), \
        "Should have skill -> laps_led edge"

    # skill -> fastest_laps
    assert cbn.structure.has_edge(f"{driver_ids[0]}_skill", f"{driver_ids[0]}_fastest_laps"), \
        "Should have skill -> fastest_laps edge"

    # aggression -> incident
    assert cbn.structure.has_edge(f"{driver_ids[0]}_aggression", f"{driver_ids[0]}_incident"), \
        "Should have aggression -> incident edge"


def test_create_mock_cbn_uses_priors(mock_ontology_constraints, driver_ids):
    """Test that create_mock_cbn uses ontology priors."""
    # When: Create mock CBN
    cbn = create_mock_cbn(mock_ontology_constraints, driver_ids)

    # Then: Ontology get_driver_priors should have been called
    assert mock_ontology_constraints.get_driver_priors.called, \
        "Should fetch driver priors from ontology"


# ============================================================================
# Tests: generate_scenarios Standalone Function
# ============================================================================

def test_generate_scenarios_standalone():
    """Test generate_scenarios standalone function."""
    # When: Generate scenarios using standalone function
    scenarios = generate_scenarios(
        track_id='test_track',
        n_scenarios=10,
        ontology_driver=None,  # Use mock ontology
        kernel=None,  # No kernel for testing
    )

    # Then: Should return scenarios
    assert len(scenarios) == 10, "Should generate 10 scenarios"

    for scenario in scenarios:
        assert isinstance(scenario, ScenarioComponents), \
            "Should return ScenarioComponents"


# ============================================================================
# Tests: RaceFlowRegime Sampling
# ============================================================================

def test_sample_race_flow_regime_bounds(mock_cbn, mock_ontology_constraints):
    """Test that sampled race-flow regimes respect bounds."""
    # Given: Generator
    generator = SkeletonNarrative(
        cbn=mock_cbn,
        ontology_constraints=mock_ontology_constraints,
        track_id='test_track',
        field_size=40,
        kernel=None,
    )

    # When: Sample many regimes
    regimes = [generator.sample_race_flow_regime() for _ in range(100)]

    # Then: All regimes should respect bounds
    for regime in regimes:
        assert 0 <= regime.n_cautions <= 10, \
            f"n_cautions ({regime.n_cautions}) must be in [0, 10]"
        assert isinstance(regime.pit_strategy, PitStrategy), \
            "pit_strategy must be PitStrategy enum"
        assert 0.0 <= regime.fuel_window_risk <= 1.0, \
            f"fuel_window_risk ({regime.fuel_window_risk}) must be in [0, 1]"
        assert 0.0 <= regime.late_race_chaos <= 1.0, \
            f"late_race_chaos ({regime.late_race_chaos}) must be in [0, 1]"


# ============================================================================
# Tests: Feasible-by-Design Conservation
# ============================================================================

def test_feasible_by_design_laps_led(mock_cbn, mock_ontology_constraints):
    """Test that Dirichlet sampling ensures laps_led conservation."""
    # Given: Generator
    generator = SkeletonNarrative(
        cbn=mock_cbn,
        ontology_constraints=mock_ontology_constraints,
        track_id='test_track',
        field_size=40,
        kernel=None,
    )

    # When: Generate many scenarios
    scenarios = generator.generate_scenarios(n_scenarios=50)

    # Then: All scenarios should have laps_led summing to race_length
    # (feasible-by-design should make this always true)
    violations = 0
    for scenario in scenarios:
        total_laps_led = sum(
            outcome.laps_led for outcome in scenario.driver_outcomes.values()
        )
        if total_laps_led > 200:  # race_length
            violations += 1

    assert violations == 0, \
        f"Feasible-by-design sampling should prevent laps_led violations (found {violations})"


# ============================================================================
# Tests: Kernel Validation Rejection
# ============================================================================

def test_kernel_validation_rejection(mock_cbn, mock_ontology_constraints):
    """Test that scenarios failing kernel validation are rejected."""
    # Given: Mock kernel that rejects all scenarios
    mock_kernel_reject = Mock()
    mock_kernel_reject.validate_dominator_conservation = Mock(return_value=MagicMock(
        is_valid=False,
        laps_led_valid=False,
        fastest_laps_valid=True,
        position_swaps_valid=True,
        veto_reasons=["Laps led conservation violated"]
    ))

    generator = SkeletonNarrative(
        cbn=mock_cbn,
        ontology_constraints=mock_ontology_constraints,
        track_id='test_track',
        field_size=40,
        kernel=mock_kernel_reject,
    )

    # When: Try to generate scenarios
    scenarios = generator.generate_scenarios(n_scenarios=10)

    # Then: Should return fewer than 10 scenarios (all rejected)
    # Note: The implementation has max_attempts = n_scenarios * 3
    # So if all are rejected, we get 0 scenarios
    assert len(scenarios) == 0, \
        "Should reject all scenarios when kernel validation fails"
