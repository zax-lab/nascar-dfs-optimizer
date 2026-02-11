# Roadmap: Axiomatic NASCAR DFS — Native Mac App

**Created:** 2026-01-27
**Updated:** 2026-01-30 (Phase 9 in progress - Distribution & Quality)
**Phases:** 9 (5 complete + 1 archived + 3 planned)

---

## Overview

This roadmap delivers a native macOS desktop application for the NASCAR DFS optimizer, transforming the headless CLI/web stack into a personal local application with Apple Silicon optimization and optional Windows GPU offload. The journey establishes native GUI patterns first (Phase 6), adds workflow acceleration and distributed computing (Phase 7), invests in power-user features (Phase 8), and ensures reliable distribution (Phase 9).

---

## Milestones

- ✅ **v1.0 Core Engine** - Phases 1-4 (shipped 2026-01-28)
- ✅ **v1.1 Production Readiness** - Phase 5.1 only (archived 2026-01-29)
- 🚧 **v1.2 Native Mac App** - Phases 6-9 (in progress)

---

## Phases

<details>
<summary>✅ v1.0 Core Engine (Phases 1-4) - SHIPPED 2026-01-28</summary>

### Phase 1: Feasible-by-Design NASCAR Simulation Core

**Goal:** Build a simulation engine that produces mechanically plausible joint outcomes with conserved dominator resources.

**Rationale:** Everything downstream (tail metrics, optimizer) is invalid if the sim produces impossible worlds or inflates dominator tails. Conservation + coherent race-flow are the "axiomatic" differentiator.

**Plans:** 6 plans (6 executed, including 2 gap closures)

**Plan List:**
- [x] 01-01-PLAN.md — State space model with explicit transition operators (green, caution, pit, fuel)
- [x] 01-02-PLAN.md — Ontology constraints and Causal Bayesian Network with veto rules
- [x] 01-03-PLAN.md — Skeleton Narrative scenario generator (1,000+ scenarios)
- [x] 01-04-PLAN.md — Kernel dominator conservation validation with JAX acceleration
- [x] 01-05-PLAN.md — CBN forward sampling from learned CPDs (Gap Closure)
- [x] 01-06-PLAN.md — CBN integration into scenario generation (Gap Closure)

**Requirements:**
- SIM-01: State space with explicit transition operators
- SIM-02: Causal Bayesian Network constrained by ontology
- SIM-03: Skeleton Narrative scenario generation
- KRN-01: Dominator conservation constraints

**Success Criteria:**
1. State space model represents green runs, caution, pit cycles, and fuel windows as explicit transitions
2. Causal Bayesian Network structure is grounded in ontology constraints (priors + veto rules)
3. Simulator generates 1,000+ coherent Skeleton Narratives per slate with realistic race-flow regimes
4. Each scenario produces conserved component totals (laps led ≤ race length, fastest laps ≤ green-flag laps)
5. Kernel validates conservation invariants and logs veto reasons clearly

**Completed:** 2026-01-27

---

### Phase 2: Ontology-Compiled Constraints + Calibration Harness

**Goal:** Compile reproducible constraint specs from Neo4j and build calibration infrastructure for track-type uncertainty.

**Rationale:** To trust (and iterate on) simulation/tail outcomes, you need reproducible specs and track-type calibrated uncertainty. Ontology must compile into immutable constraints/priors to keep inner loops deterministic.

**Plans:** 5 plans (5 executed)

**Plan List:**
- [x] 02-01-PLAN.md — ConstraintSpec compilation from Neo4j (immutable artifacts)
- [x] 02-02-PLAN.md — Telemetry pipeline with Polars and feature availability contracts
- [x] 02-03-PLAN.md — Track-archetype calibration harness (NumPyro + ArviZ)
- [x] 02-04-PLAN.md — Headless /optimize API with scenario-driven contracts
- [x] 02-05-PLAN.md — Kernel instrumentation and end-to-end integration

**Requirements:**
- DATA-01: Premium telemetry ingestion
- CALIB-01: Probabilistic calibration harness
- API-01: Headless execution contract
- PIPE-01: End-to-end pipeline integration

**Success Criteria:**
1. ConstraintSpec compilation fetches driver/track properties from Neo4j and creates immutable artifacts
2. Telemetry ETL pipeline processes loop/lap-by-lap data with temporal boundary enforcement
3. Calibration harness produces track-archetype posterior distributions with CRPS/log_score metrics
4. /optimize API accepts scenario-driven requests and returns optimization results
5. Kernel instrumentation tracks rejection statistics and logs veto reasons

**Completed:** 2026-01-27

---

### Phase 3: Tail Metrics + Tail-Objective Portfolio Optimizer

**Goal:** Build a portfolio optimizer that targets top-tail outcomes (tournament equity) rather than mean points.

**Rationale:** Once sim outputs are mechanically valid and reasonably calibrated, you can optimize what matters: top-tail probability/conditional upside, and generate portfolios with exposure/diversity constraints.

**Plans:** 9 plans (9 executed, including 5 gap closure)

**Plan List:**
- [x] 03-01-PLAN.md — Tail metrics computation (CVaR, Top X%, conditional upside)
- [x] 03-02-PLAN.md — CVaR objective builders (Rockafellar-Uryasev MILP formulation)
- [x] 03-03-PLAN.md — Portfolio generation with scenario optimization
- [x] 03-04-PLAN.md — API integration and end-to-end optimization
- [x] 03-05-PLAN.md — Reformulate CVaR for upper-tail maximization (Gap Closure)
- [x] 03-06-PLAN.md — Implement real mean-optimized baseline (Gap Closure)
- [x] 03-07-PLAN.md — Create missing test files (Gap Closure)
- [x] 03-08-PLAN.md — Create portfolio generator integration tests (Gap Closure)
- [x] 03-09-PLAN.md — Create API integration tests (Gap Closure)

**Requirements:**
- OPT-01: Conditional-upside objective (top-1% optimization)
- OPT-02: Portfolio generation with scenario optimization
- DFS-01 through DFS-06: Table stakes DFS optimizer features

**Success Criteria:**
1. Tail metrics computed from scenario outcomes (Top X%, Top 0.1%, CVaR/conditional upside)
2. Solver-integrated tail objective builder optimizes for top-tail probability
3. Portfolio generator produces 20-150 lineups with exposure controls
4. Scenario matrices cached and shared across portfolio (no re-sim per lineup)
5. Tail objectives stable under limited sims with minimum count controls
6. DK compliance, pool controls, exposure rules, group constraints all working
7. CSV export compatible with DraftKings upload

**Completed:** 2026-01-27

---

### Phase 4: Field / Ownership / Contest-Sim EV

**Goal:** Model the field and payout structure to compute true tournament EV.

**Rationale:** True tournament EV depends on the field and duplication. This can meaningfully improve decision quality, but it's heavy and should follow a validated sim/opt core.

**Plans:** 6 plans (6 executed)

**Plan List:**
- [x] 04-01-PLAN.md — Individual ownership estimators (historical, projections, salary-skill)
- [x] 04-02-PLAN.md — Hybrid ensemble with recent form and uncertainty quantification
- [x] 04-03-PLAN.md — Payout curve modeling (power-law, exponential)
- [x] 04-04-PLAN.md — Field lineup simulation and Monte Carlo contest engine
- [x] 04-05-PLAN.md — Leverage-aware optimization with ownership constraints
- [x] 04-06-PLAN.md — API integration and end-to-end testing

**Requirements:**
- DFS-01: Ownership estimation ensemble
- DFS-02: Payout curve modeling
- DFS-03: Field lineup simulation
- DFS-04: Contest simulation
- DFS-05: Leverage-aware optimization
- DFS-06: Regime-aware portfolios
- API-02: Phase 4 API integration

**Success Criteria:**
1. Ownership priors estimated with duplication proxies (historical, projections, salary-skill)
2. Hybrid ensemble produces uncertainty quantification via bootstrap confidence intervals
3. Payout curve modeling approximates large-field GPP structures (power-law, exponential)
4. Contest simulation outputs ROI, Cash%, win probability with confidence intervals
5. Leverage-aware optimization penalizes high-owned drivers for tournament equity
6. Regime-aware portfolios allocate across scenario types (dominator, chaos, fuel-mileage)

**Completed:** 2026-01-28

</details>

<details>
<summary>✅ v1.1 Production Readiness (Phase 5.1 only) - ARCHIVED 2026-01-29</summary>

### Phase 5.1: Critical Infrastructure (Job Persistence & Health Checks)

**Goal:** Implement Redis-based job state persistence and health check endpoints to prevent job loss on container restart.

**Rationale:** Addresses the highest-priority production blocker: in-memory job state loss. Jobs must survive container restarts, and orchestrators require health check endpoints.

**Plans:** 3 plans (3 executed)

**Plan List:**
- [x] 05-01-PLAN.md — Redis infrastructure and JobStateManager class
- [x] 05-02-PLAN.md — Migrate job endpoints to Redis and add health checks
- [x] 05-03-PLAN.md — Structured logging and graceful shutdown

**Requirements:**
- PROD-01: Jobs persist in Redis and survive container restarts
- PROD-02: Job status endpoint returns current state (pending/running/complete/failed)
- PROD-03: Job result endpoint retrieves completed optimization results
- PROD-04: Completed jobs auto-expire after configurable TTL (7-30 days)
- PROD-05: /health endpoint returns 200 if process is running (liveness probe)
- PROD-06: /ready endpoint checks Neo4j and Redis availability (readiness probe)
- PROD-07: API returns 503 Service Unavailable when dependencies are down
- PROD-08: Graceful shutdown waits for in-flight jobs to complete (60-120s timeout)
- PROD-13: Logs are structured JSON with timestamp, level, message, context
- PROD-14: Each request has a correlation ID for traceability across logs
- PROD-15: Errors are logged with full stack traces and request context

**Success Criteria:**
1. Optimization jobs submitted via API persist in Redis and survive container restarts
2. Clients can poll /jobs/{id} for status and /jobs/{id}/result for completed results
3. /health returns 200 when process is running, /ready returns 200 only when Neo4j and Redis are available
4. API returns 503 Service Unavailable when Neo4j or Redis are down (with dependency status)
5. Container shutdown waits up to 120 seconds for in-flight jobs to complete before terminating
6. All logs are structured JSON with correlation IDs linking request lifecycle across log entries

**Avoids:**
- In-memory job state (jobs lost on restart)
- Missing dependency health checks (cascading failures)
- Silent error masking (200 OK on failures)
- Unstructured logging (untraceable requests)

**Delivers:**
- Redis job state persistence (JobStateManager class)
- Job status and result endpoints
- Health check endpoints (/health, /ready, /live)
- Graceful shutdown with job drain
- Structured JSON logging with correlation IDs

**Why archived:** Project vision clarified as personal local Mac app, not SaaS service. Authentication, rate limiting, and public web API are unnecessary for single-user local application.

**Reusable work:** Phase 5.1 infrastructure (Redis job persistence, structured logging) may be useful for local app reliability.

**Completed:** 2026-01-28

</details>

---

### 🚧 v1.2 Native Mac App (In Progress)

**Milestone Goal:** Personal-use NASCAR DFS optimizer as native Apple Silicon Mac app with optional Windows GPU offload

#### Phase 6: Foundation GUI + Local Optimization

**Goal**: Native macOS application with local optimization workflow from data import to CSV export

**Rationale**: Establish native macOS look-and-feel first; validates desktop app pattern before investing in complex distributed computing. Delivers functional MVP that replaces headless workflow with GUI.

**Depends on**: Phase 5.1 (infrastructure patterns)

**Requirements**: GUI-01, GUI-02, GUI-03, GUI-04, GUI-05, GUI-06, GUI-10, DATA-01, DATA-02, DATA-03, OPT-01, OPT-02, OPT-03, OPT-04, OPT-05, PERS-01, PERS-02, PERS-03, PERS-06, SYS-01, SYS-02 (21 requirements)

**Success Criteria** (what must be TRUE):
  1. User launches native Mac app with standard menus (CMD+Q quit, CMD+, preferences) and dark mode support
  2. User imports CSV race data via file dialog or drag-and-drop and sees data displayed in tabbed interface
  3. User sets optimization constraints (salary cap, exposures, stacking) and triggers optimization with progress bar
  4. User views generated lineups in sortable table view and exports to DraftKings upload format
  5. User quits and relaunches app to find previous session restored (window geometry, races, lineups)

**Plans**: 10 plans (10 complete)

**Plan List:**
- [x] 06-01-PLAN.md — PySide6 application skeleton with main window and menus
- [x] 06-02-PLAN.md — SQLite persistence layer with session management
- [x] 06-03-PLAN.md — Qt Model/View architecture for driver/lineup/race tables
- [x] 06-04-PLAN.md — MainWindow with tabbed interface and session persistence
- [x] 06-05-PLAN.md — CSV import with native file dialogs and error handling
- [x] 06-06-PLAN.md — JAX[cpu] local optimization engine with progress worker
- [x] 06-07-PLAN.md — Optimization tab with constraints UI and progress dialog
- [x] 06-08-PLAN.md — CSV export in DraftKings format and file associations
- [x] 06-09-PLAN.md — About dialog, dock icon, and macOS notifications
- [x] 06-10-PLAN.md — Session restore and Settings tab

**Completed:** 2026-01-29

---

#### Phase 7: Background Jobs + GPU Offload

**Goal**: Concurrent optimization jobs with optional Windows GPU acceleration and system integration

**Rationale**: Workflow accelerators and GPU performance are natural next steps once MVP is validated. Background job queue enables concurrent optimizations; GPU offload reduces 30-60s jobs to 5-10s.

**Depends on**: Phase 6

**Requirements**: GUI-07, OPT-06, OPT-07, OPT-08, SYS-04 (5 requirements)

**Success Criteria** (what must be TRUE):
  1. User sees Dock badge with job progress count and receives macOS notification on completion with "View" action
  2. User submits multiple optimization jobs that run concurrently while viewing/editing lineups in main window
  3. User toggles GPU offload switch to route jobs to Windows GPU worker (5-10s) vs local CPU (30-60s)
  4. User views job history with timestamped runs showing inputs/outputs and can re-run previous configurations

**Plans**: 3 plans in 3 waves (including 1 gap closure)

**Plan List:**
- [x] 07-01-PLAN.md — Background Job Infrastructure (JobManager, Dock badge, menubar extra)
- [x] 07-02-PLAN.md — GPU Offload and Job History (GPU client, Settings integration, re-run)
- [x] 07-03-PLAN.md — Gap Closure: UI Wiring (GPU toggle, JobsTab connection)

**Completed:** 2026-01-30

---

#### Phase 8: Workflow Accelerators

**Goal**: Power-user features for rapid iteration and debugging (split-view editing, keyboard shortcuts, undo/redo)

**Rationale**: Once core workflow and GPU offload are stable, invest in features that differentiate from web-based optimizers: split-view editing, constraint presets, keyboard shortcuts, kernel veto logging.

**Depends on**: Phase 7

**Requirements**: GUI-08, GUI-09, OPT-09, OPT-10, PERS-04, PERS-05, PERS-07 (7 requirements)

**Success Criteria** (what must be TRUE):
  1. User adjusts constraints in left split-pane and sees live lineup preview update in right pane (debounced)
  2. User saves constraint presets by name and loads them later for similar races
  3. User presses CMD+Z to undo lineup edits and CMD+Shift+Z to redo (global undo stack)
  4. User opens kernel veto log viewer to see why lineups were rejected with rule explanations
  5. User performs all common actions via keyboard shortcuts (no mouse required for power users)

**Plans**: 6 plans in 3 waves

**Plan List:**
- [x] 08-01-PLAN.md — Constraint Presets (PresetManager, PresetsTab, SQLite JSON storage)
- [x] 08-02-PLAN.md — Undo/Redo System (UndoManager, QUndoCommand subclasses, per-race + global stacks)
- [x] 08-03-PLAN.md — Keyboard Shortcuts (ShortcutManager, customizable shortcuts, CMD+Z/Shift+Z)
- [x] 08-04-PLAN.md — Split-View Editor (QSplitter layout, debounced live optimization, LivePreview widget)
- [x] 08-05-PLAN.md — Kernel Veto Log Viewer (VetoLogTab, filtering, export to JSON/CSV)
- [x] 08-06-PLAN.md — Settings Backup/Export (BackupManager, JSON export/import, full state preservation)

**Completed:** 2026-01-30

---

#### Phase 9: Distribution & Quality

**Goal**: Reproducible .app bundle with code signing and distribution documentation

**Rationale**: Ensure the app can be reliably distributed and installed on macOS machines. Code signing prevents Gatekeeper warnings; documentation enables self-service installation.

**Depends on**: Phase 8

**Requirements**: SYS-03, SYS-05, DIST-01, DIST-02, DIST-03, DIST-04 (6 requirements)

**Success Criteria** (what must be TRUE):
  1. Developer runs py2app build to generate reproducible .app bundle with all dependencies
  2. Developer signs .app with personal Apple ID and passes Gatekeeper on clean macOS machine
  3. Developer installs .app on clean machine and verifies full workflow (import → optimize → export)
  4. User reads documentation for manual installation and troubleshooting common issues

**Plans**: 3 plans in 2 waves (including 1 human-verify checkpoint)

**Plan List:**
- [x] 09-01-PLAN.md — Build Automation & Code Signing (build script, setup.py update, CHANGELOG, version.py)
- [x] 09-02-PLAN.md — Documentation (INSTALL.md, TROUBLESHOOTING.md, README.md update)
- [x] 09-03-PLAN.md — Clean Machine Test & Release (checkpoint, zip archive, GitHub release)

---

## Progress Tracking

| Phase | Milestone | Plans | Progress | Status | Completed |
|-------|-----------|-------|----------|--------|-----------|
| 1 | v1.0 | 6 | 100% | ✅ Complete | 2026-01-27 |
| 2 | v1.0 | 5 | 100% | ✅ Complete | 2026-01-27 |
| 3 | v1.0 | 9 | 100% | ✅ Complete | 2026-01-27 |
| 4 | v1.0 | 6 | 100% | ✅ Complete | 2026-01-28 |
| 5.1 | v1.1 | 3 | 100% | ✅ Complete | 2026-01-28 |
| 6 | v1.2 | 10 | 100% | ✅ Complete | 2026-01-29 |
| 7 | v1.2 | 3 | 100% | ✅ Complete | 2026-01-30 |
| 8 | v1.2 | 6 | 100% | ✅ Complete | 2026-01-30 |
| 9 | v1.2 | 3 | 67% | In progress | 2026-01-30 |

**v1.0:** 4/4 phases executed, all phase goals verified ✅

**v1.1:** 1/4 phases executed (5.1 complete), then archived due to direction change ✅

**v1.2:** 3/4 phases complete (6-8 complete), Phase 9 in progress (2/3 complete) 🚧

**Overall:** 50 plans executed (26 v1.0 + 3 v1.1 + 21 v1.2), 1 plan remaining for Phase 9

---

*Milestone v1.0 defined: 2026-01-27*
*Milestone v1.1 defined: 2026-01-28*
*Milestone v1.2 defined: 2026-01-29*
