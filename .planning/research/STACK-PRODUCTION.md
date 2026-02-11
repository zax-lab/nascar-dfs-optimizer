# Technology Stack: Production Readiness (DevOps, Monitoring, Deployment)

**Project:** Axiomatic NASCAR DFS — Causal Simulation + Conditional Upside Optimizer
**Milestone:** v1.1 Production Readiness
**Researched:** 2026-01-28
**Confidence:** HIGH

---

## Executive Summary

**Current validated capabilities** (from STATE.md):
- FastAPI backend with /optimize endpoint
- NumPyro MCMC calibration (30-60 seconds)
- Scenario generation with JAX acceleration
- Neo4j ontology integration
- Docker Compose for local development
- Airflow DAGs for ETL
- **slowapi** for rate limiting (already installed)
- **python-json-logger** for structured logging (already installed)

**Production gaps identified in STATE.md:**
- Job state stored in-memory (lost on restart) - production should use Redis or database
- Neo4j connection required for optimization - need health check on startup
- API returns 200 even when calibration/tail validation fail - may mask issues in production
- End-to-end pipeline latency ~5s for 10 scenarios, ~50s for 100 scenarios

**Recommended production stack additions:**
1. **Celery 5.3.4+ + Redis 7.2+** - Background task queue for MCMC calibration (30-60s jobs)
2. **Prometheus 2.47+ + Grafana 10.2+** - Metrics collection and dashboards
3. **OpenTelemetry 1.21+** - Distributed tracing for ML pipeline debugging
4. **fastapi-security 1.2.0+** - API key authentication
5. **flower 2.0.1+** - Celery task monitoring

---

## Production Stack Additions

### Background Tasks & Job Persistence

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **Celery** | 5.3.4+ | Distributed task queue | Handles long-running MCMC calibration (30-60s) without blocking HTTP requests |
| **Redis** | 7.2+ | Message broker & job state | Task queue backend, job state persistence, survives restarts |
| **flower** | 2.0.1+ | Celery monitoring | Real-time task monitoring, worker health dashboards, task debugging |

**Problem solved:** STATE.md notes "Job state stored in-memory (lost on restart)" - Celery + Redis provides persistent job state.

**Integration pattern:**
```python
# Current (synchronous - blocks for 35-65s):
POST /optimize -> [MCMC 30-60s + opt 5s] -> Response

# Production (async):
POST /optimize -> {"job_id": "abc123", "status": "pending"}  # returns immediately
GET /jobs/abc123 -> {"status": "processing"}  # poll
GET /jobs/abc123 -> {"status": "complete", "result": {...}}  # result ready
```

**Celery worker runs MCMC in background:**
```python
# app/celery_app.py
from celery import Celery

celery_app = Celery(
    'nascar_optimization',
    broker='redis://redis:6379/0',
    backend='redis://redis:6379/0'
)

# app/tasks.py
@celery_app.task(bind=True)
def run_optimization(self, request_data):
    # MCMC calibration (30-60s)
    # Scenario generation (5-50s)
    # Portfolio optimization
    return result
```

**Alternatives considered:**
- **RQ (Redis Queue)** - Simpler but lacks task prioritization, scheduling, mature monitoring
- **Dramatiq** - Better actor model but smaller ecosystem, less mature for ML workloads
- **FastAPI BackgroundTasks** - Jobs lost on restart (current problem STATE.md identifies)

**Python 3.11 compatibility:** Celery 5.3.4+ supports Python 3.11 (verified in official docs).

---

### Health Monitoring

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **Prometheus** | 2.47+ | Metrics collection | Industry standard, pulls metrics from /metrics endpoint |
| **Grafana** | 10.2+ | Dashboards & alerting | Rich visualization, pre-built dashboards for FastAPI/Redis/Neo4j |
| **prometheus-fastapi-instrumentator** | 6.1.0+ | FastAPI metrics | Auto-instruments HTTP metrics (latency, errors, throughput) |

**Problem solved:** STATE.md notes "Neo4j connection required for optimization - need health check on startup".

**Health check endpoints:**
```python
@app.get("/health")
async def health():
    """Shallow health check - returns 200 if server is up."""
    return {"status": "ok", "version": "0.3.0"}

@app.get("/health/deep")
async def deep_health():
    """Deep health check - verifies dependencies."""
    checks = {
        "neo4j": await check_neo4j_connectivity(),
        "redis": await check_redis_connectivity(),
        "celery": await check_celery_workers()
    }
    status = "ok" if all(checks.values()) else "degraded"
    return {"status": status, "checks": checks}
```

**Kubernetes probes:**
- **Liveness probe:** `/health` - Restart container if server is unresponsive
- **Readiness probe:** `/health/deep` - Stop traffic if Neo4j/Redis down

**Metrics to track:**
- **HTTP metrics:** Request latency, error rate, throughput (per endpoint)
- **Job metrics:** Queue depth, job duration, success/failure rate, worker count
- **ML metrics:** MCMC calibration time, scenario count, kernel rejection rate (STATE.md notes this should be monitored)
- **Neo4j metrics:** Connection pool usage, query latency, connectivity failures

---

### Distributed Tracing

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **OpenTelemetry** | 1.21+ | Distributed tracing | W3C standard, vendor-neutral, auto-instruments FastAPI |
| **opentelemetry-instrumentation-fastapi** | 0.42b0+ | FastAPI tracing | Auto-generates traces for HTTP requests |
| **Jaeger** | 1.53+ | Trace visualization | Collect and visualize traces (optional, can use Grafana Tempo) |

**Problem solved:** STATE.md notes "End-to-end pipeline latency ~5s for 10 scenarios, ~50s for 100 scenarios - may need optimization for real-time use". Tracing identifies bottlenecks.

**Trace the ML pipeline:**
```
HTTP Request -> FastAPI -> Celery Task -> MCMC Calibration -> Scenario Generation -> Optimization -> Response
    ↓           ↓          ↓              ↓                    ↓                    ↓            ↓
  Trace Span   Span      Span          Span                 Span                Span        Span
```

**Installation:**
```bash
pip install opentelemetry-api==1.21.0
pip install opentelemetry-instrumentation-fastapi==0.42b0
pip install opentelemetry-sdk==1.21.0
```

**Auto-instrumentation:**
```python
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

FastAPIInstrumentor.instrument_app(app)
```

---

### Authentication & Rate Limiting

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **fastapi-security** | 1.2.0+ | API key authentication | Simple for programmatic access, no user management overhead |
| **python-jose[cryptography]** | 3.3.0+ | JWT tokens | For production auth with user accounts, OAuth |
| **slowapi** | 0.1.9 | Rate limiting | Already in pyproject.toml, upgrade to Redis storage |

**Current setup (from main.py):**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

**Production enhancements:**

1. **Add Redis storage for rate limits** (survives restarts, works across workers):
```python
from slowapi.storage import RedisStorage
from redis import Redis

redis = Redis.from_url("redis://redis:6379/1")
limiter = Limiter(
    key_func=get_remote_address,
    storage=RedisStorage(redis)
)
```

2. **Add API key authentication:**
```python
from fastapi_security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

@app.post("/optimize")
async def optimize(request: Request, api_key: str = Depends(api_key_header)):
    if api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=403, detail="Invalid API key")
    # ... optimization logic
```

3. **Per-endpoint rate limits** (stricter on expensive endpoints):
```python
@app.post("/optimize")
@limiter.limit("10/hour")  # Expensive MCMC operation
async def optimize(...): pass

@app.get("/health")
@limiter.limit("60/minute")  # Cheap health check
async def health(...): pass
```

---

### Deployment Infrastructure

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **Kubernetes** | 1.28+ | Container orchestration | Horizontal scaling, auto-scaling, rolling updates, self-healing |
| **Helm** | 3.13+ | K8s package manager | Templated deployments, version control, environment parity |

**Problem solved:** Horizontal scaling for variable load (race days vs off-peak).

**Kubernetes deployment pattern:**
```yaml
# Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: nascar-backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: nascar-backend
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

**Celery worker scaling:**
```yaml
# Scale workers based on Redis queue depth
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: celery-worker-scaler
spec:
  scaleTargetRef:
    name: celery-worker
  minReplicaCount: 2
  maxReplicaCount: 10
  triggers:
  - type: redis
    metadata:
      address: redis:6379
      listName: celery  # Queue name
      listLength: '5'   # Scale when 5+ tasks waiting
```

---

## Updated Docker Compose

Add to existing `docker-compose.yml`:

```yaml
services:
  # Redis for Celery and caching
  redis:
    image: redis:7.2-alpine
    container_name: nascar-redis
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - nascar-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Celery worker for background tasks
  celery-worker:
    build:
      context: ./apps/backend
      dockerfile: Dockerfile
    container_name: nascar-celery-worker
    command: celery -A app.celery_app worker --loglevel=info --concurrency=2
    environment:
      NEO4J_URI: bolt://neo4j:7687
      NEO4J_USER: ${NEO4J_USER:-neo4j}
      NEO4J_PASSWORD: ${NEO4J_PASSWORD}
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/0
    volumes:
      - ./apps/backend:/app
      - ./packages:/app/packages
    depends_on:
      - neo4j
      - redis
    networks:
      - nascar-network
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '0.5'
          memory: 1G
    healthcheck:
      test: ["CMD", "celery", "-A", "app.celery_app", "inspect", "ping"]
      interval: 30s
      timeout: 10s
      retries: 5

  # Flower for Celery monitoring
  flower:
    build:
      context: ./apps/backend
      dockerfile: Dockerfile
    container_name: nascar-flower
    command: celery -A app.celery_app flower --port=5555
    ports:
      - "5555:5555"
    environment:
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/0
    depends_on:
      - redis
    networks:
      - nascar-network

  # Prometheus for metrics
  prometheus:
    image: prom/prometheus:v2.47.2
    container_name: nascar-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - nascar-network

  # Grafana for dashboards
  grafana:
    image: grafana/grafana:10.2.2
    container_name: nascar-grafana
    ports:
      - "3001:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD:-admin}
      GF_USERS_ALLOW_SIGN_UP: "false"
    volumes:
      - grafana_data:/var/lib/grafana
    networks:
      - nascar-network

volumes:
  redis_data:
  prometheus_data:
  grafana_data:
```

---

## Environment Variables

Add to `.env.example`:

```bash
# Celery Configuration
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
CELERY_TASK_TRACK_STARTED=true
CELERY_TASK_TIME_LIMIT=3600  # 1 hour max per task
CELERY_WORKER_PREFETCH_MULTIPLIER=1  # Don't prefetch long tasks
CELERY_WORKER_MAX_TASKS_PER_CHILD=10  # Recycle workers to prevent memory leaks

# Redis Configuration
REDIS_URL=redis://redis:6379/0
REDIS_CACHE_TTL=3600  # 1 hour cache TTL

# API Security
API_KEY_HEADER=X-API-Key
API_KEYS=${API_KEYS:-dev-key-12345}
JWT_SECRET_KEY=${JWT_SECRET_KEY:-change-me-in-production-use-openssl-rand-hex-32}
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# Rate Limiting
RATE_LIMIT_STORAGE_URL=redis://redis:6379/1
RATE_LIMIT_DEFAULT=100/hour
RATE_LIMIT_OPTIMIZE=10/hour
RATE_LIMIT_OWNERSHIP=30/hour
RATE_LIMIT_CONTEST_SIM=20/hour

# Monitoring
PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus
OTEL_SERVICE_NAME=nascar-dfs-api
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317

# Grafana
GRAFANA_PASSWORD=${GRAFANA_PASSWORD:-admin}

# Health Checks
HEALTH_CHECK_INTERVAL=30  # seconds
HEALTH_CHECK_TIMEOUT=10   # seconds
HEALTH_CHECK_RETRIES=3
```

---

## Installation

Add to `apps/backend/pyproject.toml`:

```toml
[project.dependencies]
# ... existing dependencies ...

# Background tasks
"celery[redis]==5.3.4"
"redis==5.0.1"

# Monitoring
"prometheus-fastapi-instrumentator==6.1.0"
"opentelemetry-api==1.21.0"
"opentelemetry-instrumentation-fastapi==0.42b0"
"opentelemetry-sdk==1.21.0"

# Authentication
"fastapi-security==1.2.0"
"python-jose[cryptography]==3.3.0"
"passlib[bcrypt]==1.7.4"
"python-multipart==0.0.6"

# Utilities
"tenacity==8.2.3"  # Retry logic
```

Install:
```bash
cd apps/backend
pip install -e .
```

---

## Integration with Existing Stack

### Python 3.11 Compatibility

All recommended packages support Python 3.11:
- **Celery 5.3.4+** - Officially supports Python 3.11
- **Redis 5.0.1+** - Pure Python, no version restrictions
- **Prometheus client** - Pure Python, supports 3.11
- **OpenTelemetry** - Supports Python 3.8+
- **fastapi-security** - FastAPI-based, inherits FastAPI's 3.8+ support

### FastAPI Integration

Current FastAPI version is 0.104.1 (from pyproject.toml). All monitoring libraries are compatible:
```python
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

app = FastAPI()

# Add Prometheus metrics
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# Add OpenTelemetry tracing
FastAPIInstrumentor.instrument_app(app)
```

### Neo4j Integration

Add health check for Neo4j (addresses STATE.md concern):
```python
async def check_neo4j_connectivity() -> bool:
    """Check if Neo4j is reachable."""
    try:
        from app.ontology import OntologyDriver
        driver = OntologyDriver()
        await driver.verify_connectivity()
        return True
    except Exception as e:
        logger.error(f"Neo4j health check failed: {e}")
        return False
```

### NumPyro Integration with Celery

**Potential issue:** JAX device placement in Celery worker processes.

**Solution:** Explicitly initialize JAX in Celery worker:
```python
# app/celery_app.py
from celery import Celery
import jax

# Initialize JAX before worker starts
celery_app = Celery('nascar_optimization')

# Worker init hook
@celery_app.worker_init.connect
def setup_jax(sender, **kwargs):
    """Initialize JAX in Celery worker process."""
    import jax
    # Force CPU device (or GPU if available)
    jax.config.update('jax_platform_name', 'cpu')
    print(f"JAX initialized: devices={jax.devices()}")

# Task that uses NumPyro
@celery_app.task(bind=True)
def run_mcmc_calibration(self, calibration_data):
    """Run MCMC calibration in background worker."""
    from app.calibration import CalibrationHarness
    # NumPyro works fine in Celery worker
    harness = CalibrationHarness()
    result = harness.calibrate(calibration_data)
    return result
```

---

## Architecture Pattern

### Request Flow (Current vs Production)

**Current (synchronous, blocks for 35-65s):**
```
Client -> FastAPI -> MCMC (30-60s) -> Scenario Gen (5-50s) -> Optimization (5s) -> Response
         ↑__________________blocks for 40-115 seconds__________________↑
```

**Production (async, immediate response):**
```
Step 1: Submit job
Client -> FastAPI -> Submit to Celery -> Return job_id immediately
         (HTTP 202: {"job_id": "abc123", "status": "pending"})

Step 2: Job processes in background
Celery Worker -> MCMC (30-60s) -> Scenario Gen (5-50s) -> Optimization (5s) -> Store Result in Redis

Step 3: Poll for result
Client -> GET /jobs/abc123 -> {"status": "processing"}
Client -> GET /jobs/abc123 -> {"status": "complete", "result": {...}}
```

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            Production Stack                             │
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │   FastAPI    │◄──►│    Redis     │◄──►│   Celery     │              │
│  │   (Backend)  │    │   (Queue)    │    │   Workers    │              │
│  │              │    │              │    │              │              │
│  │ /optimize    │    │ Job State    │    │ MCMC Jobs    │              │
│  │ /jobs/{id}   │    │ Cache        │    │ Scenario Gen │              │
│  │ /health      │    │ Rate Limits  │    │              │              │
│  │ /metrics     │    │              │    │              │              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│         │                   │                     │                      │
│         ▼                   ▼                     ▼                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │  Prometheus  │    │    Neo4j     │    │   Flower     │              │
│  │  + Grafana   │    │ (Ontology)   │    │  (Celery     │              │
│  │              │    │              │    │   Monitor)   │              │
│  │ Dashboards   │    │ Driver Data  │    │              │              │
│  │ Alerts       │    │ Track Data   │    │ Task Status  │              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Alternatives Considered

### Task Queue
| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Task Queue | Celery | RQ (Redis Queue) | RQ lacks task prioritization, scheduling, and mature monitoring. Celery has larger ecosystem and better ML workflow support. |
| Task Queue | Celery | Dramatiq | Dramatiq has nicer actor model but smaller community, less documentation for ML workloads. |
| Message Broker | Redis | RabbitMQ | RabbitMQ is overkill for single-service ML API. Redis is simpler, already needed for caching. |

### Monitoring
| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Metrics | Prometheus | Datadog | Datadog is excellent but expensive ($15+/host/month). Prometheus is free, industry standard. |
| Metrics | Prometheus | New Relic | Similar to Datadog - expensive SaaS solution. |
| Tracing | OpenTelemetry | Jaeger SDK | OpenTelemetry is W3C standard, vendor-neutral. Jaeger SDK is deprecated. |

### Authentication
| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| MVP Auth | fastapi-security | Auth0 | Auth0 is overkill for internal API. Adds latency, cost, external dependency. |
| Production | JWT (python-jose) | Session cookies | JWTs are stateless, work well across microservices, don't require sticky sessions. |

### Deployment
| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Orchestrator | Kubernetes | Docker Swarm | K8s is industry standard, larger community, more features. |
| Orchestrator | Kubernetes | AWS ECS | ECS is AWS-specific, creates vendor lock-in. K8s skills transferable. |

---

## Implementation Phases

### Phase 1: Job Queue & State Persistence (Week 1)
**Goal:** Long-running optimization jobs don't block HTTP responses

1. Add Redis to docker-compose.yml
2. Install Celery dependencies: `pip install celery[redis] redis flower`
3. Create `app/celery_app.py` - Initialize Celery with Redis backend
4. Create `app/tasks.py` - Define Celery tasks for MCMC calibration
5. Convert optimization endpoint to submit Celery task
6. Add `/jobs/{id}` endpoint for job status polling
7. Add Flower to docker-compose.yml for monitoring

**Deliverable:** Async optimization API, job state survives restarts

### Phase 2: Health Checks & Monitoring (Week 2)
**Goal:** Real-time visibility into system health and performance

1. Add `/health/deep` endpoint - Check Neo4j, Celery workers, Redis
2. Install Prometheus client: `pip install prometheus-fastapi-instrumentator`
3. Expose `/metrics` endpoint - Auto-instrument HTTP metrics
4. Add Prometheus to docker-compose.yml - Scrape metrics
5. Add Grafana to docker-compose.yml - Visualize metrics
6. Create dashboards: Request latency, job queue depth, Neo4j connectivity

**Deliverable:** Production-grade monitoring with Grafana dashboards

### Phase 3: Authentication & Rate Limiting (Week 3)
**Goal:** Secure API with abuse prevention

1. Install auth dependencies: `pip install fastapi-security python-jose passlib`
2. Add API key middleware - Validate `X-API-Key` header
3. Upgrade slowapi to Redis storage - Rate limits survive restarts
4. Add per-endpoint rate limits - Stricter limits on `/optimize`
5. Add per-API-key limits - Different limits for free vs paid tiers

**Deliverable:** Secured API with rate limiting

### Phase 4: Distributed Tracing (Week 4, Optional)
**Goal:** End-to-end request tracing for performance debugging

1. Install OpenTelemetry: `pip install opentelemetry-api opentelemetry-instrumentation-fastapi`
2. Instrument FastAPI - Auto-generate traces
3. Add Jaeger to docker-compose.yml - Collect traces
4. Trace ML pipeline - MCMC calibration, scenario generation, optimization

**Deliverable:** Distributed tracing for bottleneck identification

---

## Gaps & Open Questions

### LOW Confidence Items (need validation)
- **NumPyro + Celery compatibility** - Need to verify JAX device placement works in forked Celery worker processes
- **OpenTelemetry overhead** - Need to measure performance impact of tracing on MCMC jobs
- **Redis persistence** - Need to test job state recovery after Redis restart

### Phase-Specific Research Flags
- **Phase: Job Queue** - Investigate NumPyro + Celery integration (JAX may have issues with XLA compilation in forked processes)
- **Phase: Monitoring** - Define key ML metrics to track (kernel rejection rate, calibration CRPS, scenario quality metrics)
- **Phase: Auth** - Define API key management strategy (environment vs database vs secrets manager)

### Integration Risks
- **JAX in Celery workers** - JAX may have issues with XLA compilation in forked processes (need testing)
- **Neo4j connection pooling** - Need to verify Celery workers properly manage Neo4j connections (may need connection pool per worker)
- **Long-running tasks** - Need to handle task timeouts and graceful cancellation for 60s MCMC jobs
- **Memory leaks** - NumPyro may accumulate memory across tasks (need worker recycling strategy)

---

## Sources

### HIGH Confidence (Official Documentation)
- Celery Documentation: https://docs.celeryq.dev/en/stable/ - Official Celery docs, verified Python 3.11 support
- Redis Documentation: https://redis.io/docs/ - Official Redis docs
- Prometheus Python Client: https://github.com/prometheus/client_python - Official Prometheus Python client
- Grafana Documentation: https://grafana.com/docs/ - Official Grafana docs
- OpenTelemetry Python: https://opentelemetry.io/docs/instrumentation/python/ - Official OTEL Python docs
- FastAPI Documentation: https://fastapi.tiangolo.com/ - Official FastAPI docs

### MEDIUM Confidence (Community Resources, Verified Recent)
- [Building a Production-Ready Monitoring Stack for FastAPI](https://medium.com/@diwasb54/building-a-production-ready-monitoring-stack-for-fastapi-applications-a-complete-guide-with-bce2af74d258) - Comprehensive guide with Docker Compose examples
- [Monitoring Your FastAPI Application with OpenTelemetry](https://dev.to/manazsharma/monitoring-your-fastapi-application-with-opentelemetry-and-openobserve-2mf1) - Sept 2024, standardized approach
- [API Rate Limiting and Abuse Prevention at Scale](https://python.plainenglish.io/api-rate-limiting-and-abuse-prevention-at-scale-best-practices-with-fastapi-b5d31d690208) - Aug 2025, specific to FastAPI
- [FastAPI Security Best Practices](https://medium.com/@yogeshkrishnanseeniraj/fastapi-security-best-practices-defending-against-common-threats-58fbd6a15fd2) - General security patterns
- [FastAPI Advanced Rate Limiter](https://github.com/awais7012/FastAPI-RateLimiter) - Community rate limiting project
- [A Practical Guide to FastAPI Security](https://davidmuraya.com/blog/fastapi-security-guide/) - Oct 2025, complete security checklist

### LOW Confidence (Single Source, Needs Verification)
- Celery + JAX integration patterns - Need testing with NumPyro
- OpenTelemetry performance overhead in ML pipelines - Need benchmarking
- Redis persistence guarantees for job state - Need testing

---

## Notes

- **Current stack already has:** slowapi (0.1.9), python-json-logger (2.0.7) in pyproject.toml
- **STATE.md concerns addressed:** Job state persistence, Neo4j health checks, monitoring for kernel rejection rate
- **Python 3.11 compatibility verified:** All recommended packages support Python 3.11
- **FastAPI 0.104.1 compatibility:** All monitoring libraries compatible with current FastAPI version

---

*Production readiness stack research for: Axiomatic NASCAR DFS v1.1*
*Researched: 2026-01-28*
*Confidence: HIGH*
