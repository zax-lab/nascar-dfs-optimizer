---
phase: 06-foundation-gui-local-optimization
plan: 08
subsystem: ui

tags: [pyside6, csv, draftkings, macos, file-association]

# Dependency graph
requires:
  - phase: 06-05
    provides: CSV import infrastructure via DataController
  - phase: 06-07
    provides: OptimizationTab generating lineups to display

provides:
  - DraftKings CSV export in exact upload format
  - CSV file association for double-click open
  - LineupsTab with export/save/load functionality
  - Drag-and-drop CSV import

affects:
  - Phase 06-09 (if exists)
  - User workflow: export lineups directly to DraftKings

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "QEvent.FileOpen for macOS file association"
    - "UTF-8 with BOM for Excel compatibility"
    - "Drag-and-drop with QDragEnterEvent/QDropEvent"

key-files:
  created:
    - apps/native_mac/gui/views/lineups_tab.py
    - apps/native_mac/Info.plist
  modified:
    - apps/native_mac/gui/controllers/data_controller.py
    - apps/native_mac/gui/models/lineup_model.py
    - apps/native_mac/gui/views/driver_table.py
    - apps/native_mac/gui/main_window.py
    - apps/native_mac/main.py

key-decisions:
  - "DraftKings format: Entry ID + Driver 1-6 columns, UTF-8 with BOM"
  - "File association: Alternate handler rank (not default) to avoid conflicts"
  - "Round-trip compatibility: export_drivers_to_csv for data portability"

patterns-established:
  - "CSV format auto-detection via header analysis"
  - "MainApplication subclass for app-level event handling"
  - "Drag-and-drop support in table views for file import"

# Metrics
duration: 5min
completed: 2026-01-29
---

# Phase 6 Plan 8: CSV Export and File Association Summary

**DraftKings CSV export in exact upload format with macOS file association for .csv files**

## Performance

- **Duration:** 5 min
- **Started:** 2026-01-29T23:18:41Z
- **Completed:** 2026-01-29T23:23:07Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- DraftKings CSV export with Entry ID + Driver 1-6 columns
- CSV file association for double-click to open in app
- LineupsTab with Export to DraftKings, Save Lineups, Load Saved buttons
- Drag-and-drop CSV import support in DriverTableView
- Round-trip driver data export for data portability
- Auto-detection of CSV format (driver data vs lineup export)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add export_lineups_to_csv method to DataController** - `475431d` (feat)
2. **Task 2: Create LineupsTab with table view and export functionality** - `502ceba` (feat)
3. **Task 3: Implement CSV file association for double-click to open** - `6a927bc` (feat)

**Plan metadata:** [pending] (docs: complete plan)

## Files Created/Modified

- `apps/native_mac/gui/controllers/data_controller.py` - Added export_lineups_to_csv(), export_drivers_to_csv(), detect_csv_format(), _import_lineup_csv()
- `apps/native_mac/gui/models/lineup_model.py` - Added get_all_lineups() method
- `apps/native_mac/gui/views/lineups_tab.py` - New LineupsTab widget with export/save/load functionality
- `apps/native_mac/gui/views/driver_table.py` - Added drag-and-drop support for CSV files
- `apps/native_mac/gui/main_window.py` - Integrated LineupsTab, added on_file_opened() handler
- `apps/native_mac/main.py` - Created MainApplication subclass with QEvent.FileOpen handling
- `apps/native_mac/Info.plist` - macOS bundle configuration with CFBundleDocumentTypes for CSV association

## Decisions Made

- **DraftKings format**: Entry ID column with sequential numbers (1, 2, 3...) followed by Driver 1-6 columns
- **Encoding**: UTF-8 with BOM (utf-8-sig) for Excel compatibility
- **File association**: LSHandlerRank set to "Alternate" to avoid conflicts with default CSV handlers
- **Round-trip support**: export_drivers_to_csv() enables saving and re-importing driver data
- **Format auto-detection**: detect_csv_format() checks headers to distinguish driver data from lineup exports

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## Next Phase Readiness

- CSV export and file association complete
- Users can export lineups directly to DraftKings upload format
- Double-clicking .csv files opens them in the application
- Drag-and-drop provides additional import convenience
- Ready for Phase 6 completion or transition to Phase 7

---
*Phase: 06-foundation-gui-local-optimization*
*Completed: 2026-01-29*
