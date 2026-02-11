# Research Summary: Native Mac App + Windows GPU Offload

**Project:** NASCAR DFS Optimizer — Native macOS desktop application with optional Windows GPU offload
**Milestone:** v1.2 Native Mac App
**Domain:** Desktop application (macOS native GUI) with distributed computing (Windows GPU worker)
**Researched:** 2026-01-29
**Confidence:** MEDIUM

## Executive Summary

This research covers **NEW capabilities only** for extending the existing NASCAR DFS optimizer: native macOS GUI with Apple Silicon optimization, app bundling for distribution, and optional Windows GPU offload for MCMC acceleration. The validated backend stack (FastAPI, NumPyro, JAX, Polars, Neo4j) remains unchanged and is documented separately.

**Desktop app pattern:** Native macOS applications are fundamentally different from web applications. Users expect native look-and-feel (Cocoa controls, macOS menus), long-running task transparency (progress indicators, cancelability, background execution), and local-first data (fast launch, offline capability). The differentiator for a DFS optimizer is **workflow efficiency** — rapid iteration from data ingest to optimized lineups with export-ready output. Desktop apps earn their keep through accelerated workflows and background processing, not feature parity with web tools.

**Recommended approach:** Build a **PySide6-based Qt6 GUI** for native macOS integration (dark mode, native menus, Cocoa API access) with **py2app** for .app bundling and distribution. For Apple Silicon optimization, use ARM64-optimized JAX[cpu] builds; optionally add experimental jax-metal for M-series GPU acceleration. For Windows GPU offload, start with **HTTP via existing FastAPI backend** (simplest implementation), then upgrade to **ZeroMQ** if streaming progress and job queuing are needed. Personal use distribution can leverage personal Apple ID code signing; public distribution requires Apple Developer Program enrollment for notarization.

**Key risks and mitigation:** (1) **GPU offload complexity** — network protocols, worker service, and fallback logic add significant engineering; mitigate by starting with HTTP/FastAPI pattern (simpler) before committing to ZeroMQ. (2) **macOS integration gaps** — Spotlight integration, Dock badges, and menubar extras may require Objective-C/Swift bridges via pyobjc; validate feasibility during Phase 1. (3) **App bundling gotchas** — py2app has complex dependency discovery and code signing workflows; mitigate by testing bundling early and automating via GitHub Actions. (4) **JAX backend conflicts** — jax-metal is experimental and cannot coexist with JAX CUDA; validate stability before committing to Metal GPU backend.

## Key Findings

### Recommended Stack

**Core GUI Framework:**
- **PySide6 (6.8.0+)** — Native Qt6 GUI for macOS; LGPL licensing (free for commercial use), official Qt bindings, native Apple Silicon support, excellent macOS integration (dark mode, native menus, Cocoa API access)
- **py2app (0.28+)** — macOS .app bundle creation; macOS-specific, creates proper .app bundles with Info.plist, supports code signing and notarization, better macOS integration than PyInstaller

**Apple Silicon Optimization:**
- **JAX[cpu] (0.4.35+)** — CPU-optimized JAX for Apple Silicon; ARM64-optimized builds, leverages Apple's unified memory architecture
- **numpyro (0.15.0+)** — JAX-native probabilistic inference; already in stack, ensure ARM64 wheels for Apple Silicon performance
- **jax-metal** (optional, experimental) — M-series GPU acceleration via Metal; use for heavy MCMC workloads if stability acceptable

**Remote GPU Offload:**
- **FastAPI (existing)** — Simplest pattern: extend `/optimize` endpoint on Windows GPU machine, Mac app calls via HTTP; leverages existing backend
- **ZeroMQ (25.0+)** — Alternative for streaming: lightweight async message queue; use if HTTP polling overhead is problematic or real-time progress updates needed

**Data Import/Export:**
- **pandas (openpyxl)** — Excel import/export; users expect Excel import
- **PySide6-Addons (QtCharts)** — In-app data visualization; native Qt charts for portfolio display

### Expected Features

**Must have (v1.2 MVP table stakes):**
- **Native macOS GUI with PySide6** — Core requirement; without this, it's not a Mac app
- **Standard macOS menus and shortcuts** — CMD+Q quit, CMD+, preferences, CMD+Z undo
- **Single main window with tabbed interface** — Race data, optimization, lineups, settings
- **Data ingestion** — Manual CSV import (v1), API fetch if available (v1.2)
- **Optimization trigger** — Single race optimization with constraints
- **Lineup display** — Table view of generated lineups with sorting
- **CSV export** — DraftKings upload format
- **Local persistence** — Save/load races and lineups (SQLite)
- **Progress indication** — Show optimization progress (30-60s jobs)
- **Dark mode support** — Follow system appearance

**Should have (v1.3 competitive differentiators):**
- **Background job queue** — Run multiple optimizations concurrently while working in lineups
- **GPU offload toggle** — Transparent switching between local and GPU-accelerated computation
- **Split-view lineup editor** — Real-time feedback when adjusting exposures, salary, ownership
- **Job history** — Audit trail of all optimization runs
- **Constraint presets** — Save/load constraint configurations
- **Kernel veto log viewer** — Debug why lineups were rejected
- **Menubar extra** — Quick status without switching windows
- **Keyboard shortcuts for all actions** — Power user efficiency

**Defer (v2+):**
- **Scenario explorer** — Interactive "what if" visualization (nice-to-have, doesn't block core workflow)
- **Portfolio diversity heatmap** — Visual exposure analysis (power user feature)
- **Advanced export templates** — Custom CSV/JSON formats (export is sufficient for MVP)
- **Spotlight integration** — Search races and lineups (HIGH complexity, validate pyobjc bridge first)

### Architecture Approach

**Desktop application architecture** follows standard patterns: PySide6 GUI runs in main thread, long-running optimization jobs run in background threads/processes (QThread or ProcessPoolExecutor), progress updates communicate via Qt signals/slots, and local SQLite persistence enables fast launch and offline operation.

**Major components:**
1. **PySide6 GUI layer** — Native macOS window system with tabbed interface (Race Data, Optimization, Lineups, Settings); handles user input and displays results
2. **Job queue system** — Background job processing with progress indicators and cancel buttons; manages local and remote (Windows GPU) optimization jobs
3. **Local persistence layer** — SQLite for races, lineups, constraints, job history; enables fast launch, offline operation, historical analysis
4. **Network client** — HTTP client for GPU offload (FastAPI on Windows machine) or ZeroMQ for streaming pattern; handles job submission, status polling, result retrieval
5. **Bundling system** — py2app configuration for .app bundle creation; code signing and notarization for distribution

**Integration points:**
- Mac App → Existing Backend (FastAPI, NumPyro, JAX) — local optimization jobs spawn subprocesses or import backend modules directly
- Mac App → Windows GPU Worker — network protocol (HTTP or ZeroMQ) for job submission and result streaming
- Mac App → macOS System APIs — Dock integration, notifications, file associations, optional Spotlight indexing

### Critical Pitfalls

1. **GPU offload complexity trap** — Network protocols, Windows worker service, authentication, fallback logic add significant engineering cost. **Avoid:** Start with HTTP/FastAPI pattern (leverages existing backend), only upgrade to ZeroMQ if polling overhead proves problematic. **Validate:** Job submission, status polling, error handling, and local fallback in Phase 1.

2. **macOS integration overreach** — Spotlight integration, Dock badges, and menubar extras may require Objective-C/Swift bridges via pyobjc, adding complexity and potential instability. **Avoid:** Defer advanced system integration to v1.3+; focus on native UI (menus, dark mode, standard dialogs) for MVP. **Validate:** pyobjc bridge feasibility before committing to Spotlight.

3. **App bundling late validation** — py2app dependency discovery, code signing, and notarization workflows have complex edge cases; discovering these late blocks distribution. **Avoid:** Test bundling end-to-end in Phase 1 (build .app, code sign, test on clean machine, Gatekeeper bypass). **Automate:** GitHub Actions for reproducible builds.

4. **JAX backend conflicts** — jax-metal is experimental and cannot coexist with JAX CUDA; switching backends requires clean reinstall. **Avoid:** Use JAX[cpu] for MVP (stable, ARM64-optimized), only add jax-metal if Metal GPU acceleration is critical and stability is validated. **Test:** Benchmark Metal vs CPU backend before committing.

5. **Long-running job UX failure** — 30-60 second MCMC jobs without progress indication, cancelability, or completion notifications make the app feel broken. **Avoid:** Implement progress bar with cancel button (Phase 1), background queue with job status (Phase 2), Dock badge and notifications (Phase 2). **Pattern:** Background thread/process → Qt signals → UI updates → notification on completion.

## Implications for Roadmap

Based on research, suggested phase structure for Native Mac App milestone:

### Phase 1: Foundation GUI + Local Optimization
**Rationale:** Establish native macOS look-and-feel first; validates desktop app pattern before investing in complex distributed computing. Delivers functional MVP that replaces headless workflow with GUI.

**Delivers:** PySide6 main window with tabbed interface, CSV data import, local optimization trigger, lineup table view, CSV export, SQLite persistence, progress indication.

**Addresses:** All P1 table stakes features (native GUI, menus, dark mode, data workflow)

**Uses:** PySide6 (GUI), JAX[cpu] (Apple Silicon optimization), SQLite (persistence), existing backend (NumPyro, JAX, Polars)

**Avoids:** GPU offload complexity (defer to Phase 2), Spotlight integration (defer to Phase 2)

**Implementation focus:**
- Native macOS controls (QTableView, QTabWidget, QFileDialog)
- Standard menus (app menu, File, Edit, View, Window, Help)
- Dark mode support (system appearance detection)
- Background job processing (QThread for optimization jobs)
- Progress indication (progress bar with cancel button)
- Local persistence (SQLite for races, lineups, constraints)
- App bundling validation (py2app build, code sign, test on clean machine)

### Phase 2: Background Jobs + Windows GPU Offload
**Rationale:** Workflow accelerators and GPU performance are natural next steps once MVP is validated. Background job queue enables concurrent optimizations; GPU offload reduces 30-60s jobs to 5-10s.

**Delivers:** Background job queue with status panel, HTTP client for Windows GPU worker, GPU offload toggle (local vs remote), job history with audit trail, Dock badge and menubar extra.

**Addresses:** P2 competitive differentiators (background queue, GPU offload, job history, menubar extra)

**Uses:** FastAPI (existing backend on Windows), HTTP client (requests or httpx), QThread or ProcessPoolExecutor (job queue)

**Implements:** Job queue architecture with progress streaming; Windows GPU worker service (extends existing `/optimize` endpoint); fallback logic (if GPU unavailable, run locally)

**Implementation focus:**
- Job queue with pending/running/completed states
- HTTP client for job submission and status polling
- Network error handling and local fallback
- Dock badge (progress pie icon)
- Menubar extra (quick status dropdown)
- Job history (SQLite with timestamped runs)

**Research flags:** This phase has well-documented patterns (HTTP client, background threading). No additional research needed if using FastAPI HTTP pattern.

### Phase 3: Workflow Accelerators + Power User Features
**Rationale:** Once core workflow and GPU offload are stable, invest in features that differentiate from web-based optimizers: split-view editing, constraint presets, keyboard shortcuts, kernel veto logging.

**Delivers:** Split-view lineup editor (live constraint/result preview), constraint preset manager (save/load configurations), kernel veto log viewer, comprehensive keyboard shortcuts, undo/redo system.

**Addresses:** Remaining P2 competitive differentiators

**Uses:** QSplitter (split view), QUndoStack (undo/redo), Qt signals/slots (live preview)

**Implements:** Advanced GUI patterns (real-time updates, command pattern for undo, keyboard shortcut system)

**Implementation focus:**
- Split-view layout (left: constraints, right: live lineup preview)
- Real-time optimization trigger on constraint changes
- Constraint preset save/load (JSON export/import)
- Kernel veto log viewer with explanations
- Comprehensive keyboard shortcuts (CMD+Shift+P for command palette)
- Undo/redo for lineup edits

**Research flags:** Well-documented Qt patterns; no additional research needed.

### Phase 4: Advanced System Integration (Optional)
**Rationale:** Power user features that require deeper macOS integration. Only implement if MVP validates desktop app value and advanced users request these capabilities.

**Delivers:** Spotlight integration (search races and lineups), advanced export templates (custom CSV/JSON formats), lineup comparison view (diff portfolios).

**Addresses:** P3 nice-to-have features

**Uses:** Core Spotlight framework (Cocoa), pyobjc (Python-ObjC bridge), NSUserActivity (indexing)

**Implements:** macOS system integration APIs (may require native Swift/ObjC extensions)

**Research flags:** **HIGH research need** — Spotlight integration via Python requires pyobjc bridge validation; verify feasibility during phase planning. Defer if bridge complexity is prohibitive.

### Phase Ordering Rationale

1. **Foundation first (Phase 1):** Native GUI and local optimization validate desktop app pattern before investing in distributed computing. App bundling validation ensures distribution isn't blocked by technical gotchas.

2. **Performance second (Phase 2):** GPU offload and background jobs are natural performance optimizations once workflow is validated. HTTP pattern leverages existing backend, minimizing new infrastructure.

3. **Differentiation third (Phase 3):** Workflow accelerators (split-view, presets, undo/redo) differentiate from web optimizers and improve power user efficiency.

4. **Polish last (Phase 4):** Advanced system integration (Spotlight) is high-complexity, low-urgency; defer until MVP proves value and users request features.

### Research Flags

**Phases likely needing deeper research during planning:**
- **Phase 4 (Advanced System Integration):** Spotlight integration via Python requires pyobjc bridge validation; verify Core Spotlight framework accessibility from Python before committing.

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (Foundation GUI):** PySide6 and Qt6 have excellent documentation; native macOS GUI patterns are well-established.
- **Phase 2 (GPU Offload):** HTTP client patterns and FastAPI are well-documented; background threading is standard Qt pattern.
- **Phase 3 (Workflow Accelerators):** QSplitter, QUndoStack, and Qt signals/slots are standard Qt features.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | PySide6, py2app, JAX[cpu] recommendations verified via official docs (HIGH); jax-metal experimental status reduces confidence to MEDIUM; ZeroMQ vs HTTP tradeoffs are MEDIUM (web search unavailable during research) |
| Features | MEDIUM | Desktop application patterns based on official macOS HIG (HIGH); specific DFS optimizer UX based on domain knowledge (MEDIUM); long-running job patterns from HIG guidelines (HIGH) |
| Architecture | MEDIUM | Desktop app architecture (GUI + background threads + SQLite) is standard pattern (HIGH); GPU offload via HTTP is straightforward (HIGH); ZeroMQ pattern needs prototyping validation (MEDIUM) |
| Pitfalls | MEDIUM | GPU offload complexity identified via architectural reasoning (MEDIUM); app bundling gotchas from py2app documentation (MEDIUM); JAX backend conflicts from official JAX docs (HIGH); macOS integration gaps from platform knowledge (MEDIUM) |

**Overall confidence:** MEDIUM

**Why not HIGH:**
- WebSearch was unavailable during research (usage limit reached); some recommendations rely on official documentation and architectural reasoning rather than community validation
- jax-metal is experimental; stability and performance need validation during implementation
- ZeroMQ pattern for MCMC streaming wasn't deeply researched; HTTP/FastAPI pattern is safer starting point
- Spotlight integration via Python (pyobjc bridge) needs feasibility validation

### Gaps to Address

**Stack validation gaps:**
- **jax-metal stability and performance** — Experimental backend may crash or produce incorrect results; validate against CPU backend during Phase 1. If unstable, ship with JAX[cpu] only.
- **py2app vs PyInstaller on Apple Silicon** — Research recommends py2app for macOS-specific integration, but performance comparison not tested; validate bundling performance and .app size during Phase 1.
- **ZeroMQ MCMC streaming pattern** — HTTP/FastAPI is recommended starting point; if streaming progress is critical, prototype ZeroMQ pattern in Phase 2 before committing.

**Architecture validation gaps:**
- **pyobjc bridge feasibility for Spotlight** — Core Spotlight integration may require native Swift/ObjC extensions; validate pyobjc bridge accessibility before Phase 4. If infeasible, defer Spotlight or implement via Spotlight-compatible file naming.
- **GPU offload fallback behavior** — Research identifies network errors and worker unavailability as failure modes; define explicit fallback policy (retry vs fail-fast vs local execution) during Phase 2.

**Feature validation gaps:**
- **Undo/Redo scope** — Global undo stack vs per-tab undo stack needs UX decision; define during Phase 3 implementation.
- **Split-view performance** — Real-time optimization on every constraint change may overwhelm system; implement debouncing or explicit "Optimize" button during Phase 3.

## Sources

### Primary (HIGH confidence)

**Official package documentation:**
- PySide6 — https://doc.qt.io/qtforpython/ (Qt6 Python bindings, LGPL licensing, macOS integration)
- Qt6 macOS Platform Notes — https://doc.qt.io/qt-6/macos-platform-notes.html (native macOS patterns, dark mode, Cocoa API)
- py2app — https://pypi.org/project/py2app/ (macOS .app bundling, code signing, notarization)
- JAX — https://pypi.org/project/jax/ (Apple Silicon ARM64 wheels, CPU-optimized builds)
- jax-metal — https://github.com/google/jax-metal (experimental Metal GPU backend)

**Apple developer documentation:**
- macOS Human Interface Guidelines — https://developer.apple.com/design/human-interface-guidelines/macos (desktop app patterns, long-running tasks, native controls)
- Code Signing and Notarization — Apple Developer documentation (app distribution, Gatekeeper)

**Existing validated stack (from prior research):**
- FastAPI — existing backend, extends to Windows GPU worker
- NumPyro, JAX, Polars — existing optimization engine
- Neo4j — existing ontology store

### Secondary (MEDIUM confidence)

**Desktop application patterns:**
- "Progress indicators" — macOS HIG patterns for long-running tasks
- "Background tasks" — macOS Energy Efficiency Guide
- "Native app benefits" — platform-specific UX patterns (industry consensus)

**GPU offload patterns:**
- HTTP/FastAPI pattern — leverages existing backend architecture (established pattern)
- ZeroMQ vs HTTP tradeoffs — architectural reasoning (web search unavailable; needs prototyping validation)

**Ecosystem knowledge:**
- Qt signals/slots for background thread communication — standard Qt pattern
- SQLite for local persistence — standard desktop app pattern
- QThread for background jobs — standard Qt pattern

### Tertiary (LOW confidence)

**Gaps requiring validation:**
- jax-metal stability and performance benchmarks — experimental status, needs testing
- py2app vs PyInstaller performance comparison on Apple Silicon — not tested, needs benchmarking
- ZeroMQ MCMC streaming implementation details — web search unavailable, needs prototyping
- pyobjc bridge for Core Spotlight — not validated, needs feasibility testing

**Competitor analysis:**
- Web-based DFS optimizers — general UX weaknesses inferred from desktop app patterns
- Spreadsheet workflows — general limitations inferred from domain knowledge

---
*Research completed: 2026-01-29*
*Ready for roadmap: yes*
