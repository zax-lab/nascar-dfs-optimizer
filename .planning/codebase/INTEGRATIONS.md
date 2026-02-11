# External Integrations

**Analysis Date:** 2026-02-11

## APIs & External Services

**NASCAR Official API:**
- **Service:** NASCAR DFS engine data ingestion
  - URL: `https://api.nascar.com` (configured via `NASCAR_API_URL` env var)
  - Usage: Historical race data, driver statistics, track information
  - Status: Currently optional (environment variable)
  - Files:
    - `apps/backend/app/config.py` - Configuration and documentation
    - `docker-compose.yml` - Environment variable setup
    - `apps/airflow/requirements.txt` - Not directly used (wait for implementation)

**ML Model Service (Optional):**
- **Service:** TinyLlama LLM checkpoint loading
  - Location: `/models/tinyllama` (configured via `TINYLLAMA_CHECKPOINT` env var)
  - Usage: Axiomatic kernel projection tooling (axiomatic-kernel package)
  - Frameworks: PyTorch + Hugging Face Transformers
  - Files:
    - `packages/axiomatic-kernel/pyproject.toml` - Dependencies (torch, transformers, datasets)
    - `packages/axiomatic-kernel/tinyllama_finetune.py` - Training/finetuning script
    - `apps/backend/app/config.py` - Environment variable configuration

## Data Storage

**Databases:**

**Neo4j Graph Database:**
- **Type:** Property graph database
- **Version:** 5.15.0-community
- **Purpose:** Store NASCAR ontology (drivers, tracks, races, relationships)
- **Connection Protocol:**
  - bolt:// - Standard Bolt protocol (local dev)
  - neo4j:// - Standard Neo4j protocol
  - bolt+s:// - Bolt with TLS (production)
  - neo4j+s:// - Neo4j with TLS (production)
- **Port:** 7687 (Bolt), 7474 (HTTP browser interface)
- **Plugins:** APOC for advanced Cypher operations
- **Environment Variables:**
  - `NEO4J_URI` - Connection URI (default: `bolt://localhost:7687`)
  - `NEO4J_USER` - Username (default: `neo4j`)
  - `NEO4J_PASSWORD` - Password (required, min 8 chars)
- **Location:**
  - Config: `apps/backend/app/config.py`
  - Service: `docker-compose.yml` (neo4j service)
  - Data volumes: `neo4j_data`, `neo4j_logs`, `neo4j_import`
- **ORM/Driver:** `neo4j==5.15.0` Python driver
  - Usage: Cypher queries via Python driver in backend app

**SQLite:**
- **Type:** File-based relational database
- **Purpose:** Airflow metadata storage
- **Connection:** `sqlite:////opt/airflow/airflow.db`
- **Location:**
  - Config: `docker-compose.yml` (airflow service)
  - No external connection required (file-based)

**File Storage:**
- **Location:** Local filesystem
- **Usage:**
  - Race logs: `race-logs.csv` (3.6MB)
  - Backtest output: `backtest_*.png`, `backtest_*.csv`, `backtest_*.txt`
  - Dashboard data: `epistemic.db` (3.5MB) - local SQLite database
- **Mount Points:**
  - `./epistemic.db` - For dashboard application
  - Docker volumes: `neo4j_*`, `redis_data`, `airflow_logs` (persistent across container restarts)

**Caching:**

**Redis In-Memory Cache:**
- **Type:** In-memory data store with persistence
- **Version:** 7-alpine
- **Purpose:**
  - Rate limiting counters (SlowAPI middleware)
  - Session storage and management
  - Job state persistence for background tasks
  - Cache for frequently accessed data
- **Connection:**
  - URL: `redis://redis:6379` (Docker network)
  - Default: `redis://localhost:6379` (local dev)
  - Storage DB: `/1` (separate database for job state)
- **Environment Variables:**
  - `REDIS_URL` - Connection URL
  - `REDIS_PASSWORD` - Optional password for production
  - `RATE_LIMIT_STORAGE_URL` - Redis backend for rate limiting (default: `/1`)
- **Location:**
  - Config: `apps/backend/app/config.py`
  - Service: `docker-compose.yml` (redis service)
  - Data volume: `redis_data`
- **Client:** `redis>=5.0.0` Python driver
- **Config Options:** AOF persistence enabled in production (`--appendonly yes`)

## Authentication & Identity

**API Key Authentication:**
- **Provider:** Custom implementation (no external auth service)
- **Mechanism:** Header-based API key validation
- **Configuration:**
  - `API_KEYS` - Comma-separated API keys (environment variable)
  - `API_KEY_HEADER` - Header name for API key (default: `X-API-Key`)
- **Implementation:**
  - Location: `apps/backend/app/security.py` (require_api_key decorator)
  - Middleware: `slowapi==0.1.9` (SlowAPI rate limiting with auth)
- **Usage:**
  - Environment: `NEXT_PUBLIC_API_KEY=dev-key-12345`
  - CORS: Whitelisted origins (see CORS_ALLOW_ORIGINS)

**Web Browser Auth:**
- No authentication required for UI (read-only access to projections)

## Monitoring & Observability

**Health Checks:**
- **Framework:** Custom health check endpoints
- **Endpoints:**
  - Backend: `/health` (curl `http://localhost:8000/health`)
  - Frontend: HTTP 200 on root (`http://localhost:3000`)
  - Airflow: HTTP 200 on `/health` (`http://localhost:8080/health`)
  - Neo4j: HTTP 200 on 7474 (healthcheck script in docker-compose)
- **Implementation:**
  - Location: `apps/backend/app/main.py`, `docker-compose.yml`
  - Timing: 30s interval, 5 retries, start_period for warm-up
- **Purpose:** Service readiness detection for Docker depends_on

**Structured Logging:**
- **Framework:** structlog >=24.1.0
- **Output:** JSON-formatted logs
- **Features:**
  - Correlation ID middleware for request tracing
  - Log level configuration (DEBUG, INFO, WARNING, ERROR)
  - Log rotation for file output
- **Location:**
  - Config: `apps/backend/app/logging_config.py`
  - Middleware: `app.middleware.CorrelationIDMiddleware`
  - Default level: INFO

**Docker Logging:**
- **Format:** Docker stdout/stderr
- **Volumed:** `airflow_logs` volume for persistent logs
- **Access:** `docker-compose logs -f [service-name]`

## CI/CD & Deployment

**Hosting:**
- **Platform:** Docker-based deployment (primary)
  - Container orchestration: Docker Compose (dev) / Docker Swarm (production)
  - Multi-stage builds: Optimized images with no volumes in production

**CI Pipeline:**
- **Service:** Not explicitly configured
- **Manual:**
  - Build process: `npm run build` (turbo)
  - Docker builds: `docker-compose build`
  - Development: `docker-compose up`
  - Production: `docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d`

**Deployment Commands:**
```bash
# Development
docker-compose -f docker-compose.yml -f docker-compose.override.yml up

# Production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Rebuild after code changes
docker-compose build && docker-compose up -d
```

## Environment Configuration

**Required Environment Variables:**
- `NEO4J_URI` - Neo4j connection string
- `NEO4J_USER` - Neo4j username
- `NEO4J_PASSWORD` - Neo4j password (min 8 chars)

**Optional Environment Variables:**
- `REDIS_URL` - Redis connection URL
- `REDIS_PASSWORD` - Redis password
- `API_KEYS` - Comma-separated API keys
- `API_KEY_HEADER` - API key header name
- `RATE_LIMIT_DEFAULT` - Default rate limit (e.g., `100/hour`)
- `NASCAR_API_URL` - NASCAR API endpoint
- `TINYLLAMA_CHECKPOINT` - TinyLlama model path
- `LOG_LEVEL` - Logging verbosity (DEBUG, INFO, WARNING, ERROR)
- `CORS_ALLOW_ORIGINS` - Comma-separated allowed origins

**Secrets Management:**
- **Current:** Environment variables in `.env` files
- **Recommendations:**
  - Use `.env.example` as template
  - Never commit `.env` to version control
  - Use secrets managers in production (AWS Secrets Manager, HashiCorp Vault)
  - Set strong passwords for Neo4j and Redis

## Webhooks & Callbacks

**Incoming:**
- **Status:** None configured
- **Future:** Potential for webhooks from NASCAR API when available

**Outgoing:**
- **Status:** None configured
- **Potential:** Optimization results, data updates, alerts via webhook notifications

## Service Dependencies

**Docker Network:**
- **Network Name:** `nascar-network`
- **Purpose:** DNS-based service discovery
- **Services:**
  - `neo4j:7687` - Backend connects via service name
  - `redis:6379` - Backend cache connection
  - `backend:8000` - Frontend API calls
  - `airflow:8080` - Internal Airflow communication

**Service Health Dependency Chain:**
1. Neo4j must be healthy before backend and Airflow start
2. Redis must be healthy before backend starts
3. Backend must be ready before frontend starts
4. Neo4j must be healthy before Airflow starts

---

*Integration audit: 2026-02-11*
