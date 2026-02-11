import pytest
import numpy as np
from apps.backend.app.portfolio_generator import generate_portfolio

@pytest.fixture
def fixed_driver_data():
    """Mock driver data for a standard field."""
    return [
        {"driver_id": i, "name": f"Driver_{i}", "salary": 8000, "team": f"team_{i % 5}"}
        for i in range(40)
    ]

def test_metaphysical_impact(fixed_driver_data):
    """Verify that changing a driver's performance distribution (skill) impacts their selection."""
    n_lineups = 1
    n_scenarios = 1000
    target_driver_id = 0
    
    # We use "mean" optimization to avoid CVaR tail instability issues in this simple test
    obj_type = "mean"
    
    # 1. Baseline: All drivers have identical distributions
    def baseline_scenario_fn(n):
        state = np.random.RandomState(42)
        return state.randn(n, 40) * 10 + 50
    
    lineups_baseline = generate_portfolio(
        race_id="baseline",
        driver_data=fixed_driver_data,
        scenario_fn=baseline_scenario_fn,
        n_lineups=n_lineups,
        n_scenarios=n_scenarios,
        random_seed=42,
        min_stack=1,
        objective_type=obj_type
    )
    
    baseline_drivers = lineups_baseline[0]["drivers"]
    print(f"Baseline Drivers: {baseline_drivers}")
    
    # 2. Impact: Boost Driver 0's "skill" drastically
    def boosted_scenario_fn(n):
        state = np.random.RandomState(42)
        scenarios = state.randn(n, 40) * 10 + 50
        # Give Driver 0 a massive points boost
        scenarios[:, target_driver_id] += 100 
        return scenarios
    
    lineups_boosted = generate_portfolio(
        race_id="boosted",
        driver_data=fixed_driver_data,
        scenario_fn=boosted_scenario_fn,
        n_lineups=n_lineups,
        n_scenarios=n_scenarios,
        random_seed=42,
        min_stack=1,
        objective_type=obj_type
    )
    
    boosted_drivers = lineups_boosted[0]["drivers"]
    print(f"Boosted Drivers: {boosted_drivers}")
    
    # Driver 0 SHOULD be in the boosted lineup
    assert target_driver_id in boosted_drivers
    
    # 3. Impact: Tank Driver 0's "skill"
    def tanked_scenario_fn(n):
        state = np.random.RandomState(42)
        scenarios = state.randn(n, 40) * 10 + 50
        scenarios[:, target_driver_id] -= 100 
        return scenarios
    
    lineups_tanked = generate_portfolio(
        race_id="tanked",
        driver_data=fixed_driver_data,
        scenario_fn=tanked_scenario_fn,
        n_lineups=n_lineups,
        n_scenarios=n_scenarios,
        random_seed=42,
        min_stack=1,
        objective_type=obj_type
    )
    
    tanked_drivers = lineups_tanked[0]["drivers"]
    print(f"Tanked Drivers: {tanked_drivers}")
    
    # Driver 0 SHOULD NOT be in the tanked lineup
    assert target_driver_id not in tanked_drivers
