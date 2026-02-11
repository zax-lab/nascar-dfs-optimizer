---
phase: 02-ontology-compiled-constraints-calibration-harness
plan: 03
subsystem: calibration
tags: [numpyro, arviz, mcmc, bayesian-inference, probabilistic-prediction]

# Dependency graph
requires:
  - phase: 02-01
    provides: Compiled constraint specifications from Neo4j (ConstraintSpec, DriverConstraints, TrackConstraints)
  - phase: 02-02
    provides: Telemetry ETL pipeline with rolling window features (compute_aggregate_features)
provides:
  - Probabilistic calibration metrics (CRPS, log score, coverage) for assessing prediction uncertainty
  - NumPyro MCMC calibration models with NUTS sampling for track-archetype-specific parameter inference
  - ArviZ diagnostics suite for posterior predictive checks and convergence assessment
  - Joint-event validation for co-hit frequency calibration by track type
affects: [02-04, 02-05, 03-optimization-engine]

# Tech tracking
tech-stack:
  added: [jax==0.4.30, jaxlib==0.4.30, numpyro==0.19.0, arviz==0.17.1, matplotlib==3.9.4]
  patterns:
    - JAX/NumPyro for GPU-accelerated Bayesian inference
    - ArviZ for MCMC diagnostics and visualization
    - Hierarchical Bayesian models for track-archetype-specific calibration
    - Property-based testing with Hypothesis for calibration metrics

key-files:
  created:
    - apps/backend/app/calibration/metrics.py
    - apps/backend/app/calibration/models.py
    - apps/backend/app/calibration/diagnostics.py
    - apps/backend/app/tests/test_calibration.py
  modified:
    - apps/backend/app/calibration/__init__.py
    - apps/backend/pyproject.toml

key-decisions:
  - "NumPyro over PyMC for JAX acceleration and GPU compatibility"
  - "Hierarchical calibration with track-archetype-specific slope/intercept parameters"
  - "CRPS, log score, and coverage as standard calibration metrics"
  - "Property-based tests with Hypothesis for validating metric invariants"

patterns-established:
  - "MCMC calibration pattern: NUTS sampler with 500 warmup + 1000 samples"
  - "Calibration assessment: Posterior predictive checks + joint-event validation"
  - "JAX array usage throughout for GPU acceleration when available"

# Metrics
duration: 45min
completed: 2026-01-27
---

# Phase 2 Plan 3: Probabilistic Calibration Harness Summary

**JAX-accelerated Bayesian calibration with NumPyro MCMC for track-archetype-specific uncertainty quantification, CRPS/log score/coverage metrics, and ArviZ posterior predictive diagnostics**

## Performance

- **Duration:** 45 minutes (0h 45m)
- **Started:** 2026-01-27T16:09:58Z
- **Completed:** 2026-01-27T16:54:58Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- **Calibration metrics module** with CRPS (Continuous Ranked Probability Score), log score, and coverage for probabilistic prediction assessment
- **NumPyro MCMC calibration models** using NUTS sampler with hierarchical priors for track-archetype-specific slope/intercept parameters
- **ArviZ diagnostics suite** with posterior predictive checks, calibration curve visualization, and joint-event validation
- **Property-based test suite** using Hypothesis to validate metric invariants across random inputs
- **Sample calibration report** generation with base64-embedded plots and convergence diagnostics

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement calibration metrics (CRPS, log score, coverage)** - `0af620b` (feat)
2. **Task 2: Implement NumPyro MCMC calibration models** - `34499ce` (feat)
3. **Task 3: Implement ArviZ diagnostics and joint-event validation** - `8b55524` (feat)

**Plan metadata:** `9eab095` (test: add property-based tests for calibration)

## Files Created/Modified

### Created

- `apps/backend/app/calibration/metrics.py` (335 lines)
  - `compute_crps()`: Continuous Ranked Probability Score for ensemble predictions
  - `compute_log_score()`: Predictive log-likelihood using Gaussian KDE
  - `compute_coverage()`: Empirical coverage for prediction intervals at multiple levels
  - `compute_all_metrics()`: Convenience function computing all metrics
  - Input validation and error handling for NaN/Inf values

- `apps/backend/app/calibration/models.py` (375 lines)
  - `track_archetype_calibration_model()`: NumPyro model with hierarchical calibration priors
  - `run_mcmc_calibration()`: NUTS sampler with configurable warmup (500) and samples (1000)
  - `predict_with_calibrated_model()`: Posterior predictive sampling
  - `compute_calibration_summary()`: Posterior means, std, HDI intervals
  - Validated track archetypes: superspeedway, intermediate, short_track, road_course

- `apps/backend/app/calibration/diagnostics.py` (471 lines)
  - `posterior_predictive_check()`: Convert NumPyro samples to ArviZ InferenceData
  - `plot_calibration_curve()`: 45-degree line plots for visual calibration assessment
  - `compute_joint_event_validation()`: Co-hit frequency validation by track type
  - `assess_mcmc_convergence()`: R-hat and ESS diagnostics
  - `generate_calibration_report()`: Automated markdown report with base64-embedded plots

- `apps/backend/app/tests/test_calibration.py` (268 lines)
  - Property-based tests for CRPS, log score, coverage using Hypothesis
  - MCMC convergence tests with synthetic data
  - Integration tests for end-to-end calibration workflow
  - Joint-event validation tests

### Modified

- `apps/backend/app/calibration/__init__.py`: Package initialization with all exports
- `apps/backend/pyproject.toml`: Added JAX, NumPyro, ArviZ, Matplotlib dependencies

## Sample Calibration Results

### Metrics (synthetic test data)
- **CRPS**: 0.488 (lower is better, 0 is perfect)
- **Log score**: -1.261 (higher is better)
- **Coverage**: 50% → 0.500, 80% → 0.900, 95% → 1.000

### MCMC Calibration (intermediate track archetype)
- **Samples collected**: 200 (100 warmup + 200 post-warmup for testing)
- **Slope mean**: -0.223 ± 1.260 (calibration transformation steepness)
- **Intercept mean**: -0.187 ± 1.042 (calibration bias)

### Joint-Event Validation
- **Events validated**: 6 (top_5, top_10, top_15 for superspeedway and intermediate)
- **Calibration errors**: 0.725 - 0.950 (expected high for uniform random predictions)
- **Warnings logged**: For calibration error > 0.1 (miscalibration detected)

## Decisions Made

1. **NumPyro over PyMC for JAX acceleration**
   - Rationale: JAX provides GPU acceleration and JIT compilation for 10-100x speedup
   - Benefit: Efficient MCMC for large-scale calibration with 40+ drivers

2. **Hierarchical calibration with track-archetype parameters**
   - Rationale: Different track types (superspeedway, intermediate, short track) have different prediction biases
   - Benefit: Share information across archetypes while allowing track-specific deviations

3. **CRPS, log score, and coverage as standard metrics**
   - Rationale: These are well-established probabilistic prediction metrics in forecasting literature
   - Benefit: Interpretable diagnostics for model calibration quality

4. **Property-based testing with Hypothesis**
   - Rationale: Calibration functions must handle edge cases (NaN, Inf, shape mismatches)
   - Benefit: Validates invariants across 100+ random examples, finds edge cases

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed scipy compatibility with ArviZ**
- **Found during:** Task 3 (ArviZ diagnostics import)
- **Issue:** scipy 1.13.1 removed `gaussian` function, causing `ImportError: cannot import name 'gaussian' from 'scipy.signal'`
- **Fix:** Downgraded scipy to <1.13 (installed 1.12.0) for ArviZ compatibility
- **Files modified:** Environment (pip downgrade)
- **Verification:** ArviZ imports successfully, diagnostics module functional
- **Committed in:** N/A (environment fix, not committed)

**2. [Rule 1 - Bug] Fixed JAX sigmoid function name**
- **Found during:** Task 2 (NumPyro model execution)
- **Issue:** `jax.scipy.special.sigmoid` doesn't exist (should be `expit`)
- **Fix:** Changed `jax.scipy.special.sigmoid` to `jax.scipy.special.expit` in calibration transformation
- **Files modified:** apps/backend/app/calibration/models.py
- **Verification:** MCMC calibration runs successfully, 200 samples collected
- **Committed in:** 34499ce (Task 2 commit)

**3. [Rule 1 - Bug] Fixed joint-event validation array handling**
- **Found during:** Task 3 (joint-event validation testing)
- **Issue:** Calibration error returned as array instead of scalar, causing `TypeError: only length-1 arrays can be converted to Python scalars`
- **Fix:** Added `np.mean()` for array errors and proper float conversion in logging
- **Files modified:** apps/backend/app/calibration/diagnostics.py
- **Verification:** Joint-event validation computes 6 events successfully
- **Committed in:** 8b55524 (Task 3 commit)

---

**Total deviations:** 3 auto-fixed (3 bugs)
**Impact on plan:** All auto-fixes were necessary for correct operation. No scope creep.

## Issues Encountered

1. **scipy 1.13.1 incompatibility with ArviZ**
   - Problem: scipy 1.13.1 removed the `gaussian` function that ArviZ depends on
   - Resolution: Downgraded scipy to 1.12.0 for compatibility
   - Impact: Minor, uses older scipy version

2. **JAX API differences from NumPy**
   - Problem: `jax.scipy.special.sigmoid` doesn't exist (should use `expit`)
   - Resolution: Fixed function name in calibration model
   - Impact: Minor, one-line fix

3. **Array-to-scalar conversion in validation**
   - Problem: NumPy array operations sometimes return arrays instead of scalars
   - Resolution: Added explicit `float()` conversion and `np.mean()` for aggregation
   - Impact: Minor, robust error handling

## User Setup Required

None - no external service configuration required. All calibration uses local NumPyro MCMC and ArviZ diagnostics.

## Next Phase Readiness

**Ready for integration:**
- Calibration harness complete with metrics, models, and diagnostics
- Can assess CBN-sampled scenario quality by track archetype
- Joint-event validation ready for co-hit frequency assessment

**Next steps (Plan 02-04):**
- Integrate calibration with headless `/optimize` API
- Add calibration endpoints for on-demand assessment
- Persist calibration results as NetCDF files for reproducibility

**Blockers:**
- None identified

**Concerns:**
- MCMC sampling can be slow for large datasets (500 warmup + 1000 samples = ~30-60 seconds)
- Consider caching calibration results or using variational inference for faster approximation

---
*Phase: 02-ontology-compiled-constraints-calibration-harness*
*Completed: 2026-01-27*
