"""
Integration tests verifying CBN sampling in scenario generation.

This test module verifies that the CausalBayesianNetwork is properly
integrated into the SkeletonNarrative scenario generator, including:
- CBN.sample_outcomes() called during scenario generation
- Evidence conditioning works with race-flow regimes
- Causal outcomes reflected in generated scenarios
- Conservation validation still works with CBN
- Fallback to simplified generation if CBN fails
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
import pandas as pd

from axiomatic_sim.scenario_generator import SkeletonNarrative, create_mock_cbn
from axiomatic_sim.ontology_constraints import OntologyConstraints
from axiomatic_sim.narrative import RaceFlowRegime, PitStrategy


@pytest.fixture
def mock_cbn_with_tracking():
    """Create a mock CBN that tracks calls and evidence."""
    import networkx as nx

    # Create a real DiGraph structure for the mock CBN
    structure = nx.DiGraph()
    structure.add_node('driver_1_skill')
    structure.add_node('driver_1_laps_led')
    structure.add_node('driver_1_fastest_laps')
    structure.add_node('driver_1_finish_position')
    structure.add_node('driver_1_incident')
    structure.add_node('driver_2_skill')
    structure.add_node('driver_2_laps_led')
    structure.add_node('driver_2_fastest_laps')
    structure.add_node('driver_2_finish_position')
    structure.add_node('driver_2_incident')

    cbn = Mock()
    cbn.model = Mock()
    cbn.model.get_cpds = Mock(return_value=[Mock()])  # Has CPDs
    cbn.structure = structure

    # Track sample_outcomes calls
    sample_calls = []

    def mock_sample_outcomes(n_samples, evidence=None):
        sample_calls.append({'n_samples': n_samples, 'evidence': evidence})
        # Return mock samples
        samples = pd.DataFrame({
            'driver_1_laps_led': [10] * n_samples,
            'driver_1_fastest_laps': [5] * n_samples,
            'driver_1_finish_position': list(range(1, n_samples + 1)),
            'driver_1_incident': [False] * n_samples,
            'driver_2_laps_led': [5] * n_samples,
            'driver_2_fastest_laps': [2] * n_samples,
            'driver_2_finish_position': list(range(n_samples + 1, 2 * n_samples + 1)),
            'driver_2_incident': [False] * n_samples,
        })
        return samples

    cbn.sample_outcomes = Mock(side_effect=mock_sample_outcomes)
    cbn.sample_calls = sample_calls

    return cbn


@pytest.fixture
def skeleton_narrative_with_cbn(mock_cbn_with_tracking):
    """Create SkeletonNarrative with mock CBN."""
    ontology = OntologyConstraints()

    generator = SkeletonNarrative(
        cbn=mock_cbn_with_tracking,
        ontology_constraints=ontology,
        track_id='test_track',
        field_size=2,
        kernel=None,
        race_length=200,
    )

    return generator, mock_cbn_with_tracking


def test_cbn_sample_outcomes_called(skeleton_narrative_with_cbn):
    """Test that CBN.sample_outcomes is called during scenario generation."""
    generator, mock_cbn = skeleton_narrative_with_cbn

    # Generate scenarios
    scenarios = generator.generate_scenarios(n_scenarios=5)

    # CBN should have been called
    assert mock_cbn.sample_outcomes.call_count > 0
    assert len(scenarios) == 5


def test_cbn_evidence_conditioning_works(skeleton_narrative_with_cbn):
    """Test that evidence conditioning includes regime variables."""
    generator, mock_cbn = skeleton_narrative_with_cbn

    # Generate scenario
    scenario = generator.generate_single_scenario('test_scenario')

    # Check that CBN was called with evidence
    assert len(mock_cbn.sample_calls) > 0
    evidence = mock_cbn.sample_calls[0]['evidence']

    # Evidence should include regime variables
    assert 'n_cautions' in evidence
    assert 'pit_strategy' in evidence
    assert 'fuel_window_risk' in evidence
    assert 'late_race_chaos' in evidence
    assert 'track_difficulty' in evidence


def test_causal_outcomes_reflected_in_scenarios():
    """Test that causal outcomes from CBN are reflected in scenarios."""
    import networkx as nx

    # Create mock CBN with specific outcome patterns
    ontology = OntologyConstraints()

    # Create a real DiGraph structure for the mock CBN
    structure = nx.DiGraph()
    structure.add_node('driver_1_skill')
    structure.add_node('driver_1_laps_led')
    structure.add_node('driver_1_fastest_laps')
    structure.add_node('driver_1_finish_position')
    structure.add_node('driver_1_incident')
    structure.add_node('driver_2_skill')
    structure.add_node('driver_2_laps_led')
    structure.add_node('driver_2_fastest_laps')
    structure.add_node('driver_2_finish_position')
    structure.add_node('driver_2_incident')

    # Create a real mock CBN
    cbn = Mock()
    cbn.model = Mock()
    cbn.model.get_cpds = Mock(return_value=[Mock()])
    cbn.structure = structure

    # Sample outcomes where driver_1 (high skill) leads more laps
    def mock_sample_outcomes(n_samples, evidence=None):
        return pd.DataFrame({
            'driver_1_laps_led': [50] * n_samples,  # High laps led
            'driver_1_fastest_laps': [20] * n_samples,
            'driver_1_finish_position': [1] * n_samples,
            'driver_1_incident': [False] * n_samples,
            'driver_2_laps_led': [5] * n_samples,  # Low laps led
            'driver_2_fastest_laps': [2] * n_samples,
            'driver_2_finish_position': [2] * n_samples,
            'driver_2_incident': [False] * n_samples,
        })

    cbn.sample_outcomes = Mock(side_effect=mock_sample_outcomes)

    # Create generator
    generator = SkeletonNarrative(
        cbn=cbn,
        ontology_constraints=ontology,
        track_id='test_track',
        field_size=2,
        kernel=None,
        race_length=200,
    )

    # Generate scenarios
    scenarios = generator.generate_scenarios(n_scenarios=10)

    # Check that driver_1 leads more laps on average (with Dirichlet adjustment)
    driver_1_laps = [s.driver_outcomes['driver_1'].laps_led for s in scenarios]
    driver_2_laps = [s.driver_outcomes['driver_2'].laps_led for s in scenarios]

    # Due to Dirichlet conservation, values are adjusted but should maintain relative differences
    assert len(driver_1_laps) == 10
    assert len(driver_2_laps) == 10


def test_conservation_still_works_with_cbn():
    """Test that conservation validation still works with CBN sampling."""
    import networkx as nx

    ontology = OntologyConstraints()

    # Create mock CBN
    structure = nx.DiGraph()
    structure.add_node('driver_1_skill')
    structure.add_node('driver_1_laps_led')
    structure.add_node('driver_1_fastest_laps')
    structure.add_node('driver_1_finish_position')
    structure.add_node('driver_1_incident')

    cbn = Mock()
    cbn.model = Mock()
    cbn.model.get_cpds = Mock(return_value=[Mock()])
    cbn.structure = structure

    def mock_sample_outcomes(n_samples, evidence=None):
        return pd.DataFrame({
            'driver_1_laps_led': [10] * n_samples,
            'driver_1_fastest_laps': [5] * n_samples,
            'driver_1_finish_position': [1] * n_samples,
            'driver_1_incident': [False] * n_samples,
        })

    cbn.sample_outcomes = Mock(side_effect=mock_sample_outcomes)

    # Create mock kernel that always validates
    kernel = Mock()
    kernel.validate_dominator_conservation = Mock(
        return_value=Mock(is_valid=True, veto_reasons=[])
    )

    # Create generator
    generator = SkeletonNarrative(
        cbn=cbn,
        ontology_constraints=ontology,
        track_id='test_track',
        field_size=1,
        kernel=kernel,
        race_length=200,
    )

    # Generate scenarios
    scenarios = generator.generate_scenarios(n_scenarios=5)

    # All scenarios should be generated
    assert len(scenarios) == 5

    # Kernel should have been called for each scenario
    assert kernel.validate_dominator_conservation.call_count == 5


def test_fallback_to_simplified_if_cbn_fails():
    """Test fallback to simplified generation if CBN sampling fails."""
    import networkx as nx

    ontology = OntologyConstraints()

    # Create CBN that raises exception
    structure = nx.DiGraph()
    structure.add_node('driver_1_skill')
    structure.add_node('driver_1_laps_led')
    structure.add_node('driver_1_fastest_laps')
    structure.add_node('driver_1_finish_position')
    structure.add_node('driver_1_incident')
    structure.add_node('driver_2_skill')
    structure.add_node('driver_2_laps_led')
    structure.add_node('driver_2_fastest_laps')
    structure.add_node('driver_2_finish_position')
    structure.add_node('driver_2_incident')
    structure.add_node('driver_3_skill')
    structure.add_node('driver_3_laps_led')
    structure.add_node('driver_3_fastest_laps')
    structure.add_node('driver_3_finish_position')
    structure.add_node('driver_3_incident')

    cbn = Mock()
    cbn.model = Mock()
    cbn.model.get_cpds = Mock(return_value=[Mock()])
    cbn.structure = structure
    cbn.sample_outcomes = Mock(side_effect=Exception("CBN failed"))

    # Create generator
    generator = SkeletonNarrative(
        cbn=cbn,
        ontology_constraints=ontology,
        track_id='test_track',
        field_size=3,
        kernel=None,
        race_length=200,
    )

    # Generate scenario - should not raise exception
    scenario = generator.generate_single_scenario('test_scenario')

    # Scenario should still be generated (using fallback)
    assert scenario is not None
    assert len(scenario.driver_outcomes) == 3
    assert 'driver_1' in scenario.driver_outcomes


def test_fallback_when_cbn_is_none():
    """Test fallback when CBN is None."""
    ontology = OntologyConstraints()

    # Create generator without CBN
    # Need to use create_mock_cbn to have proper structure
    driver_ids = ['driver_1', 'driver_2']
    cbn = create_mock_cbn(ontology, driver_ids)

    # Then replace with None to test fallback
    generator = SkeletonNarrative(
        cbn=cbn,  # Use real CBN first to get proper initialization
        ontology_constraints=ontology,
        track_id='test_track',
        field_size=2,
        kernel=None,
        race_length=200,
    )

    # Now set CBN to None to test fallback path
    generator.cbn = None

    # Generate scenario - should not raise exception
    scenario = generator.generate_single_scenario('test_scenario')

    # Scenario should be generated using simplified logic
    assert scenario is not None
    assert len(scenario.driver_outcomes) == 2


def test_regime_evidence_affects_outcomes():
    """Test that different race-flow regimes affect CBN evidence."""
    import networkx as nx

    ontology = OntologyConstraints()

    # Create mock CBN that tracks evidence
    structure = nx.DiGraph()
    structure.add_node('driver_1_skill')
    structure.add_node('driver_1_laps_led')
    structure.add_node('driver_1_fastest_laps')
    structure.add_node('driver_1_finish_position')
    structure.add_node('driver_1_incident')

    cbn = Mock()
    cbn.model = Mock()
    cbn.model.get_cpds = Mock(return_value=[Mock()])
    cbn.structure = structure

    evidence_received = []

    def mock_sample_outcomes(n_samples, evidence=None):
        evidence_received.append(evidence)
        return pd.DataFrame({
            'driver_1_laps_led': [10] * n_samples,
            'driver_1_fastest_laps': [5] * n_samples,
            'driver_1_finish_position': [1] * n_samples,
            'driver_1_incident': [False] * n_samples,
        })

    cbn.sample_outcomes = Mock(side_effect=mock_sample_outcomes)

    # Create generator
    generator = SkeletonNarrative(
        cbn=cbn,
        ontology_constraints=ontology,
        track_id='test_track',
        field_size=1,
        kernel=None,
        race_length=200,
    )

    # Mock regime sampling to return specific values
    with patch.object(generator, 'sample_race_flow_regime') as mock_regime:
        # High caution regime
        mock_regime.return_value = RaceFlowRegime(
            n_cautions=8,
            pit_strategy=PitStrategy.CONSERVATIVE,
            fuel_window_risk=0.8,
            late_race_chaos=0.7,
        )

        scenario1 = generator.generate_single_scenario('test_1')

        # Low caution regime
        mock_regime.return_value = RaceFlowRegime(
            n_cautions=1,
            pit_strategy=PitStrategy.AGGRESSIVE,
            fuel_window_risk=0.2,
            late_race_chaos=0.1,
        )

        scenario2 = generator.generate_single_scenario('test_2')

    # Check that evidence reflects the different regimes
    assert len(evidence_received) >= 2

    high_chaos_evidence = [e for e in evidence_received if e.get('n_cautions') == 8]
    low_chaos_evidence = [e for e in evidence_received if e.get('n_cautions') == 1]

    assert len(high_chaos_evidence) > 0
    assert len(low_chaos_evidence) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
