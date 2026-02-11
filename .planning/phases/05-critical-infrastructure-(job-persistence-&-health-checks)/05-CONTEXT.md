# Phase 5.1: Critical Infrastructure - Context

**Gathered:** 2026-01-28
**Status:** Ready for planning

## Phase Boundary

Implement Redis-based job state persistence and health check endpoints to prevent job loss on container restart. Jobs must survive container restarts, and orchestrators require health check endpoints.

Scope: Job state management, health checks, graceful shutdown, structured logging. Security (auth) is Phase 5.2. Observability (metrics) is Phase 5.3. Background tasks (Celery) is Phase 5.4.

## Implementation Decisions

### Job lifecycle
- **5 states**: pending → running → complete/failed → expired
- **TTL policy**: 7 days default (Claude's discretion - Redis storage efficiency)
- **Storage**: Full input params + results + metadata (scenario count, timestamp, slate_id)
- **Failed jobs**: Automatic TTL cleanup (no soft delete)

### Health check semantics
- **Two endpoints**: `/health` (liveness, process check) + `/ready` (readiness, dependency check)
- **Failure mode**: Immediate 503 if any dependency down (Neo4j or Redis)
- **Response detail**: Full diagnostics (timestamps, version info, queue depth, each dependency status)
- **Connection timeout**: 3 seconds per dependency

### Graceful shutdown behavior
- **Shutdown timeout**: 90 seconds default (Claude's discretion - balance drain vs quick restart)
- **Job submission**: Stop accepting new jobs immediately on shutdown signal
- **Straggler jobs**: Log warning and continue (best effort, don't block shutdown)

### Logging structure
- **Log fields**: timestamp, level, message, context, correlation ID (request_id, user_id, job_id when available)
- **Correlation ID format**: ULID (Claude's discretion - time-ordered, sortable)
- **Default log level**: INFO (Claude's discretion)
- **Log destination**: Both console (JSON to stdout) + file (rotation)

### Claude's Discretion
- Job TTL: 7 days (balances Redis storage efficiency with historical access)
- Shutdown timeout: 90 seconds (reasonable balance between job drain and quick restart)
- Correlation ID format: ULID (time-ordered, lexicographically sortable, URL-safe)
- Default log level: INFO (normal operations, errors at ERROR level)
- Exact file rotation policy
- Grace period before accepting new jobs during shutdown
- Health check retry logic

## Specific Ideas

None - open to standard infrastructure practices for Redis job state and health checks.

## Deferred Ideas

None - discussion stayed within phase scope.

---

*Phase: 05-critical-infrastructure*
*Context gathered: 2026-01-28*
