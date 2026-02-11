---
phase: 06-foundation-gui-local-optimization
plan: 04
subsystem: ui
tags: [pyside6, qt, mainwindow, tabs, session-manager]

# Dependency graph
requires:
  - phase: 06-01
    provides: PySide6 application skeleton with native macOS menus
  - phase: 06-02
    provides: SessionManager for window geometry persistence
  - phase: 06-03
    provides: DriverTableModel for driver data display

provides:
  - MainWindow with tabbed interface (4 tabs)
  - Race Data tab with driver table using DriverTableModel
  - Session persistence integration for window geometry
  - Clean package structure separating gui/ from main.py
  - Window title updates based on active tab

affects:
  - 06-05 (Race Data import pipeline will use Race Data tab)
  - 06-06 (Optimization will use Optimization tab)
  - 06-07 (Lineups will use Lineups tab)
  - 06-08 (Settings will use Settings tab)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Tabbed interface with QTabWidget
    - Model/View architecture with QAbstractTableModel
    - Session persistence via SessionManager
    - Package-level exports via __init__.py

key-files:
  created:
    - apps/native_mac/gui/__init__.py
    - apps/native_mac/gui/main_window.py
  modified:
    - apps/native_mac/main.py

key-decisions:
  - "MainWindow moved to gui package for clean separation of concerns"
  - "Menu creation kept in main.py as app-level concern"
  - "SessionManager passed to MainWindow constructor for dependency injection"
  - "Sample driver data included for immediate UI testing"

patterns-established:
  - "Tab creation methods: create_*_tab() pattern for each tab"
  - "Session persistence: load in __init__, save in closeEvent"
  - "Window title updates: _on_tab_changed handler for currentChanged signal"

# Metrics
duration: 2min
completed: 2026-01-29
---

# Phase 6 Plan 4: MainWindow Tabbed Interface Summary

**MainWindow with 4-tab interface (Race Data, Optimization, Lineups, Settings) using QTabWidget, DriverTableModel integration, and SessionManager persistence**

## Performance

- **Duration:** 2 min
- **Started:** 2026-01-29T23:02:55Z
- **Completed:** 2026-01-29T23:04:55Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Created `apps/native_mac/gui/` package with proper `__init__.py` exports
- MainWindow class with QTabWidget as central widget
- Race Data tab with QTableView displaying DriverTableModel with sample data
- Optimization, Lineups, and Settings tabs with placeholder content
- SessionManager integration for window geometry save/restore
- Tab changes dynamically update window title (e.g., "NASCAR DFS Optimizer - Race Data")
- Refactored main.py from 83 lines to 78 lines with cleaner structure

## Task Commits

Each task was committed atomically:

1. **Task 1: Create MainWindow class with tabbed interface** - `6e16540` (feat)
2. **Task 2: Integrate DriverTableModel into Race Data tab** - `6e16540` (feat - included in Task 1)
3. **Task 3: Update main.py entry point to use gui package** - `3dbb985` (refactor)

**Plan metadata:** `TBD` (docs: complete plan)

_Note: Task 2 was completed within Task 1 commit as it was part of creating the Race Data tab_

## Files Created/Modified

- `apps/native_mac/gui/__init__.py` - Package exports (MainWindow)
- `apps/native_mac/gui/main_window.py` - MainWindow class with 4-tab interface (283 lines)
- `apps/native_mac/main.py` - Refactored entry point using gui package (78 lines)

## Decisions Made

- **Package structure:** MainWindow moved to `gui/` package for clean separation; menu creation remains in `main.py` as app-level concern
- **Dependency injection:** SessionManager passed to MainWindow constructor rather than instantiated inside
- **Tab placeholders:** Other tabs (Optimization, Lineups, Settings) show QLabel placeholders until their respective plans implement them
- **Sample data:** Included 10 sample drivers for immediate visual verification of the driver table

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all implementations worked as expected.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- MainWindow foundation complete and ready for feature development
- Race Data tab ready for real data import (Plan 06-05)
- Optimization tab ready for optimization interface (Plan 06-06)
- Lineups tab ready for lineup management (Plan 06-07)
- Settings tab ready for configuration UI (Plan 06-08)

---
*Phase: 06-foundation-gui-local-optimization*
*Completed: 2026-01-29*
