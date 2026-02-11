---
phase: 08-workflow-accelerators
plan: 04
subsystem: ui
tags: [pyside6, qt, qsplitter, debounce, live-preview, optimization]

requires:
  - phase: 08-workflow-accelerators
    provides: PresetManager (08-01), UndoManager (08-02), ShortcutManager (08-03)
  - phase: 07-background-jobs-gpu-offload
    provides: JobManager with background job queue

provides:
  - SplitEditorTab with QSplitter layout for split-pane editing
  - LivePreview widget for real-time lineup display
  - Debounced optimization trigger (300ms default) on constraint changes
  - Real-time mode toggle for immediate optimization
  - Splitter state persistence via QSettings
  - Settings integration for debounce configuration
  - Menu integration: toggle split view (Ctrl+\), focus shortcuts (Ctrl+1/2/3)

affects:
  - User workflow for rapid constraint iteration
  - Power-user efficiency features

key-files:
  created:
    - apps/native_mac/gui/views/split_editor_tab.py - SplitEditorTab with QSplitter layout
    - apps/native_mac/gui/widgets/live_preview.py - LivePreview widget for lineup display
  modified:
    - apps/native_mac/gui/views/settings_tab.py - Live Optimization settings section
    - apps/native_mac/gui/main_window.py - SplitEditorTab integration and menu wiring

key-decisions:
  - Use nested QSplitter (horizontal main + vertical right) for flexible pane layout
  - QSettings with saveState/restoreState for binary splitter state persistence
  - QTimer.singleShot pattern for debounced constraint change handling
  - Debounced save timer (500ms) for splitter state persistence
  - Job cancellation on new constraint change before previous completes
  - Real-time mode toggle for power users who want immediate updates

patterns-established:
  - "SplitEditorTab pattern: Separate tab for power-user split-view editing"
  - "Debounce timer pattern: stop() then start() with singleShot for restart behavior"
  - "Signal disconnection: Always try/except disconnect to handle partial connections"
  - "Job tracking: Track pending_job_id to cancel obsolete jobs on constraint changes"

duration: 2min
completed: 2026-01-30
---

# Phase 8 Plan 4: Split-View Editor Summary

**Split-view editor with QSplitter layout providing iTerm/VSCode-style draggable panes, debounced live optimization, and real-time lineup preview updates for rapid constraint iteration.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-01-30T18:50:36Z
- **Completed:** 2026-01-30T18:53:21Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- **SplitEditorTab** with nested QSplitter layout (horizontal main splitter + vertical right splitter)
- **LivePreview widget** showing compact lineup table with status and progress indicators
- **Debounced optimization trigger** (300ms default) with QTimer.singleShot restart pattern
- **Real-time mode toggle** for immediate optimization without debouncing
- **Splitter state persistence** via QSettings with debounced save (500ms)
- **Settings integration** for debounce delay (100-2000ms) and mode toggles
- **Menu integration** for Toggle Split View (Ctrl+\) and focus shortcuts (Ctrl+1/2/3)
- **Job cancellation** on new constraint changes before previous optimization completes
- **Preset integration** with dropdown selector and quick-apply recent preset buttons

## Task Commits

Each task was committed atomically:

1. **Task 1: Create SplitEditorTab with QSplitter layout** - `1b3ea04` (feat)
2. **Task 2: Create LivePreview widget and settings integration** - `7521ad7` (feat)
3. **Task 3: Wire with JobManager and PresetManager** - `33668cb` (feat)

**Plan metadata:** TBD (docs: complete plan)

## Files Created/Modified

**Created:**
- `apps/native_mac/gui/views/split_editor_tab.py` (487 lines) - SplitEditorTab with QSplitter layout, constraint panel, live preview, debounce timer, splitter state persistence, race selector, preset integration
- `apps/native_mac/gui/widgets/live_preview.py` (177 lines) - LivePreview widget with lineup table, status label, progress bar, stats footer

**Modified:**
- `apps/native_mac/gui/views/settings_tab.py` - Added Live Optimization section with enable toggle, debounce delay spinbox, real-time mode checkbox
- `apps/native_mac/gui/main_window.py` - Added SplitEditorTab integration, menu action handlers for toggle_split and focus commands, JobManager and PresetManager wiring

## Decisions Made

- **Nested QSplitter layout** - Horizontal main splitter divides left/right, vertical right splitter divides preview/logs for maximum flexibility
- **QSettings binary state** - Using saveState/restoreState handles binary QByteArray properly vs JSON
- **Debounced save timer** - 500ms debounce on splitterMoved prevents excessive settings writes during dragging
- **Job cancellation pattern** - Cancel pending_job_id before submitting new job to avoid queue buildup
- **Separate tab approach** - SplitEditorTab is a separate tab alongside OptimizationTab, not a replacement, allowing user choice

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all components integrated successfully.

## Verification

```bash
# Syntax validation
python3 -c "import ast; [ast.parse(open(f).read()) for f in [
    'apps/native_mac/gui/views/split_editor_tab.py',
    'apps/native_mac/gui/widgets/live_preview.py',
    'apps/native_mac/gui/views/settings_tab.py',
    'apps/native_mac/gui/main_window.py'
]]; print('All files valid')"

# Structure verification
python3 -c "
from apps.native_mac.gui.views.split_editor_tab import SplitEditorTab
from apps.native_mac.gui.widgets.live_preview import LivePreview
assert hasattr(SplitEditorTab, 'main_splitter')
assert hasattr(SplitEditorTab, 'live_preview')
assert hasattr(LivePreview, 'update_lineups')
print('Structure OK')
"
```

## Next Phase Readiness

- Split-view editor complete and integrated with JobManager/PresetManager
- Pattern established for debounced optimization triggers
- Ready for Phase 8 Plan 5: Kernel Veto Log Viewer (will populate veto log pane in split editor)
- Ready for Phase 8 Plan 6: Settings Backup/Export (splitter state will be included)

---
*Phase: 08-workflow-accelerators*
*Completed: 2026-01-30*
