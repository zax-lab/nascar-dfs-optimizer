# Clean Machine Test Checklist

Use this checklist when testing the .app bundle on a clean macOS machine (no Python dev environment, fresh OS install).

**Test Date:** ________________________
**Tester Name:** ________________________
**macOS Version:** ________________________
**Architecture:** [ ] Intel [ ] Apple Silicon

---

## Prerequisites

Before testing, ensure:
- [ ] macOS 12.0 (Monterey) or later installed
- [ ] No Python development environment installed
- [ ] Neo4j 4.4+ installed and running
- [ ] Downloaded `NASCAR-DFS-Optimizer-vX.X.X.zip` from distribution

---

## Installation Test

### Download & Install
- [ ] Downloaded zip archive from GitHub Releases
- [ ] Verified zip file size (check against build size)
- [ ] Unzipped archive successfully
- [ ] Dragged `NASCAR-DFS-Optimizer.app` to `/Applications` folder
- [ ] App appears in Applications folder

### First Launch
- [ ] Double-clicked app icon to launch
- [ ] Gatekeeper warning appeared: "cannot be opened because the developer cannot be verified"
- [ ] Clicked "Cancel" in warning dialog
- [ ] Control-clicked (or right-clicked) app icon again
- [ ] Selected "Open" from context menu
- [ ] Clicked "Open" in confirmation dialog
- [ ] App launched successfully
- [ ] Main window appeared on screen

---

## Workflow Tests

### Tab Navigation
- [ ] Lineups tab opened successfully
- [ ] Optimization tab opened successfully
- [ ] Presets tab opened successfully
- [ ] Settings tab opened successfully
- [ ] Jobs tab opened successfully
- [ ] Veto Log tab opened successfully

### Import Data
- [ ] Clicked File > Import > From Backup
- [ ] Selected sample DraftKings CSV file
- [ ] CSV file imported without errors
- [ ] Driver table populated with data
- [ ] Driver projections displayed correctly
- [ ] Race information shown in UI

### Set Constraints & Optimize
- [ ] Switched to Optimization tab
- [ ] Constraint panel displayed all constraint groups
- [ ] Adjusted salary cap value
- [ ] Selected/deselected drivers in driver table
- [ ] Clicked "Generate Lineups" button
- [ ] Optimization job appeared in Jobs tab
- [ ] Progress indicator showed optimization progress
- [ ] Optimization completed successfully
- [ ] Lineups appeared in Lineups tab

### Export Data
- [ ] Clicked File > Export > Lineups
- [ ] Saved to default location (Downloads folder)
- [ ] Export completed without errors
- [ ] Verified exported JSON file contains lineups
- [ ] Alternative: Exported All Data (File > Export > All Data)

### Settings Persistence
- [ ] Modified settings in Settings tab
- [ ] Changed Neo4j connection settings
- [ ] Quit app (Cmd+Q or File > Exit)
- [ ] Relaunched app
- [ ] Settings were preserved across restart
- [ ] Previous lineups still visible

---

## Edge Cases

### Error Scenarios
- [ ] **Neo4j not running:** Stopped Neo4j server and launched app → Error message shown correctly
- [ ] **Empty data import:** Attempted to import empty CSV → Error message shown, no crash
- [ ] **Malformed CSV:** Imported corrupted CSV → Parse error displayed, graceful handling
- [ ] **No drivers selected:** Clicked optimize with 0 drivers → Validation error shown

### UI Interactions
- [ ] **Keyboard shortcuts:** Tested Cmd+Z (undo), Cmd+Shift+Z (redo), Cmd+Q (quit)
- [ ] **Window management:** Minimized and restored window
- [ ] **Dock interaction:** Clicked app icon in Dock (brought to front)
- [ ] **Menu bar:** Tested File, Edit, View, Window, Help menus

---

## Performance

### Response Times
- [ ] App launched within 5 seconds of double-click
- [ ] CSV import completed within 3 seconds (for 100 driver file)
- [ ] Tab switching was smooth (< 0.5 seconds)
- [ ] Optimization progress updated in real-time

### Resource Usage
- [ ] Checked Activity Monitor during optimization
- [ ] RAM usage reasonable (under 2GB for typical use)
- [ ] CPU usage during optimization (note: ___%)
- [ ] No memory leaks observed after extended use (30+ minutes)

---

## Architecture Testing (if available)

### Apple Silicon (M1/M2/M3)
- [ ] App launches natively (not via Rosetta)
- [ ] No "translated" warning in Console.app
- [ ] Performance is acceptable

### Intel (x86_64)
- [ ] App launches without compatibility warnings
- [ ] Performance is acceptable
- [ ] No architecture-specific errors in Console.app

---

## Console Logs Review

Open **Console.app** and check for errors:

### Critical Errors
- [ ] No "ModuleNotFoundError" errors
- [ ] No "ImportError" for JAX or PySide6
- [ ] No crash logs or segmentation faults
- [ ] No Neo4j connection timeout errors (if server running)

### Warnings (acceptable)
- [ ] Gatekeeper warning on first launch (expected)
- [ ] Info messages about app startup (acceptable)
- [ ] Non-critical warnings noted below

---

## Known Issues Found

Document any issues discovered during testing:

1. **Issue:** ________________________________________________________
   **Severity:** [ ] Critical [ ] Major [ ] Minor
   **Reproduce steps:** ________________________________________________________
   **Workaround:** ________________________________________________________

2. **Issue:** ________________________________________________________
   **Severity:** [ ] Critical [ ] Major [ ] Minor
   **Reproduce steps:** ________________________________________________________
   **Workaround:** ________________________________________________________

3. **Issue:** ________________________________________________________
   **Severity:** [ ] Critical [ ] Major [ ] Minor
   **Reproduce steps:** ________________________________________________________
   **Workaround:** ________________________________________________________

---

## Test Result

**Overall Status:** [ ] PASSED [ ] FAILED

**Comments:** ___________________________________________________________________

**Bundle Size Tested:** _______ MB

**Recommendations for v1.2.1:**
1. ___________________________________________________________________
2. ___________________________________________________________________
3. ___________________________________________________________________

---

*Checklist created for NASCAR DFS Optimizer v1.2.0*
*Last updated: 2026-01-30*
