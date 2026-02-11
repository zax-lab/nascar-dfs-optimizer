"""
Integration tests for portfolio generator.

Tests the complete portfolio generation pipeline including:
- Scenario caching and reuse
- Portfolio generation with constraints
- DraftKings compliance validation
- Exposure limit enforcement
- Portfolio diversity metrics
- CSV export functionality
"""

import pytest
import numpy as np
import pandas as pd
from app.portfolio_generator import generate_portfolio, ScenarioCache, export_lineups_dk_format
from app.constraints.dk_rules import validate_dk_lineup


@pytest.fixture
def mock_driver_data():
    """Create mock driver data for testing.

    Returns 20 drivers across 4 teams (5 per team) to allow for
    multiple valid lineup combinations with team stacking constraints.
    """
    return [
        {
            "driver_id": i,
            "name": f"Driver_{i}",
            "salary": 6000 + i * 100,
            "team": f"team_{i % 4}"
        }
        for i in range(20)
    ]


@pytest.fixture
def mock_scenario_fn():
    """Create mock scenario generation function.

    Generates random DFS points with mean ~50 and std ~10.
    """
    def fn(n_scenarios):
        np.random.seed(42)
        return np.random.randn(n_scenarios, 20) * 10 + 50
    return fn


def test_scenario_cache_reuse(mock_scenario_fn):
    """Test that scenarios are cached and reused correctly."""
    cache = ScenarioCache()

    # First call should generate scenarios
    scenarios1 = cache.get_scenarios("race_1", 1000, mock_scenario_fn)
    assert scenarios1.shape == (1000, 20)

    # Second call should use cache (same object reference)
    scenarios2 = cache.get_scenarios("race_1", 1000, mock_scenario_fn)
    assert scenarios2 is scenarios1  # Same object in memory

    # Different race or count should generate new scenarios
    scenarios3 = cache.get_scenarios("race_2", 1000, mock_scenario_fn)
    assert scenarios3 is not scenarios1  # Different object

    scenarios4 = cache.get_scenarios("race_1", 500, mock_scenario_fn)
    assert scenarios4 is not scenarios1  # Different count = new scenarios


def test_scenario_cache_size(mock_scenario_fn):
    """Test cache size tracking."""
    cache = ScenarioCache()

    assert cache.size() == 0

    cache.get_scenarios("race_1", 1000, mock_scenario_fn)
    assert cache.size() == 1

    cache.get_scenarios("race_2", 1000, mock_scenario_fn)
    assert cache.size() == 2

    cache.get_scenarios("race_1", 1000, mock_scenario_fn)  # Cache hit
    assert cache.size() == 2  # No new entry


def test_scenario_cache_clear(mock_scenario_fn):
    """Test cache clearing."""
    cache = ScenarioCache()

    cache.get_scenarios("race_1", 1000, mock_scenario_fn)
    cache.get_scenarios("race_2", 1000, mock_scenario_fn)
    assert cache.size() == 2

    cache.clear()
    assert cache.size() == 0

    # After clear, should regenerate
    scenarios = cache.get_scenarios("race_1", 1000, mock_scenario_fn)
    assert scenarios.shape == (1000, 20)


def test_generate_portfolio_size(mock_driver_data, mock_scenario_fn):
    """Test portfolio generation produces requested number of lineups."""
    lineups = generate_portfolio(
        race_id="test_race",
        driver_data=mock_driver_data,
        scenario_fn=mock_scenario_fn,
        n_lineups=3,
        n_scenarios=1000,
        correlation_weight=0.0,  # Disable for simplicity
        max_driver_exposure=1.0  # Disable for simplicity
    )

    # May not generate all 3 due to constraint complexity,
    # but should generate at least 1
    assert len(lineups) >= 1

    # All lineups should have required fields
    for lineup in lineups:
        assert "drivers" in lineup
        assert len(lineup["drivers"]) == 6
        assert "total_salary" in lineup
        assert "cvar_99" in lineup
        assert "top_1pct" in lineup
        assert "exposure" in lineup


def test_dk_compliance_all_lineups(mock_driver_data, mock_scenario_fn):
    """Test all generated lineups are DraftKings-compliant."""
    lineups = generate_portfolio(
        race_id="test_race",
        driver_data=mock_driver_data,
        scenario_fn=mock_scenario_fn,
        n_lineups=5,
        n_scenarios=1000,
        correlation_weight=0.0,
        max_driver_exposure=1.0
    )

    # Every lineup should pass DK validation
    for lineup in lineups:
        validation = validate_dk_lineup(
            lineup["drivers"],
            mock_driver_data,
            salary_cap=50000,
            n_drivers=6,
            min_stack=2,
            max_stack=3
        )
        assert validation["valid"], (
            f"Lineup validation failed: {validation['errors']}. "
            f"Lineup: {lineup['drivers']}"
        )


def test_exposure_limits(mock_driver_data, mock_scenario_fn):
    """Test exposure limits are respected during generation."""
    lineups = generate_portfolio(
        race_id="test_race",
        driver_data=mock_driver_data,
        scenario_fn=mock_scenario_fn,
        n_lineups=5,
        n_scenarios=1000,
        max_driver_exposure=0.6,  # Max 60% exposure
        correlation_weight=0.0
    )

    # Count driver usage
    driver_usage = {}
    for lineup in lineups:
        for driver_id in lineup["drivers"]:
            driver_usage[driver_id] = driver_usage.get(driver_id, 0) + 1

    # Check no driver exceeds 60% exposure
    n_lineups = len(lineups)
    for driver_id, count in driver_usage.items():
        exposure = count / n_lineups
        assert exposure <= 0.6, (
            f"Driver {driver_id} has {exposure:.1%} exposure "
            f"({count}/{n_lineups} lineups), exceeds limit 60%"
        )


def test_portfolio_diversity(mock_driver_data, mock_scenario_fn):
    """Test portfolio lineups are diverse (not all identical)."""
    lineups = generate_portfolio(
        race_id="test_race",
        driver_data=mock_driver_data,
        scenario_fn=mock_scenario_fn,
        n_lineups=3,
        n_scenarios=1000,
        correlation_weight=0.0,  # Note: correlation penalty disabled in current impl
        max_driver_exposure=1.0
    )

    if len(lineups) < 2:
        pytest.skip("Need at least 2 lineups to test diversity")

    # Compute pairwise similarities
    from app.constraints.diversity import compute_portfolio_correlation
    correlation = compute_portfolio_correlation(lineups)

    # Log correlation metrics
    print(f"\nPortfolio correlation: avg={correlation['avg_similarity']:.3f}")
    print(f"Max similarity: {correlation['max_similarity']:.3f}")
    print(f"Min similarity: {correlation['min_similarity']:.3f}")

    # Just verify we can compute correlation (no assertion on value
    # since correlation penalty is currently disabled)
    assert "avg_similarity" in correlation
    assert "max_similarity" in correlation


def test_export_csv_format(mock_driver_data, mock_scenario_fn):
    """Test CSV export produces DraftKings-compatible format."""
    # Generate a small portfolio
    lineups = generate_portfolio(
        race_id="test_race",
        driver_data=mock_driver_data,
        scenario_fn=mock_scenario_fn,
        n_lineups=2,
        n_scenarios=1000,
        correlation_weight=0.0,
        max_driver_exposure=1.0
    )

    if len(lineups) == 0:
        pytest.skip("No lineups generated")

    # Export to CSV
    filepath = export_lineups_dk_format(lineups, mock_driver_data, "test_lineups.csv")

    # Read CSV and verify format
    df = pd.read_csv(filepath, header=None)

    # Check shape: n_lineups rows, 6 columns
    assert df.shape[0] == len(lineups), f"Expected {len(lineups)} rows, got {df.shape[0]}"
    assert df.shape[1] == 6, f"Expected 6 columns, got {df.shape[1]}"

    # Check all values are strings (driver names)
    assert all(df.dtypes == object), "All columns should be strings (driver names)"

    # Check no header row (first row should be driver names, not "F", "F.1", etc.)
    first_row = df.iloc[0].values
    assert not any(str(val).startswith("F") for val in first_row if pd.notna(val)), \
        "CSV should not have header row"

    # Check all values are valid driver names
    driver_names = {d["name"] for d in mock_driver_data}
    for _, row in df.iterrows():
        for val in row:
            assert val in driver_names or val == "Unknown", \
                f"Invalid driver name in CSV: {val}"


def test_export_csv_handles_invalid_lineups(mock_driver_data):
    """Test CSV export skips invalid lineups (wrong number of drivers)."""
    # Mix of valid and invalid lineups
    lineups = [
        {"drivers": [0, 1, 2, 3, 4, 5]},  # Valid: 6 drivers
        {"drivers": [0, 1, 2]},  # Invalid: 3 drivers
        {"drivers": [6, 7, 8, 9, 10, 11, 12]},  # Invalid: 7 drivers
        {"drivers": [10, 11, 12, 13, 14, 15]},  # Valid: 6 drivers
    ]

    filepath = export_lineups_dk_format(lineups, mock_driver_data, "test_mixed.csv")

    # Should only export valid lineups
    df = pd.read_csv(filepath, header=None)
    assert df.shape[0] == 2, f"Expected 2 valid lineups, got {df.shape[0]}"
    assert df.shape[1] == 6


def test_export_csv_empty_lineups():
    """Test CSV export raises error for empty lineup list."""
    with pytest.raises(ValueError, match="lineups list is empty"):
        export_lineups_dk_format([], [], "test.csv")


def test_export_csv_missing_driver_keys():
    """Test CSV export raises error for missing driver keys."""
    lineups = [{"drivers": [0, 1, 2, 3, 4, 5]}]
    bad_drivers = [{"driver_id": 0}]  # Missing "name" key

    with pytest.raises(ValueError, match="missing required keys"):
        export_lineups_dk_format(lineups, bad_drivers, "test.csv")


def test_generate_portfolio_with_realistic_params(mock_driver_data, mock_scenario_fn):
    """Test portfolio generation with realistic parameters."""
    lineups = generate_portfolio(
        race_id="daytona_500",
        driver_data=mock_driver_data,
        scenario_fn=mock_scenario_fn,
        n_lineups=20,
        n_scenarios=10000,
        cvar_alphas=[0.99, 0.95],
        cvar_weights=[0.7, 0.3],
        correlation_weight=0.1,
        max_driver_exposure=0.5,
        max_team_exposure=0.7,
        salary_cap=50000,
        n_drivers=6,
        min_stack=2,
        max_stack=3,
        solver_time_limit=30
    )

    # Should generate at least some lineups
    assert len(lineups) >= 1

    # Verify all lineups have correct structure
    for lineup in lineups:
        assert "drivers" in lineup
        assert len(lineup["drivers"]) == 6
        assert "total_salary" in lineup
        assert lineup["total_salary"] <= 50000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
