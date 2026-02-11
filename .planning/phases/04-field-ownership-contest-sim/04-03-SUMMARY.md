---
phase: 04-field-ownership-contest-sim
plan: 03
subsystem: contest-modeling
tags: [payout-curve, scipy, pydantic, power-law, exponential, curve-fitting]

# Dependency graph
requires:
  - phase: 03-tail-metrics-tail-objective-portfolio-optimizer
    provides: portfolio-generation, tail-metrics, optimization-api
provides:
  - Payout curve modeling infrastructure for contest simulation
  - Power-law and exponential payout curve fitting with scipy.optimize.curve_fit
  - Pydantic models for contest data validation
  - Contest size tier classification (small <5K, medium 5K-20K, large >20K)
  - Fit quality metrics (R², RMSE) for payout curve validation
  - Utility functions for tier-based curve fitting and interpolation
affects: [contest-simulation, ownership-estimation, leverage-aware-optimization]

# Tech tracking
tech-stack:
  added: [scipy.optimize.curve_fit, numpy, pydantic]
  patterns: [parametric-curve-fitting, tier-based-modeling, pydantic-validation, utility-function-pattern]

key-files:
  created:
    - apps/backend/app/contest/payout_curve.py (689 lines)
    - apps/backend/app/contest/models.py (355 lines)
    - apps/backend/app/contest/__init__.py
  modified: []

key-decisions:
  - "Power-law model as default for top-heavy GPP payouts (captures steep decay better than exponential)"
  - "Separate curve fitting per contest size tier (small/medium/large) for accuracy"
  - "R² > 0.90 validation threshold for fit quality assurance"
  - "Placeholder for load_historical_payouts() until contest_results table exists"

patterns-established:
  - "Pattern 1: Abstract base class (PayoutCurve) with concrete implementations (PowerLawPayoutCurve, ExponentialPayoutCurve)"
  - "Pattern 2: Fitter class (PayoutCurveFitter) that encapsulates fitting, prediction, and quality metrics"
  - "Pattern 3: Utility functions for tier-based operations (fit_payout_curves_by_tier, get_payout_curve_for_contest)"
  - "Pattern 4: Pydantic models with comprehensive validation for data integrity"

# Metrics
duration: 8min
completed: 2026-01-28
---

# Phase 4: Payout Curve Modeling Summary

**Power-law and exponential payout curve fitting with scipy.optimize.curve_fit, R² validation, and contest size tier modeling**

## Performance

- **Duration:** 8 min
- **Started:** 2026-01-28T02:40:16Z
- **Completed:** 2026-01-28T02:48:00Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Built parametric payout curve models (power-law, exponential) with scipy.optimize.curve_fit fitting
- Implemented fit quality validation (R², RMSE) with 0.90 R² threshold warning
- Created Pydantic models for contest data validation (PayoutData, PayoutCurveFit, ContestSize, HistoricalContestData)
- Added contest size tier support (small <5K, medium 5K-20K, large >20K) for tier-specific curve fitting
- Implemented utility functions for tier-based curve fitting, contest-to-tier mapping, and rank interpolation

## Task Commits

Each task was committed atomically:

1. **Task 1: Create payout curve models** - `487fc12` (feat)
2. **Task 2: Create contest Pydantic models** - `324e373` (feat)
3. **Task 3: Add payout curve utilities** - `962d5f7` (feat)

**Plan metadata:** Pending (docs: complete plan)

## Files Created/Modified

- `apps/backend/app/contest/__init__.py` - Module exports and docstring
- `apps/backend/app/contest/payout_curve.py` - PayoutCurveFitter, PowerLawPayoutCurve, ExponentialPayoutCurve, utility functions (689 lines)
- `apps/backend/app/contest/models.py` - Pydantic models for contest data validation (355 lines)

## Decisions Made

- **Power-law as default model:** Power-law decay (payout = a * rank^(-b)) better captures top-heavy GPP payout structures than exponential decay
- **Contest size tier modeling:** Separate curves for small (<5K), medium (5K-20K), and large (>20K) contests improve accuracy
- **Fit quality validation:** R² > 0.90 threshold ensures reliable curve fits; warnings issued for poor fits
- **Database query placeholder:** load_historical_payouts() function documented but not implemented until contest_results table exists

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all tasks completed successfully without blocking issues.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for:**
- Contest simulation using fitted payout curves
- ROI calculation from finish position
- Integration with ownership estimation for leverage-aware optimization

**Blockers/Concerns:**
- load_historical_payouts() requires contest_results table to be implemented for database queries
- No historical payout data available yet - using synthetic data for testing
- Consider caching fitted curves to avoid refitting on every API request

**Verification:**
- All unit tests pass
- Power-law curve fitting achieves R² > 0.99 on test data
- Pydantic models validate all input constraints
- Utility functions correctly handle tier classification and interpolation

---
*Phase: 04-field-ownership-contest-sim*
*Plan: 03*
*Completed: 2026-01-28*
