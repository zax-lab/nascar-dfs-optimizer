# Architecture

**Analysis Date:** 2026-02-11

## Pattern Overview

**Overall:** Monorepo with Multi-App Microservices Architecture

**Key Characteristics:**
- Turborepo monorepo structure with separate applications and packages
- Python backend using FastAPI for REST API
- Next.js frontend with React 18
- Modular packages for reusable core logic (axiomatic-kernel, axiomatic-sim)
- Event-driven job processing with Celery/Redis (implied by architecture)
- Bayesian inference and simulation-based decision making

## Layers

**API Layer:**
- Purpose: Expose REST API endpoints for external clients
- Location: `apps/backend/app/api/`
- Contains: API routers, controllers, request/response models
- Depends on: Service layer modules (optimizer, calibration, etc.)
- Used by: Frontend applications via HTTP/REST
- Key files:
  - `apps/backend/app/api/optimize.py` - Main optimization endpoint
  - `apps/backend/app/api/nascar_optimize.py` - NASCAR-specific optimization
  - `apps/backend/app/api/health.py` - Health check endpoint
  - `apps/backend/app/api/contracts.py` - Smart contract interactions

**Service Layer:**
- Purpose: Business logic and orchestration
- Location: `apps/backend/app/`
- Contains: Core application logic, modeling, optimization algorithms
- Depends on: Packages (axiomatic-kernel, axiomatic-sim), database (Neo4j)
- Used by: API layer
- Key modules:
  - `apps/backend/app/lineup_optimizer.py` - Main optimization engine
  - `apps/backend/app/portfolio_generator.py` - Portfolio generation
  - `apps/backend/app/ontology.py` - Knowledge graph integration
  - `apps/backend/app/models.py` - Data models
  - `apps/backend/app/kernel.py` - Kernel/training functions

**Domain/Logic Layer (Packages):**
- Purpose: Shared, reusable domain logic across applications
- Location: `packages/axiomatic-kernel/`, `packages/axiomatic-sim/`
- Contains: Domain models, simulation logic, inference algorithms
- Depends on: ML frameworks (JAX, NumPyro), numerical libraries
- Used by: Backend service layer
- Key packages:
  - `packages/axiomatic-kernel/` - Data models, projection models, dataset management
  - `packages/axiomatic-sim/` - State space simulation, scenario generation

**Data Layer:**
- Purpose: Data storage and retrieval
- Location: `data/`, Neo4j database, SQLite database
- Contains: Historical race data, Neo4j graph database for entity relationships
- Depends on: SQLAlchemy (ORM), Neo4j driver
- Used by: Service layer for data access
- Data sources:
  - `data/historical/` - Historical NASCAR race data
  - `data/imports/` - External data imports
  - `data/telemetry/` - Telemetry data
  - Neo4j - Knowledge graph for drivers, tracks, teams

**Presentation Layer:**
- Purpose: User interface and data visualization
- Location: `apps/frontend/`, `apps/native_mac/`
- Contains: React components, Next.js pages, native macOS GUI
- Depends on: Backend API, internal data stores
- Used by: End users
- Key files:
  - `apps/frontend/src/app/page.tsx` - Main application page
  - `apps/frontend/src/components/` - React components
  - `apps/native_mac/gui/` - macOS native GUI (PySide6)

## Data Flow

**Optimization Request Flow:**

1. **Client Request:** User submits optimization request via frontend
   - Request includes: race ID, salary cap, number of drivers, constraints
   - Location: `apps/frontend/src/app/page.tsx`

2. **API Routing:** Request received by FastAPI endpoint
   - FastAPI app entry: `apps/backend/app/main.py`
   - Routed to appropriate handler: `apps/backend/app/api/optimize.py`

3. **Validation & Authentication:** Request validated against Pydantic models
   - Validation: `apps/backend/app/config.py`
   - Authentication: `apps/backend/app/security.py`
   - Rate limiting: `apps/backend/app/rate_limit.py`

4. **Job Submission:** Request transformed into job and queued
   - Job management: `apps/backend/app/job_manager.py`
   - Queue processing: Celery workers (implied by architecture)

5. **Optimization Execution:**
   - Load priors: `apps/backend/app/priors.py`
   - Build belief model: Uses `packages/axiomatic-kernel/`
   - Generate scenarios: Uses `packages/axiomatic-sim/`
   - Run simulations: Monte Carlo simulation (configurable n_simulations)
   - Optimize lineup: Solves constrained optimization problem
   - Apply constraints: `apps/backend/app/constraints/`

6. **Result Generation:**
   - Generate projections: Driver-level win probability distributions
   - Calculate metrics: Expected value, ceiling, risk metrics
   - Format results: Return structured JSON response

7. **Response Delivery:** Results returned to client
   - Response includes: Optimal lineup, projections, metrics, metadata
   - Frontend renders results with visualizations

**State Management:**
- API state managed via FastAPI dependency injection
- Job queue state managed via Celery/Redis
- Database state managed via Neo4j (graph data) and SQLite (relational)
- Cache layer: Redis for rate limiting and cache invalidation
- Configuration: Pydantic settings loaded from environment variables and config.yaml

## Key Abstractions

**Optimization Engine:**
- Purpose: Core decision-making engine for lineup selection
- Examples:
  - `apps/backend/app/lineup_optimizer.py`
  - `apps/backend/app/portfolio_generator.py`
- Pattern: Multi-objective optimization with constraints, using PULP for solving

**Knowledge Graph:**
- Purpose: Entity relationship management for NASCAR entities
- Examples:
  - `apps/backend/app/ontology.py`
  - Neo4j database
- Pattern: Graph database schema with drivers, tracks, teams, historical relationships

**Simulation Engine:**
- Purpose: Monte Carlo simulation for race outcome prediction
- Examples:
  - `packages/axiomatic-sim/`
  - `scripts/track_aware_simulator.py`
- Pattern: Bayesian hierarchical pooling with track-aware simulation

**Bayesian Inference Engine:**
- Purpose: Model uncertainty and update beliefs based on data
- Examples:
  - `packages/axiomatic-kernel/projection_model.py`
  - `packages/axiomatic-sim/tests/test_cbn_sampling.py`
- Pattern: Hierarchical Bayesian modeling with time decay and context features

**Constraint System:**
- Purpose: Enforce business rules and legal constraints
- Examples:
  - `apps/backend/app/constraints/dk_rules.py`
  - `apps/backend/app/constraints/leverage_aware.py`
  - `apps/backend/app/constraints/diversity.py`
- Pattern: Constraint programming with penalty-based optimization

## Entry Points

**Backend API:**
- Location: `apps/backend/app/main.py`
- Triggers: HTTP requests via FastAPI (port configurable)
- Responsibilities:
  - Initialize FastAPI app with routes, middleware
  - Configure logging, security, CORS
  - Define dependency injection for database connections
  - Serve health check and API documentation

**Frontend Application:**
- Location: `apps/frontend/src/app/page.tsx`
- Triggers: User navigation in browser
- Responsibilities:
  - Fetch optimization parameters from user
  - Call backend API endpoints
  - Display optimization results
  - Provide interactive visualizations

**CLI Entry Point:**
- Location: `main.py`
- Triggers: Command-line invocation
- Responsibilities:
  - Seed database with historical data
  - Provide CLI interface for data management

**Native Mac Application:**
- Location: `apps/native_mac/gui/controllers/`
- Triggers: User interaction in macOS GUI
- Responsibilities:
  - Provide desktop GUI for power users
  - Call backend API for optimization
  - Display results in custom UI

## Error Handling

**Strategy:** Centralized exception handling with structured logging

**Patterns:**
- FastAPI exception handlers for API errors
- Pydantic validation errors for request validation
- Custom exceptions for business logic errors
- Structured logging with `structlog` for debugging
- Rate limiting with rate limit exceeded errors

**Key mechanisms:**
- Logging configuration: `apps/backend/app/logging_config.py`
- Error responses: Standardized JSON error format
- Retry logic: Exponential backoff for transient errors

## Cross-Cutting Concerns

**Logging:** Structured logging with `structlog`, environment-based log levels

**Validation:** Pydantic models for request/response validation, custom validators

**Authentication:**
- API key authentication via header
- Environment-based configuration
- Secure password handling with minimum length validation

**Rate Limiting:** Redis-based rate limiting per endpoint with configurable limits

**CORS:** Configurable CORS origins for frontend-backend communication

**Security:** Input sanitization, environment variable management, rate limiting

---

*Architecture analysis: 2026-02-11*
