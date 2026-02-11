import pytest
import numpy as np
from app.portfolio_generator import generate_portfolio

@pytest.fixture
def fixed_driver_data():
    """Mock driver data for a standard field."""
    return [
        {"driver_id": i, "name": f"Driver_{i}", "salary": 5000 + (i % 10) * 1000, "team": f"team_{i % 5}"}
        for i in range(40)
    ]

@pytest.fixture
def scenario_fn():
    """Deterministic scenario generator."""
    def _scenario_fn(n_scenarios):
        # Return a larger matrix for 40 drivers
        state = np.random.RandomState(42)
        return state.randn(n_scenarios, 40) * 10 + 50
    return _scenario_fn

def test_optimization_determinism(fixed_driver_data, scenario_fn):
    """Verify that optimization with the same seed produces identical results."""
    n_lineups = 2
    n_scenarios = 1000
    seed = 42
    
    # Run 1
    lineups1 = generate_portfolio(
        race_id="deterministic_test",
        driver_data=fixed_driver_data,
        scenario_fn=scenario_fn,
        n_lineups=n_lineups,
        n_scenarios=n_scenarios,
        random_seed=seed,
        correlation_weight=0.0 # Disable diversity penalty to ensure identical paths
    )
    
    # Run 2
    lineups2 = generate_portfolio(
        race_id="deterministic_test",
        driver_data=fixed_driver_data,
        scenario_fn=scenario_fn,
        n_lineups=n_lineups,
        n_scenarios=n_scenarios,
        random_seed=seed,
        correlation_weight=0.0
    )
    
    assert len(lineups1) == n_lineups
    assert len(lineups2) == n_lineups
    
    # Verify each lineup's drivers are the same
    for l1, l2 in zip(lineups1, lineups2):
        assert sorted(l1["drivers"]) == sorted(l2["drivers"])
        assert pytest.approx(l1["cvar_99"]) == l2["cvar_99"]