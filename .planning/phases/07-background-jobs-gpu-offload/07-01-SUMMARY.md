---
phase: 07-background-jobs-gpu-offload
plan: 01
subsystem: jobs
tags: [thread-pool, sqlite, pyside6, dock-badge, system-tray]

# Dependency graph
requires:
  - phase: 06-foundation-gui-local-optimization
    provides: MainWindow, DatabaseManager, OptimizationEngine, SessionManager
provides:
  - JobManager with ThreadPoolExecutor for concurrent optimization jobs
  - SQLite jobs table for persistence and crash recovery
  - Jobs tab with status badges and job management UI
  - Dock badge showing running/queued job count
  - System tray icon with quick status menu
  - Job lifecycle signals (started, progress, completed, failed, cancelled)
affects:
  - Phase 7 Plan 2: GPU Offload and Job History
  - Phase 8: Workflow Accelerators

# Tech tracking
tech-stack:
  added: [concurrent.futures.ThreadPoolExecutor]
  patterns:
    - ThreadPoolExecutor for CPU-bound JAX work without GIL issues
    - Qt signals for thread-safe job status updates
    - SQLite JSON columns for flexible job config/results storage
    - Periodic timer-based UI refresh (2 second polling)

key-files:
  created:
    - apps/native_mac/jobs/__init__.py
    - apps/native_mac/jobs/job_manager.py
    - apps/native_mac/gui/views/jobs_tab.py
    - apps/native_mac/gui/menubar_extra.py
  modified:
    - apps/native_mac/persistence/models.py (added Job model, JobStatus enum)
    - apps/native_mac/persistence/database.py (added jobs table and CRUD)
    - apps/native_mac/dock_handler.py (added set_badge_count, set_badge_progress)
    - apps/native_mac/main.py (integrated JobManager, dock badge, tray icon)
    - apps/native_mac/gui/main_window.py (added Jobs tab)

key-decisions:
  - Use ThreadPoolExecutor instead of multiprocessing (JAX releases GIL, threads work for CPU-bound)
  - Job states: queued, running, completed, failed, cancelled
  - SQLite persistence enables job history and crash recovery
  - Dock badge shows total active jobs (queued + running)
  - System tray icon skipped in CI/test mode via environment variable check
  - Progress updates throttled to every 10% to reduce database writes

patterns-established:
  - "Job lifecycle: queued → running → completed/failed/cancelled"
  - "Thread-safe job status: Qt signals from worker threads to main thread"
  - "Dock badge updates: periodic timer polling job manager state"
  - "Job config/results: JSON serialization in SQLite for flexibility"

# Metrics
duration: 15min
completed: 2026-01-29
---

# Phase 7 Plan 1: Background Job Infrastructure Summary

**Concurrent optimization job queue with ThreadPoolExecutor, SQLite persistence, Dock badge progress indicator, and system tray menubar extra for quick status access.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-01-29T23:55:10Z
- **Completed:** 2026-01-29T
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments

- Created JobManager with ThreadPoolExecutor for concurrent job execution (up to CPU count workers)
- Implemented Job model with JobStatus enum and full SQLite persistence (config, results, progress)
- Added jobs table to database with CRUD operations and status indexes
- Created JobsTab with JobTableModel showing status badges (color-coded by state)
- Implemented context menu actions: View Details, Cancel, Delete, Re-run
- Added DockIconHandler.set_badge_count() for showing active job count on Dock
- Created SystemTrayIcon for menubar status with recent jobs submenu
- Integrated JobManager signals with dock badge updates and tray icon refresh
- Added periodic status updates (2 second timer) for live job status
- Job notifications on completion with job name and lineup count

## Task Commits

Each task was committed atomically:

1. **Task 1: Create JobManager with thread pool and SQLite persistence** - `2dc8ddc` (feat)
2. **Task 2: Create Jobs tab and integrate with main window** - `4f11247` (feat)
3. **Task 3: Implement Dock badge and menubar extra** - `130995d` (feat)

**Plan metadata:** [pending] (docs: complete plan)

## Files Created/Modified

- `apps/native_mac/jobs/__init__.py` - Package exports (JobManager, JobStatus)
- `apps/native_mac/jobs/job_manager.py` - JobManager class with ThreadPoolExecutor and signals
- `apps/native_mac/gui/views/jobs_tab.py` - JobsTab with JobTableModel and job management UI
- `apps/native_mac/gui/menubar_extra.py` - SystemTrayIcon for menubar status
- `apps/native_mac/persistence/models.py` - Added Job dataclass and JobStatus enum
- `apps/native_mac/persistence/database.py` - Added jobs table and CRUD methods
- `apps/native_mac/dock_handler.py` - Added set_badge_count() and set_badge_progress()
- `apps/native_mac/main.py` - Integrated JobManager, dock badge, tray icon
- `apps/native_mac/gui/main_window.py` - Added Jobs tab to tab widget

## Decisions Made

- **ThreadPoolExecutor over multiprocessing**: JAX releases GIL during computation, so threads achieve parallelism without process overhead
- **SQLite JSON columns**: Flexible schema for job config and results without rigid table structure
- **Periodic polling (2s)**: Simple and reliable for UI updates vs. complex signal routing from workers
- **Dock badge shows total active**: queued + running count gives user complete picture of pending work
- **Skip tray icon in CI**: Environment variable check prevents issues in headless test environments

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all components integrated smoothly with existing codebase.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Background job infrastructure complete and ready for GPU offload integration
- JobManager provides foundation for Phase 7 Plan 2 (GPU client, job history)
- SQLite persistence enables job history features and crash recovery
- Ready for Phase 8 workflow accelerators (split-view, constraint presets)

---
*Phase: 07-background-jobs-gpu-offload*
*Completed: 2026-01-29*
