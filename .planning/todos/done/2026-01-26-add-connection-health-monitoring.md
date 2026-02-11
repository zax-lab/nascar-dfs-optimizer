---
created: 2026-01-26T20:34:50
completed: 2026-02-01T00:00:00
title: Add connection health monitoring and logging
area: devops
files:
  - apps/backend/app/ontology.py:203-229
  - apps/backend/app/main.py:1-256
  - docker-compose.yml:31-76
---

## Problem

The system lacks comprehensive health monitoring for Neo4j connections, database connections, and service dependencies. Docker health checks exist but there's no application-level monitoring or alerting when connections degrade or fail. Logging is basic and doesn't provide enough context for debugging production issues.

## Solution

Add health check endpoints that verify Neo4j connectivity, database connectivity, and model availability. Implement structured logging with correlation IDs for request tracing. Add metrics collection (connection pool stats, request latencies, error rates). Consider integrating with monitoring tools like Prometheus/Grafana or application performance monitoring (APM) solutions.

## Implementation

### Completed Changes

1. **Enhanced health check endpoints** (`apps/backend/app/api/health.py`)
   - New `/health/detailed` endpoint with comprehensive diagnostics
   - New `/health/metrics` endpoint for Prometheus-style monitoring
   - Connection pool statistics for Neo4j (active, idle, max connections, utilization %)
   - Redis pool statistics and latency tracking
   - Service status for each dependency
   - Uptime and version information
   - Health check latency metrics

2. **Connection monitoring** (`apps/backend/app/ontology.py`)
   - Added `ConnectionMonitor` class for pool utilization tracking
   - Track connection attempts and failures with counters
   - Log connection acquisition times
   - Warn when pool utilization > 80%
   - Warn when connection pool is exhausted (no idle connections)
   - Structured logging for all Neo4j operations with execution times

3. **Structured logging improvements** (`apps/backend/app/middleware.py`)
   - Fixed `CorrelationIDMiddleware` with proper structlog integration
   - Generate ULID-based correlation IDs
   - Log request start/completion with timing
   - Add correlation ID and response time headers

4. **Middleware integration** (`apps/backend/app/main.py`)
   - Enabled `CorrelationIDMiddleware` for distributed tracing

### Commits

- `6cb0c6e`: feat(health-monitoring): add comprehensive connection health monitoring and logging

## Status

✅ **Completed** - All health monitoring and logging improvements implemented.
