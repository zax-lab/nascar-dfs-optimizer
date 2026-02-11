# Testing Strategy - NASCAR DFS Engine

## Overview

This document provides a comprehensive overview of the testing strategy for the Axiomatic NASCAR DraftKings DFS engine. The testing infrastructure is designed to ensure quality, reliability, and performance across all components of the system.

## Architecture

The NASCAR DFS engine consists of four main components:

1. **Backend API** ([`apps/backend/`](../apps/backend/)) - FastAPI service for optimization and data retrieval
2. **Frontend UI** ([`apps/frontend/`](../apps/frontend/)) - Next.js application for user interaction
3. **ETL Pipelines** ([`apps/airflow/`](../apps/airflow/)) - Airflow DAGs for data ingestion and processing
4. **ML Models** ([`packages/axiomatic-kernel/`](../packages/axiomatic-kernel/)) - Projection models and dataset utilities

## Testing Philosophy

Our testing approach follows the **Testing Pyramid** principle:

```
        /\
       /E2E\      - Critical user workflows (10%)
      /------\
     /Integration\ - Component interactions (30%)
    /------------\
   /   Unit Tests  \ - Individual functions (60%)
  /----------------\
```

### Key Principles

- **Fast Feedback**: Unit tests run quickly to catch issues early
- **Comprehensive Coverage**: Integration tests verify component interactions
- **User-Focused**: E2E tests validate complete user workflows
- **Automated**: All tests run automatically in CI/CD
- **Maintainable**: Tests are clear, isolated, and easy to update

## Test Structure

### Unit Tests

Unit tests verify individual functions and classes in isolation.

#### Backend Unit Tests
**Location**: [`apps/backend/tests/`](../apps/backend/tests/)

**Framework**: pytest

**Coverage**:
- API endpoints ([`test_main.py`](../apps/backend/tests/test_main.py))
- Kernel logic ([`test_kernel.py`](../apps/backend/tests/test_kernel.py))
- Optimizer algorithms ([`test_optimizer.py`](../apps/backend/tests/test_optimizer.py))

**Run**:
```bash
cd apps/backend
pytest tests/
```

#### Frontend Unit Tests
**Location**: [`apps/frontend/__tests__/`](../apps/frontend/__tests__/)

**Framework**: Jest + React Testing Library

**Coverage**:
- Components ([`ProjectionTable.test.tsx`](../apps/frontend/__tests__/ProjectionTable.test.tsx))
- UI panels ([`OptimizerPanel.test.tsx`](../apps/frontend/__tests__/OptimizerPanel.test.tsx))

**Run**:
```bash
cd apps/frontend
npm test
```

#### ETL Unit Tests
**Location**: [`apps/airflow/tests/`](../apps/airflow/tests/)

**Framework**: pytest

**Coverage**:
- DAG imports ([`test_dag.py`](../apps/airflow/tests/test_dag.py))
- Task validation
- Data transformations

**Run**:
```bash
cd apps/airflow
pytest tests/
```

#### ML Unit Tests
**Location**: [`packages/axiomatic-kernel/tests/`](../packages/axiomatic-kernel/tests/)

**Framework**: pytest

**Coverage**:
- Dataset loading ([`test_dataset.py`](../packages/axiomatic-kernel/tests/test_dataset.py))
- Projection models ([`test_projection_model.py`](../packages/axiomatic-kernel/tests/test_projection_model.py))

**Run**:
```bash
cd packages/axiomatic-kernel
pytest tests/
```

### Integration Tests

Integration tests verify that multiple components work together correctly.

**Location**: `tests/integration/` (to be implemented)

**Scenarios**:
- API + Database interactions
- ETL + Database loading
- ML + API projections
- Frontend + API communication

### E2E Tests

End-to-end tests validate complete user workflows across the entire system.

**Location**: `tests/e2e/` (to be implemented)

**Scenarios**: See [`E2E_TEST_PLAN.md`](./E2E_TEST_PLAN.md) for detailed scenarios

## How to Run Tests

### Run All Tests

```bash
# Backend tests
pytest apps/backend/tests/

# Frontend tests
cd apps/frontend && npm test

# ETL tests
pytest apps/airflow/tests/

# ML tests
pytest packages/axiomatic-kernel/tests/
```

### Run Specific Test Files

```bash
# Backend health and optimize tests
pytest apps/backend/tests/test_main.py -v

# Frontend component tests
cd apps/frontend && npm test -- ProjectionTable.test.tsx

# ETL DAG tests
pytest apps/airflow/tests/test_dag.py -v

# ML projection tests
pytest packages/axiomatic-kernel/tests/test_projection_model.py -v
```

### Run with Coverage

```bash
# Backend with coverage
pytest apps/backend/tests/ --cov=app --cov-report=html

# ML with coverage
pytest packages/axiomatic-kernel/tests/ --cov=axiomatic_kernel --cov-report=html
```

### Run Smoke Tests

```bash
# Quick validation for CI
./tests/smoke_test.sh
```

## Test Coverage Goals

| Component | Target Coverage | Critical Paths |
|-----------|----------------|----------------|
| Backend API | 80% | 100% |
| Frontend UI | 70% | 90% |
| ETL Pipelines | 85% | 100% |
| ML Models | 75% | 100% |

### Coverage Reports

Coverage reports are generated automatically and stored in:
- `apps/backend/htmlcov/`
- `packages/axiomatic-kernel/htmlcov/`

View reports by opening `index.html` in each directory.

## CI/CD Integration

### GitHub Actions Workflow

Tests run automatically on:

1. **Pull Requests**
   - Unit tests only (fast feedback)
   - Blocks merge if tests fail

2. **Push to Main**
   - Unit + Integration tests
   - Coverage reports generated
   - Blocks deployment if tests fail

3. **Weekly Schedule**
   - Full test suite including E2E
   - Performance benchmarks
   - Regression detection

### Smoke Tests

Smoke tests run on every commit to ensure basic functionality:
- Service health checks
- API endpoint availability
- Frontend load test
- DAG import validation

See [`smoke_test.sh`](./smoke_test.sh) for implementation details.

## Test Data Management

### Fixtures

Test fixtures are stored in component-specific directories:

- **Frontend**: [`apps/frontend/src/data/mockDrivers.json`](../apps/frontend/src/data/mockDrivers.json)
- **Backend**: Uses pytest fixtures in `conftest.py` (to be created)
- **ML**: Test data in `packages/axiomatic-kernel/tests/`

### Database

Tests use a separate test database:
- Initialized in CI pipeline
- Reset between test runs
- Populated with seed data

### Data Cleanup

All tests follow isolation principles:
- Each test creates its own data
- Data cleaned up after test completion
- No state shared between tests

## Best Practices

### Writing Tests

1. **Arrange-Act-Assert Pattern**
   ```python
   def test_optimization():
       # Arrange
       drivers = create_test_drivers()
       request = OptimizationRequest(salary_cap=50000)
       
       # Act
       result = optimize(drivers, request)
       
       # Assert
       assert result.total_salary <= 50000
       assert len(result.lineup) == 6
   ```

2. **Descriptive Test Names**
   - Use `test_should_return_valid_lineup_when_given_valid_drivers`
   - Avoid `test_1`, `test_function`, etc.

3. **Test One Thing**
   - Each test should verify a single behavior
   - Use multiple tests for different scenarios

4. **Use Fixtures**
   ```python
   @pytest.fixture
   def sample_drivers():
       return [
           Driver(id="1", name="Driver A", salary=8000, projected_points=25),
           Driver(id="2", name="Driver B", salary=9000, projected_points=30),
       ]
   ```

### Test Organization

1. **Group Related Tests**
   - Use test classes for related functionality
   - Use descriptive module names

2. **Keep Tests Fast**
   - Mock external dependencies
   - Use in-memory databases
   - Avoid unnecessary setup

3. **Make Tests Independent**
   - No test should depend on another
   - Tests can run in any order

### Debugging Tests

1. **Verbose Output**
   ```bash
   pytest tests/ -v -s
   ```

2. **Stop on First Failure**
   ```bash
   pytest tests/ -x
   ```

3. **Run Specific Test**
   ```bash
   pytest tests/test_main.py::test_health_endpoint
   ```

4. **Debug with pdb**
   ```bash
   pytest tests/ --pdb
   ```

## Common Issues and Solutions

### Issue: Tests Fail in CI but Pass Locally

**Possible Causes**:
- Environment differences (Python version, dependencies)
- Missing environment variables
- Database connection issues

**Solutions**:
- Check CI logs for specific error messages
- Ensure all dependencies are in `requirements.txt`
- Add environment variables to CI configuration
- Use test database instead of local database

### Issue: Flaky Tests

**Possible Causes**:
- Timing issues (async operations)
- External service dependencies
- Shared state between tests

**Solutions**:
- Add explicit waits for async operations
- Mock external services
- Ensure proper test isolation
- Use fixtures for setup/teardown

### Issue: Slow Tests

**Possible Causes**:
- Too many integration tests
- Heavy database operations
- No test parallelization

**Solutions**:
- Move slow tests to integration/E2E suite
- Use in-memory databases for unit tests
- Run tests in parallel: `pytest -n auto`

## Continuous Improvement

### Regular Reviews

- Review test coverage monthly
- Update test scenarios for new features
- Refactor tests for maintainability
- Remove duplicate or obsolete tests

### Metrics

Track and improve:
- Test execution time
- Pass/fail rates
- Code coverage trends
- Flaky test count

### Documentation

Keep documentation updated:
- Add new test patterns
- Document complex test scenarios
- Share testing knowledge with team

## Resources

### Documentation
- [E2E Test Plan](./E2E_TEST_PLAN.md) - Detailed E2E test scenarios
- [Backend Tests](../apps/backend/tests/) - Backend test implementation
- [Frontend Tests](../apps/frontend/__tests__/) - Frontend test implementation
- [ETL Tests](../apps/airflow/tests/) - ETL test implementation
- [ML Tests](../packages/axiomatic-kernel/tests/) - ML test implementation

### Tools
- [pytest](https://docs.pytest.org/) - Python testing framework
- [Jest](https://jestjs.io/) - JavaScript testing framework
- [React Testing Library](https://testing-library.com/react) - React component testing
- [pytest-cov](https://pytest-cov.readthedocs.io/) - Coverage plugin for pytest

## Support

For questions or issues related to testing:
1. Check this documentation
2. Review existing tests for examples
3. Consult the E2E test plan for scenarios
4. Reach out to the test team via the project's communication channels

---

**Last Updated**: 2026-01-25

**Maintained By**: Test Agent (agents/test/)
