# Technology Stack

**Analysis Date:** 2026-02-11

## Languages

**Primary:**
- **Python 3.11+** - Backend services, ML/AI models, data processing
  - Used in: `apps/backend/`, `apps/native_mac/`, `packages/`, `apps/airflow/`, `scripts/`

**Secondary:**
- **TypeScript 5.3.3** - Frontend web application
  - Used in: `apps/frontend/`

## Runtime

**Environment:**
- **Python 3.12.7** - Current runtime environment
- **Node.js** - Frontend development and build

**Package Manager:**
- **npm 10.0.0** - Frontend dependencies and monorepo management
  - Lockfile: `package-lock.json` (present)
- **pip + hatchling** - Python packages with PyPI publishing
  - Lockfile: `uv.lock` (apps/backend), `setup.py` (packages)

## Frameworks

**Core:**
- **FastAPI 0.104.1** - Backend REST API framework
  - Location: `apps/backend/app/`
  - Purpose: API endpoints for DFS optimization, ontology management

- **Next.js 14.2.21** - Frontend framework
  - Location: `apps/frontend/src/`
  - Purpose: Web UI with SSR, client-side rendering

- **React 18.2.0** - UI library
  - Used with: Next.js

- **Apache Airflow** - Workflow orchestration
  - Location: `apps/airflow/`
  - Purpose: DAG-based job scheduling for data pipelines

**Testing:**
- **pytest 7.4.3** - Python testing framework
  - Location: `apps/backend/app/tests/`, `packages/*/tests/`
  - Config: Pytest.ini files with path configurations

- **Jest 29.7.0** - JavaScript testing framework
  - Location: `apps/frontend/`
  - Config: `jest.config.js`
  - Environment: `jest-environment-jsdom`

- **@testing-library/jest-dom** - DOM matchers for Jest
- **@testing-library/react** - React component testing

**Build/Dev:**
- **Turbo 2.0.0** - Monorepo build tool
  - Config: `turbo.json`
  - Purpose: Orchestrate builds across workspaces

- **Hatchling** - Python build backend
  - Location: `apps/backend/pyproject.toml`
  - Purpose: Build and package Python modules

**GUI:**
- **PySide6 6.6.0+** - Desktop GUI framework for macOS app
  - Location: `apps/native_mac/gui/`

## Key Dependencies

**Critical - Backend:**
- **neo4j 5.15.0** - Graph database for NASCAR ontology
  - Protocol: bolt:// (primary), neo4j:// (standard), bolt+s:// (TLS)
  - Location: `apps/backend/app/config.py`

- **uvicorn[standard] 0.24.0** - ASGI server for FastAPI

- **pydantic 2.5.0** - Data validation and settings management
  - Location: `apps/backend/pyproject.toml`

- **redis 5.0+** - In-memory cache and job queue
  - Used for: Rate limiting, session storage, job state persistence
  - Location: `apps/backend/app/config.py`

- **pulp 2.7.0** - Linear programming solver for optimization

**Critical - ML/AI:**
- **jax 0.4.0+** - Machine learning framework
- **jaxlib 0.4.0+** - JAX runtime
- **numpyro 0.13.0+** - Probabilistic programming with JAX
- **numpy >=1.26.0** - Numerical computing
- **pandas >=2.1.0** - Data manipulation

**Critical - Frontend:**
- **typescript 5.3.3** - Type-safe JavaScript
- **@types/node**, **@types/react**, **@types/react-dom** - TypeScript definitions

**Critical - ML Infrastructure:**
- **torch >=2.0.0** - Deep learning framework (axiomatic-kernel package)
- **transformers >=4.30.0** - Hugging Face model library
- **datasets >=2.12.0** - ML datasets loading

**Critical - Graph/Network:**
- **pgmpy >=0.1.20** - Probabilistic Graphical Models library
- **networkx >=3.0** - Graph algorithms

**Critical - Utilities:**
- **structlog >=24.1.0** - Structured logging
- **sqlalchemy >=2.0.0** - ORM for database access
- **ulid-py >=1.1.0** - Unique ID generation
- **matplotlib >=3.5.0** - Plotting (ML results visualization)

## Configuration

**Environment:**
- **.env** - Environment-specific configuration
- **.env.example** - Template for required environment variables
- **config.yaml** - YAML-based configuration
- **.python-version** - Python version pinning (3.12.7)

**Build:**
- **turbo.json** - Turbo build pipeline configuration
- **tsconfig.json** - TypeScript compiler options
- **jest.config.js** - Jest testing configuration
- **pyproject.toml** - Python project metadata and dependencies

**Docker:**
- **docker-compose.yml** - Development Docker Compose configuration
- **docker-compose.prod.yml** - Production Docker Compose configuration
- **Dockerfile** - Multi-stage builds for backend and frontend
- **.dockerignore** - Docker build exclusions

## Platform Requirements

**Development:**
- **macOS** (primary)
- **Python 3.11+** with venv or uv
- **Node.js 18+** with npm 10
- **Docker** and **docker-compose** for local services

**Production:**
- **Linux** (Ubuntu/Debian recommended)
- **Python 3.11+** runtime
- **Node.js 18+** runtime
- **Docker** with Docker Swarm or Docker Compose 2.0+
- **Memory:**
  - Neo4j: 2-4GB minimum (4GB recommended for production)
  - Redis: 128-256MB minimum
  - Backend: 1-2GB minimum
  - Frontend: 512MB minimum
  - Airflow: 1-2GB minimum
- **CPU:**
  - Backend: 1-2 cores (4+ for production with multiple workers)
  - Frontend: 0.25-1 core
  - Airflow: 1 core (4+ for distributed executor)

---

*Stack analysis: 2026-02-11*
