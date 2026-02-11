---
phase: 04-field-ownership-contest-sim
plan: 04
subsystem: contest-simulation
tags: [monte-carlo, ownership-modeling, payout-curve, numpy-vectorization, dirichlet-multinomial]

# Dependency graph
requires:
  - phase: 04-field-ownership-contest-sim
    plan: 03
    provides: PayoutCurveFitter for payout interpolation
provides:
  - FieldLineupSampler for ownership-based field generation using Dirichlet-multinomial sampling
  - ContestSimulator for Monte Carlo contest simulation with vectorized NumPy operations
  - Contest metrics utilities (ROI, cash%, win probability) with confidence intervals
affects: [leverage-optimization, portfolio-allocation, api-endpoints]

# Tech tracking
tech-stack:
  added: [numpy, scipy (already in stack)]
  patterns: [dirichlet-multinomial-sampling, monte-carlo-simulation, vectorized-operations, confidence-intervals]

key-files:
  created:
    - apps/backend/app/contest/field_sim.py
    - apps/backend/app/contest/contest_sim.py
    - apps/backend/app/contest/metrics.py
  modified:
    - apps/backend/app/contest/__init__.py

key-decisions:
  - "Dirichlet-multinomial sampling for ownership allocation (introduces uncertainty in ownership estimates)"
  - "Oversampling with constraint filtering for salary-cap compliant lineups"
  - "Vectorized NumPy operations for contest simulation (100-1000x speedup vs Python loops)"
  - "Confidence intervals for all metrics (5th/95th percentiles for ROI, standard errors for cash%/win%)"

patterns-established:
  - "Monte Carlo simulation: Run n_scenarios × n_contest_sims for stable tail estimates"
  - "Metrics aggregation: Flatten (n_lineups, n_sims) arrays for portfolio-level statistics"
  - "Pretty-printed reports: Standardized output format for contest results"

# Metrics
duration: ~15 min
completed: 2026-01-28
---

# Phase 4: Plan 4 - Contest Simulation Infrastructure Summary

**Monte Carlo contest simulation with ownership-based field generation using Dirichlet-multinomial sampling and vectorized NumPy operations**

## Performance

- **Duration:** 15 minutes
- **Started:** 2026-01-28T02:48:05Z
- **Completed:** 2026-01-28T03:03:00Z
- **Tasks:** 3
- **Files modified:** 4 (3 created, 1 updated)

## Accomplishments

- **FieldLineupSampler:** Ownership-based field lineup generation with Dirichlet-multinomial sampling and salary cap constraint enforcement
- **ContestSimulator:** Monte Carlo contest simulation engine with vectorized NumPy operations, supporting portfolio simulation across multiple lineups
- **Contest metrics:** ROI, cash%, and win probability calculation with confidence intervals, portfolio aggregation, and pretty-printed reports

## Task Commits

Each task was committed atomically:

1. **Task 1: Create field lineup sampler** - `fcace52` (feat)
   - Implemented Dirichlet-multinomial sampling for ownership allocation
   - Added salary cap constraint enforcement with oversampling
   - Created helper methods for lineup details and salary computation
   - File: apps/backend/app/contest/field_sim.py (~430 lines)

2. **Task 2: Create contest simulator** - `5f808d7` (feat)
   - Implemented Monte Carlo simulation across race scenarios
   - Created ContestResult dataclass for structured output
   - Added portfolio simulation for multiple lineups
   - Integrated payout curve for contest winnings calculation
   - File: apps/backend/app/contest/contest_sim.py (~520 lines)

3. **Task 3: Create contest metrics utilities** - `d21dfb1` (feat)
   - Implemented ROI calculation with confidence intervals
   - Added cash% and win% computation with standard errors
   - Created portfolio-level aggregation and per-lineup metrics
   - Added pretty-printed reports and Sharpe ratio calculation
   - File: apps/backend/app/contest/metrics.py (~450 lines)

4. **Updated module exports** - `fba2250` (docs)

**Plan metadata:** Not applicable (no separate metadata commit)

## Files Created/Modified

- `apps/backend/app/contest/field_sim.py` - FieldLineupSampler class with Dirichlet-multinomial sampling for ownership-based field generation
- `apps/backend/app/contest/contest_sim.py` - ContestSimulator class with Monte Carlo simulation, ContestResult dataclass, portfolio simulation
- `apps/backend/app/contest/metrics.py` - Contest metrics utilities (ROI, cash%, win probability) with confidence intervals and aggregation
- `apps/backend/app/contest/__init__.py` - Updated exports for new classes and functions

## Decisions Made

1. **Dirichlet-multinomial sampling for ownership allocation**
   - Rationale: Introduces uncertainty in ownership estimates, more realistic than standard multinomial
   - Implementation: Gamma-distributed noise added to ownership probabilities before multinomial sampling

2. **Oversampling with constraint filtering**
   - Rationale: More efficient than rejection sampling for salary cap constraint
   - Implementation: Sample 3× target lineups, filter to valid, resample if insufficient

3. **Vectorized NumPy operations**
   - Rationale: 100-1000x speedup vs Python loops for large-scale contest simulation
   - Implementation: Pre-allocate arrays, use np.where() for conditional logic

4. **Confidence intervals for all metrics**
   - Rationale: DFS contest outcomes are highly variable; point estimates insufficient
   - Implementation: 5th/95th percentiles for ROI, standard errors for cash%/win%

## Deviations from Plan

None - plan executed exactly as written. All three tasks completed without deviations or auto-fixes.

## Issues Encountered

None - all implementations worked as expected on first try.

## User Setup Required

None - no external service configuration required. All components use existing dependencies (NumPy, SciPy).

## Next Phase Readiness

**Ready for Phase 4 Plan 05 (Leverage-Aware Optimization):**
- FieldLineupSampler provides ownership-based field simulation
- ContestSimulator enables ROI/cash%/win% evaluation
- Contest metrics support portfolio comparison

**Ready for API integration:**
- All classes have clean interfaces for FastAPI endpoints
- ContestResult dataclass for structured response format

**Considerations:**
- Test setup with limited drivers (12) produces fewer valid lineups - real NASCAR has 40+ drivers
- Contest simulation scales to 10K+ iterations for stable tail estimates (current default 100-1000)
- Ownership estimation (Plan 04-02) will need to integrate with FieldLineupSampler

---
*Phase: 04-field-ownership-contest-sim*
*Plan: 04*
*Completed: 2026-01-28*
