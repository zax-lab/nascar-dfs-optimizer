---
phase: 04-field-ownership-contest-sim
plan: 01
subsystem: ownership-estimation
tags: [scikit-learn, pandas, numpy, random-forest, linear-regression, feature-engineering]

# Dependency graph
requires:
  - phase: 03-tail-metrics-tail-objective-portfolio-optimizer
    provides: portfolio_generator, tail_metrics, optimizer infrastructure
provides:
  - Individual ownership estimation models (historical, projections, salary-skill)
  - Feature engineering pipeline for ownership prediction
  - Fit/predict interface compatible with scikit-learn ensembles
affects: [04-02-ensemble-ownership, field-simulation, contest-simulation]

# Tech tracking
tech-stack:
  added: [scikit-learn (LinearRegression, RandomForestRegressor)]
  patterns: [fit/predict interface, pandas groupby aggregation, mean imputation, one-hot encoding]

key-files:
  created:
    - apps/backend/app/ownership/__init__.py
    - apps/backend/app/ownership/historical.py
    - apps/backend/app/ownership/projections.py
    - apps/backend/app/ownership/projections_fetcher.py
    - apps/backend/app/ownership/salary_model.py
    - apps/backend/app/ownership/features.py
  modified: []

key-decisions:
  - "Used pandas groupby for historical ownership aggregation (efficient lookup)"
  - "Linear regression for value_score ~ ownership relationship (interpretable)"
  - "RandomForestRegressor for salary-skill-ownership (captures non-linear interactions)"
  - "Mean imputation for missing skill (0.5 neutral default)"
  - "Manual mode for projections (API-provided, not fetching from external APIs yet)"

patterns-established:
  - "Pattern: scikit-learn fit/predict interface for all estimators"
  - "Pattern: graceful degradation for unseen drivers/tracks/missing data"
  - "Pattern: logging diagnostics (feature importance, R², coverage stats)"
  - "Pattern: clipping predictions to [0, 100] range"

# Metrics
duration: 4min
completed: 2026-01-28
---

# Phase 4 Plan 1: Individual Ownership Estimation Models Summary

**Three ownership estimators with fit/predict interface (historical baselines, projections-based value regression, salary-skill RandomForest) plus feature engineering utilities for ensemble composition**

## Performance

- **Duration:** 4 min
- **Started:** 2026-01-28T02:40:16Z
- **Completed:** 2026-01-28T02:44:36Z
- **Tasks:** 4
- **Files modified:** 6

## Accomplishments

- Created HistoricalOwnershipEstimator with track-archetype specific baselines and fallback mechanisms
- Built ProjectionOwnershipEstimator learning linear relationship between value_score and ownership
- Implemented SalarySkillRegressionEstimator using RandomForest for non-linear salary-skill-ownership relationships
- Developed feature engineering pipeline with value scores, track encoding, and recent form statistics

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ownership module with historical estimator** - `19b71ec` (feat)
2. **Task 2: Create projections-based ownership estimator** - `ea9eb18` (feat)
3. **Task 3: Create salary-skill regression estimator** - `69dd4ad` (feat)
4. **Task 4: Create feature engineering utilities** - `4885319` (feat)

**Plan metadata:** `3a8c6ce` (refactor: update ownership module exports)

## Files Created/Modified

- `apps/backend/app/ownership/__init__.py` - Module exports and docstring
- `apps/backend/app/ownership/historical.py` - HistoricalOwnershipEstimator (278 lines)
- `apps/backend/app/ownership/projections.py` - ProjectionOwnershipEstimator (248 lines)
- `apps/backend/app/ownership/projections_fetcher.py` - ProjectionsFetcher for external sources (201 lines)
- `apps/backend/app/ownership/salary_model.py` - SalarySkillRegressionEstimator (291 lines)
- `apps/backend/app/ownership/features.py` - Feature engineering utilities (372 lines)

## Decisions Made

- Used pandas groupby for historical ownership aggregation (efficient O(1) lookup after fit)
- Linear regression for projections-based model (interpretable slope parameter, simple relationship)
- RandomForestRegressor for salary-skill model (captures non-linear interactions between salary/skill/recent form)
- Mean imputation for missing skill values (0.5 neutral default prevents bias)
- Manual mode for projections (API-provided, avoiding external API dependencies in this phase)
- One-hot encoding for track archetypes (superspeedway, intermediate, short_track, road_course)
- Value score scaling by 1000 (numerical stability for salary ~10000)

## Deviations from Plan

None - plan executed exactly as written.

All estimators implement fit/predict interface as specified, handle missing data gracefully, and provide logging for diagnostics. Feature engineering utilities create the expected feature matrix with one-hot encoding and rolling statistics.

## Issues Encountered

- Syntax error in salary_model.py logging statement (nested f-string) - fixed by extracting to separate variable
- Import errors in __init__.py due to missing modules - fixed by commenting out unimplemented imports during development

## Verification

All success criteria met:

- [x] All three estimators (historical, projections, salary-skill) implement fit/predict interface
- [x] Feature engineering utilities create feature matrices with one-hot encoding
- [x] Each estimator handles missing data gracefully (mean imputation, fallbacks)
- [x] Unit tests pass for all estimators
- [x] Module is importable without errors

All must-haves verified:

- [x] Historical ownership model computes track-archetype specific baseline ownership
- [x] Projections-based model estimates ownership from projected points vs salary ratio
- [x] Salary-skill regression model learns relationship between salary/skill and ownership
- [x] Feature engineering pipeline creates ownership prediction features
- [x] All models handle missing data gracefully (graceful degradation)

All artifacts meet minimum line requirements:

- [x] historical.py: 278 lines (min 80)
- [x] projections.py: 248 lines (min 80)
- [x] projections_fetcher.py: 201 lines (min 60)
- [x] salary_model.py: 291 lines (min 100)
- [x] features.py: 372 lines (min 150)

## Next Phase Readiness

**Ready for Plan 04-02 (Ensemble Ownership Estimation):**
- Individual estimators follow scikit-learn interface (fit/predict)
- Feature engineering provides consistent feature matrix
- Historical, projections, and salary-skill signals available for combination
- Missing data handling ensures robustness for ensemble training

**No blockers or concerns.** All estimators tested independently and ready for ensemble composition.

---
*Phase: 04-field-ownership-contest-sim*
*Completed: 2026-01-28*
