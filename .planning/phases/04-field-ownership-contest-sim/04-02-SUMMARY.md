---
phase: 04-field-ownership-contest-sim
plan: 02
subsystem: ownership-estimation
tags: [scikit-learn, pandas, numpy, pydantic, ensemble, voting-regressor, stacking-regressor, bootstrap-uncertainty]

# Dependency graph
requires:
  - phase: 04-field-ownership-contest-sim
    plan: 01
    provides: Individual ownership estimators (historical, projections, salary-skill regression)
provides:
  - RecentFormEstimator for rolling ownership calculations
  - HybridOwnershipEstimator ensemble combining all base estimators
  - Pydantic models for ownership API validation
  - Uncertainty quantification via bootstrap resampling
affects: [04-03-contest-simulation, 04-04-leverage-optimization]

# Tech tracking
tech-stack:
  added: [scikit-learn, pandas, numpy, pydantic]
  patterns: [ensemble methods, voting regressor, stacking regressor, bootstrap uncertainty, sklearn wrapper pattern]

key-files:
  created:
    - apps/backend/app/ownership/recent_form.py
    - apps/backend/app/ownership/ensemble.py
    - apps/backend/app/ownership/models.py
  modified: []

key-decisions:
  - "Custom sklearn wrapper for base estimators to enable VotingRegressor/StackingRegressor compatibility"
  - "Manual stacking meta-learner fitting due to custom estimator wrappers"
  - "Pydantic model_config['protected_namespaces'] = () to allow model_metadata field"
  - "Bootstrap uncertainty prediction using resampling for confidence bounds"

patterns-established:
  - "Pattern 1: Scikit-learn ensemble wrapper pattern for custom estimators"
  - "Pattern 2: Bootstrap uncertainty quantification for ensemble predictions"
  - "Pattern 3: Pydantic validation with enums for categorical fields (track_archetype, ensemble_method)"

# Metrics
duration: 4m
completed: 2026-01-28
---

# Phase 04 Plan 02: Ensemble Ownership Estimation Summary

**Hybrid ensemble ownership estimator combining 4 base signals with voting/stacking methods and bootstrap uncertainty quantification**

## Performance

- **Duration:** 4m (268s)
- **Started:** 2026-01-28T02:48:10Z
- **Completed:** 2026-01-28T02:52:38Z
- **Tasks:** 3
- **Files created:** 3

## Accomplishments

- **RecentFormEstimator:** Rolling ownership from last N races with exponential/linear/no decay
- **HybridOwnershipEstimator:** Ensemble combining historical, projections, salary-skill, and recent form estimators
- **Ownership Pydantic models:** Request/response validation with track archetype and uncertainty bounds
- **Uncertainty quantification:** Bootstrap resampling for confidence intervals (5th/95th percentiles)

## Task Commits

Each task was committed atomically:

1. **Task 1: RecentFormEstimator** - `44b58d0` (feat)
2. **Task 2: HybridOwnershipEstimator** - `0e89e2e` (feat)
3. **Task 3: Ownership Pydantic models** - `c602f91` (feat)

## Files Created/Modified

- `apps/backend/app/ownership/recent_form.py` - RecentFormEstimator with rolling ownership, decay options, coverage stats
- `apps/backend/app/ownership/ensemble.py` - HybridOwnershipEstimator with voting/stacking, uncertainty bounds, sklearn wrapper
- `apps/backend/app/ownership/models.py` - Pydantic models for ownership API (Request, Response, Prediction)

## Decisions Made

**Custom sklearn wrapper for base estimators**
- Rationale: VotingRegressor/StackingRegressor require estimators with get_params/set_params interface
- Implemented _BaseEstimatorWrapper to adapt custom estimators to sklearn interface
- Enables ensemble methods while maintaining custom fit/predict logic

**Manual stacking meta-learner fitting**
- Rationale: StackingRegressor's automatic fitting doesn't work with custom wrappers
- Manually create meta-features from base predictions and fit BayesianRidge meta-learner
- Works correctly for both voting and stacking methods

**Pydantic model_config for protected namespaces**
- Rationale: model_metadata field conflicts with Pydantic's protected "model_" namespace
- Set model_config = {'protected_namespaces': ()} to allow field name
- Eliminates warning while maintaining field name

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

**Issue 1: StackingRegressor attribute error**
- Problem: 'StackingRegressor' object has no attribute 'final_estimator_'
- Resolution: Changed to self.model.final_estimator (without underscore)
- Root cause: Confusion about sklearn's internal attribute naming

**Issue 2: BayesianRidge NotFittedError**
- Problem: Meta-learner not fitted when using stacking
- Resolution: Manually fit BayesianRidge on base estimator predictions
- Root cause: Custom wrappers prevent sklearn's automatic fitting

## Next Phase Readiness

**Ready for Phase 04-03 (Contest Simulation):**
- Ownership estimation complete with uncertainty quantification
- Ensemble predictions available for field lineup modeling
- Pydantic models ready for API integration

**Ready for Phase 04-04 (Leverage-Aware Optimization):**
- Ownership predictions can be used as leverage signals
- Uncertainty bounds enable risk-aware optimization
- Feature importance from ensemble informs weight selection

**Blockers/Concerns:**
- None - all ownership estimation infrastructure in place

---
*Phase: 04-field-ownership-contest-sim*
*Plan: 02*
*Completed: 2026-01-28*
