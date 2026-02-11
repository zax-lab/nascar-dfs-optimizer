# E2E Test Plan - NASCAR DFS Engine

## Overview

This document outlines the End-to-End (E2E) testing strategy for the Axiomatic NASCAR DraftKings DFS engine, covering all components: backend API, frontend UI, Airflow ETL pipelines, and ML projection models.

## Test Philosophy

- **Data-Driven**: Tests use realistic NASCAR data and scenarios
- **Component Integration**: Verify end-to-end workflows across all services
- **Performance**: Ensure optimization completes within acceptable timeframes
- **Reliability**: Validate system behavior under various conditions

## Test Environment

### Prerequisites
- Docker Compose running with all services
- PostgreSQL database initialized
- Airflow webserver and scheduler running
- Backend API accessible at `http://localhost:8000`
- Frontend accessible at `http://localhost:3000`
- ML package installed and models loaded

### Test Data
- Sample driver roster with realistic statistics
- Historical race data for projection validation
- Mock DraftKings salary and scoring rules

## Test Scenarios

### 1. Health Check E2E Test

**Objective**: Verify all services are operational

**Steps**:
1. Start all services via Docker Compose
2. Call `/health` endpoint on backend API
3. Verify Airflow webserver responds
4. Check frontend loads without errors
5. Verify ML package can load models

**Expected Results**:
- Backend returns `{"status": "healthy"}`
- Airflow UI accessible at `http://localhost:8080`
- Frontend displays dashboard
- ML models load without errors

**Success Criteria**: All services report healthy status

---

### 2. Data Pipeline E2E Test

**Objective**: Validate complete ETL workflow from data ingestion to projections

**Steps**:
1. Trigger Airflow DAG `nascar_etl_dag`
2. Monitor DAG execution through all tasks
3. Verify data is extracted from source
4. Confirm transformations are applied
5. Check data is loaded into database
6. Validate ML projections are generated
7. Verify API can retrieve latest projections

**Expected Results**:
- DAG completes successfully
- All tasks pass without retries
- Database contains updated driver data
- Projections available via `/projections` endpoint
- Data integrity maintained throughout pipeline

**Success Criteria**: Complete pipeline executes without errors

---

### 3. Optimization E2E Test

**Objective**: Test complete optimization workflow from request to optimal lineup

**Steps**:
1. Load driver projections into database
2. Submit optimization request via `/optimize` endpoint
3. Verify backend processes request
4. Check optimizer uses correct constraints
5. Validate optimal lineup returned
6. Verify lineup meets all constraints:
   - Salary cap ($50,000)
   - Exactly 6 drivers
   - No more than 4 drivers from same team
   - No duplicate drivers
7. Calculate expected lineup score
8. Verify score matches backend calculation

**Expected Results**:
- Optimization completes within 30 seconds
- Lineup is valid per all constraints
- Score is maximized for given constraints
- Response includes lineup details and total score

**Success Criteria**: Valid optimal lineup returned with correct score

---

### 4. Frontend Integration E2E Test

**Objective**: Verify user can view projections and optimize lineups through UI

**Steps**:
1. Navigate to frontend application
2. Verify projection table loads with driver data
3. Check table displays all required columns:
   - Driver name
   - Team
   - Salary
   - Projected points
   - Value metric
4. Select drivers for optimization
5. Click "Optimize Lineup" button
6. Verify API call to `/optimize`
7. Display optimal lineup results
8. Verify lineup details shown correctly
9. Check total salary and projected points

**Expected Results**:
- Frontend loads without console errors
- Projection table displays data correctly
- Optimization request completes successfully
- Results displayed clearly to user
- All interactive elements work as expected

**Success Criteria**: Complete user workflow functions end-to-end

---

### 5. ML Model E2E Test

**Objective**: Validate ML model predictions are accurate and usable

**Steps**:
1. Load historical race data
2. Train projection model (or use pre-trained)
3. Generate projections for upcoming race
4. Compare projections to actual results (if available)
5. Verify projection distribution is reasonable
6. Check API can retrieve projections
7. Validate frontend displays projections correctly

**Expected Results**:
- Model trains without errors
- Projections fall within expected ranges (0-50 points)
- Projections correlate with driver skill
- API returns projections in correct format
- Frontend displays projections accurately

**Success Criteria**: ML model generates valid, usable projections

---

### 6. Constraint Validation E2E Test

**Objective**: Ensure optimizer respects all DraftKings constraints

**Steps**:
1. Create test scenarios with edge cases:
   - All drivers from same team
   - High-value, low-salary drivers
   - Drivers with same salary
2. Submit optimization requests for each scenario
3. Verify each lineup is valid:
   - Salary ≤ $50,000
   - Exactly 6 drivers
   - ≤ 4 drivers per team
   - No duplicate drivers
4. Verify optimizer finds best solution within constraints

**Expected Results**:
- All constraints respected in every scenario
- No invalid lineups returned
- Optimizer handles edge cases gracefully
- Reasonable computation time (< 30 seconds)

**Success Criteria**: All constraints enforced correctly

---

### 7. Error Handling E2E Test

**Objective**: Verify system handles errors gracefully

**Steps**:
1. Test API with invalid requests:
   - Missing required fields
   - Invalid data types
   - Out-of-range values
2. Test with unavailable data:
   - Empty projection database
   - Missing driver data
3. Test with service failures:
   - Database connection lost
   - ML model unavailable
4. Verify appropriate error responses
5. Check frontend displays error messages

**Expected Results**:
- Clear error messages returned
- No system crashes
- Frontend shows user-friendly errors
- Services recover gracefully

**Success Criteria**: All errors handled appropriately

---

### 8. Performance E2E Test

**Objective**: Ensure system meets performance requirements

**Steps**:
1. Measure API response times:
   - `/health` endpoint
   - `/projections` endpoint
   - `/optimize` endpoint
2. Test with varying dataset sizes:
   - 20 drivers
   - 50 drivers
   - 100 drivers
3. Measure frontend load time
4. Test concurrent optimization requests
5. Monitor resource usage

**Expected Results**:
- `/health` responds in < 100ms
- `/projections` responds in < 500ms
- `/optimize` completes in < 30 seconds
- Frontend loads in < 3 seconds
- System handles 10 concurrent requests

**Success Criteria**: All performance targets met

---

### 9. Data Consistency E2E Test

**Objective**: Verify data remains consistent across components

**Steps**:
1. Ingest driver data via Airflow
2. Verify data in database
3. Check ML projections use same data
4. Verify API returns consistent data
5. Confirm frontend displays matching data
6. Update driver data
7. Verify changes propagate to all components

**Expected Results**:
- All components use same data source
- Changes propagate correctly
- No data corruption or inconsistencies
- Data integrity maintained

**Success Criteria**: Data consistent across all components

---

### 10. Regression E2E Test

**Objective**: Ensure existing functionality still works after changes

**Steps**:
1. Run all above test scenarios
2. Compare results to baseline
3. Verify no regressions introduced
4. Document any differences

**Expected Results**:
- All tests pass
- Results match baseline
- No unexpected behavior changes

**Success Criteria**: Zero regressions

---

## Integration Test Approach

### Test Pyramid

```
        /\
       /E2E\      - Critical user workflows
      /------\
     /Integration\ - Component interactions
    /------------\
   /   Unit Tests  \ - Individual functions
  /----------------\
```

### Test Categories

1. **Unit Tests** (Component-specific)
   - Backend: `apps/backend/tests/`
   - Frontend: `apps/frontend/__tests__/`
   - ETL: `apps/airflow/tests/`
   - ML: `packages/axiomatic-kernel/tests/`

2. **Integration Tests** (Cross-component)
   - API + Database
   - ETL + Database
   - ML + API
   - Frontend + API

3. **E2E Tests** (Full system)
   - Complete user workflows
   - Data pipeline end-to-end
   - Multi-service scenarios

### Test Execution Strategy

#### Local Development
```bash
# Run unit tests for all components
pytest apps/backend/tests/
pytest apps/airflow/tests/
pytest packages/axiomatic-kernel/tests/
jest apps/frontend/__tests__/

# Run integration tests
pytest tests/integration/

# Run E2E tests
pytest tests/e2e/
```

#### CI/CD Pipeline
1. **Pull Request**: Run unit tests only (fast feedback)
2. **Merge to main**: Run unit + integration tests
3. **Release**: Run full test suite including E2E

### Test Data Management

#### Fixtures
- Driver roster: `apps/frontend/src/data/mockDrivers.json`
- Test database: Initialized in CI
- ML test data: `packages/axiomatic-kernel/tests/`

#### Data Cleanup
- Each test isolates its data
- Database reset between test runs
- Temporary files cleaned up after tests

---

## Test Coverage Goals

### Backend API
- Target: 80% code coverage
- Critical paths: 100%
- Error handling: 90%

### Frontend
- Target: 70% code coverage
- Critical components: 90%
- User workflows: 100%

### ETL Pipelines
- Target: 85% code coverage
- Data transformations: 100%
- Error scenarios: 90%

### ML Models
- Target: 75% code coverage
- Model inference: 100%
- Data preprocessing: 90%

---

## Test Automation

### GitHub Actions Workflow

The E2E tests run automatically on:
- Pull requests to `main`
- Pushes to `main`
- Weekly schedule (Sunday 2 AM UTC)

### Smoke Tests

Quick validation tests run on every commit:
- Service health checks
- Basic API endpoints
- Frontend load test
- DAG import validation

See [`smoke_test.sh`](./smoke_test.sh) for details.

---

## Reporting and Metrics

### Test Results
- All test results logged to GitHub Actions
- Coverage reports generated and stored
- Failed tests block merges

### Metrics Tracked
- Test execution time
- Pass/fail rates
- Code coverage trends
- Flaky test detection

---

## Maintenance

### Regular Updates
- Review test scenarios quarterly
- Update test data as needed
- Refactor tests for maintainability
- Add new scenarios for features

### Test Quality
- Remove duplicate tests
- Consolidate similar tests
- Improve test clarity
- Add better error messages

---

## Next Steps

1. Implement automated E2E test suite
2. Set up test data fixtures
3. Configure CI/CD integration
4. Establish coverage reporting
5. Create test documentation for developers

---

## Appendix: Test Data Schema

### Driver Data
```json
{
  "id": "string",
  "name": "string",
  "team": "string",
  "salary": number,
  "projected_points": number,
  "avg_finish": number,
  "top_10_rate": number
}
```

### Optimization Request
```json
{
  "salary_cap": 50000,
  "max_drivers_per_team": 4,
  "lineup_size": 6
}
```

### Optimization Response
```json
{
  "lineup": [
    {"driver_id": "string", "salary": number, "projected_points": number}
  ],
  "total_salary": number,
  "total_points": number
}
```
