---
phase: 08-workflow-accelerators
plan: 01
subsystem: ui
tags: [pyside6, qt, sqlite, json, presets, constraints]

requires:
  - phase: 06-foundation-gui-local-optimization
    provides: MainWindow, OptimizationTab, ConstraintPanel
  - phase: 07-background-jobs-gpu-offload
    provides: JobManager integration patterns

provides:
  - PresetManager class with SQLite JSON storage for constraint presets
  - PresetsTab UI for browsing, filtering, and managing presets
  - Global and race-specific preset scoping
  - Recent presets quick-access functionality
  - Import/export to JSON for preset sharing
  - Integration between PresetsTab and ConstraintPanel

affects:
  - Phase 8 other plans (undo/redo, shortcuts, split-view)
  - User workflow for constraint configuration
  - Power-user efficiency features

tech-stack:
  added: []
  patterns:
    - "Qt Model/View with QAbstractTableModel for preset lists"
    - "SQLite JSON columns for flexible config storage"
    - "Signal/slot pattern for cross-tab communication"
    - "Context manager pattern for database connections"

key-files:
  created:
    - apps/native_mac/persistence/preset_manager.py - PresetManager with full CRUD operations
    - apps/native_mac/gui/views/presets_tab.py - PresetsTab UI with filters and details panel
  modified:
    - apps/native_mac/gui/widgets/constraint_panel.py - Updated to use PresetManager
    - apps/native_mac/gui/views/optimization_tab.py - Accepts and passes preset_manager
    - apps/native_mac/gui/main_window.py - Creates PresetsTab, set_preset_manager method
    - apps/native_mac/main.py - Creates PresetManager, wires signals

key-decisions:
  - "Use SQLite JSON columns for config storage - flexible schema with version tracking"
  - "Preset name is UNIQUE constraint - prevents duplicates, enables UPSERT"
  - "Global vs race-specific scoping via boolean + nullable race_type/track_name"
  - "Recent presets tracked in separate table with usage_count aggregation"
  - "PresetManager shares database file with DatabaseManager - single SQLite file"
  - "PresetsTab placed between Optimization and Lineups tabs - logical workflow order"

patterns-established:
  - "PresetManager: Separate manager class for feature-specific persistence"
  - "Quick-access row: Horizontal chips for recent items with click handlers"
  - "Filter proxy pattern: Multiple filters applied sequentially (scope, search, race)"
  - "Setter injection: MainWindow.set_*_manager() pattern for post-creation wiring"

duration: 8min
completed: 2026-01-30
---

# Phase 8 Plan 1: Constraint Presets Summary

**PresetManager with SQLite JSON storage, PresetsTab UI, and full integration with ConstraintPanel for saving/loading constraint configurations with global and race-specific scoping.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-01-30T18:38:25Z
- **Completed:** 2026-01-30T18:46:25Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- **PresetManager class** with full CRUD operations for constraint presets using SQLite JSON columns
- **Global and race-specific preset scoping** - presets can be available everywhere or filtered by race type/track
- **Recent presets quick-access** - horizontal row of clickable chips showing last 5 applied presets
- **PresetsTab UI** with split-view layout: filterable preset list on left, details panel on right
- **Import/export to JSON** - share presets as portable JSON files
- **Full integration** - PresetsTab loads presets into ConstraintPanel via signal/slot connection
- **Usage tracking** - usage_count incremented on load, recent_presets table tracks application history

## Task Commits

Each task was committed atomically:

1. **Task 1: Create PresetManager** - `ca3ef6d` (feat)
2. **Task 2: Create PresetsTab UI** - `2d39ba5` (feat)
3. **Task 3: Integrate with ConstraintPanel and MainWindow** - `955a3fe` (feat)

**Plan metadata:** `TBD` (docs: complete plan)

## Files Created/Modified

**Created:**
- `apps/native_mac/persistence/preset_manager.py` (548 lines) - PresetManager with save/load/list operations, SQLite JSON storage, global/race-specific scoping, recent presets tracking, import/export to JSON
- `apps/native_mac/gui/views/presets_tab.py` (736 lines) - PresetsTab UI with split view, QAbstractTableModel, filter controls, recent presets row, import/export buttons

**Modified:**
- `apps/native_mac/gui/widgets/constraint_panel.py` - Changed from db_manager to preset_manager, added preset_applied signal, updated save/load methods to use PresetManager
- `apps/native_mac/gui/views/optimization_tab.py` - Added preset_manager parameter, passes it to ConstraintPanel
- `apps/native_mac/gui/main_window.py` - Added PresetsTab between Optimization and Lineups, added set_preset_manager() method, updated tab indices
- `apps/native_mac/main.py` - Creates PresetManager, passes to MainWindow, wires PresetsTab.preset_loaded to ConstraintPanel.set_constraints

## Decisions Made

- **SQLite JSON columns** for config storage - provides flexibility with schema versioning via _version field in JSON
- **UNIQUE constraint on preset name** - prevents duplicate names, enables UPSERT behavior for updates
- **Separate recent_presets table** - decouples recent tracking from preset data, allows unlimited history
- **Single database file** - PresetManager uses same SQLite file as DatabaseManager, no separate connection needed
- **Quick-access chips as custom QWidget** - RecentPresetButton provides visual hierarchy with name, scope indicator, and usage count
- **Setter injection pattern** - Following JobManager pattern with set_preset_manager() called after MainWindow creation

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

**SQLite UNIQUE constraint missing:** Initial schema didn't have UNIQUE constraint on name column, causing ON CONFLICT clause to fail. **Fixed:** Added UNIQUE constraint to schema initialization.

**Type annotation for cursor.lastrowid:** Function return types needed to be Optional[int] since cursor.lastrowid can be None. **Fixed:** Updated type hints in save_preset and import_preset_from_json methods.

## Verification

```bash
# PresetManager functionality
python -c "from apps.native_mac.persistence.preset_manager import PresetManager; pm = PresetManager('test.db'); pid = pm.save_preset('Test', {'salary_cap': 50000}, is_global=True); loaded = pm.load_preset(pid); assert loaded['config']['salary_cap'] == 50000; print('OK')"

# File syntax validation
python -c "import ast; [ast.parse(open(f).read()) for f in ['apps/native_mac/persistence/preset_manager.py', 'apps/native_mac/gui/views/presets_tab.py', 'apps/native_mac/gui/widgets/constraint_panel.py', 'apps/native_mac/gui/main_window.py', 'apps/native_mac/main.py']]; print('All files valid')"
```

## Next Phase Readiness

- Constraint preset system is complete and integrated
- Pattern established for persistence managers (separate classes with setter injection)
- UI pattern for quick-access chips established
- Ready for Phase 8 Plan 2: Undo/Redo System (UndoManager can use similar patterns)

---
*Phase: 08-workflow-accelerators*
*Completed: 2026-01-30*
