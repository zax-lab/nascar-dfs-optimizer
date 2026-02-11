"""
Integration tests for kernel validation instrumentation and calibration.

Tests cover:
- Rejection tracking across multiple validations
- Constraint spec integration with scenario generation
- End-to-end calibration pipeline
- Kernel stats reset functionality
"""
import pytest
import sys
from pathlib import Path

# Add packages to path
packages_src = Path(__file__).parent.parent.parent.parent.parent / "packages" / "axiomatic-sim" / "src"
if str(packages_src) not in sys.path:
    sys.path.insert(0, str(packages_src))

from app.kernel import KernelLogic, get_rejection_stats, reset_rejection_stats
from app.constraints.models import ConstraintSpec, DriverConstraints, TrackConstraints
from app.calibration.diagnostics import end_to_end_calibration, assess_scenario_calibration

try:
    from axiomatic_sim.scenario_generator import generate_scenarios_with_constraints
    SCENARIO_GEN_AVAILABLE = True
except ImportError:
    SCENARIO_GEN_AVAILABLE = False


class TestRejectionTracking:
    """Test kernel validation rejection tracking."""

    def test_rejection_tracking(self):
        """Test that rejection tracking works across multiple validations."""
        # Reset stats
        reset_rejection_stats()

        # Create kernel
        kernel = KernelLogic(field_size=40)

        # Generate 10 valid scenarios
        for i in range(10):
            valid_scenario = {
                'laps_led': [100, 50] + [0] * 38,
                'fastest_laps': [10, 8] + [0] * 38,
                'start_positions': list(range(1, 41)),
                'finish_positions': list(range(1, 41)),
                'race_length': 200,
                'green_flag_laps': 180
            }
            result = kernel.validate_dominator_conservation(valid_scenario)
            assert result.is_valid, f"Valid scenario {i} should pass"

        # Generate 10 invalid scenarios (violates laps led conservation)
        for i in range(10):
            invalid_scenario = {
                'laps_led': [150, 70] + [0] * 38,  # Total > 200
                'fastest_laps': [15, 12] + [0] * 38,
                'start_positions': list(range(1, 41)),
                'finish_positions': list(range(1, 41)),
                'race_length': 200,
                'green_flag_laps': 180
            }
            result = kernel.validate_dominator_conservation(invalid_scenario)
            assert not result.is_valid, f"Invalid scenario {i} should fail"

        # Check stats
        stats = get_rejection_stats()
        assert stats['total_validated'] == 20, f"Expected 20 validated, got {stats['total_validated']}"
        assert stats['total_rejected'] == 10, f"Expected 10 rejected, got {stats['total_rejected']}"
        assert stats['rejection_rate'] == 0.5, f"Expected 0.5 rejection rate, got {stats['rejection_rate']}"
        assert len(stats.get('veto_reasons', {})) > 0, "Veto reasons should be tracked"

    def test_kernel_stats_reset(self):
        """Test that reset_rejection_stats() clears all statistics."""
        # Run validations to populate stats
        reset_rejection_stats()
        kernel = KernelLogic(field_size=40)

        # Generate some scenarios
        for i in range(5):
            valid_scenario = {
                'laps_led': [100, 50] + [0] * 38,
                'fastest_laps': [10, 8] + [0] * 38,
                'start_positions': list(range(1, 41)),
                'finish_positions': list(range(1, 41)),
                'race_length': 200,
                'green_flag_laps': 180
            }
            kernel.validate_dominator_conservation(valid_scenario)

        # Verify stats are populated
        stats_before = get_rejection_stats()
        assert stats_before['total_validated'] == 5

        # Reset stats
        reset_rejection_stats()

        # Assert stats are zeroed
        stats_after = get_rejection_stats()
        assert stats_after['total_validated'] == 0
        assert stats_after['total_rejected'] == 0
        assert stats_after['rejection_rate'] == 0.0
        assert len(stats_after.get('veto_reasons', {})) == 0


@pytest.mark.skipif(not SCENARIO_GEN_AVAILABLE, reason="Scenario generator not available")
class TestConstraintSpecIntegration:
    """Test constraint spec integration with scenario generation."""

    def test_constraint_spec_integration(self):
        """Test that ConstraintSpec integrates with scenario generation."""
        if not SCENARIO_GEN_AVAILABLE:
            pytest.skip("Scenario generator not available")

        # Reset kernel stats
        reset_rejection_stats()

        # Create ConstraintSpec with 40 drivers and 1 track
        spec = ConstraintSpec(
            slate_id='test_slate',
            compiled_at='2024-01-01T00:00:00',
            drivers={
                f'driver_{i}': DriverConstraints(
                    f'driver_{i}', skill=0.5, aggression=0.5, shadow_risk=0.5,
                    min_laps_led=0, max_laps_led=100, veto_rules=[]
                )
                for i in range(1, 41)
            },
            tracks={
                'daytona': TrackConstraints(
                    'daytona', difficulty=0.7, aggression_factor=0.6,
                    caution_rate=0.05, pit_window_laps=[35, 70, 105, 140, 175]
                )
            },
            version='1.0',
            hash='test_hash'
        )

        # Generate scenarios with constraint spec
        kernel = KernelLogic(field_size=40)
        scenarios = generate_scenarios_with_constraints(
            constraint_spec=spec,
            track_id='daytona',
            n_scenarios=10,
            kernel=kernel,
            random_seed=42
        )

        # Assert scenarios were generated
        assert len(scenarios) == 10, f"Expected 10 scenarios, got {len(scenarios)}"

        # Verify each scenario has driver outcomes
        for scenario in scenarios:
            assert hasattr(scenario, 'driver_outcomes'), "Scenario should have driver_outcomes"
            assert len(scenario.driver_outcomes) == 40, "Should have 40 drivers"

    def test_backward_compatibility(self):
        """Test that generate_scenarios() works without constraint_spec."""
        if not SCENARIO_GEN_AVAILABLE:
            pytest.skip("Scenario generator not available")

        # Reset kernel stats
        reset_rejection_stats()

        # Test backward compatibility (without constraint spec)
        kernel = KernelLogic(field_size=40)
        driver_ids = [f'driver_{i}' for i in range(1, 41)]

        try:
            from axiomatic_sim.scenario_generator import generate_scenarios
            scenarios_legacy = generate_scenarios(
                track_id='daytona',
                n_scenarios=5,
                kernel=kernel,
                driver_ids=driver_ids
            )
            assert len(scenarios_legacy) == 5, f"Expected 5 scenarios, got {len(scenarios_legacy)}"
        except ImportError:
            pytest.skip("generate_scenarios not available")


@pytest.mark.skipif(not SCENARIO_GEN_AVAILABLE, reason="Scenario generator not available")
class TestEndToEndCalibration:
    """Test end-to-end calibration pipeline."""

    def test_end_to_end_calibration(self):
        """Test that end-to-end calibration runs complete pipeline."""
        if not SCENARIO_GEN_AVAILABLE:
            pytest.skip("Scenario generator not available")

        # Reset kernel stats
        reset_rejection_stats()

        # Create ConstraintSpec
        spec = ConstraintSpec(
            slate_id='test_slate',
            compiled_at='2024-01-01T00:00:00',
            drivers={
                f'driver_{i}': DriverConstraints(
                    f'driver_{i}', skill=0.5, aggression=0.5, shadow_risk=0.5,
                    min_laps_led=0, max_laps_led=100, veto_rules=[]
                )
                for i in range(1, 41)
            },
            tracks={
                'daytona': TrackConstraints(
                    'daytona', difficulty=0.7, aggression_factor=0.6,
                    caution_rate=0.05, pit_window_laps=[35, 70, 105, 140, 175]
                )
            },
            version='1.0',
            hash='test_hash'
        )

        # Run end-to-end calibration
        kernel = KernelLogic(field_size=40)
        result = end_to_end_calibration(
            constraint_spec=spec,
            track_id='daytona',
            n_scenarios=10,
            kernel=kernel,
            random_seed=42
        )

        # Assert result contains expected keys
        assert 'scenarios' in result, "Result should contain scenarios"
        assert 'calibration_metrics' in result, "Result should contain calibration_metrics"
        assert 'kernel_rejection_stats' in result, "Result should contain kernel_rejection_stats"

        # Assert scenarios were generated
        scenarios = result['scenarios']
        assert len(scenarios) == 10, f"Expected 10 scenarios, got {len(scenarios)}"

        # Assert kernel stats are present
        kernel_stats = result['kernel_rejection_stats']
        assert 'total_validated' in kernel_stats, "Kernel stats should have total_validated"
        assert 'total_rejected' in kernel_stats, "Kernel stats should have total_rejected"
        assert 'rejection_rate' in kernel_stats, "Kernel stats should have rejection_rate"

        # Assert calibration metrics are present
        calibration_metrics = result['calibration_metrics']
        assert 'observed_finish_positions' in calibration_metrics, "Should have observed positions"
        assert 'n_scenarios' in calibration_metrics, "Should have n_scenarios"
        assert calibration_metrics['n_scenarios'] == 10

    def test_assess_scenario_calibration(self):
        """Test scenario calibration assessment."""
        if not SCENARIO_GEN_AVAILABLE:
            pytest.skip("Scenario generator not available")

        # Generate scenarios first
        reset_rejection_stats()

        spec = ConstraintSpec(
            slate_id='test_slate',
            compiled_at='2024-01-01T00:00:00',
            drivers={
                f'driver_{i}': DriverConstraints(
                    f'driver_{i}', skill=0.5, aggression=0.5, shadow_risk=0.5,
                    min_laps_led=0, max_laps_led=100, veto_rules=[]
                )
                for i in range(1, 41)
            },
            tracks={
                'daytona': TrackConstraints(
                    'daytona', difficulty=0.7, aggression_factor=0.6,
                    caution_rate=0.05, pit_window_laps=[35, 70, 105, 140, 175]
                )
            },
            version='1.0',
            hash='test_hash'
        )

        kernel = KernelLogic(field_size=40)
        scenarios = generate_scenarios_with_constraints(
            constraint_spec=spec,
            track_id='daytona',
            n_scenarios=5,
            kernel=kernel,
            random_seed=42
        )

        # Assess calibration
        metrics = assess_scenario_calibration(
            scenarios=scenarios,
            predictions=None,  # No predictions for this test
            track_archetype='daytona'
        )

        # Assert metrics are present
        assert 'observed_finish_positions' in metrics
        assert 'n_scenarios' in metrics
        assert metrics['n_scenarios'] == 5
        assert metrics['observed_finish_positions'].shape == (5, 40)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
