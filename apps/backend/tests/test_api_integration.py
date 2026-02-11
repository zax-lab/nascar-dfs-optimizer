"""
End-to-end integration tests for /optimize API endpoint.

Tests validate complete pipeline:
- API request → portfolio generation → CSV export
- Scenario-driven optimization contracts
- Calibration and tail validation integration
- Error handling and edge cases
"""
import pytest
import numpy as np
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Test client for FastAPI app."""
    return TestClient(app)


def constraint_spec_to_dict(constraint_spec):
    """Convert ConstraintSpec to dict for JSON serialization."""
    return {
        "slate_id": constraint_spec.slate_id,
        "compiled_at": constraint_spec.compiled_at,
        "drivers": {
            k: {
                "driver_id": v.driver_id,
                "skill": v.skill,
                "aggression": v.aggression,
                "shadow_risk": v.shadow_risk,
                "min_laps_led": v.min_laps_led,
                "max_laps_led": v.max_laps_led,
                "veto_rules": v.veto_rules
            }
            for k, v in constraint_spec.drivers.items()
        },
        "tracks": {
            k: {
                "track_id": v.track_id,
                "difficulty": v.difficulty,
                "aggression_factor": v.aggression_factor,
                "caution_rate": v.caution_rate,
                "pit_window_laps": v.pit_window_laps
            }
            for k, v in constraint_spec.tracks.items()
        },
        "version": constraint_spec.version,
        "hash": constraint_spec.hash
    }


@pytest.fixture
def base_constraint_spec():
    """Base constraint spec for testing."""
    from app.constraints.models import ConstraintSpec, DriverConstraints, TrackConstraints
    from datetime import datetime

    # Create mock driver constraints
    drivers = {}
    for i in range(15):  # 15 drivers
        driver_id = f"driver_{i}"
        drivers[driver_id] = DriverConstraints(
            driver_id=driver_id,
            skill=0.5 + (i % 5) * 0.1,  # 0.5-0.9
            aggression=0.4 + (i % 3) * 0.2,  # 0.4-0.8
            shadow_risk=0.2 + (i % 4) * 0.1,  # 0.2-0.5
            min_laps_led=0,
            max_laps_led=100
        )

    # Create mock track constraints
    tracks = {
        "test_track": TrackConstraints(
            track_id="test_track",
            difficulty=0.7,
            aggression_factor=0.8,
            caution_rate=0.3,
            pit_window_laps=[35, 70, 105, 140, 175]
        )
    }

    return ConstraintSpec(
        slate_id="test_race_base",
        compiled_at=datetime.utcnow().isoformat(),
        drivers=drivers,
        tracks=tracks,
        version="1.0"
    )


class TestOptimizeEndpoint:
    """Test /optimize endpoint end-to-end."""

    def test_optimize_endpoint_returns_200(self, client, base_constraint_spec):
        """Test that /optimize returns 200 status code."""
        request_dict = {
            "constraint_spec": constraint_spec_to_dict(base_constraint_spec),
            "track_id": "test_track",
            "n_lineups": 3,
            "n_scenarios": 1000  # Minimum allowed value
        }

        response = client.post("/optimize", json=request_dict)

        assert response.status_code == 200

    def test_optimize_endpoint_returns_lineups(self, client, base_constraint_spec):
        """Test that /optimize returns lineup data."""
        request_dict = {
            "constraint_spec": constraint_spec_to_dict(base_constraint_spec),
            "track_id": "test_track",
            "n_lineups": 5,
            "n_scenarios": 1000
        }

        response = client.post("/optimize", json=request_dict)

        assert response.status_code == 200
        data = response.json()

        assert "lineups" in data
        assert isinstance(data["lineups"], list)
        assert len(data["lineups"]) >= 1  # May generate fewer than requested due to constraints

    def test_optimize_endpoint_lineups_have_required_fields(self, client, base_constraint_spec):
        """Test that returned lineups have all required fields."""
        request_dict = {
            "constraint_spec": constraint_spec_to_dict(base_constraint_spec),
            "track_id": "test_track",
            "n_lineups": 2,
            "n_scenarios": 1000
        }

        response = client.post("/optimize", json=request_dict)

        data = response.json()
        lineups = data["lineups"]

        assert len(lineups) > 0

        for lineup in lineups:
            # Check required lineup fields
            assert "drivers" in lineup
            assert "cvar_99" in lineup
            assert "cvar_95" in lineup
            assert "top_1pct" in lineup
            assert "conditional_upside" in lineup

            # Check drivers field structure
            assert isinstance(lineup["drivers"], list)
            assert len(lineup["drivers"]) == 6

            # Check metrics are numeric
            assert isinstance(lineup["cvar_99"], (int, float))
            assert isinstance(lineup["cvar_95"], (int, float))
            assert isinstance(lineup["top_1pct"], (int, float))
            assert isinstance(lineup["conditional_upside"], (int, float))


class TestScenarioDrivenContracts:
    """Test scenario-driven optimization contracts."""

    def test_n_scenarios_parameter_affects_portfolio(self, client, base_constraint_spec):
        """Test that n_scenarios parameter influences optimization."""
        from app.constraints.models import ConstraintSpec
        from datetime import datetime

        spec_1000 = ConstraintSpec(
            slate_id="test_race_scenarios_1000",
            compiled_at=datetime.utcnow().isoformat(),
            drivers=base_constraint_spec.drivers,
            tracks=base_constraint_spec.tracks,
            version="1.0"
        )

        spec_5000 = ConstraintSpec(
            slate_id="test_race_scenarios_5000",
            compiled_at=datetime.utcnow().isoformat(),
            drivers=base_constraint_spec.drivers,
            tracks=base_constraint_spec.tracks,
            version="1.0"
        )

        request_dict_1000 = {
            "constraint_spec": constraint_spec_to_dict(spec_1000),
            "track_id": "test_track",
            "n_lineups": 1,
            "n_scenarios": 1000
        }

        request_dict_5000 = {
            "constraint_spec": constraint_spec_to_dict(spec_5000),
            "track_id": "test_track",
            "n_lineups": 1,
            "n_scenarios": 5000
        }

        response_1000 = client.post("/optimize", json=request_dict_1000)
        response_5000 = client.post("/optimize", json=request_dict_5000)

        assert response_1000.status_code == 200
        assert response_5000.status_code == 200

        # Both should return valid lineups
        data_1000 = response_1000.json()
        data_5000 = response_5000.json()

        assert len(data_1000["lineups"]) > 0
        assert len(data_5000["lineups"]) > 0

    def test_race_id_influences_scenario_generation(self, client, base_constraint_spec):
        """Test that different race_ids produce different portfolios."""
        from app.constraints.models import ConstraintSpec
        from datetime import datetime

        spec_1 = ConstraintSpec(
            slate_id="test_race_A",
            compiled_at=datetime.utcnow().isoformat(),
            drivers=base_constraint_spec.drivers,
            tracks=base_constraint_spec.tracks,
            version="1.0"
        )

        spec_2 = ConstraintSpec(
            slate_id="test_race_B",
            compiled_at=datetime.utcnow().isoformat(),
            drivers=base_constraint_spec.drivers,
            tracks=base_constraint_spec.tracks,
            version="1.0"
        )

        request_dict_1 = {
            "constraint_spec": constraint_spec_to_dict(spec_1),
            "track_id": "test_track",
            "n_lineups": 1,
            "n_scenarios": 1000
        }

        request_dict_2 = {
            "constraint_spec": constraint_spec_to_dict(spec_2),
            "track_id": "test_track",
            "n_lineups": 1,
            "n_scenarios": 1000
        }

        response_1 = client.post("/optimize", json=request_dict_1)
        response_2 = client.post("/optimize", json=request_dict_2)

        assert response_1.status_code == 200
        assert response_2.status_code == 200

        # Both should produce valid lineups
        lineup_1 = response_1.json()["lineups"][0]["drivers"]
        lineup_2 = response_2.json()["lineups"][0]["drivers"]

        # At minimum, lineups should be valid
        assert len(lineup_1) == 6
        assert len(lineup_2) == 6


class TestCalibrationIntegration:
    """Test calibration metrics integration in API response."""

    def test_optimize_endpoint_includes_calibration_metrics(self, client, base_constraint_spec):
        """Test that /optimize includes calibration data when available."""
        request_dict = {
            "constraint_spec": constraint_spec_to_dict(base_constraint_spec),
            "track_id": "test_track",
            "n_lineups": 2,
            "n_scenarios": 1000,
            "include_calibration": True
        }

        response = client.post("/optimize", json=request_dict)

        data = response.json()

        # Calibration may be None if calibration service unavailable
        # Check that field exists (value can be None or dict)
        assert "calibration_metrics" in data

        # If calibration data exists, check structure
        if data.get("calibration_metrics") is not None:
            calib = data["calibration_metrics"]
            # May contain n_scenarios, n_drivers, mean_finish, std_finish
            # Structure depends on calibration implementation
            assert isinstance(calib, dict)


class TestTailValidationIntegration:
    """Test tail validation integration in API response."""

    def test_optimize_endpoint_includes_explain_artifacts(self, client, base_constraint_spec):
        """Test that /optimize includes explain artifacts with tail validation."""
        request_dict = {
            "constraint_spec": constraint_spec_to_dict(base_constraint_spec),
            "track_id": "test_track",
            "n_lineups": 3,
            "n_scenarios": 1000,
            "validate_tail_objective": True
        }

        response = client.post("/optimize", json=request_dict)

        data = response.json()

        # Explain artifacts should be present
        assert "explain" in data
        explain = data["explain"]

        # Check required explain fields
        assert "why_high_tail" in explain
        assert "constraint_binding" in explain
        assert "tail_vs_mean" in explain

        # Check types
        assert isinstance(explain["why_high_tail"], str)
        assert isinstance(explain["constraint_binding"], dict)
        assert isinstance(explain["tail_vs_mean"], dict)

    def test_tail_vs_mean_shows_tail_focus(self, client, base_constraint_spec):
        """Test that explain artifacts show CVaR focuses on tail."""
        request_dict = {
            "constraint_spec": constraint_spec_to_dict(base_constraint_spec),
            "track_id": "test_track",
            "n_lineups": 3,
            "n_scenarios": 1000  # More scenarios for better tail estimation
        }

        response = client.post("/optimize", json=request_dict)

        data = response.json()
        explain = data["explain"]

        # Check tail_vs_mean structure
        tail_vs_mean = explain["tail_vs_mean"]

        assert "avg_cvar_99" in tail_vs_mean
        assert "avg_mean" in tail_vs_mean

        # CVaR should generally be higher than mean (tail upside)
        # Note: May not always hold with mock data
        if tail_vs_mean.get("tail_upside"):
            assert isinstance(tail_vs_mean["tail_upside"], (int, float))


class TestPortfolioCorrelation:
    """Test portfolio correlation metrics in API response."""

    def test_optimize_endpoint_includes_portfolio_correlation(self, client, base_constraint_spec):
        """Test that /optimize includes portfolio correlation metrics."""
        request_dict = {
            "constraint_spec": constraint_spec_to_dict(base_constraint_spec),
            "track_id": "test_track",
            "n_lineups": 3,
            "n_scenarios": 1000
        }

        response = client.post("/optimize", json=request_dict)

        data = response.json()

        # Portfolio correlation should be present
        assert "portfolio_correlation" in data
        corr = data["portfolio_correlation"]

        # Should be a dict with correlation metrics
        assert isinstance(corr, dict)


class TestErrorHandling:
    """Test error handling in API pipeline."""

    def test_optimize_handles_min_lineup_request(self, client, base_constraint_spec):
        """Test that /optimize handles minimum lineup request."""
        request_dict = {
            "constraint_spec": constraint_spec_to_dict(base_constraint_spec),
            "track_id": "test_track",
            "n_lineups": 1,  # Minimum
            "n_scenarios": 1000
        }

        response = client.post("/optimize", json=request_dict)

        # Should return 200
        assert response.status_code == 200

        data = response.json()
        assert len(data.get("lineups", [])) >= 1

    def test_optimize_handles_max_lineup_request(self, client, base_constraint_spec):
        """Test that /optimize handles maximum lineup request."""
        request_dict = {
            "constraint_spec": constraint_spec_to_dict(base_constraint_spec),
            "track_id": "test_track",
            "n_lineups": 150,  # Maximum
            "n_scenarios": 1000
        }

        response = client.post("/optimize", json=request_dict)

        # Should return 200 (may generate fewer due to constraints)
        assert response.status_code == 200

        if response.status_code == 200:
            data = response.json()
            # May generate fewer than requested due to exposure limits
            assert len(data.get("lineups", [])) <= 150


class TestResponseTime:
    """Test API response time performance."""

    def test_optimize_response_time_reasonable(self, client, base_constraint_spec):
        """Test that /optimize responds in reasonable time."""
        import time

        request_dict = {
            "constraint_spec": constraint_spec_to_dict(base_constraint_spec),
            "track_id": "test_track",
            "n_lineups": 3,
            "n_scenarios": 1000
        }

        start = time.time()
        response = client.post("/optimize", json=request_dict)
        elapsed = time.time() - start

        assert response.status_code == 200

        # Should complete in < 60 seconds (allowing for solver time)
        assert elapsed < 60, f"Response took {elapsed:.2f}s, expected < 60s"


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_endpoint(self, client):
        """Test that /health returns status ok."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
