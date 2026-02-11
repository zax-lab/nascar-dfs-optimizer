---
phase: 07-background-jobs-gpu-offload
plan: 02
subsystem: ui
tags: [pyside6, gpu-offload, job-management, http-client, qt-dialogs]

requires:
  - phase: 07-01
    provides: JobManager with thread pool, SQLite persistence, JobsTab

provides:
  - GPUWorkerClient for HTTP communication with Windows GPU worker
  - GPU offload routing in JobManager with fallback to local CPU
  - GPU configuration section in Settings tab
  - Enhanced JobDetailsDialog with tabs and re-run
  - Job filtering, search, and statistics in JobsTab
  - Export functionality for job results

affects:
  - Phase 8 (optimization enhancements)
  - Phase 9 (race import improvements)

tech-stack:
  added: []
  patterns:
    - HTTP client with urllib (zero external dependencies)
    - Tabbed dialog interface with QTabWidget
    - Job filtering with database queries
    - Signal-based re-run workflow

key-files:
  created:
    - apps/native_mac/gui/dialogs/__init__.py
    - apps/native_mac/gui/dialogs/job_details_dialog.py
  modified:
    - apps/native_mac/jobs/job_manager.py
    - apps/native_mac/gui/views/settings_tab.py
    - apps/native_mac/gui/views/jobs_tab.py
    - apps/native_mac/persistence/database.py
    - apps/native_mac/main.py

key-decisions:
  - "GPU API key stored in session only, NOT in database for security"
  - "HTTP/FastAPI pattern chosen over ZeroMQ for simplicity"
  - "GPU jobs fall back to local CPU automatically on failure"
  - "JobDetailsDialog shows execution mode (GPU/local/fallback)"
  - "Re-run jobs get (re-run) suffix for tracking"

patterns-established:
  - "Job routing: submit_job() checks gpu_offload config and routes appropriately"
  - "Fallback pattern: _execute_job_gpu() catches errors and calls fallback_job_to_local()"
  - "Signal-based dialog: JobDetailsDialog emits rerun_requested signal for loose coupling"
  - "Filter/Search: Database-level filtering with search_jobs() for efficiency"

duration: 35min
completed: 2026-01-30
---

# Phase 7 Plan 2: GPU Offload and Job History Summary

**GPU offload infrastructure with HTTP client, Settings configuration, enhanced job history with filtering/search/re-run, and tabbed job details dialog**

## Performance

- **Duration:** 35 min
- **Started:** 2026-01-30T00:10:00Z
- **Completed:** 2026-01-30T00:45:00Z
- **Tasks:** 3 (Task 1 was completed in previous session)
- **Files modified:** 7

## Accomplishments

- GPUWorkerClient communicates with Windows GPU worker via HTTP using standard library urllib (zero dependencies)
- JobManager routes jobs to GPU when enabled, with automatic fallback to local CPU on connection failure
- Settings tab has full GPU configuration section with connection test and status feedback
- JobDetailsDialog displays full job config and results in a tabbed interface with colored status badges
- Jobs tab enhanced with filtering by status, text search, and statistics display
- Re-run functionality creates new job from historical config with (re-run) suffix
- Export functionality saves job results to JSON file
- Job execution mode (GPU/local/fallback) visible in job details

## Task Commits

Each task was committed atomically:

1. **Task 2: Integrate GPU offload into JobManager and Settings** - `86e30e5` (feat)
2. **Task 3: Enhance Jobs tab with history viewer and re-run** - `9f4af7f` (feat)

**Plan metadata:** `TBD` (docs: complete plan)

## Files Created/Modified

- `apps/native_mac/jobs/job_manager.py` - Added GPU client support, routing, _execute_job_gpu(), fallback
- `apps/native_mac/gui/views/settings_tab.py` - Added GPU Offload section with configuration UI
- `apps/native_mac/main.py` - Initialize GPU client from session settings
- `apps/native_mac/gui/dialogs/__init__.py` - Created dialogs package
- `apps/native_mac/gui/dialogs/job_details_dialog.py` - Tabbed dialog with config/results/error views
- `apps/native_mac/gui/views/jobs_tab.py` - Enhanced with filtering, search, toolbar, export
- `apps/native_mac/persistence/database.py` - Added query methods for job filtering and stats

## Decisions Made

- **GPU API key security:** API key is NOT stored in persistent database, only in session state. This prevents credential leakage if database is compromised.
- **HTTP over ZeroMQ:** Chose HTTP/FastAPI pattern for simplicity and easier debugging. Can upgrade to ZeroMQ later if latency becomes critical.
- **Automatic fallback:** GPU jobs automatically fall back to local CPU if the GPU worker is unavailable or fails. Users don't lose their optimization.
- **Execution mode visibility:** Job details clearly show whether job ran on GPU, local CPU, or was a GPU fallback - important for performance analysis.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required for the Mac app itself.

**Note:** To use GPU offload, user needs to set up the Windows GPU worker separately (not part of this codebase).

## Next Phase Readiness

- GPU offload infrastructure complete and ready for Phase 8 optimization enhancements
- Job history system complete with full query capabilities
- Dialog system established for future detailed views
- Phase 7 (Background Jobs + GPU Offload) is **COMPLETE**

Ready for **Phase 8** or milestone completion.

---
*Phase: 07-background-jobs-gpu-offload*
*Completed: 2026-01-30*
