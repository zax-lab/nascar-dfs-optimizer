---
phase: 01-feasible-by-design-nascar-simulation-core
plan: 01
subsystem: simulation-core
tags: [state-space, nascar, type-safety, property-based-testing, hypothesis, dataclasses, immutability]

# Dependency graph
requires:
  - phase: None
    provides: This is the foundation phase - no dependencies
provides:
  - Type-safe state space model with RaceState and DriverState dataclasses
  - Four transition operators: green_flag, caution, pit_cycle, fuel_window
  - Property-based test suite validating state invariants
  - Immutable state update patterns using dataclasses.replace
affects: [01-02-cbn, 01-03-scenario-generation, 01-04-conservation-validation]

# Tech tracking
tech-stack:
  added: [hypothesis>=6.100.0, pytest>=7.3.0]
  patterns:
    - Frozen dataclasses for immutable state
    - Protocol-based transition operators for composability
    - Property-based testing with Hypothesis for invariant validation
    - Structured logging for transition observability

key-files:
  created:
    - packages/axiomatic-sim/src/axiomatic_sim/state_space.py
    - packages/axiomatic-sim/src/axiomatic_sim/transitions.py
    - packages/axiomatic-sim/tests/test_state_space.py
    - packages/axiomatic-sim/pyproject.toml
    - packages/axiomatic-sim/src/axiomatic_sim/__init__.py
    - packages/axiomatic-sim/tests/__init__.py
  modified: []

key-decisions:
  - "Used frozen dataclasses for immutability - prevents accidental mutations, enables pure functional transitions"
  - "Protocol-based StateTransition interface - enables transition composition via operator overloading (|)"
  - "Property-based tests over unit tests - Hypothesis generates diverse inputs, finds edge cases humans miss"
  - "State validation in __post_init__ - catches invalid states at construction time, not later"
  - "Structured logging in transitions - enables debugging and observability for Skeleton Narrative construction"

patterns-established:
  - "Pattern: Immutable state updates - all transitions create new RaceState via dataclasses.replace"
  - "Pattern: Type-safe transitions - Protocol interface ensures all transitions have same signature"
  - "Pattern: Composable operators - TransitionOperator class enables chaining with | operator"
  - "Pattern: Invariant testing - Hypothesis properties validate state constraints across random inputs"

# Metrics
duration: 8min
completed: 2026-01-27
---

# Phase 1, Plan 1: State Space Model Summary

**Type-safe state space with immutable frozen dataclasses, four transition operators (green flag, caution, pit cycle, fuel window), and property-based tests validating invariants across 100+ Hypothesis-generated examples**

## Performance

- **Duration:** 8 min (496 seconds)
- **Started:** 2026-01-27T13:36:27Z
- **Completed:** 2026-01-27T13:44:23Z
- **Tasks:** 3
- **Files created:** 6

## Accomplishments

- **Core state types defined:** RaceState (lap, segment, drivers) and DriverState (position, fuel, tires) with comprehensive validation
- **Four transition operators implemented:** Green flag racing, caution periods, pit cycles, and fuel window detection
- **Property-based test suite:** 8 Hypothesis tests validate lap bounds, fuel/tire wear, position conservation, freezing, and pit resets
- **Type safety enforced:** Frozen dataclasses prevent mutations, Protocol interface ensures transition composability

## Task Commits

Each task was committed atomically:

1. **Task 1: Create state space core types and RaceState dataclass** - `63b16ea` (feat)
2. **Task 2: Implement transition operators for green flag, caution, pit cycle, and fuel window** - `c55eec3` (feat)
3. **Task 3: Create property-based tests for state space invariants using Hypothesis** - `8dfcec9` (test)

**Plan metadata:** (not yet committed - will be in final metadata commit)

## Files Created/Modified

- `packages/axiomatic-sim/src/axiomatic_sim/state_space.py` - RaceState, DriverState, RaceSegment, StateTransition protocol, TransitionOperator base class
- `packages/axiomatic-sim/src/axiomatic_sim/transitions.py` - green_flag_transition, caution_transition, pit_cycle_transition, fuel_window_transition
- `packages/axiomatic-sim/tests/test_state_space.py` - 8 property-based tests using Hypothesis
- `packages/axiomatic-sim/pyproject.toml` - Package configuration with dependencies and pytest settings
- `packages/axiomatic-sim/src/axiomatic_sim/__init__.py` - Package initialization
- `packages/axiomatic-sim/tests/__init__.py` - Test package initialization

## Decisions Made

- **Forward reference fix:** Moved TransitionCallable type alias after RaceState definition to avoid NameError - required for proper Python type checking
- **Hypothesis for testing:** Chose property-based testing over unit tests - generates random inputs, finds edge cases, validates invariants across 100+ examples per test
- **Package structure:** Used `src/axiomatic_sim/` layout instead of flat `src/` - aligns with pyproject.toml setuptools configuration
- **Structured logging:** Added logging to all transitions - enables debugging and observability for Skeleton Narrative construction
- **Constants in transitions:** Defined FUEL_BURN_PER_LAP, TIRE_WEAR_PER_LAP, etc. at module level - makes physics parameters explicit and tunable

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed Hypothesis dependency**
- **Found during:** Task 3 (Property-based test creation)
- **Issue:** Hypothesis not installed, required for property-based testing
- **Fix:** Ran `pip3 install hypothesis` to install hypothesis-6.141.1
- **Files modified:** None (package installation only)
- **Verification:** Import succeeds, tests run with Hypothesis strategies
- **Committed in:** N/A (dependency installation, not committed)

**2. [Rule 1 - Bug] Fixed forward reference in TransitionCallable type alias**
- **Found during:** Task 1 (State space creation)
- **Issue:** TransitionCallable = Callable[[RaceState], RaceState] referenced RaceState before it was defined, causing NameError
- **Fix:** Moved type alias definition after RaceState class definition, removed from top of file
- **Files modified:** packages/axiomatic-sim/src/axiomatic_sim/state_space.py
- **Verification:** Import succeeds, no NameError
- **Committed in:** 63b16ea (Task 1 commit)

**3. [Rule 1 - Bug] Fixed Unicode category in Hypothesis strategy**
- **Found during:** Task 3 (Test execution)
- **Issue:** Used invalid Unicode category "LND" in st.characters() for driver ID generation
- **Fix:** Changed to whitelist_categories=('L', 'N') (letters and numbers separately)
- **Files modified:** packages/axiomatic-sim/tests/test_state_space.py
- **Verification:** Tests generate valid driver IDs, all tests pass
- **Committed in:** 8dfcec9 (Task 3 commit)

**4. [Rule 1 - Bug] Fixed pit_cycle_transition to reset active_caution_laps**
- **Found during:** Task 3 (Test execution - test_pit_cycle_resets_fuel_and_tires)
- **Issue:** When transitioning from CAUTION to PIT_CYCLE, active_caution_laps was not reset to 0, violating state invariant
- **Fix:** Added active_caution_laps=0 to replace() call in pit_cycle_transition
- **Files modified:** packages/axiomatic-sim/src/axiomatic_sim/transitions.py
- **Verification:** test_pit_cycle_resets_fuel_and_tires passes, state validation succeeds
- **Committed in:** 8dfcec9 (Task 3 commit)

**5. [Rule 1 - Bug] Fixed error message assertion in test_lap_never_exceeds_race_length**
- **Found during:** Task 3 (Test execution)
- **Issue:** Test asserted "exceed race length" in error message but actual message was "Cannot advance to lap X, race length is Y"
- **Fix:** Changed assertion to check for both "advance" and "exceed" in error message
- **Files modified:** packages/axiomatic-sim/tests/test_state_space.py
- **Verification:** Test passes with Hypothesis-generated edge cases
- **Committed in:** 8dfcec9 (Task 3 commit)

**6. [Rule 1 - Bug] Fixed pytest configuration for package imports**
- **Found during:** Task 3 (Test execution)
- **Issue:** pytest couldn't find axiomatic_sim module - tests failed with ModuleNotFoundError
- **Fix:** Added pythonpath = ["src"] to [tool.pytest.ini_options] in pyproject.toml
- **Files modified:** packages/axiomatic-sim/pyproject.toml
- **Verification:** pytest discovers and runs all tests successfully
- **Committed in:** 8dfcec9 (Task 3 commit)

---

**Total deviations:** 6 auto-fixed (1 blocking, 5 bugs)
**Impact on plan:** All auto-fixes necessary for correctness and functionality. Hypothesis installation was required dependency. Bug fixes addressed forward references, validation logic, and test configuration. No scope creep.

## Issues Encountered

- **Package structure confusion:** Initially placed state_space.py in wrong directory (src/ instead of src/axiomatic_sim/) - resolved by checking pyproject.toml setuptools configuration
- **Python path issues:** pytest couldn't find axiomatic_sim module - resolved by updating pyproject.toml with pythonpath setting
- **Hypothesis strategy complexity:** Generating valid RaceState with unique positions required custom strategy logic - resolved using composite pattern with explicit position assignment

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for next phase:**
- State space model is complete and validated
- All transitions are composable and type-safe
- Property-based tests provide confidence in invariant enforcement
- Foundation is solid for building Causal Bayesian Networks (Plan 02)

**No blockers or concerns.**

The state space model provides the foundation for:
- **Plan 02 (CBN):** State transitions will be encoded in Causal Bayesian Network structure
- **Plan 03 (Scenario Generation):** Transitions can be chained to build Skeleton Narratives
- **Plan 04 (Conservation Validation):** State invariants enable detection of impossible scenarios

---
*Phase: 01-feasible-by-design-nascar-simulation-core*
*Plan: 01*
*Completed: 2026-01-27*
