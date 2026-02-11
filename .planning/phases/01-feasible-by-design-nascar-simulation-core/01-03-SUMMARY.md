---
phase: 01-feasible-by-design-nascar-simulation-core
plan: 03
subsystem: simulation
tags: [cbn, scenario-generation, conservation, dirichlet-sampling, kernel-validation, jax, parquet]

# Dependency graph
requires:
  - phase: 01-01
    provides: state-space-model, race-state-transitions
  - phase: 01-02
    provides: causal-bayesian-network, ontology-constraints
  - phase: 01-04
    provides: conservation-validation, kernel-logic
provides:
  - Skeleton Narrative scenario generator with CBN-conditioned sampling
  - Race-flow regime modeling (cautions, pit strategy, fuel risk)
  - Feasible-by-design conservation using Dirichlet sampling
  - Kernel post-validation integration for conservation constraints
  - Parquet serialization for scenario storage
affects: [02-telemetry-ingestion, 03-optimization]

# Tech tracking
tech-stack:
  added: [numpy, jax (optional), pyarrow (optional), pandas (optional)]
  patterns: [feasible-by-design-sampling, hybrid-granularity-simulation, kernel-post-validation]

key-files:
  created:
    - packages/axiomatic-sim/src/axiomatic_sim/scenario_generator.py
    - packages/axiomatic-sim/src/axiomatic_sim/narrative.py
    - packages/axiomatic-sim/tests/test_scenario_generator.py
  modified: []

key-decisions:
  - "Feasible-by-design conservation using Dirichlet sampling to ensure scenarios likely valid"
  - "Hybrid enforcement: Dirichlet for generation + kernel post-validation for final verification"
  - "JAX/NumPy fallback pattern for performance without hard dependency"
  - "Parquet serialization for efficient scenario storage (requires pyarrow/pandas)"

patterns-established:
  - "Feasible-by-design pattern: Use mathematical constraints (Dirichlet) during generation to make scenarios likely valid, then post-validate"
  - "Graceful degradation: Optional JAX with NumPy fallback for environments without GPU acceleration"
  - "Kernel as final arbiter: All scenarios validated by kernel regardless of generation method"

# Metrics
duration: 15min
completed: 2026-01-27
---

# Phase 1 Plan 3: Skeleton Narrative Scenario Generation Summary

**Scenario generator producing 1,000+ coherent race outcomes per slate with CBN-conditioned driver outcomes, race-flow regime variation, and kernel-validated conservation constraints**

## Performance

- **Duration:** 15 minutes
- **Started:** 2026-01-27T14:18:03Z
- **Completed:** 2026-01-27T14:33:00Z
- **Tasks:** 4
- **Files modified:** 3

## Accomplishments

- Created SkeletonNarrative scenario generator with CBN-conditioned outcome sampling
- Implemented feasible-by-design conservation using Dirichlet distribution for laps_led and fastest_laps
- Integrated kernel post-validation for conservation constraint verification
- Built race-flow regime modeling with caution count, pit strategy, fuel risk, and late-race chaos
- Created comprehensive integration test suite (13 tests, all passing)

## Task Commits

All tasks completed in single atomic commit (narrative.py already existed from previous execution):

1. **Task 1-4: Scenario generator implementation** - `b99d37f` (feat)

**Plan metadata:** Not yet committed

## Files Created/Modified

- `packages/axiomatic-sim/src/axiomatic_sim/scenario_generator.py` - SkeletonNarrative class, create_mock_cbn, generate_scenarios standalone function
- `packages/axiomatic-sim/src/axiomatic_sim/narrative.py` - RaceFlowRegime, ScenarioComponents, DriverOutcome, ConservationMetadata dataclasses, serialization functions
- `packages/axiomatic-sim/tests/test_scenario_generator.py` - 13 integration tests covering scenario generation, conservation, regime diversity, serialization, kernel validation

## Decisions Made

- **Feasible-by-design conservation**: Use Dirichlet sampling during generation to ensure sum(laps_led) = race_length and sum(fastest_laps) ≤ green_flag_laps, making scenarios likely valid before kernel validation
- **Hybrid enforcement approach**: Combine feasible-by-design generation (mathematical constraints) with kernel post-validation (final verification) for efficiency and correctness
- **JAX/NumPy fallback pattern**: Implement performance optimizations with JAX when available, gracefully fall back to NumPy for environments without GPU acceleration
- **Parquet serialization**: Use PyArrow and pandas for efficient scenario storage, with clear error messages when dependencies not installed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Import path corrections for module structure**
- **Found during:** Task 3 (scenario_generator.py implementation)
- **Issue**: Direct imports like `from packages.axiomatic_sim.src.cbn` failed due to module structure
- **Fix**: Changed to relative imports `from axiomatic_sim.cbn` and added sys.path manipulation in tests
- **Files modified**: scenario_generator.py, test_scenario_generator.py
- **Verification**: All imports resolve correctly, tests pass
- **Committed in**: b99d37f

**2. [Rule 3 - Blocking] Mock kernel validation integration**
- **Found during:** Task 3 (kernel post-validation implementation)
- **Issue**: _scenario_to_dict method needed to convert ScenarioComponents to dict format expected by kernel
- **Fix**: Added conversion method extracting laps_led, fastest_laps, start_positions, finish_positions from driver_outcomes
- **Files modified**: scenario_generator.py
- **Verification**: Kernel validation called for each scenario in tests
- **Committed in**: b99d37f

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan**: Both auto-fixes necessary for correct module imports and kernel integration. No scope creep.

## Issues Encountered

- **narrative.py already existed**: The narrative.py file was already created (likely from previous execution attempt), so Task 1 was already complete. Verified all required exports present and correct.
- **JAX not installed**: As expected, JAX is not installed in the environment. The implementation correctly falls back to NumPy with dummy vmap/jit decorators.
- **PyArrow/pandas not installed**: Parquet serialization requires these optional dependencies. Implementation raises clear ImportError with installation instructions.

## User Setup Required

None - no external service configuration required.

**Optional dependencies** for enhanced functionality:
- JAX: Install with `pip install jax jaxlib` for GPU-accelerated scenario generation
- PyArrow/pandas: Install with `pip install pyarrow pandas` for Parquet serialization

## Next Phase Readiness

**Ready for Phase 2 (Premium Telemetry Ingestion):**
- Scenario generation pipeline complete and tested
- Kernel conservation validation integrated
- Serialization support in place (with optional dependencies)

**Considerations for Phase 2:**
- Real telemetry data will enable CBN parameter learning (currently using fixed CPDs)
- Historical lap data can refine Dirichlet sampling parameters
- Track-specific regime distributions can be learned from data

**Blockers/concerns:**
- None - Phase 1 complete, ready to proceed to Phase 2

---
*Phase: 01-feasible-by-design-nascar-simulation-core*
*Plan: 03*
*Completed: 2026-01-27*
