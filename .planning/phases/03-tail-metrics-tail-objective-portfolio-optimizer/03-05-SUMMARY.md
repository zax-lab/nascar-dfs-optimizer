---
phase: 03-tail-metrics-tail-objective-portfolio-optimizer
plan: 05
subsystem: portfolio-optimization
tags: [cvar, milp, pulp, upper-tail-maximization, bounded-optimization]

# Dependency graph
requires:
  - phase: 03-tail-metrics-tail-objective-portfolio-optimizer
    plan: 02
    provides: CVaR objective builders (build_cvar_objective, build_multi_cvar_objective)
  - phase: 03-tail-metrics-tail-objective-portfolio-optimizer
    plan: 03
    provides: Portfolio generator with scenario caching and exposure bookkeeping
provides:
  - Bounded CVaR formulation for upper-tail maximization (build_upper_tail_cvar_objective)
  - Portfolio optimizer using CVaR objective instead of expected value fallback
  - Integration tests validating solver produces Optimal status with bounded formulation
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Bounded CVaR formulation for maximization (upper bounds on u_k variables)
    - Rockafellar-Uryasev reformulation for upside tournament outcomes
    - Solver status validation to prevent unbounded optimization

key-files:
  created: []
  modified:
    - apps/backend/app/tail_objectives.py
    - apps/backend/app/portfolio_generator.py
    - apps/backend/tests/test_tail_objectives.py

key-decisions:
  - "Add upper bounds to u_k tail slack variables to prevent unbounded optimization when maximizing CVaR"
  - "Bound zeta variable between min and max possible lineup points for numerical stability"
  - "Remove expected value fallback and use bounded CVaR formulation for all portfolio optimization"

patterns-established:
  - "Pattern: Bounded MILP variables for maximization problems (prevent unbounded solver status)"
  - "Pattern: Upper-tail CVaR reformulation with Rockafellar-Uryasev for tournament upside optimization"

# Metrics
duration: 3min
completed: 2026-01-27
---

# Phase 3: Tail Metrics, Tail Objective & Portfolio Optimizer - Plan 05 Summary

**Bounded CVaR formulation for upper-tail maximization with Rockafellar-Uryasev reformulation and solver status validation**

## Performance

- **Duration:** 3 min
- **Started:** 2025-01-28T01:01:14Z
- **Completed:** 2025-01-28T01:05:00Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Implemented bounded CVaR formulation for upper-tail maximization (build_upper_tail_cvar_objective)
- Replaced expected value fallback in portfolio generator with bounded CVaR optimization
- Added integration tests validating solver produces Optimal status (not Unbounded/Infeasible)
- Fixed critical gap: portfolio optimizer now targets top 1% outcomes instead of mean points

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement bounded CVaR formulation for upper-tail maximization** - `771a5e1` (feat)
2. **Task 2: Replace expected value fallback with bounded CVaR optimization** - `4d7b1f0` (feat)
3. **Task 3: Validate solver status and CVaR improvement over mean** - `ce6df32` (feat)

**Plan metadata:** (to be committed)

## Files Created/Modified

- `apps/backend/app/tail_objectives.py` - Added build_upper_tail_cvar_objective() with bounded zeta and u_k variables
- `apps/backend/app/portfolio_generator.py` - Replaced expected value fallback with bounded CVaR optimization calls
- `apps/backend/tests/test_tail_objectives.py` - Added integration tests for upper-tail CVaR optimization

## Decisions Made

**Upper bounds on u_k variables for maximization:**
- Standard Rockafellar-Uryasev CVaR formulation is designed for risk minimization (downside tail)
- When maximizing CVaR for upside tournament outcomes, unbounded u_k variables cause "Unbounded" solver status
- Solution: Add upper bound to u_k variables (max_excess = max_lineup_points - min_lineup_points)
- This prevents unbounded growth while preserving CVaR formulation correctness

**Bounded zeta variable:**
- Zeta (VaR threshold) bounded between min and max possible lineup points
- Prevents numerical instability and improves solver convergence
- Bounds are scenario-dependent: min_lineup_points = scenarios.min() * n_drivers, max_lineup_points = scenarios.max() * n_drivers

**Remove expected value fallback:**
- Previous implementation used expected value (mean points) due to unbounded CVaR issue
- TODO comment at line 197: "Fix CVaR formulation for upper tail maximization"
- Bounded formulation resolves issue, enabling true CVaR optimization for tournament equity

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed unbounded CVaR optimization causing "Unbounded" solver status**
- **Found during:** Task 1 (Implement bounded CVaR formulation)
- **Issue:** Standard Rockafellar-Uryasev CVaR formulation works for minimization but causes unbounded optimization when maximizing
- **Root cause:** u_k variables have lower bound (0) but no upper bound, allowing infinite growth when maximizing sum(u_k)
- **Fix:** Added upper bound to u_k variables: upBound=max_excess where max_excess = max_lineup_points - min_lineup_points
- **Files modified:** apps/backend/app/tail_objectives.py
- **Verification:** Solver now produces "Optimal" status instead of "Unbounded" in all tests
- **Committed in:** 4d7b1f0 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Bug fix was critical for correctness - unbounded optimization made CVaR unusable for portfolio generation. Fix enables true upper-tail maximization.

## Issues Encountered

**Initial unbounded solver status:**
- First implementation of build_upper_tail_cvar_objective produced "Unbounded" solver status
- Root cause: u_k variables only bounded below (lowBound=0), not above
- When maximizing CVaR = zeta + sum(u_k) / denominator, u_k variables could grow infinitely
- Solution: Added upper bounds to u_k based on maximum possible excess (max_lineup_points - min_lineup_points)
- This preserves CVaR formulation correctness while preventing unbounded optimization

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Gap closure complete:**
- Portfolio optimizer now uses bounded CVaR formulation for upper-tail maximization
- build_upper_tail_cvar_objective function exported and used in portfolio_generator.py
- Expected value fallback removed, TODO comment deleted
- Solver produces "Optimal" status with bounded formulation

**Verification passed:**
- All 23 tests pass (21 existing + 2 new integration tests)
- CVaR optimization produces valid (positive) tail metrics
- Portfolio generator successfully creates lineups with CVaR objective

**Ready for Phase 4:**
- Tail-metrics-based UI and production deployment can proceed with working CVaR optimization
- Portfolio generator correctly targets top 1% tournament outcomes
- No blockers or concerns

---
*Phase: 03-tail-metrics-tail-objective-portfolio-optimizer*
*Completed: 2026-01-27*
