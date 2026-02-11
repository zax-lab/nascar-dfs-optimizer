# Testing Patterns

**Analysis Date:** 2026-02-11

## Test Framework

**Runner:**
- pytest (Version detected via package.json and test files)
- Config: No explicit pytest.ini found; uses default pytest discovery

**Assertion Library:**
- pytest's built-in assertions (e.g., `assert`, `pytest.raises`)

**Run Commands:**
```bash
pytest                    # Run all tests
pytest -v                # Run with verbose output
pytest -x                # Stop on first failure
pytest --cov              # Run with coverage
pytest tests/integration/  # Run integration tests only
```

## Test File Organization

**Location:**
- Unit tests co-located with source code: `packages/axiomatic-kernel/tests/`
- Integration tests: `tests/integration/`
- API tests: `apps/backend/app/tests/`

**Naming:**
- Test files: `test_*.py` prefix
- Descriptive names indicating tested module (e.g., `test_projection_model.py`, `test_api.py`)
- Integration tests: `test_*_verification.py`, `test_*_integration.py`

**Structure:**
```
packages/axiomatic-kernel/tests/
├── __init__.py
├── test_projection_model.py  # Unit tests for projection_model module
└── test_dataset.py           # Unit tests for nascar_dataset module

tests/integration/
├── test_jax_numpyro_verification.py
├── test_kernel_constraints.py
└── test_metaphysical_impact.py
```

## Test Structure

**Suite Organization:**
- Tests organized into test classes with descriptive names (e.g., `TestModelLoadingAndInitialization`, `TestSinglePrediction`)
- Test classes follow pattern: `Test{Feature}` where `{Feature}` is the name of the thing being tested
- Each test method follows pattern: `test_{scenario}_{expected_behavior}`

**Patterns:**
```python
class TestModelLoadingAndInitialization:
    """Test cases for model loading and initialization."""

    @patch("projection_model.AutoModelForCausalLM.from_pretrained")
    @patch("projection_model.AutoTokenizer.from_pretrained")
    def test_successful_model_loading(self, mock_tokenizer_class, mock_model_class):
        """Test successful model loading with valid checkpoint path."""
        # Setup mocks
        mock_tokenizer = MagicMock(pad_token="<pad>")
        mock_model = MagicMock()
        mock_tokenizer_class.return_value = mock_tokenizer
        mock_model_class.return_value = mock_model

        # Execute
        model = ProjectionModel(model_path="valid_path", device="cpu")

        # Assert
        assert model.model_path == "valid_path"
        assert model.device == "cpu"
        assert model.tokenizer is not None
        assert model.model is not None
```

**Setup/Teardown:**
- Use pytest fixtures for test setup and teardown
- Fixtures can be parameterized
- Autouse fixtures run automatically for all tests

**Patterns:**
```python
@pytest.fixture
def sample_input_data():
    """Provide sample input data for prediction tests."""
    return {
        "driver": "Kyle Larson",
        "track": "Daytona",
        "logic_phase": {"track_type": "Superspeedway", "weather": "Sunny"},
        "ontology_phase": {"driver_rating": 95.5, "car_number": 5},
        "narrative_phase": {"recent_finish": 1, "momentum": "High"},
    }

@pytest.fixture(autouse=True)
def reset_cache():
    """Reset the ProjectionModelCache before and after each test."""
    ProjectionModelCache.reset()
    yield
    ProjectionModelCache.reset()
```

## Mocking

**Framework:** unittest.mock (included with Python standard library)

**Patterns:**
```python
from unittest.mock import MagicMock, Mock, patch

# Patch at module level
@patch("projection_model.AutoModelForCausalLM.from_pretrained")
@patch("projection_model.AutoTokenizer.from_pretrained")
def test_prediction(mock_tokenizer_class, mock_model_class):
    mock_tokenizer = MagicMock(pad_token="<pad>")
    mock_model = MagicMock()
    mock_tokenizer_class.return_value = mock_tokenizer
    mock_model_class.return_value = mock_model

    model = ProjectionModel(model_path="test_path", device="cpu")
    # ... test code ...
```

**What to Mock:**
- External dependencies: databases, APIs, file systems, model loading
- Heavy computations or slow operations
- Random behavior or stateful operations
- Pydantic model validation (use monkeypatch for env vars)

**What NOT to Mock:**
- Pure functions or algorithms
- Database operations (use test databases or in-memory)
- API integration (use integration tests or mock HTTP client)
- Simple class instantiation

**Mock Best Practices:**
```python
# Good: Create specific mock responses
mock_tokenizer.decode.return_value = "45.5"
mock_tokenizer.encode.return_value = [1, 2, 3]

# Good: Use MagicMock for flexible mocking
mock_model = MagicMock()
mock_model.generate.return_value = torch.tensor([[0, 1, 2]])
mock_model.eval.return_value = mock_model
mock_model.to.return_value = mock_model

# Good: Set up side effects for complex scenarios
mock_tokenizer.side_effect = [
    MagicMock(pad_token="<pad>"),
    MagicMock(pad_token="<pad>"),
]
```

## Fixtures and Factories

**Test Data:**
```python
@pytest.fixture
def sample_input_data():
    """Provide sample input data for prediction tests."""
    return {
        "driver": "Kyle Larson",
        "track": "Daytona",
        "logic_phase": {"track_type": "Superspeedway", "weather": "Sunny"},
        "ontology_phase": {"driver_rating": 95.5, "car_number": 5},
        "narrative_phase": {"recent_finish": 1, "momentum": "High"},
    }

@pytest.fixture
def batch_samples():
    """Provide batch samples for batch prediction tests."""
    return [
        {
            "driver": "Kyle Larson",
            "track": "Daytona",
            "logic_phase": {"track_type": "Superspeedway"},
            "ontology_phase": {"driver_rating": 95.5},
            "narrative_phase": {"recent_finish": 1},
        },
        {
            "driver": "Chase Elliott",
            "track": "Talladega",
            "logic_phase": {"track_type": "Superspeedway"},
            "ontology_phase": {"driver_rating": 94.0},
            "narrative_phase": {"recent_finish": 3},
        },
    ]
```

**Helper Fixtures:**
```python
@pytest.fixture
def mock_torch_cuda():
    """Mock torch.cuda availability for device testing."""
    with patch.object(torch.cuda, "is_available", return_value=True):
        with patch.object(torch.cuda, "get_device_name", return_value="NVIDIA GTX 1080"):
            yield

@pytest.fixture
def mock_torch_no_gpu():
    """Mock torch with no GPU availability (CPU only)."""
    with patch.object(torch.cuda, "is_available", return_value=False):
        with patch.object(torch.backends.mps, "is_available", return_value=False):
            yield
```

**Location:**
- Fixtures defined in the test file they're used in
- Shared fixtures: create `conftest.py` in test directory or use `pytest_plugins`

## Coverage

**Requirements:** Not explicitly enforced (no coverage check in CI/CD)

**View Coverage:**
```bash
pytest --cov=. --cov-report=term-missing
pytest --cov=packages/axiomatic-kernel --cov-report=html
```

**Target:** Tests in `packages/axiomatic-kernel/tests/test_projection_model.py` aim for >90% coverage

## Test Types

**Unit Tests:**
- Scope: Test individual functions and classes in isolation
- Location: Co-located with source code (e.g., `packages/axiomatic-kernel/tests/`)
- Approach: Use mocks for external dependencies
- Example: `test_projection_model.py` tests `ProjectionModel` class

**Integration Tests:**
- Scope: Test integration between components or modules
- Location: `tests/integration/`
- Approach: Test actual functionality without mocks where possible
- Examples: `test_jax_numpyro_verification.py`, `test_kernel_constraints.py`

**API Tests:**
- Scope: Test REST API endpoints and contract validation
- Location: `apps/backend/app/tests/`
- Approach: Use TestClient for HTTP requests
- Example: `test_api.py` tests `/optimize` endpoint

**Pydantic Validation Tests:**
- Pattern: Test validation errors with `pytest.raises(ValidationError)`
- Example:
```python
from pydantic import ValidationError

def test_skill_aggression_shadow_risk_bounds():
    """Test skill, aggression, shadow_risk must be in [0, 1]."""
    from app.api.contracts import DriverConstraintsRequest

    # Valid: all in bounds
    driver = DriverConstraintsRequest(
        driver_id='d1', skill=0.5, aggression=0.5, shadow_risk=0.5
    )
    assert driver.skill == 0.5

    # Invalid: skill > 1
    with pytest.raises(ValidationError):
        DriverConstraintsRequest(driver_id='d1', skill=1.5, aggression=0.5, shadow_risk=0.5)
```

## Common Patterns

**Async Testing:**
```python
import pytest

async def test_async_operation():
    """Test async function."""
    from app.main import app

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
```

**Error Testing:**
```python
def test_error_handling():
    """Test that specific error is raised."""
    with pytest.raises(ValueError, match="Invalid input shape"):
        model.predict(driver="Test", track="Track", ...)

def test_error_message_clarity():
    """Test that error message is clear and helpful."""
    with pytest.raises(FileNotFoundError) as exc_info:
        ProjectionModel(model_path="invalid/path")

    error_msg = str(exc_info.value)
    assert "not found" in error_msg.lower()
```

**Pydantic Validation:**
```python
from pydantic import ValidationError

def test_validation_error():
    """Test Pydantic model validation."""
    with pytest.raises(ValidationError):
        ScenarioConfig(track_id='daytona', n_scenarios=5)  # Below minimum

    with pytest.raises(ValidationError):
        DriverConstraintsRequest(driver_id='d1', skill=1.5)  # Above max
```

**Mock Environment Variables:**
```python
def test_env_var_loading(monkeypatch):
    """Test loading model path from environment variable."""
    monkeypatch.setenv("TINYLLAMA_CHECKPOINT", "custom/model/path")

    model = ProjectionModel(model_path=None, device="cpu")
    assert model.model_path == "custom/model/path"
```

**Property-Based Testing:**
```python
from hypothesis import given, strategies as st

@given(
    skill=st.floats(min_value=0, max_value=1, allow_nan=False),
    aggression=st.floats(min_value=0, max_value=1, allow_nan=False),
)
def test_constraints_validation(skill, aggression):
    """Test that constraints validation works for various inputs."""
    with pytest.raises(ValidationError):
        DriverConstraintsRequest(
            driver_id='d1', skill=skill, aggression=aggression
        )
```

**Test Independence:**
```python
@pytest.fixture(autouse=True)
def reset_state():
    """Reset state before and after each test."""
    # Setup
    ProjectionModelCache.reset()
    # Run test
    yield
    # Teardown
    ProjectionModelCache.reset()
```

## Running Tests

**Development:**
```bash
pytest                      # Run all tests
pytest -v                   # Verbose output
pytest -x                   # Stop on first failure
pytest --tb=short           # Short traceback on failure
```

**With Coverage:**
```bash
pytest --cov=. --cov-report=term-missing
pytest --cov=packages/axiomatic-kernel --cov-report=html
```

**Integration Tests Only:**
```bash
pytest tests/integration/
```

**Specific Test:**
```bash
pytest test_projection_model.py::TestModelLoadingAndInitialization::test_successful_model_loading
```

**Watch Mode:**
```bash
pytest --watch
```

---

*Testing analysis: 2026-02-11*
