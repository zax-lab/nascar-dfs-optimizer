# Codebase Structure

**Analysis Date:** 2026-02-11

## Directory Layout

```
[project-root]/
├── apps/                    # Multi-app monorepo
│   ├── backend/             # Python FastAPI backend
│   ├── frontend/            # Next.js React frontend
│   ├── native_mac/          # macOS native GUI
│   └── airflow/             # Airflow DAGs for ETL
├── packages/                # Shared Python packages
│   ├── axiomatic-kernel/    # Data models, projection models
│   └── axiomatic-sim/       # Simulation engine
├── agents/                  # GSD agent definitions
│   ├── backend/
│   ├── data/
│   ├── devops/
│   ├── frontend/
│   ├── ml/
│   └── test/
├── conductor/               # Git conductor configuration
│   ├── code_styleguides/
│   └── tracks/
├── scripts/                 # Standalone Python scripts
│   ├── etl/                 # Data extraction/processing
│   └── data/                # Data utilities
├── data/                    # Data files and imports
│   ├── historical/          # Historical NASCAR data
│   ├── imports/             # External data imports
│   └── telemetry/           # Telemetry data
├── tests/                   # Test suites
│   └── integration/         # Integration tests
├── docs/                    # Documentation
├── output/                  # Generated outputs
├── logs/                    # Application logs
├── plan/                    # Planning state
├── main.py                  # CLI entry point
├── config.yaml              # Configuration file
├── package.json             # Root npm workspaces config
├── docker-compose*.yml      # Docker configuration
└── pyproject.toml           # Backend Python project
```

## Directory Purposes

**apps/:**
- Purpose: Contains all applications in the monorepo
- Contains: Backend, frontend, native macOS app, Airflow
- Key apps:
  - `apps/backend/` - FastAPI REST API service
  - `apps/frontend/` - Next.js web application
  - `apps/native_mac/` - Desktop GUI application
  - `apps/airflow/` - Data pipeline orchestration

**packages/:**
- Purpose: Shared, reusable Python packages
- Contains: Domain logic, models, simulation engines
- Key packages:
  - `packages/axiomatic-kernel/` - Data modeling, projection models
  - `packages/axiomatic-sim/` - Monte Carlo simulation, scenario generation

**agents/:**
- Purpose: GSD (Get Shit Done) agent definitions
- Contains: Specialized AI agents for different domains
- Key agents:
  - `agents/backend/` - Backend development agents
  - `agents/data/` - Data pipeline agents
  - `agents/ml/` - Machine learning agents
  - `agents/test/` - Testing agents
  - `agents/devops/` - DevOps and deployment agents

**conductor/:**
- Purpose: Git conductor for code review automation
- Contains: Code style guides, workflow tracks
- Key files:
  - `conductor/tech-stack.md` - Technology stack documentation
  - `conductor/workflow.md` - Code review workflow
  - `conductor/track_*.md` - Git review tracks

**scripts/:**
- Purpose: Standalone Python scripts for data processing and tasks
- Contains: ETL scripts, simulation runners, utilities
- Key scripts:
  - `scripts/etl/` - Data extraction and processing
  - `scripts/track_aware_simulator.py` - Track-specific simulation
  - `scripts/calibrate_drivers.py` - Driver calibration
  - `scripts/train_model.py` - Model training

**data/:**
- Purpose: Data files and data processing
- Contains: Historical race data, imports, telemetry
- Key directories:
  - `data/historical/` - Historical NASCAR race data (2024, 2025)
  - `data/imports/` - External data imports
  - `data/telemetry/` - Telemetry data

**tests/:**
- Purpose: Test suites for all applications
- Contains: Unit tests, integration tests
- Key tests:
  - `tests/integration/` - Integration tests
  - Backend tests: `apps/backend/app/tests/`

**docs/:**
- Purpose: Documentation
- Contains: User guides, technical docs, screenshots

**output/:**
- Purpose: Generated outputs from scripts and processes
- Contains: Simulation results, visualizations, logs

## Key File Locations

**Entry Points:**
- `main.py` - CLI entry point for database seeding
- `apps/backend/app/main.py` - FastAPI backend entry point
- `apps/frontend/src/app/page.tsx` - Frontend home page

**Configuration:**
- `config.yaml` - Main application configuration
- `apps/backend/pyproject.toml` - Backend Python project configuration
- `apps/frontend/package.json` - Frontend Node.js configuration
- `.env` - Environment variables
- `.env.example` - Environment variable template

**Core Logic:**
- Backend: `apps/backend/app/lineup_optimizer.py`, `apps/backend/app/ontology.py`
- Packages: `packages/axiomatic-kernel/projection_model.py`, `packages/axiomatic-sim/src/axiomatic_sim/`

**API Endpoints:**
- `apps/backend/app/api/optimize.py` - Main optimization endpoint
- `apps/backend/app/api/nascar_optimize.py` - NASCAR-specific endpoint
- `apps/backend/app/api/health.py` - Health check

**Models:**
- Backend: `apps/backend/app/models.py`
- Kernel: `packages/axiomatic-kernel/nascar_dataset.py`

**Testing:**
- Backend: `apps/backend/app/tests/`
- Packages: `packages/axiomatic-kernel/tests/`, `packages/axiomatic-sim/tests/`

**Data:**
- Historical: `data/historical/2024/`, `data/historical/2025/`
- Imports: `data/imports/`
- ETL: `scripts/etl/`

## Naming Conventions

**Files:**
- Python files: `snake_case.py` (e.g., `lineup_optimizer.py`, `models.py`)
- TypeScript files: `PascalCase.tsx` or `camelCase.ts` (e.g., `page.tsx`, `api-client.ts`)
- Config files: `kebab-case.yaml` or `kebab-case.yml` (e.g., `config.yaml`, `docker-compose.yml`)
- Test files: `test_<module>.py` (e.g., `test_optimize.py`)

**Directories:**
- Python packages: `snake_case` (e.g., `constraints/`, `optimizer/`)
- Next.js app: `app/` (standard Next.js app directory structure)
- Components: `PascalCase` or `snake_case` (e.g., `OptimizerPanel.tsx`, `utils/`)

**Functions:**
- Python: `snake_case()` (e.g., `calculate_metrics()`, `get_optimal_lineup()`)
- TypeScript: `camelCase()` (e.g., `calculateMetrics()`, `getOptimalLineup()`)

**Variables:**
- Python: `snake_case` (e.g., `optimal_lineup`, `race_data`)
- TypeScript: `camelCase` (e.g., `optimalLineup`, `raceData`)

**Types:**
- Python: `PascalCase` classes (e.g., `OptimizationRequest`, `DriverModel`)
- TypeScript: `PascalCase` interfaces/types (e.g., `OptimizationRequest`, `DriverModel`)

## Where to Add New Code

**New Backend API Endpoint:**
- Primary code: `apps/backend/app/api/<endpoint_name>.py`
- Models: Add to `apps/backend/app/models.py` if needed
- Tests: Add to `apps/backend/app/tests/`
- Documentation: Update in app README or docs

**New Backend Service:**
- Primary code: `apps/backend/app/<service_name>.py`
- Models: Add to `apps/backend/app/models.py`
- Tests: Add to `apps/backend/app/tests/`
- Entry points: Register in `apps/backend/app/main.py`

**New Package (Shared Logic):**
- Create in `packages/`
- Structure: `packages/<package_name>/src/<package_name>/`
- Tests: `packages/<package_name>/tests/`
- Install: Add to `packages/<package_name>/pyproject.toml`

**New Frontend Component:**
- Components: `apps/frontend/src/components/<ComponentName>.tsx`
- Pages: `apps/frontend/src/app/<page-name>/page.tsx`
- Types: `apps/frontend/src/types/index.ts`
- Tests: `apps/frontend/src/app/<page-name>/__tests__/`

**New Script:**
- Standalone scripts: `scripts/<script_name>.py`
- Data processing: `scripts/etl/`

**New Data Source:**
- External data: `data/imports/`
- Historical data: `data/historical/<year>/`

## Special Directories

**node_modules/:**
- Purpose: Node.js dependencies
- Generated: Yes
- Committed: No

**.venv/:**
- Purpose: Python virtual environment
- Generated: Yes
- Committed: No

**__pycache__/:**
- Purpose: Python bytecode cache
- Generated: Yes
- Committed: No

**.next/:**
- Purpose: Next.js build cache
- Generated: Yes
- Committed: No

**.git/:**
- Purpose: Git repository
- Generated: Yes
- Committed: Yes

**.turbo/:**
- Purpose: Turborepo build cache
- Generated: Yes
- Committed: No

**output/:**
- Purpose: Generated outputs (simulations, visualizations)
- Generated: Yes
- Committed: No

**logs/:**
- Purpose: Application logs
- Generated: Yes
- Committed: No

**dist/:**
- Purpose: Distribution artifacts
- Generated: Yes
- Committed: No

---

*Structure analysis: 2026-02-11*
