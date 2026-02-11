# Changelog

All notable changes to the NASCAR DFS Optimizer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.2.0] - 2026-01-30

### Added

#### Core Features
- Native macOS GUI with PySide6/Qt6 framework
- Tabbed interface with Race Data, Optimization, Lineups, Jobs, Settings tabs
- CSV import/export for race data and DraftKings lineup uploads
- Local JAX-based MCMC optimization engine with configurable iterations
- Constraint presets system for saving/loading constraint configurations
- Undo/Redo system with CMD+Z / CMD+Shift+Z keyboard shortcuts

#### Workflow Accelerators
- Keyboard shortcuts with 20+ customizable actions following macOS conventions
- Split-view editor with real-time optimization preview (debounced)
- Background job queue with dock badge and menubar status
- Kernel veto log viewer for debugging constraint rejections

#### System Integration
- Dock icon bounce on optimization completion
- Dock menu with recent races and quick actions
- Native macOS notifications with "View Lineups" action button
- Settings backup/export to JSON for data portability
- Session restoration on app launch (geometry, race, lineups, active tab)

#### Distributed Computing
- Optional Windows GPU offload for heavy optimization jobs
- HTTP/FastAPI pattern for GPU worker communication
- Automatic fallback to local CPU on GPU failure
- Job history with timestamped runs and re-run functionality
- Export job results to JSON with full metadata

### Fixed

#### Build & Distribution
- py2app setup.py compatibility (removed deprecated setup_requires)
- Python 3.14.2 compatibility issue with py2app 0.28.9
  - Using Python 3.12.7 for building until py2app updates
  - Build script automatically handles pyproject.toml workaround

### Technical

#### Architecture
- SQLite local persistence for races, lineups, jobs with full UPSERT support
- Base64 encoding for Qt binary geometry data persistence
- Neo4j driver for constraint ontology (server required)
- Universal binary support (Apple Silicon M1/M2/M3 + Intel)
- Qt Model/View architecture with QAbstractTableModel subclasses

#### Performance
- JAX[cpu] backend for Apple Silicon optimization (metal experimental, deferred)
- ThreadPoolExecutor for concurrent job execution
- Progress callback every 1% of iterations for smooth UI updates
- Temperature-based sampling for exploration/exploitation tradeoff

#### Data Handling
- DataController with pandas read_csv for robust CSV parsing
- UTF-8 with BOM encoding for Excel compatibility
- Auto-detection of CSV format (driver data vs lineup export)
- Error handling pattern: tuple (success, error_message, data)

#### Code Quality
- Context manager pattern for automatic SQLite connection cleanup
- Signal/slot mechanism for UI updates when data changes
- Per-race and global QUndoStack for context isolation
- Unlimited undo depth (never lose user work)

---

## [Unreleased]

### Planned Features

---

## [1.0.0] - 2026-01-28

### Added

#### Core Engine
- Kernel validation with immutable constraint checks
- Ontology layer with Neo4j driver wrapper
- FastAPI backend with `/optimize` endpoint
- LP optimizer with PuLP integration
- Tail-optimized portfolio generation (top-1% outcomes)
- Field/ownership simulation for tournament EV
- Payout curve modeling (power-law, exponential)

### Technical

- Causal Bayesian Network constrained by ontology
- Skeleton Narrative scenario generator
- NumPyro integration for JAX acceleration
- Polars for telemetry processing
- Telemetry ETL pipeline with premium loop/lap-by-lap data
- Track-archetype calibration with ArviZ
- Airflow DAGs for ingestion into Neo4j
