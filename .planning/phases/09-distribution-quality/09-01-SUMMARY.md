---
phase: 09-distribution-quality
plan: 01
subsystem: distribution
tags: [py2app, code-signing, macOS, build-automation, changelog]

# Dependency graph
requires:
  - phase: 08-workflow-accelerators
    provides: "Complete native Mac app with all features (GUI, jobs, GPU offload, shortcuts, presets)"
provides:
  - Build automation script (scripts/build.sh) with clean state and code signing
  - Updated setup.py with explicit dependencies and version 1.2.0
  - Version synchronization (version.py updated to 1.2.0)
  - Comprehensive CHANGELOG.md documenting all v1.2.0 features
affects:
  - Phase 09: Distribution & Quality (subsequent plans for documentation and testing)
  - Distribution workflow for GitHub Releases and clean machine testing

# Tech tracking
tech-stack:
  added: [py2app 0.28.9, codesign (macOS system tool)]
  patterns:
    - "Build automation: clean build → py2app bundle → code sign → verify"
    - "Ad-hoc signing for personal distribution (codesign --force --deep --sign -)"
    - "pyproject.toml workaround for py2app compatibility (Phase 6 pattern)"

key-files:
  created:
    - scripts/build.sh (build automation with error handling and verification)
    - CHANGELOG.md (comprehensive release notes for v1.2.0)
  modified:
    - apps/native_mac/version.py (VERSION updated to 1.2.0)
    - apps/native_mac/setup.py (verified all dependencies listed correctly)
    - apps/native_mac/pyproject.toml (version synchronized to 1.2.0, dependencies updated)

key-decisions:
  - "Python 3.12.7 used for building due to py2app 0.28.9 incompatibility with Python 3.14.2"
  - "Ad-hoc signing for personal distribution (no Apple Developer Program required)"
  - "pyproject.toml temporarily moved during build (established Phase 6 workaround)"

patterns-established:
  - "Build script pattern: clean → build → verify → sign → verify signature"
  - "Version synchronization: version.py → setup.py CFBundleVersion → CHANGELOG.md"
  - "Error handling: set -e for exit on error, verify each build stage"

# Metrics
duration: 7 min
completed: 2026-01-30
---

# Phase 9 Plan 1: Build Automation & Code Signing Summary

**Reproducible build automation with ad-hoc code signing and comprehensive v1.2.0 changelog documentation**

## Performance

- **Duration:** 7 min
- **Started:** 2026-01-30T20:40:09Z
- **Completed:** 2026-01-30T20:47:33Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Created build automation script with clean state handling, py2app bundling, and code signing
- Successfully built signed .app bundle for macOS universal binary (Apple Silicon + Intel)
- Synchronized version numbers across version.py, setup.py, and CHANGELOG.md (1.2.0)
- Documented all v1.2.0 features from Phases 6-8 in comprehensive changelog
- Verified build script creates valid signed app bundle with ad-hoc signature

## Task Commits

Each task was committed atomically:

1. **Task 1: Create build script with clean build, py2app build, and code signing** - `8b19972` (chore)
2. **Task 2: Update setup.py with explicit dependencies and verify compatibility** - `cdc54b1` (chore)
3. **Task 3: Create CHANGELOG.md with v1.2.0 release notes** - `d38cbe8` (chore)

**Plan metadata:** TBD (docs: complete plan)

## Files Created/Modified

- `scripts/build.sh` - Build automation with clean state, py2app bundling, ad-hoc signing, verification
- `CHANGELOG.md` - Comprehensive changelog documenting v1.2.0 features (Added, Fixed, Technical sections)
- `apps/native_mac/version.py` - Updated VERSION to 1.2.0, VERSION_NAME to v1.2.0, copyright year to 2026
- `apps/native_mac/setup.py` - Verified correct configuration (dependencies, universal2 arch, dark mode support)
- `apps/native_mac/pyproject.toml` - Synchronized to 1.2.0, updated dependencies and build-system

## Decisions Made

- **Python 3.12.7 for building**: py2app 0.28.9 is incompatible with Python 3.14.2 due to IndentationError in build_app.py. Used Python 3.12.7 with compatible setuptools version.
- **Ad-hoc signing for personal distribution**: Used codesign --force --deep --sign - for ad-hoc signature, avoiding Apple Developer Program ($99/year) for personal use.
- **pyproject.toml workaround**: Temporarily renamed pyproject.toml during build (Phase 6 established pattern) because py2app has issues with pyproject.toml presence.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed Python 3.14.2 incompatibility with py2app**

- **Found during:** Task 1 (build script execution)
- **Issue:** py2app 0.28.9 has IndentationError in build_app.py when run with Python 3.14.2. The py2app package hasn't been updated for Python 3.14 yet.
- **Fix:** Used Python 3.12.7 for building. Installed all dependencies (py2app, PySide6, pandas, numpy, jax, jaxlib, neo4j) for Python 3.12.7 separately. Updated build script to use Python 3.12.7 via BUILD_PYTHON variable.
- **Files modified:** scripts/build.sh
- **Verification:** Build completed successfully, .app bundle created and signed
- **Committed in:** 8b19972 (Task 1 commit)

**2. [Rule 3 - Blocking] Handled pyproject.toml conflict with py2app**

- **Found during:** Task 1 (build script execution)
- **Issue:** py2app has issues when pyproject.toml is present, causing "install_requires is no longer supported" errors even when install_requires is not in setup.py.
- **Fix:** Implemented Phase 6 workaround: temporarily rename pyproject.toml to pyproject.toml.backup during build, restore after build completes. This is a known issue documented in 06-01-SUMMARY.md.
- **Files modified:** scripts/build.sh (added mv pyproject.toml and restore logic)
- **Verification:** Build succeeded with pyproject.toml temporarily moved
- **Committed in:** 8b19972 (Task 1 commit)

**3. [Rule 2 - Missing Critical] Downgraded setuptools for py2app compatibility**

- **Found during:** Task 1 (troubleshooting build errors)
- **Issue:** setuptools 80.10.2 (installed with Python 3.12.7) caused "install_requires is no longer supported" errors. Modern setuptools deprecated features py2app relies on.
- **Fix:** Downgraded setuptools from 80.10.2 to 69.5.1 in Python 3.12.7 environment. This is not tracked in git (environment-specific change).
- **Files modified:** None (virtualenv-specific change, not committed)
- **Verification:** py2app build succeeded with setuptools 69.5.1
- **Committed in:** N/A (environment configuration, not committed)

---

**Total deviations:** 3 auto-fixed (3 blocking)
**Impact on plan:** All auto-fixes necessary for build system compatibility. Python version choice is documented in build script comments for future reference. No scope creep.

## Issues Encountered

- **Python 3.14.2 incompatibility**: py2app 0.28.9 has IndentationError in build_app.py line 662 when run with Python 3.14.2. Workaround: use Python 3.12.7 for building until py2app updates to support Python 3.14.
- **pyproject.toml conflict**: py2app has issues with pyproject.toml present. Workaround: temporarily rename during build (established Phase 6 pattern).
- **setuptools deprecation**: Modern setuptools (80.x) deprecated install_requires, which py2app internally uses. Workaround: use setuptools 69.5.1 for Python 3.12.7 environment.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for:** Plan 09-02 (Documentation - INSTALL.md, TROUBLESHOOTING.md, README.md update)

**Foundation established:**
- Build automation working with reproducible .app bundle creation
- Code signing verified (ad-hoc signature for personal distribution)
- Version numbers synchronized across all files (1.2.0)
- Comprehensive changelog documenting all v1.2.0 features

**Blockers:** None

**Notes for next plan:**
- Document Gatekeeper bypass instructions (control-click → Open on first launch for ad-hoc signed apps)
- Include Neo4j server requirement in installation guide
- Add troubleshooting for py2app build issues (Python version, pyproject.toml, setuptools)
- Update README.md with screenshots of main window, optimization tab, and settings

---
*Phase: 09-distribution-quality*
*Completed: 2026-01-30*
