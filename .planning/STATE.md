# Project State: Axiomatic NASCAR DFS

**Last Updated:** 2026-02-02 UTC

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-01-29)

**Core value:** Personal-use NASCAR DFS optimizer as native Apple Silicon Mac app with optional Windows GPU offload
**Current focus:** Phase 9: Distribution & Quality - In progress

---

## Current Position

**Milestone:** v1.2 Native Mac App
**Phase:** 4 of 4 (Phase 9: Distribution & Quality)
**Plan:** 3 of 3 (Phase 9: Distribution & Quality)
**Status:** ✅ COMPLETE

**Progress:**
```
Milestone v1.0: ██████████ 100% (26/26 plans complete)
Milestone v1.1: ████████░░  25% (archived — wrong direction)
Milestone v1.2: ██████████ 100% (23/23 plans complete - ALL PHASES COMPLETE)

Phase 9 Progress:
[██] 09-01: Build Automation & Code Signing ✅ Complete
[██] 09-02: Documentation ✅ Complete
[██] 09-03: Distribution & Release ✅ Complete (UAT deferred)
```

---

## Last Activity

**Date:** 2026-02-02
**What happened:**
- **FRONTEND:** Connected frontend to real FastAPI backend API
  - Created `api-client.ts` with fetch wrapper, retry logic, timeout handling, request/response interceptors
  - Created `api.ts` service functions for health checks (`/health`, `/ready`), NASCAR optimization (`/api/v2/optimize/nascar`), and ontology endpoints (`/ontology/drivers/{id}`)
  - Created `api.ts` types mirroring Pydantic models: `NASCAROptimizeRequest`, `NASCAROptimizeResponse`, `HealthStatus`, `DriverDetailResponse`, etc.
  - Updated `page.tsx` to use real API calls instead of mock data: health check on mount, driver loading from race endpoints, real optimization with abort controller support
  - Added proper error handling with user-friendly messages, loading states, and race condition prevention
  - Updated `ProjectionTable.tsx` with refresh button to re-fetch driver data
  - Created `.env.local.example` with `NEXT_PUBLIC_API_URL` configuration
  - Updated type exports in `types/index.ts` and lib exports in `lib/index.ts`
  - All API calls use proper TypeScript types and error handling throughout

---

## Session Continuity

**Last session:** 2026-02-02 08:45 UTC
**Stopped at:** Completed frontend connection to real backend API
**Resume file:** None

**Completed Today:**
- Connected frontend to real FastAPI backend
  - Created API client with base URL from `NEXT_PUBLIC_API_URL` environment variable
  - Implemented retry logic with exponential backoff and jitter
  - Added timeout handling and abort controller support for request cancellation
  - Created service functions for all major endpoints: health, optimize, ontology
  - Updated page.tsx to fetch real driver data and submit real optimization requests
  - Added proper loading states and error handling with user-friendly messages
  - Added refresh functionality to ProjectionTable
  - Created environment configuration template
- Fixed Neo4j connection timeout and added comprehensive retry logic to OntologyDriver
  - Implemented connection retry logic with exponential backoff and jitter
  - Added configurable retry parameters (max_retries, base_delay, max_delay) via environment variables
  - Implemented error categorization (transient vs permanent vs authentication)
  - Added is_healthy() and verify_connection() methods for health checks
  - Added connection pool monitoring with acquisition time tracking
  - Implemented auto-reconnect on stale connections with thread safety
  - Added connection_pool_stats() method for detailed pool statistics
  - Enhanced get_connection_metrics() with comprehensive monitoring data
  - Created comprehensive test suite with 15+ test classes covering retry, health, pool stats
  - Ensured backward compatibility with existing API

---

## Performance Metrics

**Velocity:**
- Total plans completed: 30 (26 v1.0 + 3 v1.1 + 1 v1.2)
- Average duration: ~45 min per plan
- Total execution time: ~20 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1 | 6 | ~4.5h | ~45m |
| 2 | 5 | ~4h | ~48m |
| 3 | 9 | ~7h | ~47m |
| 4 | 6 | ~4h | ~40m |
| 5.1 | 3 | ~6m | ~2m* |
| 6 | 10 | ~25m | 2.5m |
| 7 | 3/3 | ~42m | 14m |
| 8 | TBD | TBD | - |
| 9 | TBD | TBD | - |

*Phase 5.1 was infrastructure setup (faster than feature work)

**Recent Trend:**
- Last plan: Frontend API connection (~45 min)
- Trend: Successfully connecting frontend to backend infrastructure

---

## Accumulated Context

### Decisions

**v1.0 Decisions (validated):**
- Ontology as hard constraint/veto system — Enforces physics/race-mechanics
- Causal Bayesian Network + skeleton narrative simulation — Encodes race flow
- Optimize for conditional upside (top 1% tail) — EV insufficient for GPPs
- NumPyro over PyMC for JAX acceleration — 10-100x speedup
- Polars for telemetry processing — 10-100x performance vs pandas

**v1.2 Decisions (from research):**
- Build as local Mac app, not SaaS — Personal use; keep proprietary if profitable
- PySide6/PyQt for native GUI — Reuse Python codebase; native macOS feel
- Optional Windows GPU offload — Heavy jobs on desktop GPU, everyday use on Mac
- HTTP/FastAPI pattern for GPU offload — Start simple, upgrade to ZeroMQ if needed
- JAX[cpu] for Apple Silicon MVP — jax-metal experimental, validate stability later

**New from 06-01 execution:**
- py2app requires setuptools compatibility fix (removed deprecated setup_requires)
- Alias mode (-A) for development builds, full build for distribution
- App bundle automatically signed with ad-hoc signature for local testing

**New from 06-02 execution:**
- SQLite chosen over SQLAlchemy for zero-dependency simplicity
- Base64 encoding for Qt binary geometry data persistence
- UPSERT pattern for app_state enables repeated saves without errors
- Context manager pattern ensures automatic connection cleanup

**New from 06-03 execution:**
- Qt Model/View architecture with QAbstractTableModel subclasses
- Value-based color-coding: green (>3.0 pts/$1000), red (<1.5 pts/$1000)
- Top 20% lineup highlighting for quick identification of best lineups
- Right-align numeric columns for better readability
- Signal/slot mechanism enables automatic UI updates when data changes

**New from 06-04 execution:**
- MainWindow with QTabWidget central widget for tabbed interface
- Tab creation pattern: create_*_tab() methods for each tab
- Window title updates dynamically based on active tab
- SessionManager dependency injection via constructor
- Clean separation: gui package for window, main.py for app-level concerns

**New from 06-05 execution:**
- DataController with pandas read_csv for robust CSV parsing
- Error handling pattern: tuple (success, error_message, data)
- DriverTableView widget with import integration and signal emission
- Native QFileDialog for macOS file picker with Quick Look support
- File > Open menu with CMD+O keyboard shortcut
- User-friendly QMessageBox error dialogs instead of raw tracebacks

**New from 06-06 execution:**
- JAX-based MCMC optimizer with configurable iterations (default 1000, max 5000)
- Temperature-based sampling for exploration/exploitation tradeoff
- QThread worker with progress, finished, error, cancelled signals
- OptimizationEngine facade coordinating optimizer + worker + database
- Progress callback every 1% of iterations for smooth UI updates
- Cancellation flag checked between MCMC iterations
- Lineup validation: 6 drivers, salary cap <= $50,000
- Team stacking constraints (min/max per team)

**New from 06-07 execution:**
- ConstraintPanel widget with QFormLayout for clean input alignment
- Salary/ownership/stacking constraints with validation
- ProgressDialog as modal blocking dialog during MCMC (30-60 seconds)
- OptimizationTab with race selector, constraints, and Run Optimization button
- Lineup count (10-150) and iterations (100-5000) selectors
- Callback-based async results: progress → finished/error/cancelled
- Cross-tab communication: MainWindow passes drivers from Race Data to Optimization
- Results displayed in LineupTableModel with top 20% color-coding

**New from 06-08 execution:**
- DraftKings CSV export with Entry ID + Driver 1-6 columns
- CSV file association for double-click to open
- LineupsTab with Export to DraftKings, Save Lineups, Load Saved buttons
- Drag-and-drop CSV import support in DriverTableView
- UTF-8 with BOM encoding for Excel compatibility
- Auto-detection of CSV format (driver data vs lineup export)
- Round-trip driver data export for data portability

**New from 06-09 execution:**
- AboutDialog following macOS HIG (icon, name, version, copyright, Credits/License buttons)
- DockIconHandler with NSApp.requestUserAttention_ for dock bounce on optimization completion
- Dock menu with Recent Races section and quick actions (New Race, Generate Lineups, Preferences)
- NotificationManager with NSUserNotificationCenter for native macOS notifications
- "View Lineups" action button in notifications switches to Lineups tab when clicked
- Version management in version.py for consistent display across UI
- Signal/slot integration between optimization completion and UI feedback

**New from 06-10 execution:**
- SessionRestorer pattern: Orchestrates restoration of multiple UI components on launch
- Settings auto-persistence: showEvent loads, hideEvent saves
- Preference granularity: Each restore behavior (geometry, race, lineups, tab) independently configurable
- Timestamp tracking for last race save
- Theme changes require app restart (standard Qt behavior)

**New from 07-01 execution:**
- ThreadPoolExecutor for concurrent optimization jobs (JAX releases GIL, threads work for CPU-bound)
- Job model with JobStatus enum: queued → running → completed/failed/cancelled
- SQLite jobs table with JSON columns for flexible config/results storage
- JobTableModel with color-coded status badges and auto-refresh (2 second polling)
- Dock badge updates via set_badge_count() showing total active jobs
- SystemTrayIcon for menubar status with recent jobs submenu
- Job lifecycle signals: job_started, job_progress, job_completed, job_failed, job_cancelled
- Notifications on job completion with job name and lineup count
- Periodic status updates via QTimer for live UI refresh

**New from 07-02 execution:**
- GPUWorkerClient using urllib (zero external dependencies) for HTTP communication
- GPU offload routing in JobManager with test_connection() before routing
- _execute_job_gpu() with polling for async job completion
- Automatic fallback to local CPU on GPU failure (configurable)
- GPU Settings section with URL, API key (password), timeout, and connection test
- API key NOT stored in database (session-only) for security
- JobDetailsDialog with QTabWidget for Config/Results/Error views
- Execution mode tracking (gpu/local/fallback) in job metadata
- Job filtering by status and text search via database queries
- Re-run functionality with (re-run) suffix and _rerun_of tracking
- Export job results to JSON with full metadata

**New from 07-03 execution:**
- Recreate OptimizationTab when JobManager becomes available to inject dependency
- Graceful fallback to legacy optimization_engine when job_manager is None
- Signal connections established in main.py rather than tab constructors for flexibility
- GPU mode status label updates dynamically (blue for GPU, gray for local)
- Job submission shows confirmation dialog with job ID and execution mode

**New from 08-02 execution (Undo/Redo System):**
- UndoManager with per-race and global QUndoStack instances for context isolation
- Unlimited undo depth (setUndoLimit(0)) - never lose user work
- QUndoCommand subclasses for all undoable actions with merge support
- Edit menu with standard macOS CMD+Z and CMD+Shift+Z shortcuts
- Commands store minimal state (IDs/values) not full objects to prevent memory bloat
- Pattern: Tab.set_undo_manager() for dependency injection of undo functionality

**New from 08-03 execution (Keyboard Shortcuts):**
- ShortcutManager with QAction factory for all menu/toolbar actions
- 20+ default shortcuts following macOS conventions (⌘+N, ⌘+O, ⌘+Z, ⌘+Return, etc.)
- Qt.ApplicationShortcut context ensures global shortcut operation across all tabs
- ShortcutConfigDialog with category grouping, conflict detection, import/export
- Shortcuts persist to QSettings and can be reset to factory defaults
- Pattern: All QAction creation goes through ShortcutManager.create_action()

**New from 08-04 execution (Split-View Editor):**
- SplitEditorTab with nested QSplitter layout (horizontal main + vertical right)
- Debounced optimization trigger using QTimer.singleShot restart pattern
- LivePreview widget for compact lineup display in split-pane layout
- QSettings binary state persistence with saveState/restoreState
- Job cancellation pattern: cancel pending_job_id before submitting new job
- Settings integration for debounce delay (100-2000ms) and real-time mode
- Menu integration for Toggle Split View (Ctrl+\) and focus shortcuts (Ctrl+1/2/3)

**New from 08-06 execution (Settings Backup/Export):**
- BackupManager with comprehensive export/import of all application state
- JSON export format with metadata versioning for forward compatibility
- Base64 encoding for binary settings data (window geometry)
- ExportDialog with selective data export and date range filtering
- Merge strategies for import: replace, merge, skip_existing
- Automatic backup creation before import (safety feature)
- Keyboard shortcuts: Cmd+Shift+E (Export All), Cmd+Shift+I (Import Backup)
- Progress dialogs for long-running export/import operations

**New from 09-01 execution (Build Automation & Code Signing):**
- Build automation script with clean state, py2app bundling, and ad-hoc code signing
- Python 3.12.7 used for building (py2app 0.28.9 incompatible with Python 3.14.2)
- Ad-hoc signing for personal distribution (no Apple Developer Program required)
- pyproject.toml workaround for py2app compatibility (temporarily rename during build)
- Version synchronization: version.py, setup.py CFBundleVersion, CHANGELOG.md all set to 1.2.0

**New from Frontend API Integration:**
- API client with fetch wrapper, retry logic with exponential backoff, timeout handling
- Request/response interceptors for authentication and logging
- AbortController support for request cancellation and race condition prevention
- Service functions for all backend endpoints: health checks, optimization, ontology
- TypeScript types mirroring FastAPI Pydantic models
- Environment-based configuration with `NEXT_PUBLIC_API_URL`
- Real-time API status indicator in UI with connection error display
- Proper error handling with user-friendly messages for all API errors
- Loading states for all async operations with spinner feedback

**New from Neo4j Connection Retry Implementation:**
- Custom retry logic with exponential backoff and jitter (no external tenacity dependency)
- Environment-variable based retry configuration (NEO4J_RETRY_* variables)
- Error categorization pattern: transient, permanent, authentication, timeout, unknown
- Connection health checks with caching (30-second interval)
- Auto-reconnect on ServiceUnavailable errors with thread-safe singleton pattern
- Connection pool monitoring with acquisition time tracking and slow acquisition warnings
- ConnectionPoolStats dataclass for structured metrics
- Graceful degradation with detailed error context for debugging

### Pending Todos

5 todos pending — /gsd-check-todos to review

**Completed:**
- ✅ Add comprehensive tests for projection model — 72 tests with 97% code coverage (model loading, inference, error handling, device selection, caching)
- ✅ Add error boundaries and loading states to frontend — React error boundaries, skeleton loading, API retry logic, accessibility support
- ✅ Add Neo4j ontology endpoints to FastAPI — 7 REST endpoints implemented (GET/POST for drivers, tracks, races + metaphysical adjustments)
- ✅ Add Docker Compose retry logic and dependency management — Restart policies, wait-for-it script, dev/prod configs, .dockerignore, comprehensive documentation
- ✅ Add Neo4j ontology integration tests — 44 comprehensive tests covering DriverNode, TrackNode, RaceNode, connection handling, singleton pattern, and error cases
- ✅ Add metaphysical properties display to frontend — Visual progress bars, tooltips, filtering, DriverDetailPanel, "Why This Lineup" explanations
- ✅ Update FastAPI to use NASCAROptimizer — New `/api/v2/optimize/nascar` endpoint with epistemic database integration, belief systems, team stacking, risk-adjusted optimization; deprecated legacy `/api/v1/optimize`
- ✅ Align Airflow metaphysical fields with ontology schema — Mapped legacy fields (agility, fortune, momentum, entropy) to ontology properties (skill, psyche_aggression, shadow_risk, realpolitik_pos, difficulty, aggression_factor, chaos_factor)
- ✅ Connect frontend to real backend API — Created API client with retry logic, service functions for health checks and optimization, updated page.tsx to use real API with loading states and error handling, added refresh button to ProjectionTable, created environment configuration template
- ✅ Fix Neo4j connection timeout and add retry logic — Implemented exponential backoff with jitter, connection health checks, auto-reconnect, comprehensive error categorization, pool monitoring with 400+ lines of new tests

---

## Blockers / Concerns

**From research (may affect v1.2 execution):**
- **GPU Offload Complexity**: Network protocols, worker service, and fallback logic add significant engineering; start with HTTP/FastAPI pattern before committing to ZeroMQ
- **JAX Backend Conflicts**: jax-metal is experimental and cannot coexist with JAX CUDA; use JAX[cpu] for MVP, validate Metal stability before committing
- **py2app Gotchas**: Complex dependency discovery and code signing workflows; test bundling early in Phase 6 and automate via GitHub Actions
- **macOS Integration Gaps**: Spotlight integration may require pyobjc bridge; defer to v1.3+ if complexity is prohibitive

**Carried forward from v1.0:**
- MCMC sampling can be slow (30-60 seconds) — GPU offload in Phase 7 will address this
- Neo4j connection required for optimization — Local Neo4j instance needed

**v1.1 Results (Archived but reusable):**
- ✅ Redis-based job persistence implemented (may reuse for local app reliability)
- ✅ Health check endpoints operational (may adapt for local monitoring)
- ✅ Structured JSON logging (reusable)
- ⚠️ Correlation ID middleware disabled (not needed for local app)

---

## Quick Commands

**Check progress:**
```bash
/gsd:progress
```

**Plan Phase 6:**
```bash
/gsd:plan-phase 6
```

**View requirements:**
```bash
cat .planning/REQUIREMENTS.md
```

**View roadmap:**
```bash
cat .planning/ROADMAP.md
```

**View milestones:**
```bash
cat .planning/MILESTONES.md
```

**View research:**
```bash
cat .planning/research/SUMMARY.md
```

---
