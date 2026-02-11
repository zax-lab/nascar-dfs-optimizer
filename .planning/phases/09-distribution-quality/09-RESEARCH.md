# Phase 9: Distribution & Quality - Research

**Researched:** 2026-01-30
**Domain:** macOS app distribution with py2app, code signing, and documentation
**Confidence:** HIGH

## Summary

This phase covers creating a reproducible .app bundle for the NASCAR DFS Optimizer that can be distributed to other macOS users. The research focused on py2app configuration for standalone builds, code signing requirements for personal distribution, clean machine testing strategies, documentation patterns, and GitHub Releases workflow.

**Primary recommendation:** Use py2app's explicit dependency specification combined with `--arch universal2` for Apple Silicon + Intel compatibility, sign with ad-hoc signature for personal distribution, and distribute via GitHub Releases with zip-archived .app bundle.

## Standard Stack

The established tools for macOS Python app distribution:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| py2app | 0.28.9 | Bundle Python scripts as macOS .app | Official tool for Python-to-OSX packaging, mature ecosystem |
| setuptools | Current | Build system dependency | Required by py2app, standard Python packaging |
| codesign | macOS system tool | Code signing for Gatekeeper | Native macOS tool for app signing and verification |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | Current | Automated testing of app bundle | Test app launches and critical path workflows |
| Git | Current | Version control and release tagging | Required for GitHub Releases workflow |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| py2app | PyInstaller | PyInstaller cross-platform but less mature on macOS; py2app has native OSX integration |
| Personal Apple ID signing | Apple Developer Program | Developer program costs $99/year and requires notarization for public distribution; personal ID is free for local use |
| GitHub Releases | Direct download | GitHub Releases provides version history, changelog, and asset management automatically |

**Installation:**
```bash
# py2app already installed from previous phases
pip install --upgrade py2app
```

## Architecture Patterns

### Recommended Project Structure for Distribution
```
apps/native_mac/
├── main.py                    # Entry point (already exists)
├── setup.py                   # py2app configuration (update needed)
├── scripts/
│   └── build.sh              # Build automation script (new)
├── dist/
│   └── NASCAR-DFS-Optimizer.app  # Output bundle (build artifact)
├── build/                     # Temporary build files (gitignored)
└── docs/                      # Distribution documentation (new)
    ├── INSTALL.md              # Installation guide (new)
    ├── TROUBLESHOOTING.md     # Common issues (new)
    └── screenshots/           # UI screenshots (new)
```

### Pattern 1: py2app Setup with Explicit Dependencies
**What:** Configure `setup.py` to explicitly list all dependencies to ensure reproducible builds
**When to use:** For production builds where missing dependencies cause runtime errors
**Example:**
```python
# Source: https://py2app.readthedocs.io/en/latest/options.html
from setuptools import setup

APP = ["main.py"]
OPTIONS = {
    "packages": [
        "PySide6",
        "PySide6.QtCore",
        "PySide6.QtWidgets",
        "PySide6.QtGui",
        "pandas",
        "numpy",
        "jax",
        "jaxlib",
        "neo4j",
    ],
    "includes": [
        # Import modules that py2app might miss
        "PySide6.QtCore",
        "PySide6.QtWidgets",
        "PySide6.QtGui",
    ],
    "excludes": [
        # Exclude development/testing dependencies
        "pytest",
        "setuptools",
    ],
    "plist": {
        "CFBundleName": "NASCAR DFS Optimizer",
        "CFBundleDisplayName": "NASCAR DFS Optimizer",
        "CFBundleIdentifier": "com.zax.nascar-dfs",
        "CFBundleVersion": "1.2.0",
        "CFBundleShortVersionString": "1.2.0",
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": False,  # Dark mode support
    },
}

setup(
    app=APP,
    data_files=[],
    options={"py2app": OPTIONS},
)
```

### Pattern 2: Build Script with Clean State
**What:** Wrapper script that ensures clean build environment and provides error handling
**When to use:** For reproducible builds and CI/CD integration
**Example:**
```bash
#!/usr/bin/env bash
# Source: py2app tutorial recommendation
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

### Pattern 3: Ad-Hoc Code Signing
**What:** Sign the .app bundle with ad-hoc signature for local distribution without Apple Developer Program
**When to use:** Personal distribution where users control-click to bypass Gatekeeper on first launch
**Example:**
```bash
# Source: codesign manual (macOS system tool)
# Ad-hoc signing (uses "-" as identity)
codesign --force --deep --sign - dist/NASCAR-DFS-Optimizer.app

# Verify signature
codesign -vvv dist/NASCAR-DFS-Optimizer.app
```

### Anti-Patterns to Avoid
- **Using `--argv_emulation` with GUI apps:** Causes conflicts with PySide6 event loop; use Qt's native file-open handling instead
- **Building without cleaning `build/` and `dist/`:** Leads to cached artifacts and non-reproducible builds
- **Excluding required packages:** Catches missing dependencies only at runtime; use explicit `packages` list instead
- **Signing after distribution:** Sign the .app bundle before creating zip archive for distribution

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bundling Python into .app | Custom bundle scripts | py2app | Handles Mach-O binary relocations, Python bootstrap, and framework bundling |
| Code signing | Custom shell scripts | codesign | System tool handles signature validation, entitlements, and deep signing of nested binaries |
| Dependency resolution | Manual import scanning | py2app's modulegraph | Automatically detects transitive dependencies and handles edge cases like Cython |
| Zip creation with metadata | Custom zip scripts | `zip -r` or Finder archive | Standard tools preserve file attributes and are portable |

**Key insight:** py2app has handled the complexity of Python-to-OSX packaging for over 15 years; custom solutions inevitably miss edge cases like Mach-O header relocations, framework search paths, and code signing requirements.

## Common Pitfalls

### Pitfall 1: Missing Dependencies at Runtime
**What goes wrong:** App launches but crashes on import of required module
**Why it happens:** py2app's dependency walker misses dynamic imports (e.g., `__import__`, `getattr(module, name)`) or packages not in standard locations
**How to avoid:**
- Explicitly list all packages in `packages` option
- Use `includes` for specific modules that might be missed
- Test bundle on clean macOS machine (no dev environment)
**Warning signs:** Import errors in Console.app logs, "ModuleNotFoundError"

### Pitfall 2: Mach-O Relocation Errors
**What goes wrong:** Build fails with "Mach-O header may be too large to relocate"
**Why it happens:** Included shared libraries don't have enough space in Mach-O header for path rewriting
**How to avoid:**
- Use latest py2app (0.28.9+ has fixes)
- If persistent, rebuild dependencies with `-headerpad_max_install_names` linker flag
**Warning signs:** Build failure during py2app's copy phase

### Pitfall 3: Gatekeeper Blocks Unsigned/Ad-Hoc Apps
**What goes wrong:** Users double-click app and get "app is damaged and can't be opened"
**Why it happens:** macOS Gatekeeper blocks unsigned apps; ad-hoc signed apps require user override
**How to avoid:**
- Always sign the .app bundle before distribution
- Document that users need to control-click → Open on first launch
- Consider Apple Developer Program if public distribution without warnings is required
**Warning signs:** "unidentified developer" message in Finder, Gatekeeper alerts

### Pitfall 4: Architecture Mismatch on Apple Silicon
**What goes wrong:** App built on Intel Mac fails on M1/M2 Macs, or vice versa
**Why it happens:** py2app uses build machine's architecture by default
**How to avoid:**
- Build on target architecture or use `--arch universal2` for fat binary
- Test on both Intel and Apple Silicon if supporting universal binary
**Warning signs:** "Bad CPU type in executable" error, immediate crash on launch

### Pitfall 5: Missing Data Files
**What goes wrong:** App launches but can't load resources, icons, or templates
**Why it happens:** py2app only includes Python code by default; data files need explicit specification
**How to avoid:**
- Use `data_files` option in setup.py to bundle non-code resources
- Use `resources` option for files in bundle's Resources directory
**Warning signs:** "FileNotFoundError", missing UI assets, broken icons

## Code Examples

Verified patterns from official sources:

### py2app Build with Universal Binary Support
```python
# Source: https://py2app.readthedocs.io/en/latest/options.html
from setuptools import setup

OPTIONS = {
    "arch": "universal2",  # Apple Silicon + Intel
    "packages": ["PySide6", "pandas", "numpy"],
    "plist": {
        "CFBundleShortVersionString": "1.2.0",
        "NSRequiresAquaSystemAppearance": False,
    },
}

setup(app=["main.py"], options={"py2app": OPTIONS})
```

### Code Signing Verification
```bash
# Source: codesign manual (system tool)
# Sign with ad-hoc signature
codesign --force --deep --sign - dist/NASCAR-DFS-Optimizer.app

# Verify signature was applied
codesign -dv dist/NASCAR-DFS-Optimizer.app

# Display entitlements (none for ad-hoc)
codesign -d --entitlements - dist/NASCAR-DFS-Optimizer.app
```

### Zip Archive for Distribution
```bash
# Create zip archive of .app bundle (standard macOS distribution format)
cd dist
zip -r NASCAR-DFS-Optimizer-1.2.0.zip NASCAR-DFS-Optimizer.app

# Verify zip contents
unzip -l NASCAR-DFS-Optimizer-1.2.0.zip
```

### GitHub Release Creation (CLI)
```bash
# Source: https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository
# Create release tag
git tag -a v1.2.0 -m "Release v1.2.0"
git push origin v1.2.0

# Create release with asset (using gh CLI)
gh release create v1.2.0 \
  --title "NASCAR DFS Optimizer v1.2.0" \
  --notes "Features: ... See CHANGELOG.md for details." \
  dist/NASCAR-DFS-Optimizer-1.2.0.zip
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `setup_requires=["py2app"]` in setup.py | Remove `setup_requires` (deprecated in setuptools) | setuptools 58.0+ | Avoids deprecation warnings and build failures |
| Single-architecture builds | Universal2 builds (arm64 + x86_64) | Apple Silicon (2020) | Apps run natively on both Intel and M1/M2 Macs |
| Ad-hoc signing only | Personal Apple ID + ad-hoc | macOS Sierra (2016) | Better Gatekeeper handling with identity signing |
| No dark mode support | `NSRequiresAquaSystemAppearance=False` | macOS Mojave (2018) | Automatic dark mode support in bundled apps |

**Deprecated/outdated:**
- `setup_requires=["py2app"]`: Removed as deprecated setuptools compatibility; py2app should be installed separately
- `--prefer-ppc`: Legacy option for PowerPC translation; dropped in modern py2app versions
- Tkinter-based apps: PySide6/Qt is modern standard for Python GUI apps on macOS

## Open Questions

Things that couldn't be fully resolved:

1. **JAX bundling compatibility**
   - What we know: JAX and jaxlib are compiled libraries with complex dependencies
   - What's unclear: Whether py2app automatically includes JAX's native binaries or requires explicit handling
   - Recommendation: Test bundle early for JAX import errors; may need to include `jax`, `jaxlib`, and their shared libraries explicitly

2. **Neo4j driver dependency**
   - What we know: App requires Neo4j Python driver for constraint ontology
   - What's unclear: Whether to bundle the driver or require users to install Neo4j separately
   - Recommendation: Bundle driver but document that Neo4j server must be running; add error handling with clear message if connection fails

3. **Universal binary size impact**
   - What we know: Universal2 binaries include both arm64 and x86_64 code
   - What's unclear: Estimated final .app size with all dependencies bundled
   - Recommendation: Build and measure bundle size; if > 200MB, consider architecture-specific builds instead

4. **PySide6 plugin inclusion**
   - What we know: PySide6 uses plugins for image formats and platform integration
   - What's unclear: Whether py2app automatically includes required Qt plugins or needs explicit `qt_plugins` option
   - Recommendation: Test app image loading and platform features; add plugins if needed

## Sources

### Primary (HIGH confidence)
- https://py2app.readthedocs.io/en/latest/ - Official py2app documentation (options, tutorial, FAQ, examples, recipes)
- https://py2app.readthedocs.io/en/latest/options.html - Complete option reference for setup.py configuration
- https://py2app.readthedocs.io/en/latest/tutorial.html - Build process and alias vs deployment mode
- https://py2app.readthedocs.io/en/latest/recipes.html - Built-in recipes for numpy, scipy, PyQt
- https://py2app.readthedocs.io/en/latest/faq.html - Common issues and solutions (Mach-O errors, M1 support)
- https://py2app.readthedocs.io/en/latest/tweaking.html - Info.plist customization and universal binaries
- codesign(1) manual page - macOS system documentation for code signing commands
- https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository - GitHub Releases workflow
- https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases - Release concepts and asset limits (2GB per file, 1000 assets per release)
- https://developer.apple.com/support/code-signing/ - Apple code signing resources and certificate types

### Secondary (MEDIUM confidence)
- https://developer.apple.com/forums/thread/130855 - Manual code signing example (Apple Developer Forums)
- Existing project structure analysis: `/apps/native_mac/setup.py`, `/apps/native_mac/main.py`, `/apps/native_mac/gui/**/*.py`

### Tertiary (LOW confidence)
- None - All findings verified from official sources or project code

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Official py2app and codesign documentation
- Architecture: HIGH - py2app tutorial and options reference provide complete patterns
- Pitfalls: HIGH - py2app FAQ documents common issues and solutions; Apple docs cover Gatekeeper behavior

**Research date:** 2026-01-30
**Valid until:** 2026-02-28 (30 days - stable domain, py2app not actively changing)
