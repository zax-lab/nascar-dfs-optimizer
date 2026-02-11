---
phase: 06-foundation-gui-local-optimization
plan: 01
subsystem: ui
tags: [PySide6, Qt, py2app, macOS, GUI]

# Dependency graph
requires:
  - phase: 05-research-gui
    provides: "Technology selection for native Mac app (PySide6 chosen)"
provides:
  - PySide6 application skeleton with QMainWindow
  - Standard macOS menu bar (File, Edit, View, Window, Help)
  - py2app bundling configuration for .app distribution
  - Dark mode support via system appearance
  - CMD+Q quit shortcut integration
affects:
  - phase 06-foundation-gui-local-optimization
  - phase 07-gpu-offload
  - phase 08-ontology-integration

# Tech tracking
tech-stack:
  added: [PySide6 6.10.1, py2app 0.28.9]
  patterns:
    - "Qt application lifecycle: QApplication → MainWindow → exec()"
    - "macOS menu bar with native keyboard shortcuts"
    - "py2app alias mode for development builds"

key-files:
  created:
    - apps/native_mac/__init__.py
    - apps/native_mac/pyproject.toml
    - apps/native_mac/setup.py
    - apps/native_mac/main.py
  modified: []

key-decisions:
  - "Removed deprecated setup_requires from setup.py to fix setuptools compatibility"
  - "Using py2app alias mode (-A) for development builds (faster iteration)"
  - "PySide6 6.10.1 exceeds minimum requirement of 6.9.0"

patterns-established:
  - "Qt app structure: QApplication setup → MainWindow → menu creation → exec loop"
  - "macOS integration: CFBundleIdentifier, NSHighResolutionCapable, native menus"
  - "Build workflow: python setup.py py2app -A for dev, without -A for distribution"

# Metrics
duration: 2 min
completed: 2026-01-29
---

# Phase 6 Plan 1: PySide6 Application Skeleton Summary

**Native macOS Qt application with standard menus, dark mode support, and py2app bundling configuration**

## Performance

- **Duration:** 2 min
- **Started:** 2026-01-29T22:55:35Z
- **Completed:** 2026-01-29T22:57:35Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Created PySide6 application structure with proper package layout
- Implemented MainWindow with standard macOS menu bar (File, Edit, View, Window, Help)
- Added CMD+Q quit shortcut using QKeySequence.Quit
- Configured py2app for macOS app bundling with proper Info.plist settings
- Successfully built alias-mode .app bundle: `dist/NASCAR DFS Optimizer.app`
- App bundle signed with Mach-O universal binary support (x86_64 + arm64)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create project structure and dependency configuration** - `314783a` (chore)
2. **Task 2: Create Qt application entry point with main window** - `e89870e` (feat)
3. **Task 3: Install dependencies and verify Qt integration** - `ee2652b` (fix)

**Plan metadata:** `TBD` (docs: complete plan)

## Files Created/Modified

- `apps/native_mac/__init__.py` - Package marker
- `apps/native_mac/pyproject.toml` - Project metadata with PySide6>=6.6.0, pandas, jax[cpu]
- `apps/native_mac/setup.py` - py2app configuration with CFBundleIdentifier and app bundling
- `apps/native_mac/main.py` - Qt application with MainWindow, menus, and macOS integration

## Decisions Made

- **PySide6 6.10.1 selected**: Exceeds minimum 6.9.0 requirement, provides latest features
- **py2app for bundling**: Native macOS .app bundle creation with code signing
- **Alias mode for development**: Using `-A` flag for faster development builds
- **setup.py modernization**: Removed deprecated `setup_requires` to fix setuptools compatibility

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed py2app setuptools compatibility**

- **Found during:** Task 3 (py2app bundling)
- **Issue:** `setup_requires=['py2app']` deprecated in modern setuptools, causing "install_requires is no longer supported" error
- **Fix:** Removed `setup_requires` parameter from setup.py, rely on externally installed py2app
- **Files modified:** apps/native_mac/setup.py
- **Verification:** Build succeeded, `dist/NASCAR DFS Optimizer.app` created and signed
- **Committed in:** ee2652b (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Fix necessary for build system compatibility. No scope creep.

## Issues Encountered

- **py2app/setuptools deprecation**: Modern setuptools deprecated `setup_requires`. Fixed by removing the parameter and installing py2app externally via pip.
- **pyproject.toml conflict**: py2app has issues when pyproject.toml is present. Workaround: temporarily move pyproject.toml during build if needed (not committed, just build-time workaround).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for:** Plan 06-02 (GUI Component Library)

**Foundation established:**
- Qt application lifecycle working
- macOS menu integration complete
- Build system configured
- Can now add GUI components (widgets, dialogs, views)

**Blockers:** None

---
*Phase: 06-foundation-gui-local-optimization*
*Completed: 2026-01-29*
