# Production Readiness Architecture

**Domain:** Production Operations for FastAPI + Neo4j ML Optimization Service
**Researched:** 2026-01-28
**Overall confidence:** HIGH

## Executive Summary

The current architecture is a **FastAPI monolith** with **in-memory state** and **Neo4j persistence**. To achieve production readiness for v1.1, we need to add:

1. **Job state persistence** (Redis) - CRITICAL priority
2. **Health monitoring** (Kubernetes probes, dependency health) - HIGH priority
3. **Observability stack** (OpenTelemetry + Prometheus + Grafana) - HIGH priority
4. **Authentication layer** (JWT middleware) - MEDIUM priority
5. **Background task processing** (Celery) - MEDIUM priority

**Critical finding:** The current `/optimize` endpoint uses FastAPI's built-in `BackgroundTasks` which are **not durable**. If the container restarts, all active jobs are lost. This is the **highest priority fix** for production.

**Recommended integration approach:**
- **Phase 1:** Add health checks + structured logging (low risk, high value)
- **Phase 2:** Migrate job state from in-memory to Redis (critical for durability)
- **Phase 3:** Add authentication middleware (requires user testing)
- **Phase 4:** Add OpenTelemetry tracing (requires infrastructure setup)
- **Phase 5:** Replace BackgroundTasks with Celery for long-running MCMC jobs

## Current Architecture Analysis

### Existing Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js)                       │
└─────────────────────────────┬───────────────────────────────────┘
                              │ HTTP/REST
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend (Uvicorn)                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  API Layer:                                               │  │
│  │  - POST /optimize (BackgroundTasks - NOT DURABLE)        │  │
│  │  - GET /optimize/{run_id}/status                          │  │
│  │  - GET /optimize/{run_id}/result                          │  │
│  │  - POST /ownership                                        │  │
│  │  - POST /contest-sim                                      │  │
│  │  - POST /optimize-with-leverage                           │  │
│  │  - GET /health (basic only)                               │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Business Logic:                                          │  │
│  │  - LineupOptimizer (NumPyro, JAX)                         │  │
│  │  - HybridOwnershipEstimator                              │  │
│  │  - ContestSimulator                                       │  │
│  │  - LeverageAwareOptimizer                                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Data Layer:                                              │  │
│  │  - OntologyDriver (Neo4j)                                 │  │
│  │  - SQLAlchemy models (epistemic DB)                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  STATE (PROBLEM: Lost on restart):                        │  │
│  │  - optimization_jobs: Dict[str, OptimizationStatus]      │  │
│  │  - optimization_results: Dict[str, OptimizeResponse]     │  │
│  │  - _ownership_estimator_cache: Dict[str, Any]            │  │
│  │  - _payout_curve_cache: Dict[str, Any]                   │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────┬───────────────────────────────────┘
                              │ Bolt Protocol
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Neo4j (v5.15.0)                          │
│  - Driver, Track, Race nodes with metaphysical properties      │
│  - Connection pooling (max 50 connections)                     │
└─────────────────────────────────────────────────────────────────┘
```

### Current Issues

| Issue | Severity | Impact | Production Blocker |
|-------|----------|--------|-------------------|
| **In-memory job state** | CRITICAL | Jobs lost on container restart | YES |
| **No dependency health checks** | HIGH | Can't detect Neo4j connection failures | YES |
| **Basic /health only** | MEDIUM | No readiness/liveness probes | NO (but K8s won't work well) |
| **No authentication** | MEDIUM | API is completely open | NO (if internal) |
| **No structured logging** | MEDIUM | Can't debug production issues | NO |
| **No observability/tracing** | MEDIUM | Can't see request flow across services | NO |
| **BackgroundTasks for long jobs** | HIGH | Not suitable for MCMC (10+ seconds) | YES |
| **No rate limiting enforcement** | LOW | DoS risk | NO |
| **No request timeout handling** | MEDIUM | Hanging requests | NO |

## Recommended Architecture for v1.1 Production

### Target Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js)                       │
└─────────────────────────────┬───────────────────────────────────┘
                              │ HTTP (JWT token)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend (Uvicorn)                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  NEW: Authentication Middleware                          │  │
│  │  - JWT validation (FastAPI Security dependency)          │  │
│  │  - Optional: API key support for machine clients         │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  API Layer:                                               │  │
│  │  - POST /optimize (returns job_id, queues to Celery)     │  │
│  │  - GET /jobs/{job_id}/status (reads from Redis)          │  │
│  │  - GET /jobs/{job_id}/result (reads from Redis/S3)       │  │
│  │  - POST /ownership                                        │  │
│  │  - POST /contest-sim                                      │  │
│  │  - POST /optimize-with-leverage                           │  │
│  │  - GET /health (checks Neo4j, Redis, Celery)             │  │
│  │  - GET /ready (checks all deps ready)                     │  │
│  │  - GET /metrics (Prometheus endpoint)                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  NEW: Observability Middleware                           │  │
│  │  - OpenTelemetry request tracing (trace propagation)      │  │
│  │  - Request ID injection                                   │  │
│  │  - Structured JSON logging (log correlation)             │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Business Logic (unchanged):                             │  │
│  │  - LineupOptimizer, OwnershipEstimator, etc.             │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  NEW: Job Queue Client                                    │  │
│  │  - Celery client for submitting optimization jobs        │  │
│  │  - Result backend integration (Redis)                    │  │
│  └──────────────────────────────────────────────────────────┘  │
└───────────┬───────────────────────┬─────────────────┬───────────┘
            │                       │                 │
            │ Celery protocol       │ Redis           │ Bolt
            ▼                       │                 ▼
┌─────────────────────┐   ┌─────────────────┐  ┌─────────────────┐
│   Celery Workers    │   │  Redis (Job     │  │  Neo4j (v5.15)  │
│  ┌───────────────┐  │   │   State +      │  │  (unchanged)    │
│  │ - MCMC jobs   │  │   │   Cache)       │  └─────────────────┘
│  │ - Scenarios   │  │   │ - job_status  │
│  │ - Portfolio   │  │   │ - job_results │
│  │   optimization│  │   │ - cache       │
│  └───────────────┘  │   └─────────────────┘
└─────────────────────┘
            │
            ▼
┌─────────────────────┐
│  S3 / Volume        │
│  (Large result      │
│   storage)          │
└─────────────────────┘
```

### Component Boundaries

| Component | Responsibility | Communicates With | State |
|-----------|---------------|-------------------|-------|
| **FastAPI Backend** | HTTP API, auth, orchestration | Frontend, Redis, Neo4j, Celery | Stateless |
| **Celery Workers** | Long-running optimization tasks | Redis, Neo4j, S3 | Stateless (pulls from queue) |
| **Redis** | Job state, cache, Celery backend | FastAPI, Celery Workers | Durable (with persistence) |
| **Neo4j** | Ontology, driver/track/race metadata | FastAPI, Celery Workers | Durable |
| **S3/Volume** | Large result storage (scenarios, portfolios) | Celery Workers | Durable |

### Data Flow Changes

#### Current (Problematic) Flow

```
Client → FastAPI → BackgroundTasks → Optimizer (in-memory)
         ↓           ↓
      Returns     Job lost if restart
      job_id     (in-memory dict)
```

#### Proposed (Durable) Flow

```
Client → FastAPI → Celery Queue → Redis → Celery Worker → Optimizer
         ↓           ↓                              ↓
      Returns     Job persisted                Result stored
      job_id     (Redis hash)                  (Redis/S3)
         ↓                                           ↓
      Client polls                             Client retrieves
      /jobs/{id}/status                        /jobs/{id}/result
         ↓                                           ↓
      Reads Redis                              Reads Redis/S3
```

## Patterns to Follow

### Pattern 1: Redis-Based Job State Management

**What:** Replace in-memory `optimization_jobs` and `optimization_results` dictionaries with Redis-backed state.

**When:** All optimization endpoints (`/optimize`, `/contest-sim`, `/optimize-with-leverage`) need durable job tracking.

**Why:** Prevents job loss on container restarts; enables horizontal scaling.

**Confidence:** HIGH - Standard pattern verified with official Redis docs.

**Example Implementation:**

```python
import redis
import json
from typing import Optional
from datetime import datetime, timedelta

class JobStateManager:
    """Redis-backed job state manager."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis = redis.from_url(redis_url)
        self.job_ttl = 86400  # 24 hours

    def create_job(self, job_id: str, request_data: dict) -> None:
        """Create a new job record."""
        job_key = f"job:{job_id}"
        job_data = {
            "status": "pending",
            "progress": 0.0,
            "created_at": datetime.utcnow().isoformat(),
            "request": json.dumps(request_data),
            "error": None
        }
        self.redis.hset(job_key, mapping=job_data)
        self.redis.expire(job_key, self.job_ttl)

    def update_status(self, job_id: str, status: str, progress: float = None) -> None:
        """Update job status and progress."""
        job_key = f"job:{job_id}"
        updates = {"status": status}
        if progress is not None:
            updates["progress"] = str(progress)
        updates["updated_at"] = datetime.utcnow().isoformat()
        self.redis.hset(job_key, mapping=updates)

    def set_result(self, job_id: str, result: dict) -> None:
        """Store job result (can be large, use separate key)."""
        result_key = f"job_result:{job_id}"
        self.redis.set(result_key, json.dumps(result), ex=self.job_ttl)
        self.redis.hset(f"job:{job_id}", "status", "completed")

    def get_job(self, job_id: str) -> Optional[dict]:
        """Get job status."""
        job_key = f"job:{job_id}"
        data = self.redis.hgetall(job_key)
        if not data:
            return None
        return {k.decode(): v.decode() for k, v in data.items()}

    def get_result(self, job_id: str) -> Optional[dict]:
        """Get job result."""
        result_key = f"job_result:{job_id}"
        data = self.redis.get(result_key)
        if not data:
            return None
        return json.loads(data)
```

**Integration with FastAPI:**

```python
# In main.py
from app.job_state import JobStateManager

app.state.job_manager = JobStateManager(
    redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0")
)

@router.post("/optimize")
async def submit_optimization(request: OptimizeRequest):
    job_id = str(uuid.uuid4())
    app.state.job_manager.create_job(job_id, request.dict())
    # Submit to Celery instead of BackgroundTasks
    celery_app.send_task('app.tasks.run_optimization', args=[job_id, request.dict()])
    return {"job_id": job_id, "status": "pending"}

@router.get("/jobs/{job_id}/status")
async def get_job_status(job_id: str):
    job = app.state.job_manager.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job
```

### Pattern 2: Health Check with Dependency Validation

**What:** Implement `/health`, `/ready`, and `/live` endpoints that validate external dependencies.

**When:** Kubernetes deployments, container orchestration, any production environment.

**Why:** Enable orchestration platforms to detect unhealthy instances and restart them.

**Confidence:** HIGH - Standard Kubernetes pattern.

**Example Implementation:**

```python
from fastapi import HTTPException
import redis
from neo4j import GraphDatabase

class HealthChecker:
    """Health check with dependency validation."""

    def __init__(self, neo4j_uri: str, redis_url: str):
        self.neo4j_uri = neo4j_uri
        self.redis_url = redis_url

    async def check_neo4j(self) -> dict:
        """Check Neo4j connectivity."""
        try:
            driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
            )
            driver.verify_connectivity()
            driver.close()
            return {"status": "healthy", "latency_ms": 5}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def check_redis(self) -> dict:
        """Check Redis connectivity."""
        try:
            r = redis.from_url(self.redis_url)
            r.ping()
            return {"status": "healthy", "latency_ms": 2}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def check_celery(self) -> dict:
        """Check Celery worker availability."""
        try:
            from celery import Celery
            app = Celery('tasks', broker=self.redis_url)
            inspect = app.control.inspect()
            workers = inspect.active()
            if workers:
                return {"status": "healthy", "workers": len(workers)}
            return {"status": "unhealthy", "error": "No workers available"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

@app.get("/health")
async def health_check():
    """Basic liveness probe (is the app running?)."""
    return {"status": "healthy", "version": "0.3.0"}

@app.get("/ready")
async def readiness_check():
    """Readiness probe (are all dependencies available?)."""
    checker = HealthChecker(
        neo4j_uri=os.getenv("NEO4J_URI"),
        redis_url=os.getenv("REDIS_URL")
    )

    checks = {
        "neo4j": await checker.check_neo4j(),
        "redis": await checker.check_redis(),
        "celery": await checker.check_celery()
    }

    all_healthy = all(c["status"] == "healthy" for c in checks.values())

    if not all_healthy:
        raise HTTPException(503, detail=checks)

    return {"status": "ready", "checks": checks}
```

**Kubernetes Integration:**

```yaml
# deployment.yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
```

### Pattern 3: JWT Authentication Middleware

**What:** Add JWT authentication using FastAPI dependencies.

**When:** Securing API endpoints for production use.

**Why:** Prevent unauthorized access; enable per-user rate limiting.

**Confidence:** MEDIUM - Standard pattern, but provider choice needs validation.

**Example Implementation:**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import os

security = HTTPBearer()

async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Verify JWT token and return payload."""
    try:
        token = credentials.credentials
        payload = jwt.decode(
            token,
            os.getenv("JWT_SECRET"),
            algorithms=[os.getenv("JWT_ALGORITHM", "HS256")]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

# Optional: Skip auth for specific endpoints
from fastapi import Request

async def optional_auth(request: Request) -> Optional[dict]:
    """Optional authentication for public endpoints."""
    if "authorization" not in request.headers:
        return None
    try:
        return await verify_token(
            HTTPAuthorizationCredentials(
                scheme="bearer",
                credentials=request.headers["authorization"].split()[1]
            )
        )
    except HTTPException:
        return None

# Usage in endpoints
@app.post("/optimize")
async def submit_optimization(
    request: OptimizeRequest,
    user: dict = Depends(verify_token)  # Require auth
):
    # user contains {user_id, email, ...}
    job_id = str(uuid.uuid4())
    ...

@app.get("/health")
async def health_check(
    user: Optional[dict] = Depends(optional_auth)  # Optional auth
):
    # Works without auth, but user is available if provided
    return {"status": "healthy"}
```

### Pattern 4: OpenTelemetry Tracing Integration

**What:** Add distributed tracing with OpenTelemetry.

**When:** Production debugging, performance analysis, multi-service request tracking.

**Why:** See request flow across FastAPI → Celery → Neo4j; identify bottlenecks.

**Confidence:** MEDIUM - Community articles reviewed, official docs verification needed.

**Example Implementation:**

```python
# In main.py startup
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

@app.on_event("startup")
async def setup_telemetry():
    """Setup OpenTelemetry tracing."""
    # Configure tracer
    trace.set_tracer_provider(TracerProvider())
    tracer_provider = trace.get_tracer_provider()

    # Add OTLP exporter (for Grafana Tempo)
    otlp_exporter = OTLPSpanExporter(
        endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
        insecure=True
    )
    tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)

    # Instrument Redis
    RedisInstrumentor().instrument(tracer_provider=tracer_provider)

# In Celery tasks
from opentelemetry import trace
from opentelemetry.propagate import inject

tracer = trace.get_tracer(__name__)

@celery_app.task
def run_optimization(job_id: str, request: dict):
    """Run optimization as Celery task."""
    # Create span with context from FastAPI
    headers = {}
    inject(headers)  # Inject trace context into headers

    with tracer.start_as_current_span("run_optimization") as span:
        span.set_attribute("job_id", job_id)
        # Optimization logic here
        ...
```

**Grafana Tempo Integration:**

```yaml
# docker-compose.yml addition
tempo:
  image: grafana/tempo:latest
  ports:
    - "3200:3200"  # Tempo query
    - "4317:4317"  # OTLP gRPC
  command:
    - "--storage.trace.backend=local"
    - "--storage.trace.local.path=/var/lib/tempo"
  volumes:
    - tempo_data:/var/lib/tempo
```

### Pattern 5: Celery for Long-Running Jobs

**What:** Replace FastAPI `BackgroundTasks` with Celery for durable background processing.

**When:** Jobs take >5 seconds (MCMC optimization, scenario generation).

**Why:** Jobs survive restarts; can scale workers independently; built-in retries.

**Confidence:** HIGH - Official Celery docs verified.

**Example Implementation:**

```python
# app/tasks.py
from celery import Celery
import os

celery_app = Celery(
    'nascar_optimizer',
    broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://localhost:6379/0')
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3300,  # 55 min soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)

@celery_app.task(bind=True)
def run_optimization(self, job_id: str, request: dict):
    """Run optimization as Celery task."""
    from app.job_state import JobStateManager
    from app.optimizer import LineupOptimizer

    job_manager = JobStateManager()

    try:
        # Update status
        job_manager.update_status(job_id, "running", 0.1)

        # Run optimization (same logic as before)
        optimizer = LineupOptimizer(...)
        result = optimizer.optimize()

        # Store result
        job_manager.set_result(job_id, result)

        return {"status": "completed", "job_id": job_id}

    except Exception as e:
        job_manager.update_status(job_id, "failed")
        self.retry(exc=e, countdown=60, max_retries=3)

@celery_app.task(bind=True)
def run_contest_simulation(self, job_id: str, request: dict):
    """Run contest simulation as Celery task."""
    # Similar pattern
    ...

# In main.py
@app.post("/optimize")
async def submit_optimization(request: OptimizeRequest):
    job_id = str(uuid.uuid4())
    app.state.job_manager.create_job(job_id, request.dict())

    # Submit to Celery
    task = run_optimization.delay(job_id, request.dict())

    return {
        "job_id": job_id,
        "celery_task_id": task.id,
        "status": "pending"
    }
```

**Celery Worker Configuration:**

```python
# celery_worker.py
from app.tasks import celery_app
import os

# Worker configuration
celery_app.conf.update(
    worker_concurrency=int(os.getenv('CELERY_WORKER_CONCURRENCY', '2')),
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s',
)

if __name__ == '__main__':
    celery_app.worker_main(['worker', '--loglevel=info'])
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: In-Memory Job State in Production

**What:** Using Python dictionaries (`optimization_jobs = {}`) for job state.

**Why bad:** Lost on container restart; can't scale horizontally; no recovery from failures.

**Instead:** Use Redis or PostgreSQL for job state with TTL for cleanup.

### Anti-Pattern 2: FastAPI BackgroundTasks for Long Jobs

**What:** Using `BackgroundTasks` for MCMC optimization or scenario generation.

**Why bad:** Tied to request lifecycle; no retries; lost if process dies; blocks worker.

**Instead:** Use Celery with Redis broker for durable background processing.

### Anti-Pattern 3: Synchronous External Calls in Request Handler

**What:** Making slow external calls (Neo4j queries, HTTP requests) directly in endpoint.

**Why bad:** Blocks request handler; causes timeouts; poor UX.

**Instead:**
- For fast queries (<100ms): OK in endpoint
- For slow queries (>100ms): Use background tasks or caching
- For very slow queries (>1s): Must use Celery

### Anti-Pattern 4: No Request Timeout Handling

**What:** Letting optimization jobs run indefinitely.

**Why bad:** Resource exhaustion; queue backup; DoS vulnerability.

**Instead:** Set timeouts at multiple levels:
```python
# FastAPI level (using middleware)
# Celery level
@celery_app.task(time_limit=3600, soft_time_limit=3300)

# Optimization level
optimizer.optimize(timeout=300)  # 5 min timeout
```

### Anti-Pattern 5: Silent Failures in Background Jobs

**What:** Background tasks fail without updating job status.

**Why bad:** Users wait forever; no debugging info; poor UX.

**Instead:** Always wrap background tasks in try/except and update status:
```python
try:
    result = run_optimization()
    job_manager.set_result(job_id, result)
except Exception as e:
    logger.error(f"Optimization failed: {e}", exc_info=True)
    job_manager.update_status(job_id, "failed")
    job_manager.set_error(job_id, str(e))
```

## Scalability Considerations

| Concern | At 100 users | At 10K users | At 1M users |
|---------|--------------|--------------|-------------|
| **API concurrency** | 1 FastAPI instance | 3-5 FastAPI instances + load balancer | 10+ instances + autoscaling |
| **Job queue** | Redis + 2 Celery workers | Redis (cluster mode) + 10 workers | Redis Cluster + 50+ workers |
| **Database** | Neo4j single instance | Neo4j with read replicas | Neo4j cluster (CAUSAL_CLUSTERING) |
| **Result storage** | Redis (small results) | Redis + S3 for large results | S3/GCS for all results |
| **Monitoring** | Basic logs | Prometheus + Grafana | Full observability stack + alerts |
| **Authentication** | Optional JWT | JWT + rate limiting | OAuth2 + API keys + rate limiting |

## Recommended Build Order

### Phase 1: Foundation (Week 1-2) - HIGH Confidence

**Goal:** Add health monitoring and structured logging without breaking existing functionality.

1. **Structured JSON logging**
   - Add `python-json-logger` for JSON output
   - Add request ID middleware
   - Configure log levels via environment

2. **Health check endpoints**
   - `/health` (basic liveness)
   - `/ready` (dependency checks for Neo4j)
   - Add to docker-compose healthcheck

3. **Prometheus metrics**
   - Add `prometheus-fastapi-instrumentator`
   - Expose `/metrics` endpoint
   - Track request latency, error rates, job queue depth

**Risk:** LOW - non-breaking additions
**Value:** HIGH - enables production monitoring

### Phase 2: Job State Persistence (Week 2-3) - HIGH Confidence

**Goal:** Migrate from in-memory to Redis-backed job state.

1. **Add Redis to docker-compose**
   ```yaml
   redis:
     image: redis:7-alpine
     ports: ["6379:6379"]
     command: redis-server --appendonly yes
     volumes:
       - redis_data:/data
   ```

2. **Implement JobStateManager**
   - Use pattern from Pattern 1 above
   - Migrate `optimization_jobs` and `optimization_results` to Redis
   - Add TTL for automatic cleanup

3. **Update API endpoints**
   - Change `POST /optimize` to use JobStateManager
   - Change `GET /jobs/{id}/status` to read from Redis
   - Maintain backward compatibility if needed

4. **Add Redis health check**
   - Include in `/ready` endpoint

**Risk:** MEDIUM - requires careful migration
**Value:** CRITICAL - prevents job loss on restart

### Phase 3: Celery Integration (Week 3-4) - HIGH Confidence

**Goal:** Replace BackgroundTasks with Celery for durable job processing.

1. **Add Celery to docker-compose**
   ```yaml
   celery_worker:
     build: ./apps/backend
     command: celery -A app.tasks worker --loglevel=info
     depends_on: [redis]
     environment:
       CELERY_BROKER_URL: redis://redis:6379/0
       CELERY_RESULT_BACKEND: redis://redis:6379/0
   ```

2. **Create app/tasks.py**
   - Move optimization logic to Celery tasks
   - Add error handling and retries

3. **Update FastAPI endpoints**
   - Change from `BackgroundTasks` to `celery_task.delay()`
   - Return job_id immediately

4. **Add Celery health check**
   - Check worker availability in `/ready` endpoint

**Risk:** MEDIUM - changes job execution model
**Value:** HIGH - enables horizontal scaling and retries

### Phase 4: Authentication (Week 4-5) - MEDIUM Confidence

**Goal:** Add JWT authentication to secure API endpoints.

1. **Implement JWT utilities**
   - Add `python-jose` for JWT encoding/decoding
   - Create `/auth/login` endpoint (or use external auth)
   - Implement `verify_token` dependency

2. **Add authentication to endpoints**
   - Require auth for `/optimize`, `/ownership`, `/contest-sim`
   - Keep `/health` and `/docs` public
   - Add optional auth for graceful migration

3. **Add rate limiting**
   - Use `slowapi` (already in main.py)
   - Configure per-user rate limits

4. **Add user context logging**
   - Include user_id in logs
   - Track requests per user

**Risk:** MEDIUM - requires client changes
**Value:** HIGH - required for production security

### Phase 5: Observability (Week 5-6) - MEDIUM Confidence

**Goal:** Add distributed tracing with OpenTelemetry.

1. **Add OpenTelemetry instrumentation**
   - Instrument FastAPI with OpenTelemetry
   - Instrument Redis client
   - Add manual spans for Celery tasks

2. **Setup Jaeger or Tempo**
   - Add to docker-compose
   - Configure exporters

3. **Add trace context propagation**
   - Inject trace context into Celery tasks
   - Propagate to Neo4j queries

4. **Setup Grafana dashboards**
   - Request latency heatmap
   - Error rate by endpoint
   - Job queue depth over time
   - Celery worker utilization

**Risk:** LOW - non-breaking addition
**Value:** MEDIUM - improves debugging

### Phase 6: Optimization for Long-Running Jobs (Week 6+) - LOW Confidence

**Goal:** Handle very long jobs (MCMC with 50K+ scenarios).

1. **Implement job cancellation**
   - Add `DELETE /jobs/{id}` endpoint
   - Cancel Celery tasks
   - Clean up Redis state

2. **Add progress streaming**
   - WebSocket endpoint for real-time progress
   - Server-Sent Events (SSE) alternative

3. **Result pagination**
   - Store large results in S3
   - Paginated retrieval

4. **Job priorities**
   - High-priority queue for paid users
   - Low-priority queue for free users

**Risk:** HIGH - complex features
**Value:** MEDIUM - nice-to-have for scale

## Integration Points with Existing Components

### With Neo4j (Ontology)

**Current:**
```python
ontology_driver = OntologyDriver.get_driver()
```

**Production-ready:**
```python
# Add health check
async def check_neo4j():
    try:
        driver = OntologyDriver.get_driver()
        driver._driver.verify_connectivity()
        return True
    except:
        return False

# Add connection pooling config (already exists in ontology.py)
OntologyDriver(
    uri=os.getenv("NEO4J_URI"),
    user=os.getenv("NEO4J_USER"),
    password=os.getenv("NEO4J_PASSWORD"),
    max_connection_pool_size=int(os.getenv("NEO4J_POOL_SIZE", "50"))
)
```

### With NumPyro/JAX (Optimization)

**Current:** Runs in FastAPI request handler.

**Production-ready:**
```python
# In Celery task
@celery_app.task
def run_optimization(job_id, request):
    # Configure JAX to use limited threads
    os.environ["XLA_FLAGS"] = "--xla_cpu_multi_thread_eager=false"

    # Run optimization
    optimizer = LineupOptimizer(...)
    result = optimizer.optimize()

    # Store result
    job_manager.set_result(job_id, result)
```

### With SQLAlchemy (Epistemic DB)

**Current:** Used in some endpoints.

**Production-ready:**
```python
# Add connection pool health check
async def check_db():
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        return True
    except:
        return False

# Add to /ready endpoint
@app.get("/ready")
async def readiness():
    checks = {
        "neo4j": await check_neo4j(),
        "redis": await check_redis(),
        "database": await check_db()
    }
    ...
```

## Gaps and Areas for Further Research

1. **Authentication Provider**
   - Should we build our own `/auth/login` or use external provider (Auth0, Firebase)?
   - MEDIUM confidence - requires product decision

2. **Celery Autoscaling**
   - How to scale workers based on queue depth?
   - LOW confidence - needs production validation

3. **Result Storage Strategy**
   - At what result size should we use S3 instead of Redis?
   - MEDIUM confidence - depends on typical result sizes

4. **Job Priority Implementation**
   - How to implement multi-queue Celery setup?
   - MEDIUM confidence - standard Celery pattern

5. **Trace Sampling Strategy**
   - What sampling rate for production (100% vs 10%)?
   - LOW confidence - depends on traffic volume

6. **Rate Limiting Strategy**
   - Per-user vs per-IP vs per-API-key?
   - MEDIUM confidence - depends on user model

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Job state persistence (Redis) | HIGH | Standard pattern, verified with official docs |
| Health check patterns | HIGH | FastAPI dependencies + K8s best practices |
| Celery integration | HIGH | Official Celery docs + community patterns |
| OpenTelemetry tracing | MEDIUM | Community articles, need official docs verification |
| JWT authentication | MEDIUM | Standard pattern, but provider choice unclear |
| Result storage (S3) | MEDIUM | Depends on result size characteristics |
| Job priorities | LOW | Need to research Celery multi-queue setup |
| Autoscaling | LOW | Need production validation |

## Sources

### High Confidence (Official Documentation)

- [FastAPI Dependencies Documentation](https://fastapi.tiangolo.com/tutorial/dependencies/) - Official dependency injection patterns
- [FastAPI BackgroundTasks Documentation](https://fastapi.tiangolo.com/tutorial/background-tasks/) - Official background task patterns (shows limitations)
- [Celery Documentation](https://docs.celeryq.dev/en/stable/) - Official Celery task queue patterns
- [Redis Persistence Documentation](https://redis.io/topics/persistence) - Official Redis durability configuration

### Medium Confidence (Community Articles - 2025)

- [FastAPI Production Deployment Best Practices](https://render.com/articles/fastapi-production-deployment-best-practices) - Covers health checks and monitoring (Nov 2025)
- [Celery + Redis + FastAPI: The Ultimate 2025 Production Guide](https://medium.com/@dewasheesh.rana/celery-redis-fastapi-the-ultimate-2025-production-guide-broker-vs-backend-explained-5b84ef508fa7) - Celery integration patterns (2025)
- [How to Build Background Task Processing in FastAPI](https://oneuptime.com/blog/post/2026-01-25-background-task-processing-fastapi/view) - Background task comparison (Jan 2026 - very recent)
- [A FastAPI Implementation Guide for Logs, Metrics, and Traces](https://blog.greeden.me/en/2025/10/07/operations-friendly-observability-a-fastapi-implementation-guide-for-logs-metrics-and-traces-request-id-json-logs-prometheus-opentelemetry-and-dashboard-design/) - Observability patterns (Oct 2025)
- [FastAPI Observability Dashboard (Grafana Labs)](https://grafana.com/grafana/dashboards/16110-fastapi-observability/) - Ready-to-use dashboard
- [10 FastAPI Observability Must-Haves](https://medium.com/@bhagyarana80/10-fastapi-observability-must-haves-8daca2ba235a) - Observability checklist (2025)

### Low Confidence (WebSearch Only - Needs Verification)

- Authentication patterns for FastAPI (needs official docs verification)
- Specific OpenTelemetry Python SDK patterns (needs official docs verification)
- Celery autoscaling patterns (needs production validation)
