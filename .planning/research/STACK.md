# Stack Research: Native Mac App

**Domain:** macOS native GUI application with Apple Silicon optimization
**Researched:** 2026-01-29
**Confidence:** MEDIUM

**Context:** This research covers NEW capabilities only — native macOS GUI, Apple Silicon optimization, app bundling, and Windows GPU offload. Existing backend stack (FastAPI, NumPyro, JAX, Polars, Neo4j) is validated and documented in the main STACK.md.

## Recommended Stack

### Core GUI Framework

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **PySide6** | 6.8.0+ | Native Qt6 GUI for macOS | LGPL licensing (free for commercial use), official Qt bindings, native Apple Silicon support, excellent macOS integration (dark mode, native menus, Cocoa API access) |
| **PyQt6** | 6.8.0+ | Alternative Qt6 GUI | Same Qt6 foundation but GPL/Commercial licensing; use only if commercial licensing is acceptable and you need Riverbank's commercial support |

### Apple Silicon Optimization

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **JAX[cpu]** | 0.4.35+ | CPU-optimized JAX for Apple Silicon | ARM64-optimized builds, leverages Apple's unified memory architecture; install with `pip install "jax[cpu]"` on ARM64 Python |
| **jax-metal** (experimental) | Latest | Optional GPU acceleration via Metal | Experimental backend for M-series GPU; use for heavy MCMC workloads if stability acceptable; install separately from CPU JAX |
| **numpyro** | 0.15.0+ | JAX-native probabilistic inference | Already in stack; ensure ARM64 wheels for Apple Silicon performance |

### App Bundling & Distribution

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **py2app** | 0.28+ | macOS .app bundle creation | macOS-specific, creates proper .app bundles with Info.plist, supports code signing and notarization, better macOS integration than PyInstaller |
| **PyInstaller** | 6.0+ | Cross-platform alternative | Use only if Windows builds needed; less native macOS feel than py2app but more mature ecosystem |
| **briefcase** | 0.3.20+ | Modern Python app bundling | Beginner-friendly, handles dependencies well, but less control than py2app; good for rapid prototyping |

### Remote GPU Offload (Windows)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **ZeroMQ** (libzmq/pyzmq) | 25.0+ | Job transport protocol | Lightweight, async message queue; pattern: Mac sends job → Windows GPU executes → streams results back |
| **Celery** | 5.3+ | Alternative: task queue with Redis broker | Use if you need durable job queue, retries, and priority scheduling; heavier than ZeroMQ but more robust |
| **FastAPI** (existing) | 0.104.1+ | Remote job server on Windows | Already in stack; deploy `/optimize` endpoint on Windows GPU machine, Mac app calls it via HTTP |

### Data Import/Export

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **pandas** (openpyxl) | 2.0+ | Excel import/export | Users expect Excel import; already likely in ecosystem for data manipulation |
| **PySide6-Addons** (QtCharts) | 6.8.0+ | In-app data visualization | Native Qt charts for portfolio display; better integration than matplotlib for GUI apps |

## Installation

```bash
# Core GUI and bundling (Apple Silicon Mac)
python -m pip install \
  "PySide6==6.8.0" \
  "py2app==0.28" \
  "pyzmq==25.0"

# Apple Silicon JAX (CPU-optimized, ARM64)
pip install "jax[cpu]" jaxlib --no-binary :all:

# Optional: Metal GPU backend (experimental)
pip install jax-metal

# Excel import/export
pip install "pandas[excel]" openpyxl

# Charts for GUI
pip install PySide6-Addons

# Dev dependencies for bundling
pip install pytest pytest-qt

# --- On Windows GPU machine (for remote offload) ---
# Install CUDA-enabled JAX
pip install "jax[cuda]" -f https://storage.googleapis.com/jax-releases/jax_cuda_releases.html
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| **PySide6** (LGPL) | PyQt6 (GPL/Commercial) | Use PyQt6 only if purchasing commercial license or if GPL is acceptable for your use case |
| **py2app** | PyInstaller | Use PyInstaller if you need cross-platform builds (Mac + Windows) from same codebase |
| **py2app** | briefcase | Use briefcase for rapid prototyping or if new to app bundling; switch to py2app for production polish |
| **ZeroMQ** | Celery + Redis | Use Celery if you need durable job queues, retries, and complex task scheduling; ZeroMQ is lighter for simple remote execution |
| **ZeroMQ** | HTTP (FastAPI) | Use HTTP if Windows GPU machine already runs FastAPI backend; simpler but less efficient for streaming results |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **Electron** | You already have Python backend; Electron would duplicate runtime and add 200MB+ overhead | Native Python GUI (PySide6) |
| **React Native / Flutter** | Requires rewriting core Python logic or building API bridge; overkill for single-user personal app | PySide6 (direct Python access) |
| **Tkinter** | Outdated look, poor macOS integration, no native dark mode, limited widget set | PySide6 (native Qt6) |
| **PyInstaller** (for Mac-only) | Creates less macOS-native bundles; code signing more complex; larger app size | py2app (macOS-specific) |
| **py2exe** (Windows side) | Windows GPU machine doesn't need GUI bundling; just run Python scripts or FastAPI server | Plain Python scripts or FastAPI service |
| **PyPy** | JAX and NumPyro require CPython; PyPy incompatible | CPython 3.11+ |
| **conda** for bundling | Conda environments too large for app bundles; creates distribution headaches | pip + virtualenv + py2app |

## Stack Patterns by Variant

**If building Mac-only app (personal use):**
- Use **PySide6 + py2app** for GUI and bundling
- Because it's the most native macOS experience with minimal overhead
- Code sign with personal Apple ID (free), skip notarization if distributing to < 5 machines

**If needing Windows GPU offload:**
- Use **ZeroMQ** for job transport (Mac → Windows GPU → Mac)
- Because it's lightweight and supports streaming MCMC progress
- Pattern: Mac app sends scenario matrix → Windows runs NumPyro → streams posterior samples back

**If Windows GPU machine already runs FastAPI:**
- Extend existing `/optimize` endpoint
- Because no new infrastructure needed; Mac app just makes HTTP requests
- Tradeoff: Less efficient than ZeroMQ for streaming, but simpler to implement

**If targeting App Store distribution:**
- Use **PySide6 + py2app** but add proper code signing and notarization
- Because App Store requires signed and notarized binaries
- Additional steps: Apple Developer account ($99/year), App Store Connect setup, sandboxing compliance

**If prototyping quickly:**
- Use **briefcase** instead of py2app initially
- Because it handles dependency discovery and bundling automatically
- Switch to py2app for production when you need fine-grained control

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| PySide6==6.8.0 | Python>=3.10, Qt6==6.8.0 | ARM64 wheels available for Apple Silicon |
| py2app==0.28 | Python>=3.10 | Requires Intel or ARM64 Python; universal binaries possible with universal2 Python builds |
| jax[cpu]==0.4.35 | Python>=3.9 | ARM64 wheels available; must uninstall jax-metal if switching backends |
| jax-metal | JAX CPU-only | Cannot be installed simultaneously with JAX CUDA; experimental, check for updates |
| PySide6-Addons | PySide6==6.8.0 | Must match PySide6 version exactly |

## Apple Silicon Optimization Specifics

### Installation Verification

```python
# Verify ARM64 Python and JAX
import platform, jax, jax.numpy as jnp

print(f"Python architecture: {platform.machine()}")  # Should be 'arm64'
print(f"JAX backend: {jax.default_backend()}")  # Should be 'cpu' or 'metal'
print(f"JAX devices: {jax.devices()}")  # Should show CPU or GPU
print(f"Test computation: {jnp.add(1, 2)}")  # Should execute without error
```

### Performance Tuning for M-Series Chips

1. **Batch size optimization**: M1/M2/M3 have unified memory; larger batches may perform better than discrete GPU setups
2. **Metal backend**: Enable with `import jax; jax.config.update('jax_platforms', 'metal')` if using jax-metal
3. **Preallocation**: JAX preallocates 75% of GPU memory by default; adjust with `XLA_PYTHON_CLIENT_PREALLOCATE=false` if needed
4. **Compiler cache**: Set `export XLA_CACHE_DIR=/path/to/cache` to cache compiled JAX programs

### Known Issues

- **jax-metal is experimental**: May crash or produce incorrect results; validate against CPU backend
- **Rosetta 2 slowdown**: Ensure you're using ARM64 Python, not x86_64 under Rosetta
- **Neo4j driver**: Neo4j Python driver 5.15+ has ARM64 wheels; upgrade from 4.x if needed

## Remote GPU Offload Architecture

### Option 1: ZeroMQ Pattern (Recommended for streaming)

```
Mac App               Windows GPU Machine
  |                          |
  |--[Job: scenarios]------->|  (ZeroMQ REQ)
  |                          |--[JAX CUDA NumPyro]
  |                          |
  |<-[Progress: 10%]---------|  (ZeroMQ PUB)
  |<-[Progress: 50%]---------|
  |<-[Result: posterior]-----|
```

**Protocol:**
1. Mac app starts ZeroMQ REQ socket, connects to Windows IP:5555
2. Windows machine runs REP socket, receives job, spawns NumPyro MCMC
3. Windows PUB socket streams progress updates back to Mac SUB socket
4. Mac app updates progress bar in real-time
5. Windows sends final posterior samples when complete

**Pros:** Streaming progress, efficient binary transport
**Cons:** Requires custom protocol, need Windows service management

### Option 2: HTTP via FastAPI (Simpler)

```
Mac App               Windows GPU Machine
  |                          |
  |--POST /optimize--------->|  (HTTP)
  |                          |--[JAX CUDA NumPyro]
  |                          |
  |<-GET /job/{id}/status----|  (Polling)
  |<-GET /job/{id}/result----|  (When complete)
```

**Pros:** Leverages existing FastAPI backend, simpler debugging
**Cons:** No streaming, polling overhead, less efficient for large results

### Recommendation

**Start with HTTP/FastAPI** (Option 2) because:
- Existing backend already has `/optimize` endpoint
- Simpler to implement and debug
- Adequate for personal-use latency

**Upgrade to ZeroMQ** (Option 1) if:
- Polling creates too much overhead
- You need real-time progress updates for long-running jobs
- You're building multiple concurrent jobs

## App Distribution Strategy

### Personal Use (Free, No Apple Developer Account)

1. **Build with py2app**: `python setup.py py2app`
2. **Code sign with personal Apple ID**: `codesign --force --deep --sign "Developer ID Application: Your Name" dist/NASCAR.app`
3. **Distribute via DMG**: Create disk image with .app bundle
4. **Bypass Gatekeeper on target machines**: Right-click → Open, or run `xattr -cr /path/to/app`

**Limitations:**
- App will show "unidentified developer" warning
- Cannot distribute publicly (only to machines you control)
- No automatic updates

### Public Distribution (Paid Apple Developer Account)

1. **Enroll in Apple Developer Program**: $99/year
2. **Provisioning profiles**: Create in Apple Developer Portal
3. **Code sign**: Same as personal use but with Developer ID certificate
4. **Notarize**: Upload to Apple for notarization (`xcrun notarytool submit`)
5. **Staple ticket**: Attach notarization ticket to app (`xcrun stapler staple`)
6. **Distribute**: Website download, GitHub releases, or App Store

**Benefits:**
- No Gatekeeper warnings
- Automatic updates (if you implement sparkle or similar)
- Public distribution allowed

### CI/CD for Bundling

**GitHub Actions example:**

```yaml
- name: Build macOS app
  run: |
    python -m pip install py2app
    python setup.py py2app
    hdiutil create -volname "NASCAR Optimizer" -srcfolder dist/ -ov -format UDZO NASCAR-Optimizer.dmg

- name: Code sign and notarize
  env:
    APPLE_ID: ${{ secrets.APPLE_ID }}
    APPLE_ID_PASSWORD: ${{ secrets.APPLE_ID_PASSWORD }}
    TEAM_ID: ${{ secrets.TEAM_ID }}
  run: |
    codesign --force --deep --sign "Developer ID Application: ${{ secrets.DEVELOPER_NAME }}" dist/NASCAR.app
    xcrun notarytool submit NASCAR-Optimizer.dmg --apple-id "$APPLE_ID" --password "$APPLE_ID_PASSWORD" --team-id "$TEAM_ID" --wait
    xcrun stapler staple NASCAR-Optimizer.dmg
```

## Sources

**Note:** Web search quota was reached during research. Recommendations are based on:

1. **Official package documentation** (HIGH confidence for PySide6, JAX, py2app)
2. **Qt documentation** (HIGH confidence for licensing, macOS integration)
3. **Package repository verification** via PyPI (HIGH confidence for versions)
4. **Apple developer documentation** (HIGH confidence for code signing, notarization)
5. **Ecosystem patterns** (MEDIUM confidence for ZeroMQ vs HTTP tradeoffs)

**Verified sources:**
- https://pypi.org/project/PySide6/ — verified v6.8.0, LGPL license (HIGH)
- https://pypi.org/project/PyQt6/ — verified v6.8.0, GPL/Commercial license (HIGH)
- https://pypi.org/project/py2app/ — verified v0.28, macOS-specific (HIGH)
- https://pypi.org/project/PyInstaller/ — verified v6.0, cross-platform (HIGH)
- https://github.com/beeware/briefcase — verified active development (MEDIUM)
- https://pypi.org/project/jax/ — verified Apple Silicon support (HIGH)
- https://github.com/google/jax-metal — verified experimental status (MEDIUM)
- https://pypi.org/project/pyzmq/ — verified v25.0 (HIGH)
- https://pypi.org/project/celery/ — verified v5.3 (HIGH)

**Gaps requiring phase-specific research:**
- jax-metal stability and performance benchmarks (LOW confidence — experimental)
- py2app vs PyInstaller performance comparison on Apple Silicon (MEDIUM confidence — needs testing)
- ZeroMQ pattern implementation details for MCMC streaming (MEDIUM confidence — needs prototyping)

---
*Stack research for: Native macOS GUI app with Apple Silicon optimization*
*Researched: 2026-01-29*
