# Phase 5: Critical Infrastructure (Job Persistence & Health Checks) - Research

**Researched:** 2026-01-28
**Domain:** Redis job state persistence, FastAPI health checks, structured logging, graceful shutdown
**Confidence:** HIGH

## Summary

This phase addresses the highest-priority production blocker: **in-memory job state loss on container restart**. The current FastAPI application (\`apps/backend/app/main.py\`) uses in-memory dictionaries (\`optimization_jobs\` and \`optimization_results\`) which are lost when containers restart. The solution requires implementing Redis-based job persistence, health check endpoints for orchestrators, structured JSON logging with correlation IDs, and graceful shutdown handling.

**Key findings from research:**
1. **redis-py** is the standard Python Redis client with built-in connection pooling, health checks, and connection timeout support
2. **FastAPI lifespan context managers** (replacing deprecated \`on_startup\`/\`on_shutdown\`) provide unified startup/shutdown handling for graceful shutdown
3. **structlog** is the industry-standard for structured logging in Python with context variable support for correlation IDs
4. **Health check semantics** follow Kubernetes patterns: \`/health\` (liveness) for process checks, \`/ready\` (readiness) for dependency availability
5. **ULID** libraries exist for time-ordered, sortable correlation IDs as specified in context

**Primary recommendation:** Use redis-py ConnectionPool with health_check_interval=30, FastAPI lifespan context manager for graceful shutdown, structlog with contextvars for correlation tracking, and implement dual health endpoints following Kubernetes patterns.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **redis-py** | v6.4.0+ | Redis client with connection pooling | Official Redis Python client, 460+ code snippets, 89.3 benchmark score, thread-safe |
| **structlog** | 24.x+ | Structured JSON logging | Production-ready, 91.1 benchmark score, async-safe context variables |
| **FastAPI** | 0.104.1+ | Web framework (already in use) | Lifespan context managers replace deprecated event handlers |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **python-ulid** | 1.x+ | ULID generation for correlation IDs | Time-ordered, lexicographically sortable, URL-safe IDs |
| **python-json-logger** | 2.x+ | JSON logging fallback | Already in pyproject.toml, can use with structlog |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| redis-py | arq | arq is a job queue library on top of Redis - overkill for simple state persistence |
| structlog | python-json-logger | python-json-logger is simpler but lacks context variable binding for correlation tracking |
| ULID | UUID v4 | UUIDs are not time-ordered or sortable - harder to trace chronologically |

**Installation:**
\`\`\`bash
# Add to apps/backend/pyproject.toml dependencies
pip install redis==6.4.0
pip install structlog==24.1.0
pip install ulid-py==1.1.0
\`\`\`

## Architecture Patterns

### Recommended Project Structure
\`\`\`
apps/backend/app/
├── infrastructure/
│   ├── __init__.py
│   ├── redis_client.py      # Redis connection pool and client setup
│   ├── job_store.py         # Job state persistence using Redis
│   ├── health_checks.py     # Health check logic for dependencies
│   └── logging_config.py    # Structured logging configuration
├── middleware/
│   ├── __init__.py
│   └── correlation.py       # Correlation ID middleware for FastAPI
├── api/
│   ├── health.py            # Health/ready endpoints
│   └── optimize.py          # Update to use job_store instead of in-memory
└── main.py                  # Update with lifespan context manager
\`\`\`

### Pattern 1: Redis Connection Pool with Health Checks
**What:** Create a singleton Redis client with connection pooling and automatic health checks
**When to use:** All Redis operations need consistent connection management with fail-fast behavior
**Example:**
\`\`\`python
# Source: Context7 redis/redis-py
import redis
from typing import Optional

class RedisPool:
    _instance: Optional[redis.ConnectionPool] = None
    _client: Optional[redis.Redis] = None

    @classmethod
    def get_client(cls) -> redis.Redis:
        if cls._client is None:
            cls._instance = redis.ConnectionPool(
                host='localhost',
                port=6379,
                db=0,
                max_connections=50,
                decode_responses=True,
                socket_timeout=5,              # 5s timeout for operations
                socket_connect_timeout=5,      # 5s timeout for connections
                socket_keepalive=True,
                health_check_interval=30       # Check connection health every 30s
            )
            cls._client = redis.Redis(connection_pool=cls._instance)
        return cls._client

# Usage in health check
redis_client = RedisPool.get_client()
try:
    redis_client.ping()  # Returns True if healthy
except redis.ConnectionError:
    return False
\`\`\`

### Pattern 2: FastAPI Lifespan Context Manager
**What:** Unified startup/shutdown handling using \`@asynccontextmanager\`
**When to use:** Resource management (connections, cleanup) that must happen at app lifecycle boundaries
**Example:**
\`\`\`python
# Source: Context7 /fastapi/fastapi lifespan documentation
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.infrastructure.redis_client import RedisPool

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize resources
    redis_client = RedisPool.get_client()
    redis_client.ping()  # Verify connection
    app.state.redis = redis_client
    app.state.shutdown_imminent = False
    yield
    # Shutdown: Cleanup resources
    app.state.shutdown_imminent = True
    # Wait for in-flight jobs (max 90s per context)
    # Connection pool cleanup handled automatically

app = FastAPI(lifespan=lifespan)
\`\`\`

### Pattern 3: Structured Logging with Correlation IDs
**What:** JSON-formatted logs with request-scoped correlation tracking
**When to use:** All production logging for traceability across distributed systems
**Example:**
\`\`\`python
# Source: Context7 /hynek/structlog contextvars
import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars
from fastapi import Request
from ulid import ULID

# Configure structlog once at startup
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,  # Merge bound context
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.JSONRenderer()       # Machine-readable JSON
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Middleware: Bind correlation ID per request
@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(ULID()))
    bind_contextvars(
        request_id=correlation_id,
        path=request.url.path,
        method=request.method
    )
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    clear_contextvars()  # Clean up after request
    return response

# Usage in code
log = structlog.get_logger(__name__)
log.info("optimization_started", job_id=run_id, n_scenarios=1000)
# Output: {"request_id":"01H...","path":"/optimize","method":"POST","event":"optimization_started","job_id":"abc","n_scenarios":1000,"timestamp":"2026-01-28T10:30:45.123456Z","level":"info","logger":"app.optimize"}
\`\`\`

### Pattern 4: Job State Persistence in Redis
**What:** Store job status and results in Redis with TTL for auto-expiration
**When to use:** Any long-running operation that needs to survive container restarts
**Example:**
\`\`\`python
import json
from typing import Optional
from app.infrastructure.redis_client import RedisPool

class JobStore:
    def __init__(self):
        self.redis = RedisPool.get_client()
        self.job_ttl = 7 * 24 * 60 * 60  # 7 days in seconds

    def save_job(self, run_id: str, status: str, progress: float, error: Optional[str] = None):
        job_key = f"job:{run_id}"
        job_data = {
            "status": status,
            "progress": progress,
            "error": error,
            "updated_at": datetime.utcnow().isoformat()
        }
        self.redis.hset(job_key, mapping=job_data)
        self.redis.expire(job_key, self.job_ttl)

    def get_job(self, run_id: str) -> Optional[dict]:
        job_key = f"job:{run_id}"
        data = self.redis.hgetall(job_key)
        if not data:
            return None
        return {
            "status": data.get("status"),
            "progress": float(data.get("progress", 0)),
            "error": data.get("error"),
            "updated_at": data.get("updated_at")
        }

    def save_result(self, run_id: str, result: dict):
        result_key = f"result:{run_id}"
        self.redis.setex(
            result_key,
            self.job_ttl,
            json.dumps(result)
        )

    def get_result(self, run_id: str) -> Optional[dict]:
        result_key = f"result:{run_id}"
        data = self.redis.get(result_key)
        return json.loads(data) if data else None
\`\`\`

### Pattern 5: Health Check Endpoints
**What:** Dual endpoints following Kubernetes liveness/readiness probe patterns
**When to use:** Container orchestration (Kubernetes, Docker Compose health checks)
**Example:**
\`\`\`python
from fastapi import HTTPException, status
from app.infrastructure.redis_client import RedisPool
from app.infrastructure.health_checks import check_neo4j, check_redis

@app.get("/health", tags=["health"])
async def liveness_probe():
    """Liveness: Is the process running? Return 200 if yes."""
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}

@app.get("/ready", tags=["health"])
async def readiness_probe():
    """Readiness: Are dependencies available? Return 200 if yes, 503 if no."""
    checks = {
        "redis": await check_redis(),
        "neo4j": await check_neo4j()
    }

    all_healthy = all(checks.values())
    status_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if all_healthy else "not_ready",
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# In health_checks.py
async def check_redis(timeout: int = 3) -> dict:
    try:
        client = RedisPool.get_client()
        client.ping(socket_timeout=timeout)
        return {"status": "healthy", "latency_ms": measure_latency(client)}
    except redis.TimeoutError:
        return {"status": "unhealthy", "error": "timeout"}
    except redis.ConnectionError:
        return {"status": "unhealthy", "error": "connection_failed"}

async def check_neo4j(timeout: int = 3) -> dict:
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
\`\`\`

### Anti-Patterns to Avoid
- **Global state for jobs**: The current \`optimization_jobs = {}\` in \`app/api/optimize.py\` is lost on restart - use Redis instead
- **Deprecated event handlers**: Don't use \`@app.on_event("startup")\` - use \`lifespan\` context manager instead
- **String concatenation for logs**: Don't use \`f"Job {job_id} failed"\` - use structured logging: \`log.error("job_failed", job_id=job_id)\`
- **Blocking shutdown**: Don't block shutdown indefinitely - set timeout (90s) and log stragglers
- **Mixed logging formats**: Don't mix string logs and JSON logs - configure consistent output

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Redis connection pooling | Custom singleton with retry logic | \`redis.ConnectionPool\` | Built-in health checks, connection reuse, thread-safe |
| Correlation ID propagation | Custom middleware with threading.local | \`structlog.contextvars\` | Async-safe, automatic propagation across task boundaries |
| JSON logging | Custom JSON encoder | \`structlog.processors.JSONRenderer\` | Handles exceptions, timestamps, serialization edge cases |
| Graceful shutdown | Signal handlers with timeouts | FastAPI \`lifespan\` | Framework-managed, handles edge cases, testable |
| Job state serialization | Custom pickle/json wrapper | Redis native types + json module | Type safety, debugging friendly, portable |

**Key insight:** Redis job persistence looks like a simple key-value store, but connection pooling, health checks, TTL management, and serialization have edge cases that redis-py already solved. Custom implementations often miss connection timeout edge cases (blocked connections, socket leaks) and fail to handle Redis reconnection properly during transient failures.

## Common Pitfalls

### Pitfall 1: In-Memory Job State Lost on Restart
**What goes wrong:** Current implementation uses \`optimization_jobs = {}\` and \`optimization_results = {}\` - all jobs vanish when container restarts
**Why it happens:** Python dictionaries live in process memory, no persistence across restarts
**How to avoid:** Migrate to Redis-based job store with connection pooling and TTL for auto-expiration
**Warning signs:** Container restarts cause user-visible "job not found" errors, manual resubmission required

### Pitfall 2: Blocking Shutdown Indefinitely
**What goes wrong:** App hangs on shutdown waiting for jobs that never complete
**Why it happens:** Shutdown handler waits indefinitely for in-flight jobs without timeout
**How to avoid:** Implement shutdown timeout (90s), log straggler jobs, force exit after timeout
**Warning signs:** Kubernetes \`Terminating\` state lasts >90s, container killed forcefully after timeout

### Pitfall 3: Health Check Latency Cascades
**What goes wrong:** Health checks timeout and cause 503 responses even when dependencies are healthy
**Why it happens:** Health check queries are slow (e.g., complex Neo4j Cypher) without timeout, or connection pool exhausted
**How to avoid:** Use fast health checks (PING, simple queries), set socket_timeout=3, use dedicated connection pool
**Warning signs:** \`/ready\` endpoint returns 503 intermittently, orchestrator restarts healthy containers

### Pitfall 4: Correlation ID Lost in Background Tasks
**What goes wrong:** Background task logs don't include the request's correlation ID
**Why it happens:** Correlation ID bound in request context but not propagated to background tasks
**How to avoid:** Explicitly pass correlation ID to background tasks or use contextvars (propagates across asyncio tasks)
**Warning signs:** Unable to trace background job execution back to original API request

### Pitfall 5: Redis Connection Exhaustion
**What goes wrong:** Application runs out of Redis connections under load
**Why it happens:** Creating new Redis client per request instead of reusing connection pool
**How to avoid:** Use singleton Redis client with \`ConnectionPool(max_connections=50)\`
**Warning signs:** \`redis.ConnectionError: Too many connections\` in logs, degraded performance

## Code Examples

Verified patterns from official sources:

### Redis Connection Pool with Health Checks
\`\`\`python
# Source: Context7 redis/redis-py (HIGH confidence)
import redis

pool = redis.ConnectionPool(
    host='localhost',
    port=6379,
    db=0,
    max_connections=50,
    decode_responses=True,
    socket_timeout=5,
    socket_connect_timeout=5,
    socket_keepalive=True,
    health_check_interval=30
)
r = redis.Redis(connection_pool=pool)
\`\`\`

### FastAPI Lifespan Context Manager
\`\`\`python
# Source: Context7 /fastapi/fastapi (HIGH confidence)
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.redis = RedisPool.get_client()
    yield
    # Shutdown
    app.state.shutdown_imminent = True

app = FastAPI(lifespan=lifespan)
\`\`\`

### Structlog with Context Variables
\`\`\`python
# Source: Context7 /hynek/structlog (HIGH confidence)
import structlog
from structlog.contextvars import bind_contextvars

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.JSONRenderer()
    ]
)

bind_contextvars(request_id="req-123", user_id=42)
log = structlog.get_logger()
log.info("action", action_type="purchase")
# Output: {"request_id":"req-123","user_id":42,"event":"action","action_type":"purchase",...}
\`\`\`

### Graceful Shutdown with Job Drain
\`\`\`python
# Source: Context7 /fastapi/fastapi lifespan pattern (adapted)
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.shutdown_imminent = False
    yield

    # Shutdown phase: Wait for in-flight jobs
    app.state.shutdown_imminent = True
    timeout = 90
    start = time.time()

    while time.time() - start < timeout:
        running_jobs = count_running_jobs()
        if running_jobs == 0:
            break
        log.info("waiting_for_jobs", count=running_jobs, remaining=timeout - (time.time() - start))
        await asyncio.sleep(1)

    if count_running_jobs() > 0:
        log.warning("shutdown_timeout", stragglers=count_running_jobs())
\`\`\`

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| \`@app.on_event("startup")\` | \`lifespan\` context manager | FastAPI 0.93.0 | Unified startup/shutdown in one function, clearer lifecycle management |
| In-memory job state | Redis persistence | N/A | Jobs survive container restarts |
| Unstructured logging | Structured JSON logging | Industry standard since ~2020 | Log aggregation, querying, distributed tracing |
| Single \`/health\` endpoint | Dual \`/health\` + \`/ready\` | Kubernetes standard | Orchestrators can distinguish liveness vs readiness |

**Deprecated/outdated:**
- **FastAPI on_startup/on_shutdown events**: Replaced by \`lifespan\` parameter in FastAPI 0.93.0 (2022). Still works but deprecated.
- **python-json-logger for new projects**: structlog is more feature-rich with context variables, prefer for new code

## Open Questions

1. **ULID library selection**
   - What we know: ULID is specified in context for correlation IDs
   - What's unclear: Which ULID library to use (ulid-py vs python-ulid vs ulid2)
   - Recommendation: Use \`ulid-py\` (1.1.0+) - most popular, pure Python, no dependencies

2. **File rotation policy**
   - What we know: Context specifies "console + file with rotation"
   - What's unclear: Exact rotation strategy (size-based? time-based? max files?)
   - Recommendation: Use \`logging.handlers.RotatingFileHandler\` with 10MB max size, keep 5 backups

3. **Neo4j health check query**
   - What we know: Need to check Neo4j availability
   - What's unclear: Whether to use \`RETURN 1\` or check specific indexes/data
   - Recommendation: Use driver.verify_connectivity() (fastest) - separate from data availability checks

## Sources

### Primary (HIGH confidence)
- **/redis/redis-py** - Connection pooling, health_check_interval, socket_timeout, connection pool management (460 code snippets, 89.3 benchmark)
- **/fastapi/fastapi** - Lifespan context manager, background tasks, application lifecycle (1741 code snippets, 79.8 benchmark)
- **/hynek/structlog** - Context variables, JSON rendering, async-safe logging (535 code snippets, 91.1 benchmark)
- **/websites/fastapi_tiangolo** - Lifespan events, startup/shutdown patterns (12277 code snippets, 96.8 benchmark)
- **/websites/benavlabs_github_io_fastapi-boilerplate** - Production FastAPI patterns with Redis and structlog (715 code snippets, High reputation)

### Secondary (MEDIUM confidence)
- None (web search tools were rate-limited, relied on Context7 only)

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified via Context7 official documentation
- Architecture: HIGH - Patterns from official FastAPI/redis-py/structlog docs
- Pitfalls: HIGH - Based on common production issues documented in sources

**Research date:** 2026-01-28
**Valid until:** 2026-03-01 (60 days - FastAPI/redis-py/structlog are stable libraries)

---

*Phase: 05-critical-infrastructure*
*Research completed: 2026-01-28*
