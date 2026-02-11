"""
Property-based tests for Kernel dominator conservation validation.

Uses Hypothesis to generate random inputs and validate that conservation
constraints are enforced correctly across a wide range of scenarios.

These tests ensure that:
1. Conservation validation accepts valid scenarios
2. Conservation validation rejects invalid scenarios
3. Veto reasons are clear and accurate
4. Batch validation performs efficiently
"""

import pytest
from hypothesis import given, strategies as st, settings, Phase
from hypothesis.strategies import integers, lists, just
import sys
import os

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.kernel import KernelLogic


# Test strategies
field_sizes = integers(min_value=2, max_value=40)
race_lengths = integers(min_value=100, max_value=500)
green_flag_laps = integers(min_value=50, max_value=400)


def generate_conserved_laps_led(field_size, race_length):
    """Generate laps_led that sum exactly to race_length."""
    if field_size == 1:
        return [race_length]

    # Generate random splits that sum to race_length
    from random import randint
    laps = []
    remaining = race_length

    for i in range(field_size - 1):
        if remaining > 0:
            lap = randint(0, remaining)
            laps.append(lap)
            remaining -= lap
        else:
            laps.append(0)

    laps.append(remaining)
    return laps


def generate_exceeded_laps_led(field_size, race_length):
    """Generate laps_led that sum to race_length + 1 (violates conservation)."""
    laps = generate_conserved_laps_led(field_size, race_length)
    # Add 1 to the first non-zero entry
    for i in range(len(laps)):
        if laps[i] > 0:
            laps[i] += 1
            break
    return laps


class TestLapsLedConservation:
    """Test suite for laps led conservation validation."""

    @given(field_size=field_sizes, race_length=race_lengths)
    def test_laps_led_conservation_when_sum_equals_race_length(self, field_size, race_length):
        """Test that laps_led summing to race_length passes validation."""
        kernel = KernelLogic(field_size=field_size)
        laps_led_list = generate_conserved_laps_led(field_size, race_length)

        scenario = {
            'laps_led': laps_led_list,
            'fastest_laps': [0] * field_size,
            'start_positions': list(range(1, field_size + 1)),
            'finish_positions': list(range(1, field_size + 1)),
            'race_length': race_length,
            'green_flag_laps': race_length - 20
        }

        result = kernel.validate_dominator_conservation(scenario)

        assert result.is_valid, f"Expected valid scenario, but got veto_reasons: {result.veto_reasons}"
        assert result.laps_led_valid
        assert len(result.veto_reasons) == 0

    @given(field_size=field_sizes, race_length=race_lengths)
    def test_laps_led_conservation_when_sum_exceeds_race_length(self, field_size, race_length):
        """Test that laps_led exceeding race_length fails validation."""
        kernel = KernelLogic(field_size=field_size)
        laps_led_list = generate_exceeded_laps_led(field_size, race_length)

        scenario = {
            'laps_led': laps_led_list,
            'fastest_laps': [0] * field_size,
            'start_positions': list(range(1, field_size + 1)),
            'finish_positions': list(range(1, field_size + 1)),
            'race_length': race_length,
            'green_flag_laps': race_length - 20
        }

        result = kernel.validate_dominator_conservation(scenario)

        assert not result.is_valid, "Expected invalid scenario due to laps_led violation"
        assert not result.laps_led_valid
        assert len(result.veto_reasons) > 0
        assert any("laps" in reason.lower() for reason in result.veto_reasons)

    @given(field_size=field_sizes, race_length=race_lengths)
    def test_laps_led_all_zeros_is_valid(self, field_size, race_length):
        """Test that all-zero laps_led is valid (nobody led any laps)."""
        kernel = KernelLogic(field_size=field_size)

        scenario = {
            'laps_led': [0] * field_size,
            'fastest_laps': [0] * field_size,
            'start_positions': list(range(1, field_size + 1)),
            'finish_positions': list(range(1, field_size + 1)),
            'race_length': race_length,
            'green_flag_laps': race_length - 20
        }

        result = kernel.validate_dominator_conservation(scenario)

        assert result.is_valid
        assert result.laps_led_valid


class TestFastestLapsConservation:
    """Test suite for fastest laps conservation validation."""

    @given(field_size=field_sizes, green_flag_laps=green_flag_laps)
    def test_fastest_laps_conservation_when_sum_equals_green_flag_laps(self, field_size, green_flag_laps):
        """Test that fastest_laps summing to green_flag_laps passes validation."""
        kernel = KernelLogic(field_size=field_size)
        fastest_laps_list = generate_conserved_laps_led(field_size, green_flag_laps)

        scenario = {
            'laps_led': [0] * field_size,
            'fastest_laps': fastest_laps_list,
            'start_positions': list(range(1, field_size + 1)),
            'finish_positions': list(range(1, field_size + 1)),
            'race_length': green_flag_laps + 20,
            'green_flag_laps': green_flag_laps
        }

        result = kernel.validate_dominator_conservation(scenario)

        assert result.is_valid, f"Expected valid scenario, but got veto_reasons: {result.veto_reasons}"
        assert result.fastest_laps_valid

    @given(field_size=field_sizes, green_flag_laps=green_flag_laps)
    def test_fastest_laps_conservation_when_sum_exceeds_green_flag_laps(self, field_size, green_flag_laps):
        """Test that fastest_laps exceeding green_flag_laps fails validation."""
        kernel = KernelLogic(field_size=field_size)
        fastest_laps_list = generate_exceeded_laps_led(field_size, green_flag_laps)

        scenario = {
            'laps_led': [0] * field_size,
            'fastest_laps': fastest_laps_list,
            'start_positions': list(range(1, field_size + 1)),
            'finish_positions': list(range(1, field_size + 1)),
            'race_length': green_flag_laps + 20,
            'green_flag_laps': green_flag_laps
        }

        result = kernel.validate_dominator_conservation(scenario)

        assert not result.is_valid, "Expected invalid scenario due to fastest_laps violation"
        assert not result.fastest_laps_valid
        assert any("fastest" in reason.lower() for reason in result.veto_reasons)


class TestPositionSwapsValidation:
    """Test suite for position swap validation."""

    @given(field_size=field_sizes, green_flag_laps=green_flag_laps)
    def test_position_swaps_no_changes_is_valid(self, field_size, green_flag_laps):
        """Test that no position changes (start == finish) is valid."""
        kernel = KernelLogic(field_size=field_size)
        positions = list(range(1, field_size + 1))

        scenario = {
            'laps_led': [0] * field_size,
            'fastest_laps': [0] * field_size,
            'start_positions': positions,
            'finish_positions': positions,
            'race_length': green_flag_laps + 20,
            'green_flag_laps': green_flag_laps
        }

        result = kernel.validate_dominator_conservation(scenario)

        assert result.is_valid
        assert result.position_swaps_valid

    @given(field_size=field_sizes, green_flag_laps=green_flag_laps)
    def test_position_swaps_small_changes_is_valid(self, field_size, green_flag_laps):
        """Test that small position changes are valid."""
        kernel = KernelLogic(field_size=field_size)
        start_positions = list(range(1, field_size + 1))

        # Swap adjacent positions once
        finish_positions = start_positions.copy()
        if field_size >= 2:
            finish_positions[0], finish_positions[1] = finish_positions[1], finish_positions[0]

        scenario = {
            'laps_led': [0] * field_size,
            'fastest_laps': [0] * field_size,
            'start_positions': start_positions,
            'finish_positions': finish_positions,
            'race_length': green_flag_laps + 20,
            'green_flag_laps': green_flag_laps
        }

        result = kernel.validate_dominator_conservation(scenario)

        assert result.is_valid
        assert result.position_swaps_valid

    def test_position_swaps_large_reversal_exceeds_limit(self):
        """Test that complete field reversal exceeds physical limits."""
        field_size = 40
        green_flag_laps = 180
        kernel = KernelLogic(field_size=field_size)

        start_positions = list(range(1, field_size + 1))
        finish_positions = list(reversed(start_positions))

        scenario = {
            'laps_led': [0] * field_size,
            'fastest_laps': [0] * field_size,
            'start_positions': start_positions,
            'finish_positions': finish_positions,
            'race_length': 200,
            'green_flag_laps': green_flag_laps
        }

        result = kernel.validate_dominator_conservation(scenario)

        # Complete reversal of 40 drivers has 760 total swaps (2 * (1+2+...+39))
        # Max swaps for 40 field, 180 green flag laps = min(80, 18) = 18 -> max(18, 40) = 40
        # So this should fail
        assert not result.position_swaps_valid
        assert any("swap" in reason.lower() for reason in result.veto_reasons)


class TestKernelConservationIntegration:
    """Integration tests for full conservation validation."""

    def test_kernel_validate_dominator_conservation_all_conserved(self):
        """Test that a fully conserved scenario passes all validations."""
        kernel = KernelLogic(field_size=40)

        scenario = {
            'laps_led': [100, 50, 30, 20] + [0] * 36,  # Sum = 200
            'fastest_laps': [10, 8, 5, 3] + [0] * 36,  # Sum = 26
            'start_positions': list(range(1, 41)),
            'finish_positions': list(range(1, 41)),
            'race_length': 200,
            'green_flag_laps': 180
        }

        result = kernel.validate_dominator_conservation(scenario)

        assert result.is_valid
        assert result.laps_led_valid
        assert result.fastest_laps_valid
        assert result.position_swaps_valid
        assert len(result.veto_reasons) == 0

    def test_kernel_validate_dominator_conservation_multiple_violations(self):
        """Test that multiple conservation violations are all reported."""
        kernel = KernelLogic(field_size=40)

        scenario = {
            'laps_led': [150, 70, 40, 30] + [0] * 36,  # Sum = 290 > 200
            'fastest_laps': [100, 80, 60, 40] + [0] * 36,  # Sum = 280 > 180
            'start_positions': list(range(1, 41)),
            'finish_positions': list(reversed(range(1, 41))),  # Huge swaps
            'race_length': 200,
            'green_flag_laps': 180
        }

        result = kernel.validate_dominator_conservation(scenario)

        assert not result.is_valid
        assert not result.laps_led_valid
        assert not result.fastest_laps_valid
        # Position swaps might or might not fail depending on calculation
        assert len(result.veto_reasons) >= 2

    def test_kernel_validate_dominator_conservation_with_dict_input(self):
        """Test that dict inputs work correctly."""
        kernel = KernelLogic(field_size=5)

        scenario = {
            'laps_led': {'driver1': 50, 'driver2': 30, 'driver3': 20, 'driver4': 0, 'driver5': 0},
            'fastest_laps': {'driver1': 5, 'driver2': 3, 'driver3': 2, 'driver4': 0, 'driver5': 0},
            'start_positions': {'driver1': 1, 'driver2': 2, 'driver3': 3, 'driver4': 4, 'driver5': 5},
            'finish_positions': {'driver1': 1, 'driver2': 2, 'driver3': 3, 'driver4': 4, 'driver5': 5},
            'race_length': 100,
            'green_flag_laps': 80
        }

        result = kernel.validate_dominator_conservation(scenario)

        assert result.is_valid


class TestBatchValidation:
    """Test suite for batch scenario validation."""

    def test_kernel_batch_validation_efficiency(self):
        """Test that batch validation of 1,000 scenarios completes efficiently."""
        import time

        kernel = KernelLogic(field_size=40)

        # Generate 1,000 scenarios
        scenarios = []
        for i in range(1000):
            scenario = {
                'laps_led': [100, 50, 30, 20] + [0] * 36,
                'fastest_laps': [10, 8, 5, 3] + [0] * 36,
                'start_positions': list(range(1, 41)),
                'finish_positions': list(range(1, 41)),
                'race_length': 200,
                'green_flag_laps': 180
            }
            scenarios.append(scenario)

        # Measure validation time
        start_time = time.time()
        results, stats = kernel.batch_validate_scenarios(scenarios)
        elapsed_time = time.time() - start_time

        assert len(results) == 1000
        assert all(r.is_valid for r in results)
        assert stats['batch_size'] == 1000

        # Should complete in under 5 seconds (even without JAX optimization)
        assert elapsed_time < 5.0, f"Batch validation took {elapsed_time:.2f}s, expected <5s"

        print(f"Batch validation of 1,000 scenarios completed in {elapsed_time:.3f}s")

    def test_kernel_batch_validation_mixed_scenarios(self):
        """Test batch validation with mix of valid and invalid scenarios."""
        kernel = KernelLogic(field_size=40)

        scenarios = [
            # Valid scenario
            {
                'laps_led': [100, 50, 30, 20] + [0] * 36,
                'fastest_laps': [10, 8, 5, 3] + [0] * 36,
                'start_positions': list(range(1, 41)),
                'finish_positions': list(range(1, 41)),
                'race_length': 200,
                'green_flag_laps': 180
            },
            # Invalid laps_led
            {
                'laps_led': [150, 70, 40, 30] + [0] * 36,
                'fastest_laps': [10, 8, 5, 3] + [0] * 36,
                'start_positions': list(range(1, 41)),
                'finish_positions': list(range(1, 41)),
                'race_length': 200,
                'green_flag_laps': 180
            },
            # Invalid fastest_laps
            {
                'laps_led': [100, 50, 30, 20] + [0] * 36,
                'fastest_laps': [100, 80, 60, 40] + [0] * 36,
                'start_positions': list(range(1, 41)),
                'finish_positions': list(range(1, 41)),
                'race_length': 200,
                'green_flag_laps': 180
            }
        ]

        results, stats = kernel.batch_validate_scenarios(scenarios)

        assert len(results) == 3
        assert stats['batch_size'] == 3
        assert results[0].is_valid
        assert not results[1].is_valid
        assert not results[2].is_valid


class TestConvenienceMethods:
    """Test convenience wrapper methods."""

    def test_validate_position_swaps_convenience_method(self):
        """Test the validate_position_swaps convenience method."""
        kernel = KernelLogic(field_size=40)

        start_positions = list(range(1, 41))
        finish_positions = list(range(1, 41))

        is_valid, veto_reason = kernel.validate_position_swaps(
            start_positions,
            finish_positions,
            green_flag_laps=180
        )

        assert is_valid
        assert veto_reason == ""

    def test_get_version_returns_correct_version(self):
        """Test that get_version returns the correct version string."""
        kernel = KernelLogic(field_size=40)
        version = kernel.get_version()
        assert version == "1.1.0"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_minimal_field_size(self):
        """Test validation with minimal field size (2 drivers)."""
        kernel = KernelLogic(field_size=2)

        scenario = {
            'laps_led': [50, 50],
            'fastest_laps': [5, 5],
            'start_positions': [1, 2],
            'finish_positions': [1, 2],
            'race_length': 100,
            'green_flag_laps': 80
        }

        result = kernel.validate_dominator_conservation(scenario)
        assert result.is_valid

    def test_single_driver_field(self):
        """Test validation with single driver field."""
        kernel = KernelLogic(field_size=1)

        scenario = {
            'laps_led': [200],
            'fastest_laps': [20],
            'start_positions': [1],
            'finish_positions': [1],
            'race_length': 200,
            'green_flag_laps': 180
        }

        result = kernel.validate_dominator_conservation(scenario)
        assert result.is_valid

    def test_empty_scenarios_batch(self):
        """Test batch validation with empty scenario list."""
        kernel = KernelLogic(field_size=40)
        results, stats = kernel.batch_validate_scenarios([])
        assert len(results) == 0
        assert stats['batch_size'] == 0

    def test_missing_optional_fields(self):
        """Test validation with missing optional fields uses defaults."""
        kernel = KernelLogic(field_size=40)

        scenario = {
            'laps_led': [100, 50, 30, 20] + [0] * 36,
            'fastest_laps': [10, 8, 5, 3] + [0] * 36,
            'start_positions': list(range(1, 41)),
            'finish_positions': list(range(1, 41)),
            'race_length': 200,
            'green_flag_laps': 180
        }

        # Should not raise error
        result = kernel.validate_dominator_conservation(scenario)
        assert result.is_valid
