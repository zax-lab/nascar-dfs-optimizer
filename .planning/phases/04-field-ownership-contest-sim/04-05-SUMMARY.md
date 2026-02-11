---
phase: 04-field-ownership-contest-sim
plan: 05
subsystem: portfolio-optimization
tags: [leverage-aware-optimization, ownership-constraints, regime-aware-portfolios, nascar-dfs, pulp]

# Dependency graph
requires:
  - phase: 04-field-ownership-contest-sim
    plan: 01
    provides: "Individual ownership estimators (historical, projections, salary-skill, recent form)"
  - phase: 04-field-ownership-contest-sim
    plan: 02
    provides: "HybridOwnershipEstimator ensemble combining multiple ownership signals"
  - phase: 04-field-ownership-contest-sim
    plan: 04
    provides: "Field lineup sampling and contest simulation infrastructure"
provides:
  - LeverageAwareOptimizer extending NASCAROptimizer with ownership penalties
  - Regime-aware portfolio allocation across race-flow scenarios (dominator, chaos, fuel_mileage)
  - Ownership constraints (max per driver, min low-ownership drivers, max total ownership)
  - Leverage metrics (avg ownership, max ownership, leverage score) for portfolio evaluation
affects: [contest-simulation, portfolio-optimization, tournament-equity]

# Tech tracking
tech-stack:
  added: [LeverageAwareOptimizer, regime-classification, ownership-metrics]
  patterns:
    - TYPE_CHECKING for avoiding circular imports
    - Ownership-aware objective functions with leverage penalties
    - Regime-based portfolio allocation for scenario diversity
    - Leverage metrics calculation for lineup differentiation

key-files:
  created:
    - apps/backend/app/optimizer/leverage_aware.py
    - apps/backend/app/optimizer/__init__.py
    - apps/backend/test_leverage_structure.py
    - apps/backend/test_portfolio_regime.py
  modified:
    - apps/backend/app/portfolio_generator.py

key-decisions:
  - "Used TYPE_CHECKING to avoid circular import with NASCAROptimizer"
  - "Ownership penalty calculated as quadratic function (ownership^2) to heavily penalize chalk"
  - "Regime classification based on variance and dominance ratios for race-flow patterns"
  - "Integer lineup allocation with remainder to highest-weight regime"
  - "Ownership constraints enforced at optimization level, not post-hoc filtering"

patterns-established:
  - "Pattern: Ownership-aware optimization - extends base optimizer without modification"
  - "Pattern: Regime-aware allocation - classify scenarios, allocate lineups, optimize per regime"
  - "Pattern: Leverage metrics - avg/max/total ownership plus leverage score for differentiation"

# Metrics
duration: 25min
completed: 2026-01-28
---

# Phase 4: Plan 5 - Leverage-Aware Portfolio Optimization Summary

**Leverage-aware optimizer with ownership penalties and regime-aware portfolio allocation for tournament equity differentiation**

## Performance

- **Duration:** 25 min
- **Started:** 2026-01-28T03:00:59Z
- **Completed:** 2026-01-28T03:25:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Created LeverageAwareOptimizer extending NASCAROptimizer with ownership-aware optimization
- Added ownership constraints (max per driver, min low-ownership drivers, max total ownership)
- Implemented leverage metrics calculation (avg ownership, max ownership, leverage score)
- Extended portfolio generator with regime-aware allocation across race-flow scenarios
- Added classify_scenario_regime() for dominator/chaos/fuel_mileage classification
- Added allocate_lineups_by_regime() for distributing lineups by regime weights

## Task Commits

Each task was committed atomically:

1. **Task 1: Create leverage-aware optimizer** - `7e7352b` (feat)
   - LeverageAwareOptimizer class with ownership penalties
   - Ownership constraints and leverage metrics
   - Input validation and comprehensive docstrings

2. **Task 2: Extend portfolio generator for regime-aware allocation** - `7721d83` (feat)
   - Regime classification based on variance/dominance
   - Lineup allocation by regime weights
   - Regime-aware portfolio generation

**Plan metadata:** (pending final commit)

## Files Created/Modified

### Created

- `apps/backend/app/optimizer/leverage_aware.py` - LeverageAwareOptimizer with ownership penalties (250+ lines)
- `apps/backend/app/optimizer/__init__.py` - Package initialization for optimizer module
- `apps/backend/test_leverage_structure.py` - Structure validation tests
- `apps/backend/test_portfolio_regime.py` - Regime function tests

### Modified

- `apps/backend/app/portfolio_generator.py` - Added regime-aware allocation functions

## Decisions Made

- Used TYPE_CHECKING to avoid circular import with NASCAROptimizer (optimizer.py imports app.models)
- Ownership penalty calculated as quadratic function (ownership^2) to heavily penalize high-owned drivers
- Regime classification based on variance and dominance ratios for race-flow patterns
- Integer lineup allocation with remainder distributed to highest-weight regime
- Ownership constraints enforced at optimization level (not post-hoc filtering) for efficiency

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed circular import with optimizer.py**
- **Found during:** Task 1 (LeverageAwareOptimizer creation)
- **Issue:** Direct import of NASCAROptimizer caused circular import (optimizer.py imports app.models)
- **Fix:** Used TYPE_CHECKING for type hints, avoiding runtime import of NASCAROptimizer
- **Files modified:** apps/backend/app/optimizer/leverage_aware.py
- **Verification:** Module imports successfully, tests pass
- **Committed in:** 7e7352b (Task 1 commit)

**2. [Rule 3 - Blocking] Created optimizer package __init__.py**
- **Found during:** Task 1 (Package structure)
- **Issue:** optimizer/ directory needs __init__.py for proper Python package
- **Fix:** Created __init__.py with LeverageAwareOptimizer export
- **Files modified:** apps/backend/app/optimizer/__init__.py
- **Verification:** Package imports correctly
- **Committed in:** 7e7352b (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both auto-fixes necessary for Python module structure and imports. No scope creep.

## Issues Encountered

- Initial attempt to import NASCAROptimizer directly failed due to app.models dependency in optimizer.py
- Resolved by using TYPE_CHECKING for type hints and Any type for runtime base_optimizer parameter

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Leverage-aware optimizer ready for integration with contest simulation
- Regime-aware portfolio allocation provides scenario diversity for tournament equity
- Ownership constraints enable field differentiation for GPP leverage
- Ready for Phase 4 completion (final integration and end-to-end testing)

### Blockers/Concerns

- LeverageAwareOptimizer extends NASCAROptimizer but uses TYPE_CHECKING to avoid circular import
  - This works for type hints but runtime calls to NASCAROptimizer methods need to be validated
  - Integration testing required with full database setup

- Regime classification logic based on variance/dominance heuristics
  - May need calibration with real NASCAR race data
  - Consider machine learning approach for regime classification in production

- Ownership constraints enforced at optimization level but not validated in portfolio_generator
  - Need to ensure leverage metrics are calculated and constraints checked
  - Post-generation filtering may be needed for edge cases

---
*Phase: 04-field-ownership-contest-sim*
*Plan: 05*
*Completed: 2026-01-28*
