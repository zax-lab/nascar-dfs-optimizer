"""
API contract tests for /optimize endpoint.

This module tests the API contracts and endpoint behavior:
- Request validation with Pydantic models
- Response structure and types
- Status polling behavior
- Error handling

Note: These tests use mocking to avoid Neo4j dependencies.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from app.main import app


class TestOptimizeEndpoint:
    """Tests for /optimize endpoint."""

    def test_health_check(self):
        """Test health check endpoint works."""
        client = TestClient(app)
        response = client.get('/health')
        assert response.status_code == 200
        assert response.json()['status'] == 'ok'

    def test_optimize_endpoint_in_openapi_schema(self):
        """Test that optimize endpoints are in OpenAPI schema."""
        client = TestClient(app)
        response = client.get('/openapi.json')
        schema = response.json()

        assert '/api/v1/optimize' in schema['paths']
        assert '/api/v1/optimize/{run_id}/status' in schema['paths']
        assert '/api/v1/optimize/{run_id}/result' in schema['paths']

    def test_submit_optimization_valid_request(self):
        """Test submitting optimization with valid request."""
        client = TestClient(app)

        request_data = {
            'slate_id': 'test_slate',
            'drivers': [
                {
                    'driver_id': f'd{i}',
                    'skill': 0.5,
                    'aggression': 0.5,
                    'shadow_risk': 0.5,
                    'min_laps_led': 0,
                    'max_laps_led': 100
                }
                for i in range(1, 7)
            ],
            'scenario_config': {
                'track_id': 'daytona',
                'n_scenarios': 100
            },
            'salary_cap': 50000,
            'random_seed': 42
        }

        response = client.post('/api/v1/optimize', json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert 'run_id' in data
        assert 'status' in data
        assert data['status'] in ['pending', 'running']

    def test_submit_optimization_invalid_skill(self):
        """Test submitting optimization with invalid skill (>1)."""
        client = TestClient(app)

        request_data = {
            'slate_id': 'test_slate',
            'drivers': [
                {
                    'driver_id': 'd1',
                    'skill': 1.5,  # Invalid: > 1
                    'aggression': 0.5,
                    'shadow_risk': 0.5,
                    'min_laps_led': 0,
                    'max_laps_led': 100
                }
            ] + [
                {
                    'driver_id': f'd{i}',
                    'skill': 0.5,
                    'aggression': 0.5,
                    'shadow_risk': 0.5,
                    'min_laps_led': 0,
                    'max_laps_led': 100
                }
                for i in range(2, 7)
            ],
            'scenario_config': {
                'track_id': 'daytona',
                'n_scenarios': 100
            },
            'salary_cap': 50000
        }

        response = client.post('/api/v1/optimize', json=request_data)
        assert response.status_code == 422  # Validation error

    def test_submit_optimization_duplicate_drivers(self):
        """Test submitting optimization with duplicate driver_ids."""
        client = TestClient(app)

        request_data = {
            'slate_id': 'test_slate',
            'drivers': [
                {
                    'driver_id': 'd1',  # Duplicate
                    'skill': 0.5,
                    'aggression': 0.5,
                    'shadow_risk': 0.5,
                    'min_laps_led': 0,
                    'max_laps_led': 100
                },
                {
                    'driver_id': 'd1',  # Duplicate
                    'skill': 0.5,
                    'aggression': 0.5,
                    'shadow_risk': 0.5,
                    'min_laps_led': 0,
                    'max_laps_led': 100
                }
            ] + [
                {
                    'driver_id': f'd{i}',
                    'skill': 0.5,
                    'aggression': 0.5,
                    'shadow_risk': 0.5,
                    'min_laps_led': 0,
                    'max_laps_led': 100
                }
                for i in range(2, 7)
            ],
            'scenario_config': {
                'track_id': 'daytona',
                'n_scenarios': 100
            },
            'salary_cap': 50000
        }

        response = client.post('/api/v1/optimize', json=request_data)
        assert response.status_code == 422  # Validation error

    def test_submit_optimization_invalid_n_scenarios(self):
        """Test submitting optimization with n_scenarios not divisible by 10."""
        client = TestClient(app)

        request_data = {
            'slate_id': 'test_slate',
            'drivers': [
                {
                    'driver_id': f'd{i}',
                    'skill': 0.5,
                    'aggression': 0.5,
                    'shadow_risk': 0.5,
                    'min_laps_led': 0,
                    'max_laps_led': 100
                }
                for i in range(1, 7)
            ],
            'scenario_config': {
                'track_id': 'daytona',
                'n_scenarios': 105  # Invalid: not divisible by 10
            },
            'salary_cap': 50000
        }

        response = client.post('/api/v1/optimize', json=request_data)
        assert response.status_code == 422  # Validation error

    def test_get_status_invalid_run_id(self):
        """Test getting status for non-existent run_id."""
        client = TestClient(app)

        response = client.get('/api/v1/optimize/nonexistent-run/status')
        assert response.status_code == 404

    def test_get_result_invalid_run_id(self):
        """Test getting result for non-existent run_id."""
        client = TestClient(app)

        response = client.get('/api/v1/optimize/nonexistent-run/result')
        assert response.status_code == 404


class TestScenarioConfigValidation:
    """Tests for ScenarioConfig validation."""

    def test_n_scenarios_bounds(self):
        """Test n_scenarios min/max bounds."""
        from app.api.contracts import ScenarioConfig
        from pydantic import ValidationError

        # Test minimum (10)
        config = ScenarioConfig(track_id='daytona', n_scenarios=10)
        assert config.n_scenarios == 10

        # Test maximum (10000)
        config = ScenarioConfig(track_id='daytona', n_scenarios=10000)
        assert config.n_scenarios == 10000

        # Test below minimum
        with pytest.raises(ValidationError):
            ScenarioConfig(track_id='daytona', n_scenarios=5)

        # Test above maximum
        with pytest.raises(ValidationError):
            ScenarioConfig(track_id='daytona', n_scenarios=15000)

    def test_n_scenarios_divisible_by_10(self):
        """Test n_scenarios must be divisible by 10."""
        from app.api.contracts import ScenarioConfig
        from pydantic import ValidationError

        # Valid: divisible by 10
        config = ScenarioConfig(track_id='daytona', n_scenarios=100)
        assert config.n_scenarios == 100

        # Invalid: not divisible by 10
        with pytest.raises(ValidationError):
            ScenarioConfig(track_id='daytona', n_scenarios=105)


class TestDriverConstraintsRequestValidation:
    """Tests for DriverConstraintsRequest validation."""

    def test_skill_aggression_shadow_risk_bounds(self):
        """Test skill, aggression, shadow_risk must be in [0, 1]."""
        from app.api.contracts import DriverConstraintsRequest
        from pydantic import ValidationError

        # Valid: all in bounds
        driver = DriverConstraintsRequest(
            driver_id='d1',
            skill=0.5,
            aggression=0.5,
            shadow_risk=0.5,
            min_laps_led=0,
            max_laps_led=100
        )
        assert driver.skill == 0.5

        # Invalid: skill > 1
        with pytest.raises(ValidationError):
            DriverConstraintsRequest(
                driver_id='d1',
                skill=1.5,
                aggression=0.5,
                shadow_risk=0.5,
                min_laps_led=0,
                max_laps_led=100
            )

        # Invalid: aggression < 0
        with pytest.raises(ValidationError):
            DriverConstraintsRequest(
                driver_id='d1',
                skill=0.5,
                aggression=-0.1,
                shadow_risk=0.5,
                min_laps_led=0,
                max_laps_led=100
            )

    def test_max_laps_led_gte_min_laps_led(self):
        """Test max_laps_led must be >= min_laps_led."""
        from app.api.contracts import DriverConstraintsRequest
        from pydantic import ValidationError

        # Valid: max > min
        driver = DriverConstraintsRequest(
            driver_id='d1',
            skill=0.5,
            aggression=0.5,
            shadow_risk=0.5,
            min_laps_led=0,
            max_laps_led=100
        )
        assert driver.max_laps_led >= driver.min_laps_led

        # Invalid: max < min
        with pytest.raises(ValidationError):
            DriverConstraintsRequest(
                driver_id='d1',
                skill=0.5,
                aggression=0.5,
                shadow_risk=0.5,
                min_laps_led=100,
                max_laps_led=50
            )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
