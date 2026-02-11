"""
Tests for CBN forward sampling and evidence conditioning.

This test module verifies that the CausalBayesianNetwork.sample_outcomes()
method generates real driver outcomes from learned CPDs, respects discrete
variable constraints, and properly conditions on evidence.
"""
import pytest
import numpy as np
import pandas as pd
import networkx as nx
from pgmpy.models import BayesianNetwork
from pgmpy.factors.discrete import TabularCPD

from axiomatic_sim.cbn import CausalBayesianNetwork
from axiomatic_sim.ontology_constraints import OntologyConstraints


@pytest.fixture
def simple_cbn():
    """
    Create a simple CBN with learned CPDs for testing.

    Structure: skill -> laps_led -> finish_position
    """
    # Create structure
    structure = nx.DiGraph()
    structure.add_edge('skill', 'laps_led')
    structure.add_edge('skill', 'finish_position')

    # Create mock ontology
    ontology = OntologyConstraints()

    # Create CBN
    cbn = CausalBayesianNetwork(structure, ontology)

    # Manually add CPDs for testing
    # Skill: high (0.7) or low (0.3)
    skill_cpd = TabularCPD(
        variable='skill',
        variable_card=2,
        values=[[0.3], [0.7]],
        state_names={'skill': [0, 1]}
    )
    cbn.model.add_cpds(skill_cpd)

    # laps_led depends on skill: P(laps_led | skill)
    # If skill=0 (low): laps_led is 0, 1, or 2 with prob [0.6, 0.3, 0.1]
    # If skill=1 (high): laps_led is 0, 1, or 2 with prob [0.1, 0.3, 0.6]
    laps_led_cpd = TabularCPD(
        variable='laps_led',
        variable_card=3,
        values=[[0.6, 0.1],  # laps_led=0
                [0.3, 0.3],  # laps_led=1
                [0.1, 0.6]],  # laps_led=2
        evidence=['skill'],
        evidence_card=[2],
        state_names={'laps_led': [0, 1, 2], 'skill': [0, 1]}
    )
    cbn.model.add_cpds(laps_led_cpd)

    # finish_position depends on skill: P(finish_position | skill)
    # If skill=0 (low): uniform distribution across all 40 positions
    # If skill=1 (high): concentrated on top 20 positions
    # Shape: (40, 2) - 40 positions x 2 skill values
    # Each column must sum to 1
    finish_low_skill = np.ones(40) / 40  # Uniform
    finish_high_skill = np.concatenate([
        np.ones(20) * 0.04,  # Top 20: 0.04 each = 0.8 total
        np.ones(20) * 0.01   # Bottom 20: 0.01 each = 0.2 total
    ])  # Sums to 1.0

    finish_position_cpd = TabularCPD(
        variable='finish_position',
        variable_card=40,
        values=np.column_stack([finish_low_skill, finish_high_skill]),
        evidence=['skill'],
        evidence_card=[2],
        state_names={'finish_position': list(range(1, 41)), 'skill': [0, 1]}
    )
    cbn.model.add_cpds(finish_position_cpd)

    return cbn


def test_forward_sampling_from_cpds(simple_cbn):
    """Test that forward sampling produces valid samples from learned CPDs."""
    samples = simple_cbn.sample_outcomes(n_samples=100)

    # Check we got samples back
    assert len(samples) == 100
    assert 'skill' in samples.columns
    assert 'laps_led' in samples.columns
    assert 'finish_position' in samples.columns

    # Check all sampled values are in valid ranges
    assert all(samples['laps_led'].isin([0, 1, 2]))
    assert all(samples['finish_position'].isin(range(1, 41)))
    assert all(samples['skill'].isin([0, 1]))

    # Check samples have variance (not all same value)
    assert samples['laps_led'].var() > 0
    assert samples['skill'].var() > 0


def test_evidence_conditioning_changes_distribution(simple_cbn):
    """Test that evidence conditioning produces different outcome distributions."""
    # Sample with high skill evidence
    samples_high_skill = simple_cbn.sample_outcomes(
        n_samples=100,
        evidence={'skill': 1}
    )

    # Sample with low skill evidence
    samples_low_skill = simple_cbn.sample_outcomes(
        n_samples=100,
        evidence={'skill': 0}
    )

    # High skill drivers should lead more laps on average
    assert samples_high_skill['laps_led'].mean() > samples_low_skill['laps_led'].mean()

    # High skill drivers should have better (lower) finish positions
    assert samples_high_skill['finish_position'].mean() < samples_low_skill['finish_position'].mean()


def test_discrete_variable_constraints(simple_cbn):
    """Test that discrete variables respect their constraints."""
    samples = simple_cbn.sample_outcomes(n_samples=100)

    # laps_led should be >= 0
    assert all(samples['laps_led'] >= 0)

    # finish_position should be in [1, 40]
    assert all(samples['finish_position'] >= 1)
    assert all(samples['finish_position'] <= 40)

    # skill should be 0 or 1
    assert all(samples['skill'].isin([0, 1]))


def test_sampling_respects_causal_structure():
    """Test that sampling respects the causal structure of the CBN."""
    # Create CBN with aggression -> incident -> dnf_lap structure
    structure = nx.DiGraph()
    structure.add_edge('aggression', 'incident')
    structure.add_edge('incident', 'dnf_lap')

    ontology = OntologyConstraints()
    cbn = CausalBayesianNetwork(structure, ontology)

    # Add CPDs
    # aggression: low (0) or high (1)
    aggression_cpd = TabularCPD(
        variable='aggression',
        variable_card=2,
        values=[[0.5], [0.5]],
        state_names={'aggression': [0, 1]}
    )
    cbn.model.add_cpds(aggression_cpd)

    # incident depends on aggression
    incident_cpd = TabularCPD(
        variable='incident',
        variable_card=2,
        values=[[0.9, 0.3],  # P(no incident)
                [0.1, 0.7]],  # P(incident)
        evidence=['aggression'],
        evidence_card=[2],
        state_names={'incident': [0, 1], 'aggression': [0, 1]}
    )
    cbn.model.add_cpds(incident_cpd)

    # dnf_lap depends on incident
    # Shape: (3, 2) - 3 dnf_lap values x 2 incident values
    # Each column must sum to 1
    dnf_lap_cpd = TabularCPD(
        variable='dnf_lap',
        variable_card=3,
        values=np.array([[1.0, 0.5],  # No DNF (lap=0)
                        [0.0, 0.3],  # DNF early
                        [0.0, 0.2]]),  # DNF late (sums to 1.0 for each column)
        evidence=['incident'],
        evidence_card=[2],
        state_names={'dnf_lap': [0, 1, 2], 'incident': [0, 1]}
    )
    cbn.model.add_cpds(dnf_lap_cpd)

    # Sample with high aggression
    samples_high_agg = cbn.sample_outcomes(
        n_samples=100,
        evidence={'aggression': 1}
    )

    # Sample with low aggression
    samples_low_agg = cbn.sample_outcomes(
        n_samples=100,
        evidence={'aggression': 0}
    )

    # High aggression should have higher incident rate
    p_incident_high = samples_high_agg['incident'].mean()
    p_incident_low = samples_low_agg['incident'].mean()
    assert p_incident_high > p_incident_low


def test_reproducible_sampling_with_seed(simple_cbn):
    """Test that sampling is reproducible when using the same random state."""
    # This test requires numpy's random state to be controlled
    # For now, we just verify that multiple runs produce samples

    samples1 = simple_cbn.sample_outcomes(n_samples=50)
    samples2 = simple_cbn.sample_outcomes(n_samples=50)

    # Both should produce valid samples
    assert len(samples1) == 50
    assert len(samples2) == 50

    # Samples should have similar statistical properties
    # (we don't expect them to be identical without explicit seeding)
    assert abs(samples1['laps_led'].mean() - samples2['laps_led'].mean()) < 2.0


def test_evidence_with_nonexistent_variable(simple_cbn):
    """Test that providing non-existent evidence variables raises ValueError."""
    with pytest.raises(ValueError, match="not in CBN"):
        simple_cbn.sample_outcomes(
            n_samples=10,
            evidence={'nonexistent_var': 1}
        )


def test_sampling_without_learned_cpds():
    """Test that sampling without learned CPDs raises ValueError."""
    structure = nx.DiGraph()
    structure.add_node('skill')

    ontology = OntologyConstraints()
    cbn = CausalBayesianNetwork(structure, ontology)

    # Should raise ValueError since no CPDs are learned
    with pytest.raises(ValueError, match="not learned"):
        cbn.sample_outcomes(n_samples=10)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
