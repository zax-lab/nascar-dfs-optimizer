import pytest
from app.kernel import KernelLogic

@pytest.fixture
def kernel():
    return KernelLogic(field_size=40)

def test_salary_cap_constraint(kernel):
    """Verify that KernelLogic rejects a lineup exceeding the salary cap."""
    positions = [1, 2, 3, 4, 5, 6]
    salaries = [10000, 10000, 10000, 10000, 10000, 500] # Total 50500
    salary_cap = 50000
    
    # is_impossible_state returns True if the state is impossible (invalid)
    assert kernel.is_impossible_state(positions, salaries, salary_cap) == True

def test_unique_positions_constraint(kernel):
    """Verify that KernelLogic rejects a lineup with duplicate positions."""
    positions = [1, 1, 3, 4, 5, 6] # Duplicate '1'
    assert kernel.is_impossible_state(positions) == True

def test_valid_lineup(kernel):
    """Verify that KernelLogic accepts a valid lineup."""
    positions = [1, 2, 3, 4, 5, 6]
    salaries = [8000, 8000, 8000, 8000, 8000, 8000] # Total 48000
    salary_cap = 50000
    assert kernel.is_impossible_state(positions, salaries, salary_cap) == False

def test_dominator_conservation_laps_led(kernel):
    """Verify that KernelLogic rejects a scenario where laps led > race length."""
    scenario = {
        'laps_led': [150, 60] + [0] * 38, # Total 210
        'fastest_laps': [10] * 40,
        'start_positions': list(range(1, 41)),
        'finish_positions': list(range(1, 41)),
        'race_length': 200,
        'green_flag_laps': 180
    }
    result = kernel.validate_dominator_conservation(scenario)
    assert result.is_valid == False
    assert any("Laps led conservation violated" in r for r in result.veto_reasons)

def test_dominator_conservation_valid(kernel):
    """Verify that KernelLogic accepts a valid conservation scenario."""
    scenario = {
        'laps_led': [100, 50] + [0] * 38, # Total 150 <= 200
        'fastest_laps': [10, 5] + [0] * 38, # Total 15 <= 180
        'start_positions': list(range(1, 41)),
        'finish_positions': list(range(1, 41)),
        'race_length': 200,
        'green_flag_laps': 180
    }
    result = kernel.validate_dominator_conservation(scenario)
    assert result.is_valid == True
