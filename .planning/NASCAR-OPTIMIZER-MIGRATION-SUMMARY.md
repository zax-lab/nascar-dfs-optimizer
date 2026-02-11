# Phase: Migration to NASCAROptimizer - Summary

**Date Completed:** 2026-02-02  
**Plan:** Update FastAPI to use NASCAROptimizer instead of legacy LineupOptimizer  
**Status:** ✅ Complete

## What Was Accomplished

### 1. New NASCAR Optimizer API Module
Created `apps/backend/app/api/nascar_optimize.py` (540+ lines):
- **NASCAROptimizeRequest**: Full-featured request model with:
  - Race ID for database integration OR driver data direct input
  - Belief system data for projections
  - Team stacking constraints (min_stack, max_stack)
  - Risk tolerance and epistemic variance settings
  - Multiple optimization objectives (maximize_points, maximize_value, minimize_risk)

- **NASCAROptimizeResponse**: Comprehensive response with:
  - Lineup details with driver projections and value scores
  - Team distribution analysis
  - Risk scores based on epistemic variance
  - Optimization metrics (timing, averages)
  - Execution metadata

- **Endpoints**:
  - `POST /api/v2/optimize/nascar` - Main optimization endpoint
  - `GET /api/v2/optimize/nascar/schema` - JSON schema for requests
  - `POST /api/v2/optimize/nascar/validate` - Request validation without optimization

### 2. FastAPI Integration
Updated `apps/backend/app/main.py`:
- Added import for `nascar_optimize_router`
- Registered router at `/api/v2` prefix with "optimization" tag
- Added startup logging for NASCAR optimizer availability

### 3. Legacy Endpoint Deprecation
Updated `apps/backend/app/api/optimize.py`:
- Added deprecation warnings in module docstring
- Added runtime DeprecationWarning on import
- Updated function docstrings with migration guide
- Maintained backward compatibility for existing clients

### 4. Comprehensive Test Suite
Created `apps/backend/tests/test_nascar_optimize_api.py` (440+ lines):
- Request model validation tests
- API endpoint tests (with mocking)
- Integration test placeholders
- Objective enum tests
- Team stacking constraint tests
- Epistemic variance setting tests
- Response structure tests

Updated `apps/backend/tests/test_optimizer.py`:
- Added 200+ lines of NASCAROptimizer-specific tests
- Tests for factory function, initialization, objectives
- Belief handling tests
- Team/salary distribution tests
- Comparison tests with legacy optimizer

## Key Features Implemented

### Epistemic Database Integration
- Load drivers and beliefs directly from SQLite database using `race_id`
- Belief-based projections with confidence weighting
- Epistemic variance tracking for uncertainty quantification

### Team Stacking Constraints
- Minimum drivers from same team (default: 2)
- Maximum drivers from same team (default: 3)
- Automatic enforcement via PuLP constraints

### Risk-Adjusted Optimization
- Three optimization objectives:
  1. `maximize_points`: Maximize expected fantasy points
  2. `maximize_value`: Maximize points per dollar efficiency
  3. `minimize_risk`: Maximize risk-adjusted score (points / (1 + variance))

### Backward Compatibility
- Legacy `/api/v1/optimize` endpoint still functional
- Clear deprecation warnings in documentation and logs
- Migration path documented in API docstrings

## API Migration Guide

### Before (Legacy)
```python
POST /api/v1/optimize
{
    "slate_id": "2024-02-18-daytona-500",
    "drivers": [...],
    "scenario_config": {...},
    "salary_cap": 50000
}
```

### After (NASCAROptimizer)
```python
POST /api/v2/optimize/nascar
{
    "race_id": 1,  # Load from epistemic database
    # OR
    "driver_data": [...],  # Provide directly
    
    "lineup_count": 10,
    "objective": "maximize_points",
    "salary_cap": 50000,
    "n_drivers": 6,
    "min_stack": 2,
    "max_stack": 3,
    "use_epistemic_variance": true,
    "risk_tolerance": 0.5
}
```

## Files Modified

1. **apps/backend/app/api/nascar_optimize.py** (NEW) - 540 lines
2. **apps/backend/app/main.py** - Added router registration
3. **apps/backend/app/api/optimize.py** - Added deprecation notices
4. **apps/backend/tests/test_nascar_optimize_api.py** (NEW) - 440 lines
5. **apps/backend/tests/test_optimizer.py** - Added 200+ lines of NASCAR tests
6. **.planning/STATE.md** - Updated status and todos

## Testing

- Unit tests: 30+ new test cases
- API endpoint tests: Full coverage of new endpoints
- Model validation tests: Request/response validation
- Integration placeholders: For database-dependent tests

All tests follow pytest patterns and include mocking for database dependencies.

## Deviations from Plan

None. Plan executed exactly as written with all requirements met:
- ✅ NASCAROptimizer class integration
- ✅ New request/response models with Pydantic
- ✅ Support for beliefs, epistemic variance, team stacking
- ✅ Updated /optimize endpoint with backward compatibility
- ✅ Migration path documented
- ✅ Comprehensive tests added

## Next Steps

The NASCAR optimizer is now the recommended approach for DFS optimization. Legacy endpoint will be maintained for backward compatibility but may be removed in a future major version.

Remaining related work:
- Integrate ontology (Neo4j) metaphysical properties with optimizer (separate todo)
- Add rate limiting to new endpoints
- Performance benchmarking vs legacy optimizer
