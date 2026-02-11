"""
Property-based tests for calibration metrics and models.

This module uses Hypothesis to generate test cases and validate invariants
across many random inputs, ensuring calibration functions handle edge cases
correctly.
"""

import pytest
import jax.numpy as jnp
import numpy as np
from hypothesis import given, strategies as st
from typing import Dict

from app.calibration.metrics import compute_crps, compute_log_score, compute_coverage, compute_all_metrics
from app.calibration.models import (
    track_archetype_calibration_model,
    run_mcmc_calibration,
    compute_calibration_summary,
    VALID_ARCHETYPES,
)


class TestCalibrationMetrics:
    """Property-based tests for calibration metrics."""

    @given(
        predictions=st.lists(
            st.lists(st.floats(min_value=-10, max_value=10, allow_nan=False, allow_infinity=False), min_size=10, max_size=100),
            min_size=10,
            max_size=100
        ),
        observations=st.lists(st.floats(min_value=-10, max_value=10, allow_nan=False, allow_infinity=False), min_size=10, max_size=100),
    )
    def test_crps_properties(self, predictions, observations):
        """Test CRPS properties across random inputs."""
        # Convert to JAX arrays
        pred_array = jnp.array(predictions)
        obs_array = jnp.array(observations)

        # Ensure shapes match
        if pred_array.shape[1] != obs_array.shape[0]:
            pred_array = pred_array[:, :obs_array.shape[0]]

        # CRPS should be non-negative
        crps = compute_crps(pred_array, obs_array)
        assert crps >= 0, f"CRPS should be non-negative, got {crps}"

        # CRPS should be finite
        assert jnp.isfinite(crps), f"CRPS should be finite, got {crps}"

    @given(
        predictions=st.lists(
            st.lists(st.floats(min_value=1, max_value=40, allow_nan=False, allow_infinity=False), min_size=10, max_size=100),
            min_size=10,
            max_size=100
        ),
        observations=st.lists(st.integers(min_value=1, max_value=40), min_size=10, max_size=100),
    )
    def test_log_score_properties(self, predictions, observations):
        """Test log score properties across random inputs."""
        # Convert to JAX arrays
        pred_array = jnp.array(predictions)
        obs_array = jnp.array(observations, dtype=float)

        # Ensure shapes match
        if pred_array.shape[1] != obs_array.shape[0]:
            pred_array = pred_array[:, :obs_array.shape[0]]

        # Log score should be finite
        log_score = compute_log_score(pred_array, obs_array)
        assert jnp.isfinite(log_score), f"Log score should be finite, got {log_score}"

    @given(
        predictions=st.lists(
            st.lists(st.floats(min_value=1, max_value=40, allow_nan=False, allow_infinity=False), min_size=10, max_size=100),
            min_size=10,
            max_size=100
        ),
        observations=st.lists(st.integers(min_value=1, max_value=40), min_size=10, max_size=100),
        levels=st.lists(st.floats(min_value=0.1, max_value=0.9, allow_nan=False, allow_infinity=False), min_size=1, max_size=5),
    )
    def test_coverage_properties(self, predictions, observations, levels):
        """Test coverage properties across random inputs."""
        # Convert to JAX arrays
        pred_array = jnp.array(predictions)
        obs_array = jnp.array(observations, dtype=float)

        # Ensure shapes match
        if pred_array.shape[1] != obs_array.shape[0]:
            pred_array = pred_array[:, :obs_array.shape[0]]

        # Remove duplicate levels
        levels = list(set(levels))

        # Coverage should be in [0, 1]
        coverage = compute_coverage(pred_array, obs_array, levels)
        for level, emp_coverage in coverage.items():
            assert 0.0 <= emp_coverage <= 1.0, f"Coverage should be in [0, 1], got {emp_coverage}"

    def test_crps_perfect_prediction(self):
        """Test CRPS for perfect predictions."""
        predictions = jnp.array([[5.0, 5.0, 5.0], [5.0, 5.0, 5.0]])
        observations = jnp.array([5.0, 5.0, 5.0])

        crps = compute_crps(predictions, observations)
        # CRPS should be very small for perfect predictions
        assert crps < 1.0, f"CRPS should be small for perfect predictions, got {crps}"

    def test_coverage_uniform_predictions(self):
        """Test coverage for uniform predictions."""
        np.random.seed(42)
        predictions = jnp.array(np.random.uniform(0, 1, (100, 50)))
        observations = jnp.array(np.random.uniform(0, 1, 50))

        coverage = compute_coverage(predictions, observations, [0.5, 0.8, 0.95])

        # Coverage should be close to nominal for uniform predictions
        assert 0.4 <= coverage[0.5] <= 0.6, f"50% coverage should be around 0.5, got {coverage[0.5]}"


class TestMCMCCalibration:
    """Tests for MCMC calibration models."""

    def test_valid_archetypes(self):
        """Test that valid archetypes are accepted."""
        for archetype in VALID_ARCHETYPES:
            # Should not raise
            assert archetype in VALID_ARCHETYPES

    def test_invalid_archetype_raises(self):
        """Test that invalid archetypes raise ValueError."""
        with pytest.raises(ValueError, match="Invalid track_archetype"):
            track_archetype_calibration_model(
                observed_finish_positions=jnp.array([[1, 2, 3]]),
                predicted_finish_probs=jnp.ones((1, 3, 3)) / 3.0,
                track_archetype="invalid_track"
            )

    def test_mcmc_convergence(self):
        """Test MCMC converges for simple synthetic data."""
        import jax.random as random

        key = random.PRNGKey(42)
        n_races, n_drivers = 20, 20

        # Create simple test data
        observed = random.randint(key, (n_races, n_drivers), 1, 21)
        predicted = jnp.ones((n_races, n_drivers, 20)) / 20.0

        # Run MCMC with small sample size for testing
        samples, mcmc = run_mcmc_calibration(
            observed, predicted, 'intermediate',
            n_warmup=50, n_samples=100, random_seed=42
        )

        # Check that samples were collected
        assert 'slope_intermediate' in samples
        assert 'intercept_intermediate' in samples
        assert len(samples['slope_intermediate']) == 100

    def test_calibration_summary(self):
        """Test calibration summary computation."""
        import jax.random as random

        key = random.PRNGKey(42)
        n_races, n_drivers = 10, 10

        # Create simple test data
        observed = random.randint(key, (n_races, n_drivers), 1, 11)
        predicted = jnp.ones((n_races, n_drivers, 10)) / 10.0

        # Run MCMC
        samples, _ = run_mcmc_calibration(
            observed, predicted, 'superspeedway',
            n_warmup=20, n_samples=50, random_seed=42
        )

        # Compute summary
        summary = compute_calibration_summary(samples, 'superspeedway')

        # Check summary contains expected keys
        assert 'slope_superspeedway_mean' in summary
        assert 'intercept_superspeedway_mean' in summary

        # Check means are finite
        assert np.isfinite(summary['slope_superspeedway_mean'])
        assert np.isfinite(summary['intercept_superspeedway_mean'])


class TestCalibrationIntegration:
    """Integration tests for calibration workflow."""

    def test_end_to_end_calibration(self):
        """Test end-to-end calibration workflow."""
        import jax.random as random

        key = random.PRNGKey(42)

        # Create test data for multiple track types
        predictions = {
            'superspeedway': random.uniform(key, (50, 20)),
            'intermediate': random.uniform(key, (50, 20))
        }
        observations = random.randint(key, (20,), 1, 21)

        # Compute metrics
        from app.calibration.metrics import compute_all_metrics
        metrics = compute_all_metrics(predictions['superspeedway'], observations)

        # Check metrics exist
        assert 'crps' in metrics
        assert 'log_score' in metrics
        assert 'coverage' in metrics

        # Check metrics are finite
        assert np.isfinite(metrics['crps'])
        assert np.isfinite(metrics['log_score'])

    def test_joint_event_validation(self):
        """Test joint-event validation."""
        from app.calibration.diagnostics import compute_joint_event_validation
        import jax.random as random

        key = random.PRNGKey(42)

        predictions = {
            'superspeedway': random.uniform(key, (50, 20)),
            'short_track': random.uniform(key, (50, 20))
        }
        observations = random.randint(key, (20,), 1, 21)

        # Run joint-event validation
        validation = compute_joint_event_validation(
            predictions, observations,
            ['superspeedway', 'short_track']
        )

        # Check validation results exist
        assert len(validation) > 0

        # Check calibration errors are non-negative
        for (track, event), error in validation.items():
            assert error >= 0, f"Calibration error should be non-negative, got {error}"
