"""
Tests for optimizer.py LineupOptimizer class.
"""
from app.lineup_optimizer import LineupOptimizer


def test_optimizer_initialization() -> None:
    """
    Test LineupOptimizer initialization.
    """
    drivers = [
        {
            "driver_id": "driver1",
            "name": "Driver One",
            "salary": 8000,
            "projected_points": 45.5,
            "position": 1,
        },
        {
            "driver_id": "driver2",
            "name": "Driver Two",
            "salary": 7500,
            "projected_points": 42.3,
            "position": 2,
        },
    ]
    
    optimizer = LineupOptimizer(drivers=drivers, salary_cap=50000, lineup_size=6)
    assert optimizer.salary_cap == 50000
    assert optimizer.lineup_size == 6
    assert len(optimizer.drivers) == 2


def test_optimize_valid_lineup() -> None:
    """
    Test optimize with valid driver data.
    """
    drivers = [
        {
            "driver_id": "driver1",
            "name": "Driver One",
            "salary": 8000,
            "projected_points": 45.5,
            "position": 1,
        },
        {
            "driver_id": "driver2",
            "name": "Driver Two",
            "salary": 7500,
            "projected_points": 42.3,
            "position": 2,
        },
        {
            "driver_id": "driver3",
            "name": "Driver Three",
            "salary": 7000,
            "projected_points": 38.7,
            "position": 3,
        },
        {
            "driver_id": "driver4",
            "name": "Driver Four",
            "salary": 6500,
            "projected_points": 35.2,
            "position": 4,
        },
        {
            "driver_id": "driver5",
            "name": "Driver Five",
            "salary": 6000,
            "projected_points": 32.1,
            "position": 5,
        },
        {
            "driver_id": "driver6",
            "name": "Driver Six",
            "salary": 5500,
            "projected_points": 28.9,
            "position": 6,
        },
        {
            "driver_id": "driver7",
            "name": "Driver Seven",
            "salary": 5000,
            "projected_points": 25.4,
            "position": 7,
        },
    ]
    
    optimizer = LineupOptimizer(drivers=drivers, salary_cap=50000, lineup_size=6)
    result = optimizer.optimize()
    
    assert result is not None
    assert len(result["drivers"]) == 6
    assert result["total_salary"] <= 50000
    assert result["total_projected_points"] > 0
    
    # Verify all selected drivers have required fields
    for driver in result["drivers"]:
        assert "driver_id" in driver
        assert "name" in driver
        assert "salary" in driver
        assert "projected_points" in driver
        assert "position" in driver


def test_optimize_insufficient_drivers() -> None:
    """
    Test optimize with fewer than required drivers.
    """
    drivers = [
        {
            "driver_id": "driver1",
            "name": "Driver One",
            "salary": 8000,
            "projected_points": 45.5,
            "position": 1,
        },
        {
            "driver_id": "driver2",
            "name": "Driver Two",
            "salary": 7500,
            "projected_points": 42.3,
            "position": 2,
        },
        {
            "driver_id": "driver3",
            "name": "Driver Three",
            "salary": 7000,
            "projected_points": 38.7,
            "position": 3,
        },
        {
            "driver_id": "driver4",
            "name": "Driver Four",
            "salary": 6500,
            "projected_points": 35.2,
            "position": 4,
        },
        {
            "driver_id": "driver5",
            "name": "Driver Five",
            "salary": 6000,
            "projected_points": 32.1,
            "position": 5,
        },
    ]
    
    optimizer = LineupOptimizer(drivers=drivers, salary_cap=50000, lineup_size=6)
    result = optimizer.optimize()
    
    assert result is None


def test_optimize_salary_cap_exceeded() -> None:
    """
    Test optimize when salary cap is too low.
    """
    drivers = [
        {
            "driver_id": "driver1",
            "name": "Driver One",
            "salary": 12000,
            "projected_points": 55.5,
            "position": 1,
        },
        {
            "driver_id": "driver2",
            "name": "Driver Two",
            "salary": 11500,
            "projected_points": 52.3,
            "position": 2,
        },
        {
            "driver_id": "driver3",
            "name": "Driver Three",
            "salary": 11000,
            "projected_points": 48.7,
            "position": 3,
        },
        {
            "driver_id": "driver4",
            "name": "Driver Four",
            "salary": 10500,
            "projected_points": 45.2,
            "position": 4,
        },
        {
            "driver_id": "driver5",
            "name": "Driver Five",
            "salary": 10000,
            "projected_points": 42.1,
            "position": 5,
        },
        {
            "driver_id": "driver6",
            "name": "Driver Six",
            "salary": 9500,
            "projected_points": 38.9,
            "position": 6,
        },
    ]
    
    optimizer = LineupOptimizer(drivers=drivers, salary_cap=30000, lineup_size=6)
    result = optimizer.optimize()
    
    assert result is None


def test_optimize_custom_salary_cap() -> None:
    """
    Test optimize with custom salary cap.
    """
    drivers = [
        {
            "driver_id": "driver1",
            "name": "Driver One",
            "salary": 8000,
            "projected_points": 45.5,
            "position": 1,
        },
        {
            "driver_id": "driver2",
            "name": "Driver Two",
            "salary": 7500,
            "projected_points": 42.3,
            "position": 2,
        },
        {
            "driver_id": "driver3",
            "name": "Driver Three",
            "salary": 7000,
            "projected_points": 38.7,
            "position": 3,
        },
        {
            "driver_id": "driver4",
            "name": "Driver Four",
            "salary": 6500,
            "projected_points": 35.2,
            "position": 4,
        },
        {
            "driver_id": "driver5",
            "name": "Driver Five",
            "salary": 6000,
            "projected_points": 32.1,
            "position": 5,
        },
        {
            "driver_id": "driver6",
            "name": "Driver Six",
            "salary": 5500,
            "projected_points": 28.9,
            "position": 6,
        },
        {
            "driver_id": "driver7",
            "name": "Driver Seven",
            "salary": 5000,
            "projected_points": 25.4,
            "position": 7,
        },
    ]
    
    optimizer = LineupOptimizer(drivers=drivers, salary_cap=40000, lineup_size=6)
    result = optimizer.optimize()
    
    assert result is not None
    assert len(result["drivers"]) == 6
    assert result["total_salary"] <= 40000


def test_get_salary_distribution() -> None:
    """
    Test get_salary_distribution method.
    """
    drivers = [
        {
            "driver_id": "driver1",
            "name": "Driver One",
            "salary": 4000,
            "projected_points": 35.5,
            "position": 1,
        },
        {
            "driver_id": "driver2",
            "name": "Driver Two",
            "salary": 6000,
            "projected_points": 38.3,
            "position": 2,
        },
        {
            "driver_id": "driver3",
            "name": "Driver Three",
            "salary": 9000,
            "projected_points": 42.7,
            "position": 3,
        },
        {
            "driver_id": "driver4",
            "name": "Driver Four",
            "salary": 12000,
            "projected_points": 48.2,
            "position": 4,
        },
        {
            "driver_id": "driver5",
            "name": "Driver Five",
            "salary": 18000,
            "projected_points": 55.1,
            "position": 5,
        },
        {
            "driver_id": "driver6",
            "name": "Driver Six",
            "salary": 7500,
            "projected_points": 40.9,
            "position": 6,
        },
    ]
    
    optimizer = LineupOptimizer(drivers=drivers, salary_cap=50000, lineup_size=6)
    distribution = optimizer.get_salary_distribution()
    
    assert "0-5000" in distribution
    assert "5001-10000" in distribution
    assert "10001-15000" in distribution
    assert "15001-20000" in distribution
    assert "20001+" in distribution
    assert distribution["0-5000"] == 1
    assert distribution["5001-10000"] == 3
    assert distribution["10001-15000"] == 1
    assert distribution["15001-20000"] == 1
    assert distribution["20001+"] == 0  # No drivers in this salary range


def test_get_projection_summary() -> None:
    """
    Test get_projection_summary method.
    """
    drivers = [
        {
            "driver_id": "driver1",
            "name": "Driver One",
            "salary": 8000,
            "projected_points": 45.5,
            "position": 1,
        },
        {
            "driver_id": "driver2",
            "name": "Driver Two",
            "salary": 7500,
            "projected_points": 42.3,
            "position": 2,
        },
        {
            "driver_id": "driver3",
            "name": "Driver Three",
            "salary": 7000,
            "projected_points": 38.7,
            "position": 3,
        },
        {
            "driver_id": "driver4",
            "name": "Driver Four",
            "salary": 6500,
            "projected_points": 35.2,
            "position": 4,
        },
        {
            "driver_id": "driver5",
            "name": "Driver Five",
            "salary": 6000,
            "projected_points": 32.1,
            "position": 5,
        },
        {
            "driver_id": "driver6",
            "name": "Driver Six",
            "salary": 5500,
            "projected_points": 28.9,
            "position": 6,
        },
    ]
    
    optimizer = LineupOptimizer(drivers=drivers, salary_cap=50000, lineup_size=6)
    summary = optimizer.get_projection_summary()
    
    assert "min" in summary
    assert "max" in summary
    assert "mean" in summary
    assert "median" in summary
    assert summary["min"] == 28.9
    assert summary["max"] == 45.5
    assert summary["mean"] == 37.11666666666667
    assert summary["median"] == 36.95  # (35.2 + 38.7) / 2 for even-length list


def test_get_projection_summary_empty() -> None:
    """
    Test get_projection_summary with empty driver list.
    """
    drivers = []
    
    optimizer = LineupOptimizer(drivers=drivers, salary_cap=50000, lineup_size=6)
    summary = optimizer.get_projection_summary()
    
    assert summary["min"] == 0.0
    assert summary["max"] == 0.0
    assert summary["mean"] == 0.0
    assert summary["median"] == 0.0


def test_get_multiple_lineups() -> None:
    """
    Test get_multiple_lineups method.
    """
    drivers = [
        {
            "driver_id": "driver1",
            "name": "Driver One",
            "salary": 8000,
            "projected_points": 45.5,
            "position": 1,
        },
        {
            "driver_id": "driver2",
            "name": "Driver Two",
            "salary": 7500,
            "projected_points": 42.3,
            "position": 2,
        },
        {
            "driver_id": "driver3",
            "name": "Driver Three",
            "salary": 7000,
            "projected_points": 38.7,
            "position": 3,
        },
        {
            "driver_id": "driver4",
            "name": "Driver Four",
            "salary": 6500,
            "projected_points": 35.2,
            "position": 4,
        },
        {
            "driver_id": "driver5",
            "name": "Driver Five",
            "salary": 6000,
            "projected_points": 32.1,
            "position": 5,
        },
        {
            "driver_id": "driver6",
            "name": "Driver Six",
            "salary": 5500,
            "projected_points": 28.9,
            "position": 6,
        },
        {
            "driver_id": "driver7",
            "name": "Driver Seven",
            "salary": 5000,
            "projected_points": 25.4,
            "position": 7,
        },
        {
            "driver_id": "driver8",
            "name": "Driver Eight",
            "salary": 4500,
            "projected_points": 22.1,
            "position": 8,
        },
    ]
    
    optimizer = LineupOptimizer(drivers=drivers, salary_cap=50000, lineup_size=6)
    lineups = optimizer.get_multiple_lineups(num_lineups=2)
    
    # With 8 drivers and lineup_size=6, after first lineup only 2 remain
    # So we can only generate 1 lineup
    assert len(lineups) >= 1
    assert len(lineups) <= 2  # May generate 1 or 2 depending on constraints
    for lineup in lineups:
        assert len(lineup["drivers"]) == 6
        assert lineup["total_salary"] <= 50000
        assert lineup["total_projected_points"] > 0
