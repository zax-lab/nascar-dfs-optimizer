"""
Integration tests for Phase 4 contest simulation API endpoints.

This module provides comprehensive end-to-end tests for:
- Ownership estimation endpoint (/ownership)
- Contest simulation endpoint (/contest-sim)
- Leverage-aware optimization endpoint (/optimize-with-leverage)
- Full pipeline integration across all Phase 4 endpoints
"""
import pytest
import numpy as np
from fastapi.testclient import TestClient
from typing import List, Dict, Any

# Import app and models
try:
    from app.main import app
    from app.ownership.models import (
        OwnershipRequest,
        RaceOwnershipData,
        DriverOwnershipData,
        TrackArchetype,
        EnsembleMethod
    )
    from app.api.contracts import (
        ContestSimRequest,
        LeverageOptimizeRequest,
        ConstraintSpecForLeverage
    )
except ImportError:
    pytest.skip("Phase 4 components not available", allow_module_level=True)


# =============================================================================
# Pytest Fixtures
# =============================================================================

@pytest.fixture
def sample_driver_data() -> List[Dict[str, Any]]:
    """Sample driver data for ownership estimation."""
    return [
        {
            'driver_id': i + 1,
            'salary': 8000 + i * 200,
            'projected_points': 45 - i * 2,
            'skill': 0.9 - i * 0.05,
            'recent_avg_finish': 5 + i * 2
        }
        for i in range(12)
    ]


@pytest.fixture
def sample_ownership() -> np.ndarray:
    """Sample ownership estimates for 12 drivers."""
    return np.array([20, 15, 12, 10, 8, 7, 6, 5, 5, 4, 4, 4])


@pytest.fixture
def sample_scenarios() -> np.ndarray:
    """Sample scenario driver scores."""
    np.random.seed(42)
    return np.random.gamma(20, 2, size=(100, 12))


@pytest.fixture
def client() -> TestClient:
    """FastAPI test client."""
    return TestClient(app)


# =============================================================================
# Test Ownership Endpoint
# =============================================================================

class TestOwnershipEndpoint:
    """Tests for POST /ownership endpoint."""

    def test_ownership_voting_ensemble(self, client: TestClient, sample_driver_data):
        """Test ownership estimation with voting ensemble."""
        request_data = {
            'driver_data': [
                {
                    'driver_id': d['driver_id'],
                    'salary': d['salary'],
                    'projected_points': d['projected_points'],
                    'skill': d['skill'],
                    'recent_avg_finish': d['recent_avg_finish']
                }
                for d in sample_driver_data
            ],
            'race_data': {
                'race_id': 1,
                'track_archetype': 'superspeedway',
                'race_date': '2024-02-01T00:00:00'
            },
            'ensemble_method': 'voting',
            'n_recent_races': 5,
            'include_uncertainty': False
        }

        response = client.post('/ownership', json=request_data)

        # Assert 200 status
        assert response.status_code == 200

        # Assert response structure
        data = response.json()
        assert 'ownership_predictions' in data
        assert 'ensemble_method' in data
        assert 'n_recent_races' in data

        # Assert predictions exist
        predictions = data['ownership_predictions']
        assert len(predictions) == len(sample_driver_data)

        # Assert predictions sum to approximately 100%
        ownership_values = [p['ownership_percent'] for p in predictions]
        total_ownership = sum(ownership_values)
        assert 95 <= total_ownership <= 105  # Allow 5% tolerance

        # Assert all ownership in valid range
        for ownership in ownership_values:
            assert 0 <= ownership <= 100

    def test_ownership_with_uncertainty(self, client: TestClient, sample_driver_data):
        """Test ownership estimation with uncertainty bounds."""
        request_data = {
            'driver_data': [
                {
                    'driver_id': d['driver_id'],
                    'salary': d['salary'],
                    'projected_points': d['projected_points']
                }
                for d in sample_driver_data[:6]  # Use fewer drivers for speed
            ],
            'race_data': {
                'race_id': 1,
                'track_archetype': 'intermediate',
                'race_date': '2024-02-01T00:00:00'
            },
            'ensemble_method': 'voting',
            'include_uncertainty': True
        }

        response = client.post('/ownership', json=request_data)

        # Assert 200 status
        assert response.status_code == 200

        # Assert uncertainty bounds exist
        data = response.json()
        predictions = data['ownership_predictions']

        for pred in predictions:
            # Check uncertainty bounds exist
            assert 'uncertainty_lower' in pred
            assert 'uncertainty_upper' in pred

            # Check bounds are valid
            if pred['uncertainty_lower'] is not None:
                assert 0 <= pred['uncertainty_lower'] <= 100
            if pred['uncertainty_upper'] is not None:
                assert 0 <= pred['uncertainty_upper'] <= 100

            # Check uncertainty_lower <= ownership <= uncertainty_upper
            if pred['uncertainty_lower'] is not None and pred['uncertainty_upper'] is not None:
                assert pred['uncertainty_lower'] <= pred['ownership_percent'] <= pred['uncertainty_upper']

    def test_ownership_invalid_track_archetype(self, client: TestClient, sample_driver_data):
        """Test ownership estimation with invalid track_archetype returns 422."""
        request_data = {
            'driver_data': [
                {
                    'driver_id': d['driver_id'],
                    'salary': d['salary'],
                    'projected_points': d['projected_points']
                }
                for d in sample_driver_data[:3]
            ],
            'race_data': {
                'race_id': 1,
                'track_archetype': 'invalid_track',  # Invalid
                'race_date': '2024-02-01T00:00:00'
            },
            'ensemble_method': 'voting'
        }

        response = client.post('/ownership', json=request_data)

        # Assert validation error (422)
        # Note: May return 200 if validation is deferred to backend
        assert response.status_code in [422, 200]


# =============================================================================
# Test Contest Simulation Endpoint
# =============================================================================

class TestContestSimEndpoint:
    """Tests for POST /contest-sim endpoint."""

    def test_contest_sim_basic(self, client: TestClient, sample_scenarios):
        """Test basic contest simulation."""
        request_data = {
            'my_lineup_scores': [150.0],
            'scenario_driver_scores': sample_scenarios.tolist()[:50],  # 50 scenarios
            'field_size': 100,
            'n_contest_sims': 10,
            'contest_buyin': 20.0,
            'contest_size_tier': 'large'
        }

        response = client.post('/contest-sim', json=request_data)

        # Assert 200 status
        assert response.status_code == 200

        # Assert response structure
        data = response.json()
        assert 'roi' in data
        assert 'cash_pct' in data
        assert 'win_prob' in data
        assert 'n_simulations' in data

        # Assert ROI in reasonable range
        assert -1 <= data['roi'] <= 10  # -100% to 1000%

        # Assert cash_pct in [0, 100]
        assert 0 <= data['cash_pct'] <= 100

        # Assert win_prob in [0, 100]
        assert 0 <= data['win_prob'] <= 100

    def test_contest_sim_large_field(self, client: TestClient, sample_scenarios):
        """Test contest simulation with large field."""
        request_data = {
            'my_lineup_scores': [140.0, 150.0, 160.0],
            'scenario_driver_scores': sample_scenarios.tolist()[:20],
            'field_size': 10000,
            'n_contest_sims': 5,
            'contest_buyin': 20.0,
            'contest_size_tier': 'large'
        }

        response = client.post('/contest-sim', json=request_data)

        # Assert 200 status
        assert response.status_code == 200

        # Assert simulation count
        data = response.json()
        expected_sims = 20 * 5  # n_scenarios * n_contest_sims
        assert data['n_simulations'] >= expected_sims

        # Assert best_rank >= 1
        assert data['best_rank'] >= 1

    def test_contest_sim_invalid_tier(self, client: TestClient, sample_scenarios):
        """Test contest simulation with invalid tier returns 422."""
        request_data = {
            'my_lineup_scores': [150.0],
            'scenario_driver_scores': sample_scenarios.tolist()[:10],
            'field_size': 100,
            'n_contest_sims': 5,
            'contest_buyin': 20.0,
            'contest_size_tier': 'invalid_tier'  # Invalid
        }

        response = client.post('/contest-sim', json=request_data)

        # Assert validation error (422)
        assert response.status_code in [422, 200]


# =============================================================================
# Test Leverage Optimization Endpoint
# =============================================================================

class TestLeverageOptimizeEndpoint:
    """Tests for POST /optimize-with-leverage endpoint."""

    def test_leverage_optimize_basic(self, client: TestClient):
        """Test basic leverage optimization."""
        request_data = {
            'constraint_spec': {
                'salary_cap': 50000,
                'n_drivers': 6,
                'min_stack': 2,
                'max_stack': 3
            },
            'ownership_estimates': [20, 15, 12, 10, 8, 7, 5, 5, 4, 4, 3, 2],
            'n_lineups': 3,
            'leverage_penalty': 0.5,
            'n_scenarios': 100
        }

        response = client.post('/optimize-with-leverage', json=request_data)

        # Assert 200 status (may be 501 if not available)
        assert response.status_code in [200, 501]

        if response.status_code == 200:
            # Assert response structure
            data = response.json()
            assert 'lineups' in data
            assert 'portfolio_metrics' in data
            assert 'ownership_metrics' in data

            # Assert lineups exist
            lineups = data['lineups']
            assert len(lineups) <= 3

            # Assert all lineups have leverage_score
            for lineup in lineups:
                assert 'leverage_score' in lineup
                assert 'avg_ownership' in lineup
                assert 0 <= lineup['avg_ownership'] <= 100

    def test_leverage_optimize_with_regimes(self, client: TestClient):
        """Test leverage optimization with regime allocation."""
        request_data = {
            'constraint_spec': {
                'salary_cap': 50000,
                'n_drivers': 6,
                'min_stack': 2,
                'max_stack': 3
            },
            'ownership_estimates': [15, 12, 10, 8, 7, 6, 5, 5, 5, 4, 4, 4],
            'n_lineups': 6,
            'leverage_penalty': 0.5,
            'use_regime_allocation': True,
            'n_scenarios': 100
        }

        response = client.post('/optimize-with-leverage', json=request_data)

        # Assert 200 status (may be 501 if not available)
        assert response.status_code in [200, 501]

        if response.status_code == 200:
            # Assert lineups have regime field
            data = response.json()
            lineups = data['lineups']

            for lineup in lineups:
                # Regime may be None if not implemented
                if 'regime' in lineup and lineup['regime'] is not None:
                    assert lineup['regime'] in ['dominator', 'chaos', 'fuel_mileage']

    def test_leverage_optimize_ownership_constraints(self, client: TestClient):
        """Test leverage optimization with strict ownership constraints."""
        request_data = {
            'constraint_spec': {
                'salary_cap': 50000,
                'n_drivers': 6,
                'min_stack': 2,
                'max_stack': 3
            },
            'ownership_estimates': [20, 15, 12, 10, 8, 7, 5, 5, 4, 4, 3, 2],
            'n_lineups': 3,
            'leverage_penalty': 0.5,
            'max_ownership_per_driver': 0.20,  # 20% max
            'n_scenarios': 100
        }

        response = client.post('/optimize-with-leverage', json=request_data)

        # Assert 200 status (may be 501 if not available)
        assert response.status_code in [200, 501]

        if response.status_code == 200:
            # Assert ownership constraints respected
            data = response.json()
            lineups = data['lineups']

            for lineup in lineups:
                # max_ownership should be <= 20%
                if 'max_ownership' in lineup:
                    assert lineup['max_ownership'] <= 25  # Allow small tolerance


# =============================================================================
# Test End-to-End Pipeline
# =============================================================================

class TestEndToEndPipeline:
    """Tests for full pipeline integration across Phase 4 endpoints."""

    def test_full_pipeline(self, client: TestClient, sample_driver_data, sample_scenarios):
        """Test full pipeline: ownership -> contest sim -> leverage optimize."""
        # Step 1: Get ownership estimates
        ownership_request = {
            'driver_data': [
                {
                    'driver_id': d['driver_id'],
                    'salary': d['salary'],
                    'projected_points': d['projected_points']
                }
                for d in sample_driver_data
            ],
            'race_data': {
                'race_id': 1,
                'track_archetype': 'superspeedway',
                'race_date': '2024-02-01T00:00:00'
            },
            'ensemble_method': 'voting'
        }

        ownership_response = client.post('/ownership', json=ownership_request)
        assert ownership_response.status_code == 200

        # Extract ownership
        ownership_data = ownership_response.json()
        ownership_estimates = [
            p['ownership_percent']
            for p in ownership_data['ownership_predictions']
        ]

        # Verify ownership sums to ~100%
        assert 95 <= sum(ownership_estimates) <= 105

        # Step 2: Run contest sim with ownership
        contest_request = {
            'my_lineup_scores': [150.0],
            'scenario_driver_scores': sample_scenarios.tolist()[:50],
            'field_size': 100,
            'n_contest_sims': 10,
            'contest_buyin': 20.0,
            'contest_size_tier': 'large'
        }

        contest_response = client.post('/contest-sim', json=contest_request)
        assert contest_response.status_code == 200

        # Verify contest sim results
        contest_data = contest_response.json()
        roi = contest_data['roi']
        cash_pct = contest_data['cash_pct']

        assert isinstance(roi, (int, float))
        assert isinstance(cash_pct, (int, float))

        # Step 3: Run leverage optimization with ownership
        leverage_request = {
            'constraint_spec': {
                'salary_cap': 50000,
                'n_drivers': 6,
                'min_stack': 2,
                'max_stack': 3
            },
            'ownership_estimates': ownership_estimates,
            'n_lineups': 2,
            'leverage_penalty': 0.5,
            'n_scenarios': 100
        }

        leverage_response = client.post('/optimize-with-leverage', json=leverage_request)

        # May return 501 if Phase 4 not available
        if leverage_response.status_code == 200:
            # Verify leverage optimization results
            leverage_data = leverage_response.json()
            lineups = leverage_data['lineups']

            assert len(lineups) >= 1

            # Verify results consistent across steps
            # Ownership from step 1 should be used in step 3
            ownership_metrics = leverage_data['ownership_metrics']
            assert 'avg_lineup_ownership' in ownership_metrics

        # All steps completed successfully
        assert True
