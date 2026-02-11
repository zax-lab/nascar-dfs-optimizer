# Architecture Research: Native Mac GUI with Remote GPU Offload

**Domain:** NASCAR DFS Optimizer — Native Mac desktop application with optional Windows GPU compute
**Researched:** 2026-01-29
**Confidence:** HIGH

## Executive Summary

The native Mac GUI architecture follows a **Model-View-Presenter (MVP) pattern** with PySide6, where the GUI orchestrates existing Python optimization code through a **service layer abstraction**. The critical architectural decision is extracting business logic from FastAPI endpoints into **library functions** that can be called by both the GUI and the API. Remote GPU offload to Windows uses a **RESTful job submission protocol** with HTTPS, JWT authentication, and polling-based result retrieval, leveraging the existing JobStateManager pattern.

The key integration challenge is the **FastAPI-to-library refactor**: current endpoints contain business logic that must be extracted into pure Python functions. The GUI communicates with these services through Qt's signal-slot mechanism, ensuring UI responsiveness during long-running optimizations via QThreadPool background workers.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           Native Mac GUI Application                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                         Main Window (QMainWindow)                          │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │  │
│  │  │ Driver       │  │ Portfolio    │  │ Configuration│  │ Jobs Log     │  │  │
│  │  │ Table View   │  │ Results View │  │ Panel        │  │ View         │  │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                              Presenter / Controller Layer                        │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  OptimizationPresenter  │  DataIngestPresenter  │  SettingsPresenter      │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                               Service Layer (New)                               │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐          │
│  │ Optimization      │  │ Data Ingestion    │  │ Remote Job        │          │
│  │ Service           │  │ Service           │  │ Submission        │          │
│  │ (refactored from  │  │ (new)             │  │ Service           │          │
│  │  FastAPI)         │  │                   │  │                   │          │
│  └─────────┬─────────┘  └─────────┬─────────┘  └─────────┬─────────┘          │
├────────────┼──────────────────────┼──────────────────────┼──────────────────────┤
│            │                      │                      │                      │
│  ┌─────────▼─────────┐  ┌─────────▼─────────┐  ┌─────────▼─────────┐         │
│  │ Scenario Cache    │  │ Local Data Store  │  │ HTTP Client       │         │
│  │ (in-memory)       │  │ (SQLite)          │  │ (requests + JWT)  │         │
│  └───────────────────┘  └───────────────────┘  └─────────┬─────────┘         │
├────────────────────────────────────────────────────────────┼───────────────────┤
│                                                             │                   │
│  ┌─────────────────────────────────────────────────────────┴───────────┐     │
│  │              Core Library (Existing Backend Code)                  │     │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │     │
│  │  │ kernel.py    │  │ optimizer.py │  │ portfolio_   │  │ ontology.py│ │
│  │  │ (KernelLogic)│  │ (PuLP)       │  │ generator.py │  │ (Neo4j)    │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘ │
│  └─────────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ HTTPS + JWT
                                      │ (Optional Remote GPU)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    Windows GPU Machine (Remote Compute)                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                    FastAPI Backend (Existing)                              │  │
│  │  POST /optimize  │  GET /optimize/{id}/status  │  GET /optimize/{id}/result│  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                          │                                         │
│  ┌───────────────────────────────────────┴────────────────────────────────────┐  │
│  │                  Background Workers (Celery or GPU Process)                │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                    │  │
│  │  │ JAX/NumPyro  │  │ Scenario     │  │ Portfolio    │                    │  │
│  │  │ MCMC         │  │ Generation   │  │ Optimization │                    │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘                    │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                          │                                         │
│  ┌───────────────────────────────────────▼────────────────────────────────────┐  │
│  │                     Job State (Redis)                                      │  │
│  └─────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **Main Window** | Top-level window container, menu bar, status bar, window state management | `QMainWindow` subclass with dock widgets for different views |
| **Views** | Display-only widgets (tables, plots, forms) that emit signals on user interaction | `QTableView`, `QTableView` with custom models, `MatplotlibWidget` |
| **Presenters** | Coordinate between views and services, handle user logic, update views | Plain Python classes with Qt signals for async updates |
| **Optimization Service** | Business logic for lineup optimization (extracted from FastAPI endpoints) | Pure Python functions in `apps/backend/app/services/` |
| **Data Ingest Service** | CSV/JSON import, validation, storage to local SQLite | Python module with `pandas` for ETL, `sqlite3` for persistence |
| **Remote Job Service** | HTTP client for submitting jobs to Windows GPU, polling for results | `requests.Session` with JWT auth, exponential backoff |
| **Scenario Cache** | In-memory cache of generated scenarios to avoid re-simulation | `ScenarioCache` class (already exists in `portfolio_generator.py`) |
| **Local Data Store** | SQLite database for local data persistence (driver metadata, historical results) | `sqlalchemy` with SQLite backend |
| **Core Library** | Existing optimization code (kernel, optimizer, portfolio_generator) | No changes — pure Python modules called as library |

## Recommended Project Structure

```
apps/
  desktop-gui/                    # NEW: Native Mac GUI application
    app/
      main.py                     # Application entry point (QApplication)
      main_window.py              # Main window with menu bar, dock widgets
      views/
        __init__.py
        driver_view.py            # Driver table view with QTableView
        portfolio_view.py         # Portfolio results with Matplotlib plots
        config_view.py            # Settings panel (remote GPU config, paths)
        jobs_view.py              # Background jobs log with progress bars
      presenters/
        __init__.py
        optimization_presenter.py # Coordinates optimization workflow
        data_ingest_presenter.py  # Coordinates data import workflow
        settings_presenter.py     # Manages application settings
      services/
        __init__.py
        optimization_service.py   # EXTRACTED from FastAPI endpoints
        data_ingest_service.py    # NEW: CSV/JSON import to SQLite
        remote_job_service.py     # NEW: HTTP client for Windows GPU
        storage_service.py        # NEW: SQLite database wrapper
      models/
        __init__.py
        driver_model.py           # QAbstractTableModel for driver table
        portfolio_model.py        # QAbstractListModel for portfolio results
        job_model.py              # QAbstractTableModel for jobs log
      workers/
        __init__.py
        optimization_worker.py    # QRunnable for background optimization
        ingest_worker.py          # QRunnable for background data import
        remote_job_worker.py      # QRunnable for polling remote job status
      resources/
        icons/                    # Application icons
        styles.qss                # Qt stylesheet for theming
      pyproject.toml              # Desktop GUI dependencies (PySide6, matplotlib)

  backend/                        # EXISTING: FastAPI backend
    app/
      api/                        # MODIFY: Extract business logic to services/
        optimize.py               # BEFORE: Contains business logic
        contracts.py              # KEEP: Request/response models
      services/                   # NEW: Extracted business logic
        __init__.py
        optimization_service.py   # MOVED from api/optimize.py
        # This module can now be imported by both FastAPI and GUI
      # ... rest unchanged (kernel.py, optimizer.py, etc.)
```

### Structure Rationale

- **Separate `desktop-gui/` from `backend/`:** GUI is a separate application with its own dependencies (PySide6) that coexists with the FastAPI backend
- **Extract services to `backend/app/services/`:** Business logic lives in pure Python modules callable by both FastAPI endpoints and GUI presenters
- **Presenter pattern:** Separates UI logic from business logic, making GUI testable and keeping views dumb
- **Workers in `desktop-gui/app/workers/`:** Qt background workers keep UI responsive during long operations
- **Models in `desktop-gui/app/models/`:** Qt Model/View architecture for efficient table rendering and data binding

## Architectural Patterns

### Pattern 1: Model-View-Presenter (MVP) with Qt Signals

**What:** Views emit signals on user actions, Presenters receive signals and coordinate services, Services return results via Qt signals to update views. Keeps views stateless and testable.

**When to use:** Always for GUI architecture. Enables clear separation of concerns and async UI updates.

**Trade-offs:** More boilerplate than putting logic in views, but essential for testable, maintainable GUI code.

**Example:**
```python
# views/portfolio_view.py
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal

class PortfolioView(QWidget):
    """Display portfolio optimization results."""

    # Signals emitted on user interaction
    optimize_requested = Signal(dict)  # Emits optimization config
    export_requested = Signal(str)     # Emits export format

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def display_results(self, portfolio_data):
        """Update view with optimization results."""
        # Update table, plots, etc.
        pass

# presenters/optimization_presenter.py
from PySide6.QtCore import QObject, Signal

class OptimizationPresenter(QObject):
    """Coordinate optimization workflow."""

    # Signals to update view
    optimization_started = Signal()
    optimization_progress = Signal(float)  # 0.0 to 1.0
    optimization_completed = Signal(dict)  # Portfolio results
    optimization_failed = Signal(str)      # Error message

    def __init__(self, optimization_service):
        super().__init__()
        self.service = optimization_service

    def on_optimize_requested(self, config):
        """Handle optimize signal from view."""
        self.optimization_started.emit()

        # Create background worker
        worker = OptimizationWorker(self.service, config)
        worker.signals.progress.connect(self.optimization_progress.emit)
        worker.signals.result.connect(self.optimization_completed.emit)
        worker.signals.error.connect(self.optimization_failed.emit)

        # Run in thread pool
        QThreadPool.globalInstance().start(worker)
```

### Pattern 2: Service Layer Extraction from FastAPI

**What:** Extract business logic from FastAPI endpoint functions into pure Python service functions. Endpoints become thin wrappers that handle HTTP concerns (auth, response formatting) and delegate to services.

**When to use:** When adding a GUI to an existing FastAPI backend. Services can be imported by both FastAPI and GUI without code duplication.

**Trade-offs:** Requires refactoring existing endpoints, but enables code reuse and testability.

**Example:**
```python
# services/optimization_service.py (NEW)
from typing import Dict, Any, List
from app.optimizer import NASCAROptimizer
from app.portfolio_generator import generate_lineup_with_cvar
from app.kernel import KernelLogic

class OptimizationService:
    """Business logic for portfolio optimization."""

    def __init__(self, db_session, neo4j_driver):
        self.db_session = db_session
        self.neo4j_driver = neo4j_driver
        self.scenario_cache = ScenarioCache()

    def optimize_portfolio(
        self,
        slate_id: str,
        n_lineups: int,
        cvar_alpha: float = 0.95,
        n_scenarios: int = 10000,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Optimize portfolio using CVaR objective.

        This is pure Python logic callable by both FastAPI and GUI.
        """
        # Compile constraints from Neo4j
        compiler = ConstraintCompiler(self.neo4j_driver)
        constraint_spec = compiler.compile_spec(slate_id=slate_id, ...)

        # Generate or retrieve cached scenarios
        scenarios = self.scenario_cache.get_scenarios(
            slate_id, n_scenarios, generate_scenarios_fn
        )

        # Generate portfolio lineups
        portfolio = []
        for i in range(n_lineups):
            lineup = generate_lineup_with_cvar(
                scenarios, driver_data, exposure_book, ...
            )
            portfolio.append(lineup)

        return {
            "lineups": portfolio,
            "scenario_diagnostics": {...},
            "constraint_spec_hash": constraint_spec.hash
        }

# api/optimize.py (MODIFIED)
from fastapi import APIRouter, Depends
from app.services.optimization_service import OptimizationService

router = APIRouter()

@router.post("/optimize")
async def submit_optimization(
    request: OptimizeRequest,
    service: OptimizationService = Depends(get_optimization_service)
):
    """FastAPI endpoint wraps service with HTTP concerns."""
    try:
        result = service.optimize_portfolio(
            slate_id=request.slate_id,
            n_lineups=request.n_lineups,
            **request.dict()
        )
        return OptimizeResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# presenters/optimization_presenter.py (NEW)
from app.services.optimization_service import OptimizationService

class OptimizationPresenter(QObject):
    """Presenter calls same service as FastAPI."""

    def __init__(self, service: OptimizationService):
        self.service = service

    def on_optimize_requested(self, config):
        """GUI presenter calls same service."""
        result = self.service.optimize_portfolio(**config)
        self.optimization_completed.emit(result)
```

### Pattern 3: Remote GPU Job Submission with Polling

**What:** GUI submits optimization job to remote Windows GPU machine via REST API, receives job ID, polls for status periodically, retrieves results when complete. Uses JWT authentication and exponential backoff.

**When to use:** When local compute is insufficient (JAX/NumPyro on CPU) and remote GPU resources are available.

**Trade-offs:** Adds network latency and dependency on remote machine availability, but enables GPU acceleration without local hardware.

**Example:**
```python
# services/remote_job_service.py
import requests
import time
from typing import Dict, Any, Optional
import jwt

class RemoteJobService:
    """HTTP client for remote GPU optimization jobs."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self._jwt_token()}',
            'Content-Type': 'application/json'
        })

    def _jwt_token(self) -> str:
        """Generate JWT token from API key."""
        # In production, use proper JWT library with secret key
        payload = {'api_key': self.api_key, 'exp': int(time.time()) + 3600}
        return jwt.encode(payload, secret='your-secret-key', algorithm='HS256')

    def submit_job(self, job_config: Dict[str, Any]) -> str:
        """Submit optimization job to remote GPU machine."""
        response = self.session.post(
            f'{self.base_url}/api/optimize',
            json=job_config,
            timeout=30
        )
        response.raise_for_status()
        job_id = response.json()['run_id']
        return job_id

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Poll job status from remote machine."""
        response = self.session.get(
            f'{self.base_url}/api/optimize/{job_id}/status',
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    def get_job_result(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve job result if complete."""
        response = self.session.get(
            f'{self.base_url}/api/optimize/{job_id}/result',
            timeout=30
        )
        if response.status_code == 202:
            return None  # Still running
        response.raise_for_status()
        return response.json()

# workers/remote_job_worker.py
from PySide6.QtCore import QRunnable, Signal, QObject

class RemoteJobWorker(QRunnable):
    """Background worker for remote job polling."""

    class Signals(QObject):
        progress = Signal(float)      # 0.0 to 1.0
        result = Signal(dict)         # Portfolio results
        error = Signal(str)           # Error message

    def __init__(self, remote_service: RemoteJobService, job_id: str):
        super().__init__()
        self.signals = self.Signals()
        self.remote_service = remote_service
        self.job_id = job_id

    def run(self):
        """Poll job status until complete."""
        poll_interval = 2.0  # Start with 2 second polls
        max_interval = 30.0  # Max 30 second polls
        timeout = 600  # 10 minute timeout

        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                status = self.remote_service.get_job_status(self.job_id)

                if status['status'] == 'completed':
                    result = self.remote_service.get_job_result(self.job_id)
                    self.signals.result.emit(result)
                    return
                elif status['status'] == 'failed':
                    self.signals.error.emit(status.get('error', 'Unknown error'))
                    return

                # Emit progress (estimated)
                progress = self._estimate_progress(status)
                self.signals.progress.emit(progress)

                # Exponential backoff
                time.sleep(poll_interval)
                poll_interval = min(poll_interval * 1.5, max_interval)

            except requests.RequestException as e:
                self.signals.error.emit(f"Network error: {e}")
                return

        self.signals.error.emit("Job timed out")

    def _estimate_progress(self, status) -> float:
        """Estimate progress from status."""
        # Heuristic based on typical MCMC calibration time
        elapsed = time.time() - status.get('created_at', time.time())
        return min(elapsed / 60.0, 0.95)  # Assume ~60 seconds for completion
```

### Pattern 4: Qt Model/View for Tables

**What:** Use Qt's Model/View architecture for tables and lists. Models wrap data (e.g., driver list, portfolio results) and provide interface for views. Views handle display and user interaction.

**When to use:** For all table/list displays. Enables efficient rendering, sorting, filtering without duplicating data.

**Trade-offs:** More boilerplate than simple widgets, but essential for performance and separation of concerns.

**Example:**
```python
# models/driver_model.py
from PySide6.QtCore import QAbstractTableModel, Qt

class DriverModel(QAbstractTableModel):
    """Qt model for driver table."""

    COLUMNS = ['Driver ID', 'Name', 'Salary', 'Avg Finish', 'Top 5%', 'Skill']

    def __init__(self, drivers: List[Dict], parent=None):
        super().__init__(parent)
        self._drivers = drivers

    def rowCount(self, parent=None):
        return len(self._drivers)

    def columnCount(self, parent=None):
        return len(self.COLUMNS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        driver = self._drivers[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0:
                return driver['driver_id']
            elif col == 1:
                return driver['name']
            elif col == 2:
                return f"${driver['salary']:,.0f}"
            elif col == 3:
                return f"{driver['avg_finish']:.1f}"
            elif col == 4:
                return f"{driver['top5']*100:.1f}%"
            elif col == 5:
                return f"{driver['skill']:.2f}"

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.COLUMNS[section]
        return None

# views/driver_view.py
from PySide6.QtWidgets import QTableView
from app.models.driver_model import DriverModel

class DriverView(QTableView):
    """Table view of drivers."""

    driver_selected = Signal(str)  # Emits driver_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionBehavior(QTableView.SelectRows)
        self.setSelectionMode(QTableView.SingleSelection)
        self.clicked.connect(self._on_row_clicked)

    def set_drivers(self, drivers: List[Dict]):
        """Update model with new driver data."""
        model = DriverModel(drivers, self)
        self.setModel(model)

    def _on_row_clicked(self, index):
        """Handle row click."""
        driver_id = index.model().index(index.row(), 0).data()
        self.driver_selected.emit(driver_id)
```

## Data Flow

### Local Optimization Flow

```
User clicks "Optimize" button
    ↓
PortfolioView.optimize_requested signal
    ↓
OptimizationPresenter.on_optimize_requested()
    ↓
OptimizationPresenter creates OptimizationWorker
    ↓
QThreadPool starts worker in background thread
    ↓
OptimizationWorker.run():
    │
    ├→ OptimizationService.optimize_portfolio()
    │   ├→ ScenarioCache.get_scenarios()  [cached if exists]
    │   ├→ generate_scenarios()          [if cache miss]
    │   ├→ portfolio_generator.generate_lineup_with_cvar()
    │   │   ├→ NASCAROptimizer.optimize_lineup()
    │   │   ├→ KernelLogic.validate_dominator_conservation()
    │   │   └→ PuLP solve
    │   └→ return portfolio results
    │
    └→ worker.signals.result.emit(results)
        ↓
OptimizationPresenter.optimization_completed signal
    ↓
PortfolioView.display_results()
    ↓
Update table, plots, metrics
```

### Remote GPU Optimization Flow

```
User clicks "Optimize with Remote GPU" button
    ↓
PortfolioView.remote_optimize_requested signal
    ↓
OptimizationPresenter.on_remote_optimize_requested()
    ↓
RemoteJobService.submit_job(job_config)
    ├→ POST https://gpu-machine.example.com/api/optimize
    ├→ Authorization: Bearer <JWT>
    └→ receive job_id
    ↓
OptimizationPresenter creates RemoteJobWorker(job_id)
    ↓
QThreadPool starts worker in background thread
    ↓
RemoteJobWorker.run():
    │
    ├→ loop:
    │   ├→ RemoteJobService.get_job_status(job_id)
    │   │   ├→ GET /api/optimize/{job_id}/status
    │   │   └→ receive {status: "running"|"completed"|"failed"}
    │   ├→ emit progress signal (0.0 to 1.0)
    │   ├→ sleep (exponential backoff: 2s → 30s)
    │   └→ break if status == "completed" or "failed"
    │
    ├→ if completed:
    │   ├→ RemoteJobService.get_job_result(job_id)
    │   │   ├→ GET /api/optimize/{job_id}/result
    │   │   └→ receive portfolio results
    │   └→ emit result signal
    │
    └→ if failed:
        └→ emit error signal
        ↓
OptimizationPresenter receives result/error
    ↓
PortfolioView displays results or error message
```

### Data Ingestion Flow

```
User clicks "Import CSV" button
    ↓
ConfigView.file_selected signal (with file path)
    ↓
DataIngestPresenter.on_import_requested(file_path)
    ↓
Create IngestWorker(file_path)
    ↓
QThreadPool starts worker
    ↓
IngestWorker.run():
    │
    ├→ DataIngestService.import_csv(file_path)
    │   ├→ pandas.read_csv(file_path)
    │   ├→ validate data (schema checks)
    │   ├→ transform to standard format
    │   ├→ StorageService.save_drivers(drivers)
    │   │   └→ INSERT INTO local SQLite database
    │   └→ return import summary
    │
    └→ emit result signal
        ↓
DataIngestPresenter displays summary
    ↓
DriverView refreshes with new data
```

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Single user (local Mac) | In-memory scenario cache, local SQLite for data, QThreadPool for background tasks |
| 1-10 concurrent users | Same as single user (desktop GUI is single-user by design) |
| Remote GPU offload | Add RemoteJobService with HTTP client, poll for results, handle network failures |
| Multiple remote workers | Extend RemoteJobService with load balancing across multiple GPU machines |

### Scaling Priorities

1. **First bottleneck:** Scenario generation (10,000+ scenarios via CBN sampling). Fix with scenario caching and remote GPU offload.
2. **Second bottleneck:** Portfolio optimization (150 lineups × MILP solve). Fix with remote GPU and parallel worker processing.

## Anti-Patterns

### Anti-Pattern 1: "Put Business Logic in Views"

**What people do:** Write optimization logic directly in view event handlers (e.g., in `on_optimize_clicked()`).

**Why it's wrong:** Makes views untestable, duplicates logic between GUI and API, mixes UI concerns with business logic.

**Do this instead:** Extract business logic to services (e.g., `OptimizationService`). Views emit signals, Presenters coordinate services, Workers call services in background threads.

### Anti-Pattern 2: "Run Long Operations in Main Thread"

**What people do:** Call optimization functions directly from view event handlers, blocking UI thread.

**Why it's wrong:** UI freezes during optimization (30-60 seconds), terrible UX, appears unresponsive.

**Do this instead:** Use `QThreadPool` and `QRunnable` for any operation >100ms. Emit Qt signals for progress updates and results. Keep main thread responsive.

### Anti-Pattern 3: "Duplicate Logic Between GUI and API"

**What people do:** Copy-paste optimization logic between GUI presenters and FastAPI endpoints.

**Why it's wrong:** Code duplication, maintenance burden, bugs fixed in one place but not the other.

**Do this instead:** Extract business logic to services in `backend/app/services/`. Both FastAPI endpoints and GUI presenters import and call the same service functions.

### Anti-Pattern 4: "Synchronous Remote Job Polling in Main Thread"

**What people do:** Call `remote_service.get_job_result()` in a loop in the main thread.

**Why it's wrong:** Blocks UI thread, freezes GUI during network requests, no progress updates.

**Do this instead:** Use `RemoteJobWorker` with `QRunnable`. Poll in background thread, emit progress signals, update UI asynchronously.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Neo4j | Direct driver import (existing `OntologyDriver`) | Reuse existing singleton pattern from backend |
| Windows GPU Machine | HTTPS REST API with JWT auth | Use `RemoteJobService` with polling, exponential backoff |
| Local SQLite | SQLAlchemy ORM for local data persistence | Use for driver metadata, historical results, settings |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| View ↔ Presenter | Qt signals/slots | Views emit signals, Presenters receive and coordinate |
| Presenter ↔ Worker | Qt signals/slots | Presenters create workers, workers emit results via signals |
| Presenter ↔ Service | Direct function calls | Synchronous calls in worker thread, pure Python |
| Service ↔ Core Library | Direct imports | Services import and call kernel, optimizer, portfolio_generator |
| GUI ↔ Backend (FastAPI) | HTTP REST API | Optional: GUI can call local FastAPI backend instead of importing services directly |

## Build Order

### Phase 1: Service Layer Extraction
**Goal:** Extract business logic from FastAPI endpoints to services callable by both API and GUI.

1. Create `backend/app/services/optimization_service.py`
2. Move optimization logic from `api/optimize.py` to service
3. Update FastAPI endpoints to call service
4. Write unit tests for service (without HTTP concerns)

**Deliverable:** `OptimizationService` class with pure Python methods

### Phase 2: Basic GUI Structure
**Goal:** Setup PySide6 application with basic views and presenters.

1. Create `desktop-gui/app/main.py` with `QApplication`
2. Create `main_window.py` with menu bar and dock widgets
3. Create empty views (DriverView, PortfolioView, ConfigView)
4. Create presenter stubs with signal/slot connections
5. Run basic GUI (no functionality yet)

**Deliverable:** Working PySide6 app with empty views

### Phase 3: Driver Display and Local Optimization
**Goal:** Display driver data and run local optimization (CPU-only).

1. Implement `DriverModel` (Qt Model/View)
2. Implement `DataIngestService` for CSV import to SQLite
3. Implement `OptimizationPresenter` with `OptimizationWorker`
4. Connect to `OptimizationService` from Phase 1
5. Display optimization results in `PortfolioView`

**Deliverable:** Functional GUI for local optimization

### Phase 4: Remote GPU Offload
**Goal:** Add option to submit jobs to Windows GPU machine.

1. Implement `RemoteJobService` with HTTP client and JWT auth
2. Implement `RemoteJobWorker` for polling
3. Add "Remote GPU" checkbox to config panel
4. Route optimization to local or remote based on checkbox
5. Handle network failures and timeouts

**Deliverable:** Remote GPU job submission and polling

### Phase 5: Polish and Advanced Features
**Goal:** Add advanced features and improve UX.

1. Add progress bars and status updates
2. Add export to CSV (DraftKings upload)
3. Add settings panel for API keys, paths
4. Add job history log
5. Add Matplotlib plots for portfolio visualization
6. Add keyboard shortcuts and menu actions

**Deliverable:** Production-ready GUI

## Sources

### Primary (HIGH confidence — Official Documentation)
- **PySide6 Documentation** (https://doc.qt.io/qtforpython/) — Official Qt for Python documentation, verified Model/View, signals/slots, QThreadPool patterns
- **Qt Model/View Programming** (https://doc.qt.io/qt-6/model-view-programming.html) — Official Qt Model/View architecture guide
- **QThreadPool and QRunnable** (https://doc.qt.io/qt-6/qthreadpool.html) — Official Qt threading documentation
- **Python requests Library** (https://docs.python-requests.org/) — HTTP client library documentation

### Secondary (MEDIUM confidence — Community Guides)
- **PySide6 Model/View Tutorial** (https://www.learnpyqt.com/tutorials/pyside6-qmodel-qabstracttablemodel/) — Community tutorial for Qt Model/View
- **PyQt Threading Best Practices** (https://www.riverbankcomputing.com/static/Docs/PyQt6/advanced.html) — Threading patterns for PyQt/PySide
- **REST API Job Patterns** (https://restfulapi.net/job-status-resource-pattern/) — Job status resource pattern for REST APIs

### Internal Sources (Current Codebase Analysis)
- **apps/backend/app/api/optimize.py** — Existing optimization endpoint to refactor
- **apps/backend/app/optimizer.py** — Core optimization logic
- **apps/backend/app/portfolio_generator.py** — Portfolio generation with scenario caching
- **apps/backend/app/kernel.py** — Kernel validation logic
- **apps/backend/app/ontology.py** — Neo4j driver wrapper
- **apps/backend/app/job_manager.py** — Job state management (similar pattern for remote jobs)

---
*Architecture research for: Native Mac GUI with Remote GPU Offload*
*Researched: 2026-01-29*
*Confidence: HIGH*
