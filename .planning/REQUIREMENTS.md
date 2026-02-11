# Requirements: Axiomatic NASCAR DFS — Native Mac App

**Defined:** 2026-01-29
**Milestone:** v1.2 Native Mac App
**Core Value:** Personal-use NASCAR DFS optimizer as native Apple Silicon Mac app with optional Windows GPU offload

## v1.2 Requirements

Requirements for native macOS desktop application. Each maps to a roadmap phase.

### GUI Foundation

- [x] **GUI-01**: Native macOS GUI with PySide6/Qt6 framework
- [x] **GUI-02**: Single main window with tabbed interface (Race Data, Optimization, Lineups, Settings)
- [x] **GUI-03**: Standard macOS menus (app menu, File, Edit, View, Window, Help)
- [x] **GUI-04**: Standard macOS shortcuts (CMD+Q quit, CMD+, preferences, CMD+W close, CMD+Z undo)
- [x] **GUI-05**: Dark mode support (follow system appearance)
- [x] **GUI-06**: Native file dialogs (QFileDialog for CSV import/export)
- [ ] **GUI-07**: Menubar extra for quick status and job progress
- [ ] **GUI-08**: Split-view lineup editor (left: constraints, right: live results)
- [ ] **GUI-09**: Comprehensive keyboard shortcuts for all actions
- [x] **GUI-10**: About window (version, license, credits)

### Data Ingestion & Export

- [x] **DATA-01**: CSV import for race data (manual file import via QFileDialog)
- [x] **DATA-02**: CSV export in DraftKings upload format
- [x] **DATA-03**: File associations (.csv files open in app via double-click)
- [ ] **DATA-04**: Drag-and-drop data import (drop CSV files onto window or Dock icon)
- [ ] **DATA-05**: API data fetching (NASCAR/DraftKings if available/free)
- [ ] **DATA-06**: Web scraping with fallback chain (API → scraping → manual CSV)

### Optimization & Computation

- [x] **OPT-01**: Single race optimization trigger with constraints
- [x] **OPT-02**: Progress indication for long-running MCMC jobs (30-60s)
- [x] **OPT-03**: Local Apple Silicon optimization using JAX[cpu] ARM64 builds
- [x] **OPT-04**: Lineup display table view with sorting and filtering
- [x] **OPT-05**: Constraint input UI (salary cap, exposure limits, stacking rules)
- [ ] **OPT-06**: Background job queue (run multiple optimizations concurrently)
- [ ] **OPT-07**: GPU offload toggle (local Mac CPU vs Windows GPU worker)
- [ ] **OPT-08**: Job history with audit trail (timestamped runs with inputs/outputs)
- [ ] **OPT-09**: Real-time optimization on constraint changes (debounced trigger)
- [ ] **OPT-10**: Kernel veto log viewer (debug why lineups were rejected)

### Persistence & State

- [x] **PERS-01**: Local persistence via SQLite (races, lineups, constraints, job history)
- [x] **PERS-02**: Save/load optimization configurations
- [x] **PERS-03**: Window geometry persistence (remember window size and position)
- [ ] **PERS-04**: Constraint presets (save/load constraint sets)
- [ ] **PERS-05**: Undo/Redo system (CMD+Z / CMD+Shift+Z for lineup edits)
- [x] **PERS-06**: Session resume (restore previous state on app launch)
- [ ] **PERS-07**: Backup/export of settings and lineups to JSON

### System Integration

- [x] **SYS-01**: Dock icon with standard behavior (bounce on completion, dock menu)
- [x] **SYS-02**: macOS notification on job completion with "View" action button
- [ ] **SYS-03**: App bundling via py2app (.app bundle creation)
- [ ] **SYS-04**: Dock badge for job status (progress pie icon, completion count)
- [ ] **SYS-05**: Personal Apple ID code signing for local distribution

### Distribution & Quality

- [ ] **DIST-01**: py2app configuration for reproducible .app builds
- [ ] **DIST-02**: Code signing with personal Apple ID
- [ ] **DIST-03**: Test .app bundle on clean macOS machine (verify Gatekeeper)
- [ ] **DIST-04**: Documentation for manual installation and troubleshooting

## v1.3+ Requirements

Deferred to future release. Tracked but not in current roadmap.

### Advanced Features

- **ADV-01**: Spotlight integration (search races and lineups via Core Spotlight)
- **ADV-02**: Lineup comparison view (diff two portfolios side-by-side)
- **ADV-03**: Portfolio diversity heatmap (visual exposure analysis)
- **ADV-04**: Advanced export templates (custom CSV/JSON formats)
- **ADV-05**: Scenario explorer (interactive "what if" visualization)

### Future Considerations

- **FUT-01**: Live race optimization (real-time during race)
- **FUT-02**: Mobile companion app (iOS for viewing lineups)
- **FUT-03**: Multi-site support (FanDuel, Yahoo beyond DraftKings)
- **FUT-04**: Public App Store distribution

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Public web API or SaaS deployment | Personal use tool; if highly profitable, keep proprietary |
| Multi-user authentication or authorization | Single-user local app |
| CORS, rate limiting, or public-facing security | Local-only, no web exposure |
| Kubernetes, Docker Compose, or cloud infrastructure | Local desktop app only |
| Electron or web-view wrapper | Must be native PySide6 for authentic Mac experience |
| Real-time live betting or in-race optimization | Out of scope for v1.2; pre-lock only |
| Mobile apps (iOS/Android) | Native Mac desktop only |
| Multiple DFS sites | DraftKings NASCAR Classic only |
| Cloud sync or multi-device sync | Single-user local app |
| Auto-updates or telemetry | Personal tool; manual updates sufficient |
| Plugin system or scripting | Hardcoded features; no extensibility needed |
| Social sharing or collaboration | Single-user personal tool |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| GUI-01 | Phase 6 | Complete |
| GUI-02 | Phase 6 | Complete |
| GUI-03 | Phase 6 | Complete |
| GUI-04 | Phase 6 | Complete |
| GUI-05 | Phase 6 | Complete |
| GUI-06 | Phase 6 | Complete |
| GUI-07 | Phase 7 | Pending |
| GUI-08 | Phase 8 | Pending |
| GUI-09 | Phase 8 | Pending |
| GUI-10 | Phase 6 | Complete |
| DATA-01 | Phase 6 | Complete |
| DATA-02 | Phase 6 | Complete |
| DATA-03 | Phase 6 | Complete |
| DATA-04 | Phase 7 | Pending |
| DATA-05 | Phase 7 | Pending |
| DATA-06 | Phase 7 | Pending |
| OPT-01 | Phase 6 | Complete |
| OPT-02 | Phase 6 | Complete |
| OPT-03 | Phase 6 | Complete |
| OPT-04 | Phase 6 | Complete |
| OPT-05 | Phase 6 | Complete |
| OPT-06 | Phase 7 | Pending |
| OPT-07 | Phase 7 | Pending |
| OPT-08 | Phase 7 | Pending |
| OPT-09 | Phase 8 | Pending |
| OPT-10 | Phase 8 | Pending |
| PERS-01 | Phase 6 | Complete |
| PERS-02 | Phase 6 | Complete |
| PERS-03 | Phase 6 | Complete |
| PERS-04 | Phase 8 | Pending |
| PERS-05 | Phase 8 | Pending |
| PERS-06 | Phase 6 | Complete |
| PERS-07 | Phase 8 | Pending |
| SYS-01 | Phase 6 | Complete |
| SYS-02 | Phase 6 | Complete |
| SYS-03 | Phase 9 | Pending |
| SYS-04 | Phase 7 | Pending |
| SYS-05 | Phase 9 | Pending |
| DIST-01 | Phase 9 | Pending |
| DIST-02 | Phase 9 | Pending |
| DIST-03 | Phase 9 | Pending |
| DIST-04 | Phase 9 | Pending |

**Coverage:**
- v1.2 requirements: 37 total
- Mapped to phases: 37 (100% coverage)
- Unmapped: 0

**Phase Breakdown (actual):**
- Phase 6: Foundation GUI + Local Optimization (21 requirements)
- Phase 7: Background Jobs + GPU Offload (8 requirements)
- Phase 8: Workflow Accelerators (7 requirements)
- Phase 9: Distribution & Quality (6 requirements)

**Requirements Count by Phase:**
- Phase 6: 21 requirements (GUI-01,02,03,04,05,06,10, DATA-01,02,03, OPT-01,02,03,04,05, PERS-01,02,03,06, SYS-01,02)
- Phase 7: 8 requirements (GUI-07, DATA-04,05,06, OPT-06,07,08, SYS-04)
- Phase 8: 7 requirements (GUI-08,09, OPT-09,10, PERS-04,05,07)
- Phase 9: 6 requirements (SYS-03,05, DIST-01,02,03,04)

---
*Requirements defined: 2026-01-29*
*Last updated: 2026-01-29 — Phase 6 requirements marked Complete*
