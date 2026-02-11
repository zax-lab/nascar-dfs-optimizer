# Phase 9: Distribution & Quality - Plan

**Created:** 2026-01-30
**Status:** Ready for execution
**Duration Estimate:** 4-6 hours

## Phase Goal

Create a reproducible .app bundle for NASCAR DFS Optimizer that can be distributed to other macOS users with code signing, comprehensive documentation, and verified functionality on clean machines.

**Decision summary for open questions:**
- **JAX bundling:** Include `jax` and `jaxlib` explicitly in `packages` list (compiled libraries need explicit inclusion)
- **Neo4j driver:** Bundle Python driver but document that Neo4j server must be running separately
- **Universal binary size:** Measure bundle size; if > 200MB, document architecture-specific builds for future consideration
- **PySide6 plugins:** Include basic image format plugins (PNG, JPEG) to ensure screenshot/image loading works

---

## Task 01: Update setup.py for Production Build

**Dependencies:** None
**Estimated Time:** 30 minutes

**Acceptance Criteria:**
- `setup.py` updated with explicit dependency list
- `--arch universal2` configured for Apple Silicon + Intel compatibility
- `NSRequiresAquaSystemAppearance=False` added for dark mode support
- `CFBundleVersion` and `CFBundleShortVersionString` set to "1.2.0"
- PySide6, JAX, pandas, numpy, and neo4j all listed in `packages`
- Development dependencies (pytest, setuptools) excluded

**Implementation Steps:**
1. Open `apps/native_mac/setup.py`
2. Update `OPTIONS` dict to match research pattern:
   - Add `packages` list with all runtime dependencies: PySide6, PySide6.QtCore, PySide6.QtWidgets, PySide6.QtGui, pandas, numpy, jax, jaxlib, neo4j
   - Add `includes` list for PySide6 submodules
   - Add `excludes` list for pytest, setuptools
   - Add `arch: "universal2"` for fat binary
   - Add `qt_plugins` with basic image formats (optional, add if images fail to load)
3. Update `plist` dict with required keys:
   - `NSRequiresAquaSystemAppearance: False`
   - `CFBundleVersion: "1.2.0"`
   - `CFBundleShortVersionString: "1.2.0"`
4. Remove `setup_requires=["py2app"]` if present (deprecated)
5. Verify all imports in `main.py` are covered in packages/includes

**Verification:**
- Read `setup.py` and confirm all changes
- Run `python setup.py --help-commands` to verify py2app recognizes options
- No syntax errors in file

---

## Task 02: Create Build Automation Script

**Dependencies:** Task 01 (setup.py updated)
**Estimated Time:** 20 minutes

**Acceptance Criteria:**
- `scripts/build.sh` created with executable permissions
- Script cleans `build/` and `dist/` directories before building
- Script calls `python setup.py py2app` with error handling
- Script verifies .app bundle was created successfully
- Script provides clear success/failure messages

**Implementation Steps:**
1. Create `apps/native_mac/scripts/` directory if it doesn't exist
2. Create `apps/native_mac/scripts/build.sh`:
   ```bash
   #!/usr/bin/env bash
   set -e  # Exit on error

   echo "Building NASCAR DFS Optimizer..."

   # Clean previous builds (required for reproducible builds)
   rm -rf build dist

   # Build with py2app
   python setup.py py2app

   # Verify bundle was created
   if [ ! -d "dist/NASCAR-DFS-Optimizer.app" ]; then
       echo "ERROR: Build failed - .app bundle not found"
       exit 1
   fi

   echo "Build complete: dist/NASCAR-DFS-Optimizer.app"
   ```
3. Make script executable: `chmod +x apps/native_mac/scripts/build.sh`
4. Test script by running it: `./scripts/build.sh`

**Verification:**
- Script runs without errors
- `dist/NASCAR-DFS-Optimizer.app` is created
- Script fails gracefully if build fails

---

## Task 03: Implement Code Signing Workflow

**Dependencies:** Task 02 (build script working)
**Estimated Time:** 30 minutes

**Acceptance Criteria:**
- App bundle signed with ad-hoc signature for personal distribution
- `codesign` command integrated into build process
- Signature verification step added to build script
- Documented that users need to control-click on first launch

**Implementation Steps:**
1. Update `scripts/build.sh` to add signing after build:
   ```bash
   # Sign the app bundle (ad-hoc signature for personal distribution)
   echo "Signing app bundle..."
   codesign --force --deep --sign - dist/NASCAR-DFS-Optimizer.app

   # Verify signature
   echo "Verifying signature..."
   codesign -vvv dist/NASCAR-DFS-Optimizer.app

   if [ $? -ne 0 ]; then
       echo "ERROR: Code signing failed"
       exit 1
   fi

   echo "Signing complete"
   ```
2. Test signing: Run updated build script
3. Verify signature manually: `codesign -dv dist/NASCAR-DFS-Optimizer.app`
4. Note: If you have a Developer ID certificate, replace `-` with `"Developer ID Application: <Your Name>"`

**Verification:**
- Build script completes without errors
- `codesign -dv` shows signature information
- Double-clicking .app shows Gatekeeper prompt (expected for ad-hoc signature)

---

## Task 04: Create Clean Machine Test Suite

**Dependencies:** None
**Estimated Time:** 45 minutes

**Acceptance Criteria:**
- Test suite created in `apps/native_mac/tests/`
- Automated tests verify build succeeds and app launches
- Manual test checklist documents full workflow verification
- Tests cover macOS 12+ compatibility (documentation)

**Implementation Steps:**

1. Create test directory: `mkdir -p apps/native_mac/tests`
2. Create `apps/native_mac/tests/test_build.py`:
   ```python
   """Test build process and app bundle integrity."""

   import subprocess
   import os
   from pathlib import Path

   def test_build_succeeds():
       """Verify py2app build completes successfully."""
       result = subprocess.run(
           ["python", "setup.py", "py2app"],
           cwd="apps/native_mac",
           capture_output=True,
           timeout=300
       )
       assert result.returncode == 0, f"Build failed: {result.stderr.decode()}"

   def test_app_bundle_exists():
       """Verify .app bundle was created."""
       app_path = Path("apps/native_mac/dist/NASCAR-DFS-Optimizer.app")
       assert app_path.exists(), "App bundle not found"

   def test_app_launches():
       """Verify app can launch without crashing."""
       # Run app in background with timeout
       result = subprocess.run(
           ["open", "-W", "apps/native_mac/dist/NASCAR-DFS-Optimizer.app"],
           capture_output=True,
           timeout=10
       )
       # open returns 0 even if app crashes, so we rely on manual testing
       assert result.returncode == 0, "Failed to launch app"
   ```

3. Create manual test checklist `apps/native_mac/tests/CLEAN_MACHINE_CHECKLIST.md`:
   ```markdown
   # Clean Machine Test Checklist

   ## Prerequisites
   - [ ] macOS 12.0 (Monterey) or later
   - [ ] No Python development environment installed
   - [ ] Downloaded .app bundle from distribution

   ## Installation Test
   - [ ] Unzip archive to Applications folder
   - [ ] Double-click to launch (Gatekeeper prompt appears)
   - [ ] Control-click → Open (first launch workaround)
   - [ ] App opens and main window appears

   ## Workflow Tests
   - [ ] Import CSV file (File > Import > From Backup)
   - [ ] Navigate to all tabs (Lineups, Optimization, Presets, Settings, Jobs, Veto Log)
   - [ ] Set constraints and click "Generate Lineups"
   - [ ] Wait for optimization to complete
   - [ ] Export lineups (File > Export > Lineups)
   - [ ] Quit app and relaunch
   - [ ] Verify settings persisted

   ## Edge Cases
   - [ ] Launch with Neo4j not running (check error message)
   - [ ] Launch without imported data (check empty state)
   - [ ] Import malformed CSV (check error handling)
   - [ ] Export to different file formats (JSON)

   ## Architecture Test (if available)
   - [ ] Test on Intel Mac (x86_64)
   - [ ] Test on Apple Silicon (arm64)
   ```

4. Install pytest if not present: `pip install pytest`

**Verification:**
- Run `pytest apps/native_mac/tests/test_build.py` - tests pass
- Manual checklist is complete and actionable

---

## Task 05: Write INSTALL.md Documentation

**Dependencies:** None
**Estimated Time:** 30 minutes

**Acceptance Criteria:**
- `apps/native_mac/docs/INSTALL.md` created
- Step-by-step installation instructions for clean macOS machine
- Prerequisites clearly documented (macOS version, Neo4j server)
- Gatekeeper workaround documented (control-click → Open)
- Neo4j setup instructions included
- Troubleshooting section for common issues

**Implementation Steps:**

1. Create `apps/native_mac/docs/` directory
2. Create `apps/native_mac/docs/INSTALL.md`:
   ```markdown
   # Installation Guide - NASCAR DFS Optimizer

   ## Prerequisites

   ### System Requirements
   - macOS 12.0 (Monterey) or later
   - Apple Silicon (M1/M2/M3) or Intel Mac
   - 500 MB free disk space
   - 8 GB RAM recommended

   ### Required Software
   - Neo4j Graph Database (version 4.4+)
     - Download from: https://neo4j.com/download/
     - Install and start Neo4j server
     - Default URL: `bolt://localhost:76874`
     - Default credentials: `neo4j` / `password`

   ## Installation

   ### Step 1: Download Application
   1. Visit [GitHub Releases](https://github.com/your-repo/releases)
   2. Download the latest `NASCAR-DFS-Optimizer-vX.X.X.zip`
   3. Unzip the archive

   ### Step 2: Install Application
   1. Drag `NASCAR-DFS-Optimizer.app` to your `Applications` folder
   2. Right-click and choose "Open" (first launch only)

   ### Step 3: First Launch
   1. Double-click `NASCAR-DFS-Optimizer.app` in Applications
   2. You may see a Gatekeeper warning: "cannot be opened because the developer cannot be verified"
   3. Click "Cancel" in the warning dialog
   4. Control-click (or right-click) the app icon again
   5. Choose "Open" from the context menu
   6. Click "Open" in the confirmation dialog
   7. The app will launch normally after this first-time setup

   **Note:** This Gatekeeper workaround is required for personal distribution. The app is safe; macOS just doesn't recognize the developer identity.

   ## Configuration

   ### Neo4j Connection
   On first launch, the app will prompt for Neo4j settings:
   - URL: `bolt://localhost:76874`
   - Username: `neo4j`
   - Password: (enter password set during Neo4j installation)

   If Neo4j is not running, you'll see an error message: "Failed to connect to Neo4j database."

   ### Importing Data
   1. Download a sample NASCAR data CSV from DraftKings
   2. Use File > Import > From Backup to load driver projections
   3. The app will parse and display driver data

   ## Troubleshooting

   ### App won't open
   - **Gatekeeper blocks launch:** Use Control-click → Open on first launch
   - **Compatibility check:** Ensure macOS 12.0 or later
   - **Corrupt download:** Re-download the zip file and verify checksum

   ### Neo4j connection fails
   - **Server not running:** Start Neo4j from Applications or Terminal
   - **Wrong credentials:** Verify username/password in Neo4j settings
   - **Port blocked:** Check firewall allows port 76874

   ### App crashes on launch
   - **Insufficient RAM:** Close other applications
   - **Corrupt preferences:** Delete `~/Library/Application Support/Zax/NASCAR DFS Optimizer`
   - **Console logs:** Open Console.app to view error messages

   ### Missing data after import
   - **Wrong format:** Ensure CSV matches DraftKings format
   - **Empty file:** Check CSV has driver data rows
   - **Parse error:** Review Console.app logs for import errors
   ```

3. Review and adjust instructions for your specific setup

**Verification:**
- Document is clear and complete
- Instructions can be followed on a clean macOS machine
- All common issues addressed

---

## Task 06: Write TROUBLESHOOTING.md Documentation

**Dependencies:** Task 05 (INSTALL.md created)
**Estimated Time:** 20 minutes

**Acceptance Criteria:**
- `apps/native_mac/docs/TROUBLESHOOTING.md` created
- Covers Gatekeeper issues, Neo4j errors, dependency problems
- Includes Console.app log viewing instructions
- Provides recovery steps for each issue

**Implementation Steps:**

1. Create `apps/native_mac/docs/TROUBLESHOOTING.md`:
   ```markdown
   # Troubleshooting - NASCAR DFS Optimizer

   ## Viewing Error Logs

   macOS applications log errors to the Console app. To view logs:

   1. Open **Console.app** (Command + Space, type "Console")
   2. In the sidebar, select your computer name
   3. In the search bar, type "NASCAR" to filter logs
   4. Look for error messages in red or yellow
   5. Copy relevant error text when reporting issues

   ## Gatekeeper Issues

   ### "App is damaged and can't be opened"
   **Cause:** macOS Gatekeeper blocking unsigned app

   **Solution:**
   1. Control-click (or right-click) the app icon
   2. Choose "Open" from the context menu
   3. Click "Open" in the confirmation dialog
   4. This only needs to be done once per download

   **Prevention:** Sign with Developer ID for public distribution (requires Apple Developer Program, $99/year)

   ## Neo4j Connection Issues

   ### "Failed to connect to Neo4j database"
   **Cause:** Neo4j server not running or unreachable

   **Solution:**
   1. Open Neo4j from Applications or run `neo4j start` in Terminal
   2. Verify server is running: Visit http://localhost:7474 in browser
   3. Check URL in app settings: `bolt://localhost:76874`
   4. Verify firewall allows port 76874

   ### "Authentication failed"
   **Cause:** Incorrect Neo4j username or password

   **Solution:**
   1. Reset Neo4j password: `neo4j-admin set-initial-password new-password`
   2. Update password in app settings (Settings tab)
   3. Default username is always `neo4j`

   ## Import Errors

   ### "CSV parse error"
   **Cause:** Incorrect CSV format or malformed file

   **Solution:**
   1. Verify CSV uses DraftKings format (headers: Name, Salary, AvgPoints, etc.)
   2. Check file encoding (UTF-8)
   3. Open CSV in text editor and look for corrupted lines
   4. Re-download from DraftKings if data looks wrong

   ### "No drivers found"
   **Cause:** Empty CSV or wrong file selected

   **Solution:**
   1. Verify CSV has data rows after header
   2. Check file path in import dialog
   3. Confirm file is not locked by another application

   ## Performance Issues

   ### App is slow or unresponsive
   **Cause:** Insufficient RAM or optimization in progress

   **Solution:**
   1. Close other applications to free RAM
   2. Check Jobs tab for optimization status
   3. Reduce number of lineups in optimization settings
   4. If using GPU, verify GPU worker is accessible

   ### Optimization never completes
   **Cause:** Infeasible constraints or network issue

   **Solution:**
   1. Review constraint panel for overly restrictive settings
   2. Check Neo4j server is responsive
   3. Verify GPU worker URL (if using GPU offload)
   4. Try with default constraints to isolate issue

   ## UI Issues

   ### Window doesn't appear
   **Cause:** App launched in background or display issue

   **Solution:**
   1. Click app icon in Dock to bring to front
   2. Check multiple desktop spaces
   3. Quit and relaunch app
   4. If persistent, delete preferences: `~/Library/Application Support/Zax/NASCAR DFS Optimizer`

   ### Dark mode not working
   **Cause:** macOS setting overrides app appearance

   **Solution:**
   1. System Preferences > General > Appearance
   2. Set to "Dark" (not "Auto")
   3. Relaunch app

   ## Crash on Launch

   **Immediate crash on double-click**
   **Possible causes:**
   - Corrupt app bundle
   - Missing system dependencies
   - Incompatible macOS version

   **Solution:**
   1. Check macOS version (requires 12.0+)
   2. Re-download app bundle
   3. View Console.app for crash details
   4. Try running from Terminal: `./dist/NASCAR-DFS-Optimizer.app/Contents/MacOS/NASCAR-DFS-Optimizer`

   ## Reporting Issues

   When reporting issues, include:
   - macOS version (Apple menu > About This Mac)
   - App version (Help > About)
   - Console.app error logs
   - Steps to reproduce the problem
   - Screenshots if applicable
   ```

2. Cross-reference with INSTALL.md to avoid duplication

**Verification:**
- Troubleshooting guide covers all common issues
- Console.app logging instructions are clear
- Solutions are actionable

---

## Task 07: Create Screenshots and Update README

**Dependencies:** None
**Estimated Time:** 30 minutes

**Acceptance Criteria:**
- 3-4 screenshots captured showing key UI screens
- Screenshots saved to `apps/native_mac/docs/screenshots/`
- README.md updated with screenshots and installation overview
- Screenshots show dark mode (test on dark mode system)

**Implementation Steps:**

1. Create screenshots directory: `mkdir -p apps/native_mac/docs/screenshots`
2. Launch app and capture screenshots:
   - **Screenshot 1:** Main window showing driver table and lineups tab
   - **Screenshot 2:** Optimization tab with constraint panel
   - **Screenshot 3:** Settings tab with Neo4j configuration
   - (Optional) Screenshot 4: Jobs tab showing optimization progress
3. Use Command+Shift+4 to capture screenshots
4. Name screenshots clearly:
   - `main-window.png`
   - `optimization-tab.png`
   - `settings-tab.png`
   - `jobs-tab.png`
5. Update `README.md` (root directory):
   - Add Installation section linking to `INSTALL.md`
   - Add Quick Start section with screenshots
   - Link to TROUBLESHOOTING.md
   - Include system requirements

6. Add to README.md:
   ```markdown
   ## Installation

   ![Main Window](apps/native_mac/docs/screenshots/main-window.png)

   The NASCAR DFS Optimizer is distributed as a macOS .app bundle. For detailed installation instructions, see [INSTALL.md](apps/native_mac/docs/INSTALL.md).

   **Quick Start:**
   1. Download the latest [release](../../releases)
   2. Unzip and drag `NASCAR-DFS-Optimizer.app` to Applications
   3. Launch and Control-click → Open on first launch
   4. Import DraftKings CSV data
   5. Set constraints and generate optimized lineups

   For troubleshooting common issues, see [TROUBLESHOOTING.md](apps/native_mac/docs/TROUBLESHOOTING.md).
   ```

**Verification:**
- Screenshots are clear and show app features
- README.md includes screenshots and installation links
- Documentation is accessible and helpful

---

## Task 08: Create CHANGELOG.md

**Dependencies:** None
**Estimated Time:** 15 minutes

**Acceptance Criteria:**
- `apps/native_mac/CHANGELOG.md` created
- Documents changes for v1.2.0 release
- Uses semantic versioning format (MAJOR.MINOR.PATCH)
- Organized by Features, Fixes, Known Issues

**Implementation Steps:**

1. Create `apps/native_mac/CHANGELOG.md`:
   ```markdown
   # Changelog

   All notable changes to NASCAR DFS Optimizer are documented in this file.

   ## [1.2.0] - 2026-01-30

   ### Added
   - macOS native app distribution (.app bundle)
   - PySide6 GUI with native macOS look and feel
   - Dark mode support (automatic)
   - Undo/redo functionality for constraint changes
   - Preset system for saving and loading constraint configurations
   - Background job management with GPU offload support
   - Export/import backup of all application data
   - Veto logging for tracking constraint violations

   ### Changed
   - Optimized driver table rendering with live preview
   - Improved constraint panel with collapsible sections
   - Enhanced optimization progress reporting
   - Better error messages for Neo4j connection failures

   ### Fixed
   - Fixed crash when importing malformed CSV files
   - Fixed settings persistence on app quit
   - Fixed keyboard shortcuts not working in some contexts

   ### Known Issues
   - First launch requires Control-click → Open (Gatekeeper limitation)
   - App requires Neo4j server to be running
   - Optimization may be slow without GPU offload

   ## [1.1.0] - 2026-01-20

   ### Added
   - Initial release with core optimization engine
   - DraftKings CSV import
   - Constraint-based lineup generation

   ## Version Format

   Versioning follows [Semantic Versioning](https://semver.org/):
   - MAJOR: Incompatible API changes
   - MINOR: Backwards-compatible functionality additions
   - PATCH: Backwards-compatible bug fixes
   ```

2. Review and adjust changelog based on actual features implemented

**Verification:**
- Changelog is complete and accurate
- Version numbers are consistent
- Format is clear and readable

---

## Task 09: Perform End-to-End Clean Machine Test

**Dependencies:** Tasks 01-08 (build, docs complete)
**Estimated Time:** 60 minutes

**Acceptance Criteria:**
- Clean macOS machine test completed
- Full workflow verified (launch, import, optimize, export)
- All tabs and features tested manually
- Console logs reviewed for errors
- Bundle size measured and documented
- Test checklist signed off

**Implementation Steps:**

1. **Prepare Clean Test Environment:**
   - Use a macOS 12+ test machine (VM or spare Mac)
   - Ensure no Python dev environment installed
   - Ensure Neo4j is installed and running

2. **Build Distribution Bundle:**
   ```bash
   cd apps/native_mac
   ./scripts/build.sh
   ```

3. **Create Distribution Archive:**
   ```bash
   cd dist
   zip -r NASCAR-DFS-Optimizer-1.2.0.zip NASCAR-DFS-Optimizer.app
   ls -lh NASCAR-DFS-Optimizer-1.2.0.zip
   ```

4. **Document Bundle Size:**
   - Record size in MB
   - If > 200MB, add note to INSTALL.md about architecture-specific builds

5. **Install and Test:**
   - Transfer zip file to test machine
   - Unzip and install to Applications folder
   - Perform first launch (Control-click → Open workaround)
   - Verify main window opens

6. **Run Manual Test Checklist:**
   - Follow `tests/CLEAN_MACHINE_CHECKLIST.md` line by line
   - Test all tabs: Lineups, Optimization, Presets, Settings, Jobs, Veto Log
   - Test file import/export functionality
   - Test keyboard shortcuts
   - Test settings persistence (quit and relaunch)

7. **Verify Critical Path:**
   - Import sample CSV data
   - Set constraints
   - Click "Generate Lineups"
   - Wait for optimization to complete
   - Export lineups to JSON
   - Verify exported data is correct

8. **Test Error Scenarios:**
   - Launch with Neo4j stopped (check error message)
   - Import empty CSV (check error handling)
   - Import malformed CSV (check error message)
   - Try to optimize without drivers (check validation)

9. **Review Console Logs:**
   - Open Console.app on test machine
   - Filter for "NASCAR" or app name
   - Review all error messages
   - Fix any critical issues found

10. **Document Test Results:**
    - Update `tests/CLEAN_MACHINE_CHECKLIST.md` with test date and results
    - Note any issues found and their resolution
    - Record bundle size and performance observations

**Verification:**
- All checklist items completed
- No critical errors in Console.app
- App functions smoothly on clean machine
- Bundle size is reasonable (< 200MB ideal, < 500MB acceptable)

---

## Task 10: Create GitHub Release with Signed .app Bundle

**Dependencies:** Task 09 (clean machine test passed)
**Estimated Time:** 20 minutes

**Acceptance Criteria:**
- Git tag `v1.2.0` created and pushed
- GitHub release created with tagged version
- `NASCAR-DFS-Optimizer-1.2.0.zip` attached as release asset
- Release notes populated from CHANGELOG.md
- Release marked as "latest" (not pre-release)

**Implementation Steps:**

1. **Create and Push Git Tag:**
   ```bash
   # Ensure all changes are committed
   git status

   # Create annotated tag
   git tag -a v1.2.0 -m "Release v1.2.0 - macOS distribution with code signing"

   # Push tag to remote
   git push origin v1.2.0
   ```

2. **Prepare Release Notes:**
   - Copy relevant section from `CHANGELOG.md`
   - Format with Markdown headers
   - Include installation instructions summary
   - Add known issues note

   Example release notes:
   ```markdown
   ## NASCAR DFS Optimizer v1.2.0

   First macOS native distribution with code signing.

   ### Installation
   1. Download `NASCAR-DFS-Optimizer-1.2.0.zip` below
   2. Unzip and drag to Applications folder
   3. Control-click → Open on first launch (Gatekeeper workaround)

   See [INSTALL.md](apps/native_mac/docs/INSTALL.md) for detailed instructions.

   ### What's New
   - PySide6 GUI with native macOS look and feel
   - Dark mode support
   - Undo/redo for constraint changes
   - Preset system for saving configurations
   - Background job management with GPU offload
   - Export/import backup of all data

   ### Known Issues
   - Requires Neo4j server to be running
   - First launch requires Control-click workaround
   - Optimization may be slow without GPU offload

   For troubleshooting, see [TROUBLESHOOTING.md](apps/native_mac/docs/TROUBLESHOOTING.md).
   ```

3. **Create GitHub Release (Web UI):**
   - Go to GitHub repository → Releases
   - Click "Draft a new release"
   - Choose tag: `v1.2.0`
   - Release title: `NASCAR DFS Optimizer v1.2.0`
   - Paste release notes
   - Attach `dist/NASCAR-DFS-Optimizer-1.2.0.zip` as binary asset
   - Uncheck "Set as a pre-release"
   - Check "Set as the latest release"
   - Click "Publish release"

   OR use GitHub CLI:
   ```bash
   gh release create v1.2.0 \
     --title "NASCAR DFS Optimizer v1.2.0" \
     --notes-file RELEASE_NOTS.md \
     dist/NASCAR-DFS-Optimizer-1.2.0.zip
   ```

4. **Verify Release:**
   - Visit GitHub Releases page
   - Confirm release is visible
   - Download zip and verify it extracts correctly
   - Confirm release notes are formatted properly

5. **Update Documentation Links:**
   - Update README.md to link to latest release
   - Add "Download" badge if desired

**Verification:**
- Release is publicly accessible
- Zip file downloads and extracts correctly
- Release notes are clear and helpful
- Version tag is correct

---

## Verification Criteria

Phase 9 is complete when:

- [ ] **Build reproducibility:** `setup.py` updated with explicit dependencies and universal binary support
- [ ] **Build automation:** `scripts/build.sh` creates signed .app bundle successfully
- [ ] **Code signing:** App bundle signed and verified with `codesign`
- [ ] **Test coverage:** Clean machine test suite created and executed
- [ ] **Documentation:** INSTALL.md and TROUBLESHOOTING.md provide clear guidance
- [ ] **Screenshots:** README.md updated with 3-4 screenshots of key features
- [ ] **Changelog:** CHANGELOG.md documents all changes for v1.2.0
- [ ] **Clean machine verified:** Full workflow tested on macOS 12+ with no dev tools
- [ ] **Bundle size:** Measured and documented (< 200MB ideal)
- [ ] **GitHub release:** v1.2.0 published with signed .app bundle and release notes
- [ ] **Gatekeeper documented:** Control-click → Open workaround clearly explained
- [ ] **Neo4j documented:** Server requirement and connection troubleshooting covered

---

## Phase Boundaries

### What's In Scope
- Creating reproducible .app bundle with py2app
- Ad-hoc code signing for personal distribution
- Clean machine testing on macOS 12+
- Documentation (INSTALL.md, TROUBLESHOOTING.md, CHANGELOG.md, screenshots)
- GitHub Release creation with versioned assets

### What's Out of Scope (Deferred to Future Phases)
- Automated CI/CD pipeline for builds and releases
- Notarization for Mac App Store distribution
- Windows distribution (PyInstaller or similar)
- Auto-update mechanism
- Docker containerization
- Developer Program enrollment ($99/year) for public distribution without Gatekeeper warnings

---

## Success Metrics

- **Build success rate:** 100% of builds complete without errors
- **Install success rate:** Clean machine installs app and launches on first try
- **Test coverage:** All critical path workflows tested and passing
- **Documentation quality:** Users can install and troubleshoot without asking for help
- **Distribution:** GitHub release published with working .app bundle
- **User experience:** "First 5 minutes" experience is smooth (launch, import, optimize, export)

---

## Notes and Considerations

1. **Architecture Testing:** If possible, test on both Intel and Apple Silicon Macs to verify universal binary works correctly.

2. **Bundle Size Monitoring:** If bundle size exceeds 200MB, consider offering architecture-specific builds (arm64 only for M1/M2/M3 users).

3. **PySide6 Plugins:** If image loading fails in tests, add `qt_plugins` option to setup.py:
   ```python
   "qt_plugins": ["imageformats"],  # Include PNG, JPEG, etc.
   ```

4. **JAX Compatibility:** If optimization crashes with JAX import errors, may need to include jaxlib explicitly in packages and ensure platform-specific binaries are bundled.

5. **Gatekeeper Education:** Emphasize in documentation that the Control-click → Open workaround is a macOS security feature for personal distribution, not a bug.

---

*Phase: 09-distribution-quality*
*Plan created: 2026-01-30*
*Ready for execution*
