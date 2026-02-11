---
phase: 02-ontology-compiled-constraints-calibration-harness
plan: 02
subsystem: data-engineering
tags: [polars, parquet, telemetry, data-leakage-prevention, rolling-windows, etl]

# Dependency graph
requires:
  - phase: 01-feasible-by-design-nascar-simulation-core
    provides: CBN scenario generation, kernel validation
provides:
  - Telemetry ETL pipeline with feature availability contracts
  - Polars-based lazy ingestion and rolling window transformations
  - Parquet artifact persistence with Snappy compression
affects:
  - 02-03: Calibration harness integration with telemetry features
  - 02-04: Data-driven constraint calibration

# Tech tracking
tech-stack:
  added: [polars>=0.20.0]
  patterns: [lazy-evaluation, feature-availability-contracts, rolling-window-aggregations, parquet-artifacts]

key-files:
  created: [apps/backend/app/telemetry/__init__.py, apps/backend/app/telemetry/features.py, apps/backend/app/telemetry/ingest.py, apps/backend/app/telemetry/transform.py, apps/backend/app/telemetry/artifacts.py, apps/backend/pyproject.toml]
  modified: []

key-decisions:
  - "Polars lazy evaluation (scan_parquet) for memory-efficient processing of multi-gigabyte files"
  - "Feature availability contracts enforce temporal boundaries to prevent data leakage"
  - "Snappy compression for Parquet artifacts (fast compression/decompression)"
  - "Rolling window aggregations over per-driver groups using .over('driver_id')"
  - "Forward-fill and mean imputation for missing data handling"

patterns-established:
  - "Feature availability validation: Check for forbidden race telemetry features before ingestion"
  - "Lazy evaluation pattern: Use pl.scan_parquet for large files, defer execution until .collect()"
  - "Rolling window pattern: Compute per-driver aggregations with .over() for grouped operations"
  - "Artifact persistence: Save transformed data as Parquet with compression for fast loading"

# Metrics
duration: 7min
completed: 2026-01-27
---

# Phase 2 Plan 2: Telemetry ETL Pipeline Summary

**Polars-based telemetry pipeline with feature availability contracts to prevent data leakage, rolling window aggregations for driver performance metrics, and Parquet artifact persistence with Snappy compression.**

## Performance

- **Duration:** 7 min (461 seconds)
- **Started:** 2026-01-27T15:58:32Z
- **Completed:** 2026-01-27T16:05:33Z
- **Tasks:** 4
- **Files modified:** 5

## Accomplishments
- Built telemetry ETL pipeline preventing data leakage from future race information
- Implemented Polars lazy evaluation for memory-efficient processing of large Parquet files
- Created rolling window aggregations (10l, 20l, 50l) for driver performance metrics
- Established Parquet artifact persistence with Snappy compression for fast I/O

## Task Commits

Each task was committed atomically:

1. **Task 1: Create feature availability contract enforcement** - `0888572` (feat)
2. **Task 2: Implement Polars telemetry ingestion with lazy scan** - `de2c02e` (feat)
3. **Task 3: Implement Polars transformations with rolling windows** - `feb9cda` (feat)
4. **Task 4: Implement Parquet artifact persistence** - `e90a4c8` (feat)
5. **Module exports completion** - `c10041f` (chore)

**Plan metadata:** (to be committed after SUMMARY.md)

## Files Created/Modified

### Created Files

- `apps/backend/app/telemetry/__init__.py` - Module exports for all telemetry components
- `apps/backend/app/telemetry/features.py` - FeatureAvailabilityContract class (95 lines)
  - HISTORICAL_FEATURES: avg_finish_position, avg_laps_led, win_rate, dnf_rate, recent_form
  - PRACTICE_FEATURES: practice_lap_time, practice_speed, practice_laps_complete
  - QUALIFYING_FEATURES: qualifying_position, qualifying_speed, qualifying_gap
  - FORBIDDEN_FEATURES: race_laps_led, race_finish_position, race_incidents, race_dnf_lap
  - validate_features() raises ValueError for forbidden race telemetry
  - get_allowed_features() filters to non-forbidden features
  - validate_dataframe() checks columns for data leakage

- `apps/backend/app/telemetry/ingest.py` - TelemetryIngestor class with lazy Parquet scanning (187 lines)
  - ingest_parquet() uses pl.scan_parquet for lazy evaluation
  - Validates schema columns against feature availability contract
  - Filters to requested drivers with pl.col().is_in()
  - Selects only allowed features (filters forbidden race telemetry)
  - Handles missing data with forward-fill and zero-fill
  - ingest_lap_by_lap_telemetry() standalone convenience function
  - Validates required metadata columns (lap, driver_id, timestamp, track_id)

- `apps/backend/app/telemetry/transform.py` - Polars transformations with rolling windows (259 lines)
  - compute_aggregate_features() for rolling window aggregations over 10l, 20l, 50l windows
  - Computes per-driver rolling features using .over('driver_id')
  - Rolling position features: avg_position_last_N, best_position_last_N
  - Rolling laps led sum: laps_led_last_N
  - rolling_statistics() for mean, std, min, max over windows
  - compute_falloff_metrics() for tire degradation analysis (lap time delta, slow lap detection)
  - handle_missing_data() for data cleaning (forward-fill, mean imputation)

- `apps/backend/app/telemetry/artifacts.py` - Parquet artifact persistence (220 lines)
  - persist_telemetry_artifact() for Parquet storage with compression
  - Validates .parquet file extension
  - Supports compression formats: snappy (default), gzip, brotli, lz4
  - load_telemetry_artifact() for loading Parquet files
  - list_artifacts() for directory scanning with metadata
  - validate_artifact_schema() for schema validation

- `apps/backend/pyproject.toml` - Added polars>=0.20.0 dependency

### Modified Files

None

## Decisions Made

### Tech Stack Decisions

1. **Polars for telemetry processing** - Chosen over pandas for 10-100x performance on large datasets via lazy evaluation and multi-threaded execution

2. **Lazy evaluation (scan_parquet)** - Enables processing multi-gigabyte Parquet files without loading entire file into memory

3. **Feature availability contracts** - Temporal boundary enforcement prevents using future race information (data leakage) in predictions

4. **Snappy compression for Parquet** - Fast compression/decompression balances storage efficiency with I/O performance

5. **Rolling window aggregations** - Per-driver rolling features capture recent performance without leaking future information

### Architectural Decisions

1. **Forbidden features as class-level sets** - HISTORICAL, PRACTICE, QUALIFYING, FORBIDDEN enable compile-time validation

2. **Metadata columns always included** - lap, driver_id, timestamp, track_id preserved even when selecting features

3. **Forward-fill then mean imputation** - Two-stage missing data handling preserves temporal patterns while filling gaps

4. **Per-driver rolling windows** - Using .over('driver_id') ensures each driver's statistics computed independently

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed missing polars dependency**
- **Found during:** Initial verification before Task 1
- **Issue:** polars package not installed, imports failing
- **Fix:** Ran `python3 -m pip install polars`, added polars>=0.20.0 to pyproject.toml
- **Files modified:** apps/backend/pyproject.toml
- **Verification:** Import succeeds, lazy scan works correctly
- **Committed in:** 0888572 (Task 1 commit)

**2. [Rule 1 - Bug] Fixed Polars rolling API usage**
- **Found during:** Task 3 verification
- **Issue:** Used deprecated rolling().mean() API, should use rolling_mean() method
- **Fix:** Changed to rolling_mean(), rolling_sum(), rolling_min(), rolling_max() with window_size parameter
- **Files modified:** apps/backend/app/telemetry/transform.py
- **Verification:** Rolling features computed correctly for 3l window
- **Committed in:** feb9cda (Task 3 commit)

**3. [Rule 1 - Bug] Fixed interpolation strategy for missing data**
- **Found during:** Task 3 verification
- **Issue:** Polars fill_null() doesn't support 'interpolate' strategy
- **Fix:** Changed to forward-fill first, then mean imputation for remaining nulls
- **Files modified:** apps/backend/app/telemetry/transform.py
- **Verification:** Missing values handled correctly, forward-fill propagates last valid observation
- **Committed in:** feb9cda (Task 3 commit)

**4. [Rule 1 - Bug] Fixed compute_aggregate_features logic**
- **Found during:** Task 3 verification
- **Issue:** Complex per-driver loop with concat/join logic failed to merge rolling features
- **Fix:** Simplified to use .over('driver_id') for grouped rolling aggregations
- **Files modified:** apps/backend/app/telemetry/transform.py
- **Verification:** Rolling features (avg_position_last_3l, laps_led_last_3l) computed correctly
- **Committed in:** feb9cda (Task 3 commit)

---

**Total deviations:** 4 auto-fixed (1 blocking, 3 bugs)
**Impact on plan:** All auto-fixes necessary for correct Polars API usage. No scope creep. Plan executed as specified.

## Issues Encountered

**Issue 1: Polars API differences from pandas**
- **Problem:** Polars rolling API uses rolling_mean() not rolling().mean(), and doesn't support 'interpolate' strategy
- **Resolution:** Updated to use correct Polars API methods and forward-fill + mean imputation
- **Impact:** Required learning Polars-specific API, but resulted in more idiomatic code

**Issue 2: data/ directory gitignored**
- **Problem:** Created data/telemetry/.gitkeep but git ignored it
- **Resolution:** Skipped committing .gitkeep file (directory structure created at runtime)
- **Impact:** None - directory structure will be created when needed

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Telemetry pipeline complete and ready for integration:**
- Feature availability contracts enforce no data leakage
- Polars lazy evaluation handles large telemetry files efficiently
- Rolling window features capture driver performance metrics
- Parquet artifacts enable fast loading for calibration

**Ready for:**
- Plan 02-03: Integrate telemetry features with calibration harness
- Plan 02-04: Data-driven constraint calibration using historical telemetry

**No blockers or concerns.**

---
*Phase: 02-ontology-compiled-constraints-calibration-harness*
*Plan: 02*
*Completed: 2026-01-27*
