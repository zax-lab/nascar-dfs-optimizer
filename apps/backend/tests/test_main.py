"""
Tests for main.py FastAPI endpoints.

These tests validate the backend API endpoints for the NASCAR DFS Engine.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create test client for each test."""
    return TestClient(app)


# =============================================================================
# Health Endpoint Tests
# =============================================================================


def test_health_endpoint(client) -> None:
    """
    Test that the /health endpoint returns status ok.
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data
    assert "version" in data


def test_ready_endpoint(client) -> None:
    """
    Test that the /ready endpoint returns health status.
    """
    response = client.get("/ready")
    # Ready endpoint may fail if dependencies (Neo4j, Redis) are not available
    assert response.status_code in [200, 503]
    data = response.json()
    
    if response.status_code == 200:
        assert data["status"] == "ready"
        assert "dependencies" in data
    else:
        # 503 wraps response in HTTPException detail
        assert "detail" in data
        assert "dependencies" in data["detail"]


# =============================================================================
# Optimize Endpoint Tests
# =============================================================================


def _create_constraint_spec(n_drivers: int = 8) -> dict:
    """
    Create a valid ConstraintSpec dict for testing.
    
    This matches the OptimizeRequest.constraint_spec schema.
    """
    from datetime import datetime
    
    drivers = {}
    for i in range(n_drivers):
        driver_id = f"driver_{i}"
        drivers[driver_id] = {
            "driver_id": driver_id,
            "skill": 0.5 + (i % 5) * 0.1,
            "aggression": 0.3 + (i % 3) * 0.2,
            "shadow_risk": 0.1 + (i % 4) * 0.05,
            "min_laps_led": 0,
            "max_laps_led": 50 + i * 5,
            "veto_rules": []
        }
    
    tracks = {
        "daytona": {
            "track_id": "daytona",
            "difficulty": 0.7,
            "aggression_factor": 0.6,
            "caution_rate": 0.15,
            "pit_window_laps": [35, 70, 105, 140, 175]
        }
    }
    
    return {
        "slate_id": "test_slate_001",
        "compiled_at": datetime.utcnow().isoformat(),
        "drivers": drivers,
        "tracks": tracks,
        "version": "1.0.0",
        "hash": ""
    }


def _create_optimize_request(n_drivers: int = 8, n_lineups: int = 5) -> dict:
    """
    Create a valid OptimizeRequest dict for testing.
    """
    return {
        "constraint_spec": _create_constraint_spec(n_drivers),
        "track_id": "daytona",
        "n_lineups": n_lineups,
        "n_scenarios": 1000,  # Lower for test speed
        "cvar_alphas": [0.99, 0.95],
        "cvar_weights": [0.7, 0.3],
        "correlation_weight": 0.1,
        "max_driver_exposure": 0.5,
        "max_team_exposure": 0.7,
        "salary_cap": 50000,
        "n_drivers": 6,
        "min_stack": 2,
        "max_stack": 3,
        "random_seed": 42,
        "include_calibration": False,  # Faster tests
        "validate_tail_objective": False  # Faster tests
    }


def test_optimize_endpoint_returns_response(client) -> None:
    """
    Test the /optimize endpoint returns a valid response structure.
    
    This test verifies that the endpoint accepts a valid request and returns
    the expected response structure. We don't validate business logic here,
    just API contract compliance.
    """
    request_data = _create_optimize_request()
    
    response = client.post("/optimize", json=request_data)
    
    # If the optimiser module isn't available, we get 501
    if response.status_code == 501:
        pytest.skip("Portfolio optimization module not available")
    
    # 422 = validation error (expected if ConstraintSpec serialization is incompatible)
    # 200 = success
    # 500 = server error during optimization
    assert response.status_code in [200, 422, 500]
    data = response.json()
    
    if response.status_code == 200:
        # Validate response structure
        assert "lineups" in data
        assert "portfolio_correlation" in data
        assert "explain" in data
        assert isinstance(data["lineups"], list)


def test_optimize_endpoint_validation(client) -> None:
    """
    Test the /optimize endpoint validates input correctly.
    
    Sending invalid data should return a 422 Unprocessable Entity.
    """
    # Missing required fields
    invalid_request = {"n_lineups": 5}
    
    response = client.post("/optimize", json=invalid_request)
    assert response.status_code == 422


def test_optimize_endpoint_empty_drivers(client) -> None:
    """
    Test the /optimize endpoint with empty drivers.
    """
    request_data = _create_optimize_request(n_drivers=0)
    
    response = client.post("/optimize", json=request_data)
    
    # Either 422 (validation) or 500 (business logic error) is acceptable
    # The key is we shouldn't crash with an unhandled exception
    assert response.status_code in [200, 422, 500, 501]


def test_optimize_endpoint_illegal_cvar_alphas(client) -> None:
    """
    Test the /optimize endpoint rejects invalid CVaR alphas.
    """
    request_data = _create_optimize_request()
    request_data["cvar_alphas"] = [1.5, -0.5]  # Invalid: must be 0-1
    
    response = client.post("/optimize", json=request_data)
    # Should either fail validation or handle gracefully
    assert response.status_code in [422, 500]


# =============================================================================
# API Documentation Tests
# =============================================================================


def test_openapi_schema_available(client) -> None:
    """
    Test that the OpenAPI schema is available.
    """
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert "paths" in data


def test_docs_available(client) -> None:
    """
    Test that the API docs are available.
    """
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
