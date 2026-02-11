# Feature Research: Native Mac App + Windows GPU Offload

**Domain:** NASCAR DFS Optimizer — Native macOS desktop application with optional Windows GPU offload
**Researched:** 2026-01-29
**Confidence:** MEDIUM

## Executive Summary

Research into native macOS desktop application patterns reveals distinct expectations from web applications. Desktop users expect:

1. **Native look-and-feel** — macOS controls, menus, window management, not wrapped web interfaces
2. **Long-running task transparency** — Progress indicators, cancelability, background execution
3. **Local-first data** — Fast launch, offline capability, no cloud dependency
4. **System integration** — Menubar extras, notifications, file associations, Spotlight indexing

For a DFS optimizer with 30-60 second MCMC runs and optional GPU offload, the critical differentiator is **workflow efficiency** — rapid iteration from data ingest to optimized lineups with export-ready output.

**Key insight:** Desktop apps earn their keep through **accelerated workflows** and **background processing**, not feature parity with web tools. The Mac app should feel like a precision instrument, not a ported web dashboard.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that define a "native Mac app." Missing these makes the application feel foreign or broken.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Native macOS menus** (app menu, File, Edit, View, Window, Help) | Standard Mac app pattern; users look for app-level commands in menu bar | MEDIUM | PySide6 `QMenuBar` with standard macOS menu structure |
| **Command+Q quit behavior** | Mac users expect consistent app quitting; CMD+Q should work everywhere | LOW | Standard PySide6 window close event handling |
| **Preferences/Settings window (Command+,)** | Standard location for app configuration; users expect CMD+, shortcut | LOW | Single settings window with tabbed interface |
| **Standard macOS dialogs** (File open/save, sheets, alerts) | Consistency with OS; native file picker integration | LOW | `QFileDialog` with macOS-native dialogs |
| **Window management** (close, minimize, maximize, full-screen) | Basic window behavior expected by all Mac users | MEDIUM | Standard `QMainWindow` with native window buttons |
| **Undo/Redo (Command+Z/Shift+Command+Z)** | Standard text editing expectation; critical for data entry errors | MEDIUM | Requires undo stack for lineups, constraints, parameters |
| **Dark mode support** | macOS 12+ users expect dark mode compatibility; apps that don't support it feel dated | MEDIUM | Follow system appearance; test light/dark themes |
| **Spotlight integration** (search for races, lineups) | Power users expect Spotlight to find app content | HIGH | Requires Core Spotlight framework integration |
| **Notification on job completion** | Long-running jobs (30-60s) need completion alerts when user is in another app | MEDIUM | macOS notifications with action buttons |
| **Dock icon with badge** | Visual feedback for job status; badge shows progress/completion count | MEDIUM | `NSDockTile` integration for badges and progress |
| **File associations** (.csv, .json race data) | Double-click race data files to open in app | LOW | Info.plist UTI declarations for file types |
| **About window** (version, license) | Standard Mac app requirement; users expect to check version | LOW | Standard About dialog with app info |
| **Keyboard navigation** (Tab, arrow keys, Return, Escape) | Accessibility and power user efficiency; mouse-less operation | MEDIUM | Full keyboard traversal of all controls |
| **Scrolling gestures** (trackpad, mouse) | Mac users expect smooth momentum scrolling | LOW | Native Qt scroll areas with momentum enabled |
| **Resizeable windows** with saved dimensions | Users set window size once; app should remember | LOW | Save/restore window geometry to UserDefaults |
| **Resume on launch** (restore previous session) | Mac users expect apps to reopen where they left off | MEDIUM | Restore last race, lineups, window state on launch |

### Differentiators (Competitive Advantage)

Features that make this desktop app superior to web-based DFS optimizers and spreadsheet workflows.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Background job processing** with queue | Run multiple optimizations/simulations while working in lineups | HIGH | Job queue with progress indicators and cancel buttons |
| **Instant data refresh** (cache invalidation) | No page reloads; data updates propagate immediately to all views | MEDIUM | Reactive data binding (PySide6 signals/slots) |
| **Split-view lineup editor** (left: constraints, right: live results) | Real-time feedback when adjusting exposures, salary, ownership | HIGH | `QSplitter` with live preview; constraint changes trigger re-opt |
| **Quick filters** (Keyboard-driven: /driver, /track, /salary) | Power users can filter lineups instantly without mouse | MEDIUM | Command palette-style filter (CMD+Shift+P) |
| **Lineup comparison view** (diff two lineups side-by-side) | Understand exposure differences and driver overlap at a glance | MEDIUM | Three-pane diff: Lineup A, Lineup B, shared/diff |
| **Export templates** (DraftKings CSV, custom formats) | One-click export directly to upload format | LOW | Template-based CSV export with field mapping |
| **Local data persistence** (SQLite for races, lineups, results) | Fast launch, no network required, historical analysis | MEDIUM | SQLite via `qt_sqlite` or `sqlite3` module |
| **GPU offload toggle** (Mac local vs Windows remote) | Transparent switching between local and GPU-accelerated computation | HIGH | Network job submission with status polling |
| **Scenario explorer** (interactive scenario outcomes) | Visualize "what if" scenarios (caution rate, pit strategy) | HIGH | Interactive controls driving simulation params |
| **Portfolio diversity heatmap** | Visual representation of lineup exposures and overlap | MEDIUM | 2D heatmap grid with color-coded exposure |
| **Constraint presets** (save/load constraint sets) | Quick switching between strategies (stacking, exposure, risk) | MEDIUM | Preset manager with import/export |
| **Optimization history** (audit trail of all runs) | Reproduce previous results; compare optimization iterations | MEDIUM | Timestamped run log with input/output artifacts |
| **Kernel veto log viewer** | Debug why lineups were rejected; understand constraint violations | MEDIUM | Veto log with explanations and rule references |
| **Keyboard shortcuts for all actions** | Power users can operate entirely from keyboard | HIGH | Comprehensive shortcut system (customizable) |
| **Menubar extra** (quick status, job progress) | Monitor long jobs without switching windows | MEDIUM | `NSStatusBar` item with dropdown panel |
| **Drag-and-drop data import** | Drop CSV/JSON files anywhere to import race data | LOW | File drag events with validation and import wizard |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem valuable but create technical debt, UX problems, or violate Mac app patterns.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Real-time live data during race** | "I want to see projections update during the race" | Creates real-time dependency on NASCAR APIs; adds complexity to causal simulation (changing mid-race violates assumptions); personal use doesn't justify infra overhead | Pre-lock only; live race optimization is separate product |
| **Cloud sync for lineups/settings** | "I want to use the app on multiple Macs" | Single-user personal use; cloud sync adds authentication, backend, privacy concerns; local backup is sufficient | Local backup/export of settings; no sync needed |
| **Multiple DFS sites (FanDuel, Yahoo)** | "More sites = more edge" | Scoring rules differ; ontology constraints would need per-site branching; DraftKings Classic only is explicit non-goal | DraftKings NASCAR Classic only (v1.2) |
| **Mobile companion app** | "I want to check my lineups on my phone" | Out of scope (native Mac app only); mobile adds cross-platform complexity, security concerns | Export lineups to CSV; view in any mobile app |
| **Social sharing of lineups** | "I want to share my portfolios with friends" | Single-user personal tool; sharing adds social features, privacy, account complexity | Export to CSV/JSON; manual sharing |
| **Machine learning auto-tuning** | "The app should learn my preferences" | Adds complexity without clear benefit; causal simulation already encodes domain knowledge; personal use doesn't justify ML pipeline | Manual parameter tuning with presets |
| **Web view wrapper** (Electron-style) | "Faster to build, reuse existing web UI" | Feels non-native; performance issues; violates "native Mac app" vision | Native PySide6 GUI with macOS look-and-feel |
| **In-app purchases or licensing** | "I could sell this to others" | Out of scope (personal use); payment adds compliance, security, support burden | Free personal tool; no commerce |
| **Auto-updates** | "I want the app to update itself" | Adds update server, code signing, security complexity for single user | Manual updates (download new .app bundle) |
| **Telemetry or analytics** | "I want to know how I use the app" | Privacy concerns for personal tool; adds network dependency; no clear benefit | Local logging only; no telemetry |
| **Plugin system or scripting** | "Power users could extend the app" | Adds security surface, complexity, maintenance burden for single user | Hardcoded features; no plugins |
| **Multi-window workspace management** | "I want to save window layouts" | Uncommon for Mac apps; adds complexity for limited benefit | Single main window with saved geometry |
| **Collaborative editing** | "I want to work with others on lineups" | Single-user personal use; collaboration adds sync, conflict resolution | Single user only; no collaboration |

---

## Feature Dependencies

```
[Native macOS GUI]
    ├──requires──> [PySide6/Qt framework]
    └──requires──> [Apple Silicon runtime]

[Background job processing]
    ├──requires──> [Job queue system]
    ├──requires──> [Progress notification system]
    └──enhanced by──> [Menubar extra]

[GPU offload to Windows]
    ├──requires──> [Network job API]
    ├──requires──> [Windows GPU worker service]
    └──requires──> [Local fallback logic]

[Local data persistence]
    ├──requires──> [SQLite schema design]
    └──enhanced by──> [Backup/export features]

[Spotlight integration]
    ├──requires──> [Core Spotlight framework]
    └──requires──> [Indexable data model]

[Dark mode support]
    ├──requires──> [System appearance detection]
    └──requires──> [Theme-aware UI assets]

[Undo/Redo system]
    ├──requires──> [Command stack implementation]
    └──requires──> [State serialization]
```

### Dependency Notes

- **Native macOS GUI requires PySide6/Qt**: Foundation for all native UI controls; must be in Phase 1
- **Background job processing requires job queue**: Cannot build long-running jobs without queue system; prerequisite for GPU offload
- **GPU offload requires Windows worker service**: Remote compute is useless without worker; this is a separate backend component
- **Local data persistence enhances Spotlight integration**: Searchable data requires stored data; these build together
- **Undo/Redo requires state serialization**: Need to save/restore app state for meaningful undo

---

## MVP Definition

### Launch With (v1.2 Minimum)

**Essential features for a functional native Mac app that delivers value over the existing headless system.**

- [ ] **Native macOS GUI with PySide6** — Core requirement; without this, it's not a Mac app
- [ ] **Single main window with tabbed interface** — Race data, optimization, lineups, settings
- [ ] **Standard macOS menus and shortcuts** — CMD+Q quit, CMD+, preferences, CMD+Z undo
- [ ] **Data ingestion** — Manual CSV import (v1), API fetch if available (v1.2)
- [ ] **Optimization trigger** — Single race optimization with constraints
- [ ] **Lineup display** — Table view of generated lineups with sorting
- [ ] **CSV export** — DraftKings upload format
- [ ] **Local persistence** — Save/load races and lineups (SQLite)
- [ ] **Progress indication** — Show optimization progress (30-60s jobs)
- [ ] **Dark mode support** — Follow system appearance

**Why these are MVP:**
- Delivers core workflow: import data → optimize → view lineups → export
- Native UI feels like a Mac app (not wrapped web)
- Local persistence enables offline use
- Dark mode is expected on modern macOS

### Add After Validation (v1.3+)

**Features that enhance workflow efficiency once MVP is validated.**

- [ ] **Background job queue** — Run multiple optimizations concurrently
- [ ] **GPU offload toggle** — Switch to Windows GPU worker
- [ ] **Job history** — Audit trail of all optimization runs
- [ ] **Constraint presets** — Save/load constraint configurations
- [ ] **Split-view lineup editor** — Live constraint/result preview
- [ ] **Kernel veto log viewer** — Debug rejected lineups
- [ ] **Menubar extra** — Quick status without switching windows
- [ ] **Keyboard shortcuts for all actions** — Power user efficiency
- [ ] **Spotlight integration** — Search races and lineups
- [ ] **Lineup comparison view** — Diff two portfolios

**Trigger for adding:** MVP validates that native GUI workflow is valuable; these are workflow accelerators.

### Future Consideration (v2+)

**Features to defer until product-market fit is established (or if this becomes a public product).**

- [ ] **Scenario explorer** — Interactive "what if" visualization
- [ ] **Portfolio diversity heatmap** — Visual exposure analysis
- [ ] **Advanced export templates** — Custom CSV/JSON formats
- [ ] **Plugin system** — User extensibility (if multi-user)
- [ ] **Live race optimization** — Real-time during race (if justified)
- [ ] **Mobile companion** — iOS app for viewing lineups (if multi-user)

**Why defer:** These are nice-to-have features that don't block core workflow; they add complexity for unclear gain in a personal-use context.

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Native macOS GUI (PySide6) | HIGH | MEDIUM | P1 |
| Data ingestion (CSV import) | HIGH | LOW | P1 |
| Optimization trigger | HIGH | LOW | P1 |
| Lineup display (table view) | HIGH | LOW | P1 |
| CSV export | HIGH | LOW | P1 |
| Local persistence (SQLite) | HIGH | MEDIUM | P1 |
| Progress indication | HIGH | MEDIUM | P1 |
| Standard macOS menus | MEDIUM | LOW | P1 |
| Dark mode support | MEDIUM | MEDIUM | P1 |
| Background job queue | HIGH | HIGH | P2 |
| GPU offload toggle | HIGH | HIGH | P2 |
| Job history | MEDIUM | MEDIUM | P2 |
| Constraint presets | MEDIUM | MEDIUM | P2 |
| Undo/Redo system | MEDIUM | HIGH | P2 |
| Split-view lineup editor | HIGH | HIGH | P2 |
| Kernel veto log viewer | MEDIUM | MEDIUM | P2 |
| Menubar extra | MEDIUM | MEDIUM | P2 |
| Keyboard shortcuts for all actions | MEDIUM | HIGH | P2 |
| Spotlight integration | LOW | HIGH | P3 |
| Lineup comparison view | MEDIUM | MEDIUM | P2 |
| Scenario explorer | LOW | HIGH | P3 |
| Portfolio diversity heatmap | LOW | MEDIUM | P3 |
| Advanced export templates | LOW | MEDIUM | P3 |
| Plugin system | LOW (personal use) | HIGH | P3 |

**Priority key:**
- **P1 (Must have for v1.2):** Core workflow features; app is incomplete without these
- **P2 (Should have for v1.3):** Workflow accelerators; significant value but can ship after MVP
- **P3 (Nice to have for v2+):** Power user features; defer until validated

---

## Desktop Application Patterns

### Long-Running Computation

Desktop applications handle 30-60 second jobs differently than web apps:

**Pattern 1: Progress with Cancel**
- Show determinate progress bar when possible (scenario count, iteration)
- Always show cancel button
- Update UI every 100-500ms (don't spam UI thread)
- Play notification sound on completion (user may be in another app)

**Pattern 2: Background Queue**
- Jobs run in background thread/process
- UI remains responsive during computation
- Queue shows pending, running, completed jobs
- User can continue working (view previous lineups) while job runs

**Pattern 3: Status Feedback**
- Dock icon shows progress badge (percentage pie icon)
- Menubar extra shows job status dropdown
- Notification center alerts on completion
- Window title shows job state: "NASCAR DFS — Optimizing (45%)"

**Pattern 4: Result Presentation**
- Don't show results until job completes (avoid partial state)
- When job completes, switch to results tab or show dialog
- If user is in another app, bounce Dock icon once
- Notification with "View" action button

### Native Look and Feel

**Guidelines for feeling like a Mac app:**

1. **Use native controls**
   - `QTableView` for data grids (not HTML tables)
   - `QComboBox` for dropdowns (not custom div)
   - `QTabWidget` for tabs (not JavaScript UI)
   - `QSplitter` for resizable panes

2. **Follow macOS layout standards**
   - 10pt system font (San Francisco)
   - 20px standard margin between sections
   - Left-aligned labels above controls
   - Right-aligned action buttons (OK on right, Cancel on left)

3. **Respect system appearance**
   - Detect dark mode change: `paletteChanged` event
   - Use system colors: `windowText`, `window`, `base`
   - Test in both light and dark modes
   - Support high DPI (Retina displays)

4. **Standard keyboard shortcuts**
   - CMD+, → Preferences
   - CMD+Q → Quit app
   - CMD+W → Close window
   - CMD+Z / CMD+Shift+Z → Undo/Redo
   - CMD+A → Select all
   - CMD+C / CMD+V → Copy/Paste

### Data Persistence

**Desktop app persistence patterns:**

1. **Fast launch**
   - Defer heavy loading until after window shows
   - Show skeleton UI immediately, populate data async
   - Cache last-used race data for instant re-open

2. **Offline-first**
   - All features work without network
   - API data fetching is optional enhancement
   - Manual CSV import always available as fallback

3. **Local backup**
   - Auto-backup SQLite database weekly
   - Export settings/lineups to JSON for migration
   - Support "Import from backup" recovery

4. **Data versioning**
   - Schema migrations for SQLite
   - Handle old file formats on import
   - Graceful degradation for unknown fields

### System Integration

**Mac-specific integration features:**

1. **File associations**
   - Register .csv, .json file types in Info.plist
   - Double-click race data file opens app
   - Drag file onto app icon opens file

2. **Spotlight indexing**
   - Index race names, dates, lineups
   - "nascar daytona 500" → finds race
   - "lineups 2026-02-15" → finds lineups

3. **Notifications**
   - Request notification permission on first use
   - Show notification when job completes
   - Include "View" action button
   - Respect "Do Not Disturb"

4. **Dock integration**
   - Dock menu: "New Optimization", "Show Lineups"
   - Badge with job count or progress
   - Bounce once on completion (if user preference)

5. **Menubar extra**
   - Small icon in menu bar (always visible)
   - Dropdown shows: current job, last result, quick actions
   - Clicking opens main window

---

## Implementation Complexity Notes

### Native GUI (PySide6)

**MEDIUM complexity**
- Well-documented framework
- macOS-specific APIs available (Cocoa bindings via `qtmacextras`)
- Layout with `QVBoxLayout`, `QHBoxLayout`, `QGridLayout`
- Custom widgets may be needed for lineup-specific UI

### Background Job Queue

**HIGH complexity**
- Requires threading or multiprocessing (QThread, ProcessPoolExecutor)
- Progress communication from worker thread to UI thread
- Job cancellation requires cooperative cancellation or process kill
- Queue persistence (survive app restart)

### GPU Offload

**HIGH complexity**
- Network protocol for job submission (HTTP, WebSocket, or custom)
- Windows worker service (separate Python service)
- Authentication/encryption for local network
- Fallback logic (if GPU worker unavailable, run locally)
- Status polling and error handling

### Local Persistence

**MEDIUM complexity**
- SQLite schema design for races, lineups, constraints, jobs
- Migration system for schema changes
- Query layer with typed models
- Backup/export functionality

### Spotlight Integration

**HIGH complexity**
- Core Spotlight framework (Cocoa, may need Objective-C/Swift bridge)
- Indexing of app data (NSUserActivity)
- Search result handling (open app to specific state)
- May require `pyobjc` or native Swift/ObjC extension

### Undo/Redo System

**HIGH complexity**
- Command pattern for reversible operations
- Serialize app state for undo snapshots
- Undo stack management (memory, limits)
- Scoped undo (per-tab or global?)

---

## Competitor Analysis

### Web-Based DFS Optimizers

**Competitor strengths:**
- Accessible from any device
- No installation required
- Automatic updates

**Competitor weaknesses:**
- Page reloads break workflow
- No background processing
- Poor keyboard navigation
- Dependent on network connectivity
- Slower for large operations (web latency)

**Our desktop advantage:**
- Instant UI response (no page loads)
- Background job processing
- Local data (fast, offline)
- Native keyboard shortcuts
- System integration (notifications, Spotlight)

### Spreadsheet Workflows

**Competitor (Excel/Google Sheets) strengths:**
- Fully customizable
- Familiar interface
- No development effort

**Competitor weaknesses:**
- No built-in causal simulation
- Manual constraint checking
- Slow for large optimizations
- No portfolio diversification
- Error-prone copy/paste to DraftKings

**Our desktop advantage:**
- Built-in optimization engine
- Constraint validation (Kernel veto)
- Portfolio generation with exposure control
- One-click DraftKings export
- Audit trail and reproducibility

---

## Sources

**Desktop application patterns:**
- macOS Human Interface Guidelines (Apple) — https://developer.apple.com/design/human-interface-guidelines/macos (HIGH confidence, official)
- Qt for macOS documentation — https://doc.qt.io/qt-6/macos-platform-notes.html (HIGH confidence, official)
- PySide6 documentation — https://doc.qt.io/qtforpython/ (HIGH confidence, official)

**Long-running task UX:**
- "Progress indicators" — HIG patterns (HIGH confidence, official)
- "Background tasks" — macOS Energy Efficiency Guide (HIGH confidence, official)

**Desktop vs web apps:**
- "When to use desktop vs web" — general software architecture knowledge (MEDIUM confidence, industry consensus)
- "Native app benefits" — platform-specific UX patterns (MEDIUM confidence, common practice)

**Gaps and limitations:**
- WebSearch was unavailable (usage limit reached); relied on official documentation and general desktop application knowledge
- Specific macOS GPU offload patterns not researched in depth; flagged as HIGH complexity
- Spotlight integration via Python requires verification; `pyobjc` bridge may be needed

**Confidence assessment:**
- Desktop application patterns: MEDIUM (based on official HIG and Qt docs)
- Long-running task UX: MEDIUM (based on HIG guidelines)
- macOS system integration: MEDIUM (official docs, but Python bridges add uncertainty)
- GPU offload architecture: LOW (web search unavailable; no authoritative sources)

---

*Feature research for: NASCAR DFS Optimizer — Native macOS desktop application with Windows GPU offload*
*Researched: 2026-01-29*
