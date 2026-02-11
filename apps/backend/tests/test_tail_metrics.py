"""
Unit tests for tail metrics computation (CVaR, Top X%, conditional upside).

Tests validate correctness of tail metric calculations against known values
and edge cases (empty arrays, single scenario, insufficient scenarios).
"""
import pytest
import numpy as np
from app.tail_metrics import (
    compute_cvar,
    compute_tail_metrics,
    adaptive_scenario_count,
    TailMetrics
)


class TestComputeCVaR:
    """Test CVaR calculation using Rockafellar-Uryasev formulation."""

    def test_cvar_with_known_values(self):
        """Test CVaR calculation with deterministic scenario outcomes."""
        # Simple case: 100 scenarios, values 0-99
        scenarios = np.arange(100, dtype=float)

        # CVaR at alpha=0.99 (top 1% = best scenario)
        cvar = compute_cvar(scenarios, alpha=0.99)

        # Top 1% of 100 scenarios = 1 scenario (value 99)
        # CVaR should be mean of top 1% = 99.0
        assert cvar == pytest.approx(99.0, rel=0.01)

    def test_cvar_with_multiple_tail_scenarios(self):
        """Test CVaR with multiple scenarios in tail region."""
        # 1000 scenarios, values 0-999
        scenarios = np.arange(1000, dtype=float)

        # CVaR at alpha=0.95 (top 5% = 50 scenarios)
        cvar = compute_cvar(scenarios, alpha=0.95)

        # Top 5% of 1000 = 50 scenarios (values 950-999)
        # Mean of 950-999 = (950 + 999) / 2 = 974.5
        expected_cvar = np.mean(np.arange(950, 1000, dtype=float))
        assert cvar == pytest.approx(expected_cvar, rel=0.01)

    def test_cvar_with_negative_values(self):
        """Test CVaR handles negative scenario outcomes (losses)."""
        scenarios = np.array([-50, -40, -30, -20, -10, 0, 10, 20, 30, 40])

        # CVaR at alpha=0.90 (top 10% = 1 scenario)
        cvar = compute_cvar(scenarios, alpha=0.90)

        # Top 10% = best scenario = 40
        assert cvar == pytest.approx(40.0, rel=0.01)

    def test_cvar_with_all_same_values(self):
        """Test CVaR when all scenarios have same outcome."""
        scenarios = np.full(100, 100.0)

        cvar = compute_cvar(scenarios, alpha=0.99)

        # CVaR should equal the constant value
        assert cvar == pytest.approx(100.0, rel=0.01)

    def test_cvar_with_insufficient_scenarios(self):
        """Test CVaR falls back to mean when too few scenarios."""
        # Only 10 scenarios for alpha=0.99 (needs 100+)
        scenarios = np.arange(10, dtype=float)

        # Should handle gracefully (either raise warning or use available)
        cvar = compute_cvar(scenarios, alpha=0.99)

        # With only 10 scenarios, tail is 1 scenario = value 9
        assert cvar == pytest.approx(9.0, rel=0.01)


class TestComputeTailMetrics:
    """Test comprehensive tail metrics computation."""

    def test_tail_metrics_returns_complete_dataclass(self):
        """Test that tail metrics returns all required fields."""
        scenarios = np.random.randn(1000) * 10 + 100

        metrics = compute_tail_metrics(scenarios, alpha=0.99)

        # Check all required fields present
        assert hasattr(metrics, 'CVaR')
        assert hasattr(metrics, 'VaR')
        assert hasattr(metrics, 'top_X_pct')
        assert hasattr(metrics, 'conditional_upside')
        assert hasattr(metrics, 'alpha')

        # Check types
        assert isinstance(metrics.CVaR, (float, np.floating))
        assert isinstance(metrics.VaR, (float, np.floating))
        assert isinstance(metrics.top_X_pct, (float, np.floating))
        assert isinstance(metrics.conditional_upside, (float, np.floating))
        assert isinstance(metrics.alpha, (float, np.floating))

    def test_tail_metrics_cvar_greater_than_var(self):
        """Test that CVaR >= VaR for upper-tail optimization."""
        scenarios = np.random.randn(1000) * 15 + 120

        metrics = compute_tail_metrics(scenarios, alpha=0.99)

        # For upper tail, CVaR (mean of tail) should be >= VaR (worst in tail)
        assert metrics.CVaR >= metrics.VaR

    def test_tail_metrics_top_x_pct_in_tail(self):
        """Test that top_X_pct is in the tail region."""
        scenarios = np.array([100, 110, 120, 130, 140, 150])

        metrics = compute_tail_metrics(scenarios, alpha=0.90)

        # top_X_pct should be one of the values in scenarios
        assert metrics.top_X_pct in scenarios
        # And it should be relatively high (in the top portion)
        assert metrics.top_X_pct >= 130  # At least in the top portion

    def test_tail_metrics_conditional_upside_calculation(self):
        """Test conditional upside = CVaR - mean."""
        scenarios = np.random.randn(500) * 12 + 115

        metrics = compute_tail_metrics(scenarios, alpha=0.95)

        # Conditional upside should be CVaR - mean
        overall_mean = np.mean(scenarios)
        expected_upside = metrics.CVaR - overall_mean
        assert metrics.conditional_upside == pytest.approx(expected_upside, rel=0.01)

    def test_tail_metrics_with_realistic_dfs_points(self):
        """Test tail metrics with realistic NASCAR DFS point distribution."""
        # Simulate DFS points: mean ~120, std ~20, skew right
        np.random.seed(42)
        scenarios = np.random.gamma(shape=6, scale=20, size=1000) + 80

        metrics = compute_tail_metrics(scenarios, alpha=0.99)

        # Sanity checks for realistic DFS outcomes
        overall_mean = np.mean(scenarios)
        assert 80 < overall_mean < 250  # Mean in reasonable range (gamma can skew high)
        assert metrics.CVaR > overall_mean  # CVaR > mean for upper tail
        assert metrics.top_X_pct > metrics.VaR  # Top X% > VaR (best > worst in tail)


class TestAdaptiveScenarioCount:
    """Test adaptive scenario count thresholds."""

    def test_adaptive_count_for_cvar_99(self):
        """Test that CVaR(99%) requires at least 10,000 scenarios."""
        n_scenarios = adaptive_scenario_count(target_alpha=0.99)

        assert n_scenarios >= 10000

    def test_adaptive_count_for_cvar_95(self):
        """Test that CVaR(95%) requires at least 2,000 scenarios."""
        n_scenarios = adaptive_scenario_count(target_alpha=0.95)

        assert n_scenarios >= 2000

    def test_adaptive_count_for_cvar_90(self):
        """Test that CVaR(90%) requires at least 1,000 scenarios."""
        n_scenarios = adaptive_scenario_count(target_alpha=0.90)

        assert n_scenarios >= 1000

    def test_adaptive_count_increases_with_alpha(self):
        """Test that higher alpha (more extreme tail) requires more scenarios."""
        n_90 = adaptive_scenario_count(target_alpha=0.90)
        n_95 = adaptive_scenario_count(target_alpha=0.95)
        n_99 = adaptive_scenario_count(target_alpha=0.99)

        assert n_99 > n_95 > n_90


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_scenarios_raises_error(self):
        """Test that empty scenario array raises appropriate error."""
        scenarios = np.array([])

        with pytest.raises((ValueError, IndexError)):
            compute_cvar(scenarios, alpha=0.99)

    def test_single_scenario_returns_that_value(self):
        """Test CVaR with single scenario returns that scenario's value."""
        scenarios = np.array([150.0])

        cvar = compute_cvar(scenarios, alpha=0.99)

        assert cvar == pytest.approx(150.0, rel=0.01)

    def test_nan_scenarios_propagate(self):
        """Test that NaN values in scenarios result in NaN CVaR (NumPy behavior)."""
        scenarios = np.array([100, np.nan, 120, 130])

        # NumPy operations propagate NaN by default
        cvar = compute_cvar(scenarios, alpha=0.99)

        # Result should be NaN (NumPy's default behavior)
        assert np.isnan(cvar)

    def test_cvar_with_alpha_equals_one(self):
        """Test CVaR with alpha=1.0 returns maximum value."""
        scenarios = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

        cvar = compute_cvar(scenarios, alpha=1.0)

        # Should return max value
        assert cvar == pytest.approx(10.0, rel=0.01)

    def test_cvar_with_alpha_equals_zero(self):
        """Test CVaR with alpha=0.0 returns minimum value."""
        scenarios = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

        cvar = compute_cvar(scenarios, alpha=0.0)

        # Should return min value
        assert cvar == pytest.approx(1.0, rel=0.01)

    def test_cvar_invalid_alpha_raises_error(self):
        """Test that invalid alpha values raise ValueError."""
        scenarios = np.array([1, 2, 3, 4, 5])

        # alpha > 1.0
        with pytest.raises(ValueError, match="alpha must be in"):
            compute_cvar(scenarios, alpha=1.5)

        # alpha < 0.0
        with pytest.raises(ValueError, match="alpha must be in"):
            compute_cvar(scenarios, alpha=-0.1)

    def test_tail_metrics_empty_scenarios_raises_error(self):
        """Test that empty scenarios raise ValueError in compute_tail_metrics."""
        scenarios = np.array([])

        with pytest.raises(ValueError):
            compute_tail_metrics(scenarios, alpha=0.99)

    def test_adaptive_count_invalid_alpha_raises_error(self):
        """Test that invalid alpha raises ValueError in adaptive_scenario_count."""
        with pytest.raises(ValueError, match="target_alpha must be in"):
            adaptive_scenario_count(target_alpha=1.5)

        with pytest.raises(ValueError, match="target_alpha must be in"):
            adaptive_scenario_count(target_alpha=-0.1)

    def test_adaptive_count_invalid_min_tail_samples_raises_error(self):
        """Test that invalid min_tail_samples raises ValueError."""
        with pytest.raises(ValueError, match="min_tail_samples must be"):
            adaptive_scenario_count(target_alpha=0.99, min_tail_samples=0)

        with pytest.raises(ValueError, match="min_tail_samples must be"):
            adaptive_scenario_count(target_alpha=0.99, min_tail_samples=-10)
