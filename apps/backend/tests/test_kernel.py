"""
Tests for kernel.py KernelLogic class.
"""
import pytest
from app.kernel import KernelLogic


def test_kernel_logic_initialization() -> None:
    """
    Test KernelLogic initialization with default field size.
    """
    kernel = KernelLogic()
    assert kernel.get_field_size() == 40


def test_kernel_logic_custom_field_size() -> None:
    """
    Test KernelLogic initialization with custom field size.
    """
    kernel = KernelLogic(field_size=36)
    assert kernel.get_field_size() == 36


def test_validate_position_valid() -> None:
    """
    Test validate_position with valid positions.
    """
    kernel = KernelLogic(field_size=40)
    assert kernel.validate_position(1) is True
    assert kernel.validate_position(20) is True
    assert kernel.validate_position(40) is True


def test_validate_position_invalid_below_range() -> None:
    """
    Test validate_position with position below valid range.
    """
    kernel = KernelLogic(field_size=40)
    assert kernel.validate_position(0) is False
    assert kernel.validate_position(-1) is False
    assert kernel.validate_position(-10) is False


def test_validate_position_invalid_above_range() -> None:
    """
    Test validate_position with position above valid range.
    """
    kernel = KernelLogic(field_size=40)
    assert kernel.validate_position(41) is False
    assert kernel.validate_position(50) is False
    assert kernel.validate_position(100) is False


def test_validate_lineup_positions_valid() -> None:
    """
    Test validate_lineup_positions with all valid positions.
    """
    kernel = KernelLogic(field_size=40)
    positions = [1, 2, 3, 4, 5, 6]
    assert kernel.validate_lineup_positions(positions) is True


def test_validate_lineup_positions_invalid() -> None:
    """
    Test validate_lineup_positions with invalid positions.
    """
    kernel = KernelLogic(field_size=40)
    positions = [1, 2, 3, 4, 5, 41]
    assert kernel.validate_lineup_positions(positions) is False


def test_validate_unique_positions_valid() -> None:
    """
    Test validate_unique_positions with all unique positions.
    """
    kernel = KernelLogic()
    positions = [1, 2, 3, 4, 5, 6]
    assert kernel.validate_unique_positions(positions) is True


def test_validate_unique_positions_invalid() -> None:
    """
    Test validate_unique_positions with duplicate positions.
    """
    kernel = KernelLogic()
    positions = [1, 2, 3, 4, 5, 5]
    assert kernel.validate_unique_positions(positions) is False


def test_validate_lineup_size_valid() -> None:
    """
    Test validate_lineup_size with correct lineup size.
    """
    kernel = KernelLogic()
    assert kernel.validate_lineup_size(6) is True


def test_validate_lineup_size_invalid() -> None:
    """
    Test validate_lineup_size with incorrect lineup size.
    """
    kernel = KernelLogic()
    assert kernel.validate_lineup_size(5) is False
    assert kernel.validate_lineup_size(7) is False


def test_validate_lineup_size_custom() -> None:
    """
    Test validate_lineup_size with custom required size.
    """
    kernel = KernelLogic()
    assert kernel.validate_lineup_size(5, required_size=5) is True


def test_is_impossible_state_valid() -> None:
    """
    Test is_impossible_state with valid state.
    """
    kernel = KernelLogic(field_size=40)
    positions = [1, 2, 3, 4, 5, 6]
    assert kernel.is_impossible_state(positions) is False


def test_is_impossible_state_invalid_position() -> None:
    """
    Test is_impossible_state with invalid position.
    """
    kernel = KernelLogic(field_size=40)
    positions = [1, 2, 3, 4, 5, 41]
    assert kernel.is_impossible_state(positions) is True


def test_is_impossible_state_duplicate_positions() -> None:
    """
    Test is_impossible_state with duplicate positions.
    """
    kernel = KernelLogic(field_size=40)
    positions = [1, 2, 3, 4, 5, 5]
    assert kernel.is_impossible_state(positions) is True


def test_is_impossible_state_salary_exceeds_cap() -> None:
    """
    Test is_impossible_state when salary exceeds cap.
    """
    kernel = KernelLogic(field_size=40)
    positions = [1, 2, 3, 4, 5, 6]
    salaries = [10000, 10000, 10000, 10000, 10000, 10000]
    assert kernel.is_impossible_state(positions, salaries, salary_cap=50000) is True


def test_is_impossible_state_salary_within_cap() -> None:
    """
    Test is_impossible_state when salary is within cap.
    """
    kernel = KernelLogic(field_size=40)
    positions = [1, 2, 3, 4, 5, 6]
    salaries = [8000, 7500, 7000, 6500, 6000, 5500]
    assert kernel.is_impossible_state(positions, salaries, salary_cap=50000) is False


def test_set_field_size_valid() -> None:
    """
    Test set_field_size with valid value.
    """
    kernel = KernelLogic(field_size=40)
    kernel.set_field_size(36)
    assert kernel.get_field_size() == 36


def test_set_field_size_invalid() -> None:
    """
    Test set_field_size with invalid value.
    """
    kernel = KernelLogic(field_size=40)
    with pytest.raises(ValueError, match="Field size must be at least 1"):
        kernel.set_field_size(0)
    
    with pytest.raises(ValueError, match="Field size must be at least 1"):
        kernel.set_field_size(-1)


def test_set_field_size_updates_validation() -> None:
    """
    Test that set_field_size updates position validation.
    """
    kernel = KernelLogic(field_size=40)
    assert kernel.validate_position(40) is True
    
    kernel.set_field_size(36)
    assert kernel.validate_position(40) is False
    assert kernel.validate_position(36) is True
