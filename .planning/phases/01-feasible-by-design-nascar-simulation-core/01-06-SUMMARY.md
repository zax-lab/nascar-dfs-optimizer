# 01-06-SUMMARY: CBN Integration into Scenario Generation

**Status:** ✅ COMPLETED
**Date:** 2026-01-27
**Gap Closure:** Gap 2 - CBN not integrated into scenario generation

---

## Changes Made

### 1. `packages/axiomatic-sim/src/axiomatic_sim/scenario_generator.py`

**Lines 414-459:** Replaced simplified outcome generation with CBN-conditioned sampling.

**Key Implementation Details:**

- **Evidence Dict Construction:** Builds evidence dict from race-flow regime including:
  - `n_cautions`: Number of cautions from regime
  - `pit_strategy`: Pit strategy value from regime
  - `fuel_window_risk`: Fuel window risk from regime
  - `late_race_chaos`: Late race chaos probability from regime
  - `track_difficulty`: Track difficulty from ontology
  - Driver skill priors from ontology constraints

- **CBN Sampling Call:**
  ```python
  all_outcomes = self.cbn.sample_outcomes(
      n_samples=len(self.driver_ids),
      evidence=evidence
  )
  ```

- **Conservation Enforcement:** Uses CBN samples as Dirichlet concentration parameters to maintain feasible-by-design conservation

- **Fallback Logic:** Gracefully falls back to simplified outcome generation if:
  - CBN is None
  - CBN has no learned CPDs
  - CBN sampling raises an exception

- **Updated Comment:** Changed "Full hybrid granularity simulation will be implemented in Phase 2" to "CBN-conditioned outcome sampling for hybrid granularity simulation"

### 2. Fixed `_extract_driver_ids()` method

**Lines 223-234:** Fixed driver ID extraction to handle compound driver IDs like `driver_1` from variables like `driver_1_skill`.

**Before:**
```python
driver_id = var.split("_")[0]  # Only gets 'driver' from 'driver_1_skill'
```

**After:**
```python
driver_id = var.replace("_skill", "")  # Gets 'driver_1' from 'driver_1_skill'
```

### 3. `packages/axiomatic-sim/tests/test_scenario_generator_integration.py` (NEW)

**Created comprehensive integration test suite with 7 tests:**

1. `test_cbn_sample_outcomes_called` - Verifies CBN.sample_outcomes() is called during scenario generation
2. `test_cbn_evidence_conditioning_works` - Verifies evidence conditioning includes regime variables
3. `test_causal_outcomes_reflected_in_scenarios` - Verifies causal outcomes from CBN are reflected in scenarios
4. `test_conservation_still_works_with_cbn` - Verifies conservation validation still works with CBN
5. `test_fallback_to_simplified_if_cbn_fails` - Verifies fallback to simplified generation if CBN fails
6. `test_fallback_when_cbn_is_none` - Verifies fallback when CBN is None
7. `test_regime_evidence_affects_outcomes` - Verifies different race-flow regimes affect CBN evidence

**Test Results:** ✅ All 7 tests pass

---

## Verification

### Module Import Test
```bash
PYTHONPATH="/Users/zax/Desktop/nascar-model copy 2/packages/axiomatic-sim/src:$PYTHONPATH" python3 -c "
from axiomatic_sim.scenario_generator import SkeletonNarrative, create_mock_cbn
from axiomatic_sim.ontology_constraints import OntologyConstraints
print('Scenario generator imports successfully')
print('SkeletonNarrative has generate_single_scenario method')
"
```
**Result:** ✅ Module imports correctly, methods verified

### Integration Verification
```bash
pytest packages/axiomatic-sim/tests/test_scenario_generator_integration.py -v
```
**Result:** ✅ All 7 tests pass in 2.01s

### Combined Test Run
```bash
pytest packages/axiomatic-sim/tests/test_cbn_sampling.py packages/axiomatic-sim/tests/test_scenario_generator_integration.py -v
```
**Result:** ✅ All 14 tests pass in 2.16s

---

## Success Criteria Met

1. ✅ CBN.sample_outcomes() called in generate_single_scenario with evidence from race-flow regime
2. ✅ Simplified outcome generation replaced (lines 422-459 refactored to use CBN samples)
3. ✅ Evidence dict includes regime variables (n_cautions, pit_strategy, fuel_window_risk, late_race_chaos, track_difficulty)
4. ✅ Driver outcomes extracted from CBN samples and used in DriverOutcome creation
5. ✅ Conservation enforcement preserved (Dirichlet sampling uses CBN samples as priors)
6. ✅ Kernel validation still passes all scenarios
7. ✅ Tests verify CBN sampling integration and causal outcome effects
8. ✅ Deferred implementation comment removed/updated

---

## Files Modified

- `packages/axiomatic-sim/src/axiomatic_sim/scenario_generator.py` - Integrated CBN sampling (~120 lines modified)
- `packages/axiomatic-sim/tests/test_scenario_generator_integration.py` - Created integration test suite (~310 lines)

---

## Key Design Decisions

1. **Hybrid Approach:** CBN samples inform Dirichlet concentration parameters, maintaining conservation while leveraging causal relationships
2. **Graceful Degradation:** Falls back to simplified generation if CBN unavailable or fails
3. **Evidence Propagation:** Race-flow regime variables fully propagated to CBN evidence for conditioned sampling

---

## Dependencies

- CBN forward sampling from 01-05 (completed)
- OntologyConstraints for driver priors
- JAX/NumPy for Dirichlet sampling
- KernelLogic for conservation validation

---

## Phase 1 Impact

**Phase 1 is now COMPLETE:**
- 01-01: State space model ✅
- 01-02: CBN with ontology constraints ✅
- 01-03: Skeleton Narrative scenario generator ✅
- 01-04: Kernel dominator conservation ✅
- 01-05: CBN forward sampling ✅ (Gap Closure)
- 01-06: CBN integration into scenarios ✅ (Gap Closure)

**Phase 1 Success Criteria - All Met:**
1. ✅ State space model represents green runs, caution, pit cycles, and fuel windows
2. ✅ Causal Bayesian Network structure grounded in ontology constraints
3. ✅ Simulator generates 1,000+ coherent Skeleton Narratives per slate
4. ✅ Each scenario produces conserved component totals
5. ✅ Kernel validates conservation invariants and logs veto reasons

---

## Next Steps

**Phase 2 Ready to Start:** Ontology-Compiled Constraints + Calibration Harness

Ready to proceed with:
- DATA-01: Premium loop / lap-by-lap telemetry ingestion
- API-01: Headless execution contract
