# Phase 9: Distribution & Quality - Context

**Gathered:** 2026-01-30
**Status:** Ready for planning

## Phase Boundary

Reproducible .app bundle with code signing and distribution documentation. This phase delivers a distributable macOS application that can be installed and run on clean machines, with clear installation instructions and troubleshooting guidance. No new features are added — only packaging, signing, testing, and documentation.

---

## Implementation Decisions

### Build automation

- Simple build script (`scripts/build.sh`) that wraps `python setup.py py2app`
- No CI integration for this phase (personal use project, not enterprise)
- Build reproducibility: Use `py2app` with explicit dependency list in `setup.py`
- Clean build directory before each build (`rm -rf build dist`)
- Build artifacts: `dist/NASCAR-DFS-Optimizer.app`

### Code signing strategy

- Personal Apple ID signing (free, sufficient for personal distribution)
- No Apple Developer Program enrollment (unnecessary expense for personal project)
- Distribution via direct download from GitHub Releases
- Gatekeeper compliance: Sign with personal identity, users may need to control-click on first launch
- Ad-hoc signing for development builds, full identity signing for release builds
- Sign command: `codesign --force --deep --sign "Developer ID Application: <Name>" dist/NASCAR-DFS-Optimizer.app`

### Clean machine testing

- Verify full workflow: Launch app → Import CSV → Set constraints → Optimize → Export lineups
- Both automated tests (pytest) and manual verification on clean macOS machine
- Automated tests cover: Build succeeds, app launches without crash, basic UI interaction
- Manual verification: Test all tabs, settings persistence, file import/export, keyboard shortcuts
- Test on macOS versions: Target macOS 12+ (Monterey and later)
- Architecture: Universal binary (arm64 + x86_64) via `py2app` auto-detection

### Documentation format

- `README.md` in project root with overview, installation, and quick start
- `INSTALL.md` dedicated installation guide with step-by-step instructions
- `TROUBLESHOOTING.md` for common issues (Gatekeeper, Neo4j connection, dependency errors)
- Screenshots: Include 3-4 key screenshots in README (main window, optimization tab, settings)
- Documentation style: Clear, concise, assume technical user comfortable with command line
- Update ROADMAP.md with release notes for each version

### Distribution mechanism

- GitHub Releases for distribution
- Create releases manually after testing completes
- Attach `.app` bundle as release asset (dmg or zip for download)
- Versioning: Semantic versioning (`v1.2.0` for milestone v1.2)
- Release notes in Markdown format, organized by: Features, Fixes, Known Issues
- Changelog in `CHANGELOG.md` maintained during development
- Download format: Zip archive of `.app` bundle (smaller than dmg, easy to extract)

## Claude's Discretion

- Exact build script implementation (error handling, logging)
- Test coverage depth (focus on critical path vs exhaustive testing)
- Screenshot styling and placement in README
- Release note formatting details
- Zip archive compression settings

---

## Specific Ideas

- "Make it easy for someone to download and run without wrestling with dependencies"
- Clean machine test should simulate a user who just downloaded the app for the first time
- Documentation should be self-contained (no external references beyond official docs)
- Keep the "first 5 minutes" experience smooth — launch, import, optimize, export

---

## Deferred Ideas

- Automated CI/CD pipeline for builds and releases — Phase 10+ if needed
- Notarization for Mac App Store distribution — out of scope for personal use
- Windows distribution — would require PyInstaller or similar, separate phase
- Auto-update mechanism — nice to have, but manual updates acceptable for personal use
- Docker containerization — not needed for native Mac app distribution

---

*Phase: 09-distribution-quality*
*Context gathered: 2026-01-30*
