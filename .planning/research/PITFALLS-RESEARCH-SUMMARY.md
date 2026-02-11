# Production Readiness Pitfalls Research Summary

**Project:** Axiomatic NASCAR DFS — v1.1 Production Readiness Milestone
**Research Type:** Pitfalls Dimension for Production Operations
**Date:** 2026-01-28
**Confidence:** MEDIUM

## Executive Summary

Research identified **10 critical pitfalls** specific to productionizing ML/optimization APIs with long-running jobs. The current FastAPI monolith exhibits **severe production-readiness gaps**: in-memory job state (lost on restart), mock health checks, and silent error masking (200 OK on failures). These issues will cause data loss, undetected outages, and debugging nightmares in production.

**Most critical finding:** The codebase already shows symptoms of all 10 pitfalls. Job state is in global dictionaries (`optimization_jobs`, `optimization_results`), health check returns static `{"status": "ok"}`, and try-except blocks return None without proper error handling. These are not theoretical concerns—they are present in the current code.

**Immediate action required:** Before deploying to production, the project must implement job persistence (Redis/PostgreSQL), dependency health checks, proper HTTP status codes, and async job processing for long-running MCMC calibrations.

## Key Findings

### 1. In-Memory Job State Loss (CRITICAL)
**Current state:** Job state stored in `optimization_jobs` and `optimization_results` global dictionaries in `app/api/optimize.py`
**Impact:** All active jobs lost on container restart, no recovery mechanism
**Prevention:** Migrate to Redis or PostgreSQL for job persistence
**Phase:** Phase 1: Job Queue & Persistence

### 2. Missing Health Checks (HIGH)
**Current state:** `/health` endpoint returns static `{"status": "ok"}` without checking Neo4j or other dependencies
**Impact:** Load balancers route traffic to unhealthy instances, cascading failures
**Prevention:** Implement deep health checks with dependency connectivity tests
**Phase:** Phase 1: Infrastructure Foundations

### 3. Silent Error Masking (HIGH)
**Current state:** Try-except blocks in `optimize_portfolio.py` return None on calibration failures, API returns 200 OK
**Impact:** Hidden failures, impossible debugging, silent data quality issues
**Prevention:** Return proper HTTP status codes (500 for errors), never mask failures
**Phase:** Phase 1: Error Handling & API Contracts

### 4. Long-Running Job Timeouts (HIGH)
**Current state:** MCMC calibration takes 30-60s, scenario generation 10-50s, exceeds typical 30s HTTP timeouts
**Impact:** Clients receive 504 errors, jobs waste resources producing unretrievable results
**Prevention:** Implement async job queue with polling/webhook callbacks
**Phase:** Phase 1: Async Job Processing

### 5. Missing Rate Limiting (MEDIUM)
**Current state:** No rate limiting configured, expensive optimization endpoints are unprotected
**Impact:** Single client can cause DoS, unfair resource allocation
**Prevention:** Implement per-user rate limits, stricter on expensive endpoints
**Phase:** Phase 2: Security & Resource Management

### 6. No Job Cancellation (MEDIUM)
**Current state:** No mechanism to cancel submitted jobs
**Impact:** Wasted resources, poor UX when users make mistakes
**Prevention:** Design job system with cancellation support from start
**Phase:** Phase 2: Job Management

### 7. Alert Fatigue (MEDIUM)
**Current state:** Generic monitoring (CPU, memory) without ML-specific metrics
**Impact:** Real issues missed due to noise, operators ignore alerts
**Prevention:** Focus on domain-specific metrics (kernel rejection rate, calibration CRPS)
**Phase:** Phase 3: Observability

### 8. Duplicate Jobs from Retries (MEDIUM)
**Current state:** No idempotency keys on optimization requests
**Impact:** Network timeouts cause duplicate jobs, wasted compute
**Prevention:** Implement idempotency keys, detect duplicate requests
**Phase:** Phase 2: API Reliability

### 9. Missing Authentication on Results (HIGH)
**Current state:** GET endpoints may not require authentication (common pattern)
**Impact:** Users can access each other's results via run ID enumeration
**Prevention:** Require auth on ALL endpoints, implement ownership checks
**Phase:** Phase 2: Security

### 10. No Graceful Shutdown (MEDIUM)
**Current state:** Workers killed immediately on deployment
**Impact:** In-progress jobs aborted, users lose work
**Prevention:** Implement graceful shutdown with 60-120s timeout
**Phase:** Phase 1: Deployment Infrastructure

## ML/Optimization-Specific Pitfalls

### Calibration Drift
Models degrade over time as track conditions change. Monitor CRPS trends, schedule weekly recalibration, track model age.

### Kernel Rejection Rate Spikes
Constraint errors cause rejection rates to spike from ~5% to >50%. Monitor rejection rate, validate constraint combinations, use "preview mode."

### Scenario Cache Invalidation
Cached scenarios become stale when track conditions change. Include constraint_spec_hash in cache key, implement TTL invalidation.

## Roadmap Implications

Based on pitfall analysis, recommended phase structure for v1.1 Production Readiness:

### Phase 1: Infrastructure Foundations (CRITICAL - Blocks Production)
**Focus:** Job persistence, health checks, error handling, async processing
**Deliverables:**
- Redis/PostgreSQL job storage replacing in-memory state
- Deep health checks for all dependencies (Neo4j, Redis)
- Proper HTTP status codes (no more 200 OK on errors)
- Async job queue (Celery/ARQ) for long-running operations
- Graceful shutdown with job completion

**Why first:** These are hard prerequisites. Without job persistence, the API loses data on every restart. Without health checks, outages go undetected. These block production deployment.

### Phase 2: Security & Reliability
**Focus:** Authentication, rate limiting, idempotency, cancellation
**Deliverables:**
- Authentication on ALL endpoints (including GET)
- Per-user rate limiting (stricter on expensive endpoints)
- Idempotency keys for all POST operations
- Job cancellation API
- Audit logging for security events

**Why second:** Builds on Phase 1's job queue. Requires persistent job storage for cancellation and idempotency.

### Phase 3: Observability & Monitoring
**Focus:** ML-specific metrics, alerting, dashboards
**Deliverables:**
- Domain-specific metrics (kernel rejection rate, calibration CRPS)
- Intelligent alerting (anomaly detection, not static thresholds)
- Separate operations vs. ML quality dashboards
- Calibration drift monitoring
- Scenario cache invalidation tracking

**Why third:** Monitoring is most effective after system is stable. Focus on signal-to-noise ratio.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Job state pitfalls | HIGH | Directly observed in current codebase |
| Health check gaps | HIGH | Current implementation reviewed |
| Error handling issues | HIGH | Try-except patterns identified in code |
| Timeout handling | HIGH | MCMC duration documented in STATE.md |
| Rate limiting | MEDIUM | Standard pattern, no code evidence of implementation |
| Cancellation | MEDIUM | Common issue, not explicitly checked in code |
| Monitoring pitfalls | MEDIUM | Based on best practices, not code review |
| Security issues | MEDIUM | GET endpoints not audited for auth |
| ML-specific drift | MEDIUM | Domain knowledge, not FastAPI-specific |

## Gaps to Address

Topics that need phase-specific research during implementation:

1. **Job queue technology selection:** Celery vs. ARQ vs. RQ — needs performance testing with MCMC workloads
2. **Health check timeout configuration:** How long to wait for Neo4j/Redis responses?
3. **Rate limiting thresholds:** What are appropriate limits for optimization endpoints?
4. **Monitoring baselines:** Need to establish baseline metrics before alerting (kernel rejection rate, calibration CRPS)
5. **Authentication strategy:** API keys vs. OAuth vs. JWT — what fits the use case?

## Sources

- Current codebase analysis: `apps/backend/app/main.py`, `apps/backend/app/api/optimize.py`
- FastAPI background task literature (2025-2026)
- ML API deployment best practices
- Production readiness patterns for long-running jobs

## Files Created

| File | Purpose |
|------|---------|
| `.planning/research/PITFALLS-PRODUCTION.md` | Comprehensive production readiness pitfalls for ML/optimization APIs |

## Next Steps

1. **Review PITFALLS-PRODUCTION.md** — Full details on all 10 critical pitfalls plus ML-specific issues
2. **Prioritize Phase 1** — Job persistence, health checks, and error handling block production deployment
3. **Audit current code** — Map each pitfall to specific code locations requiring fixes
4. **Define acceptance criteria** — Each phase should include pitfall prevention verification steps

---
**Research Complete:** Production Readiness Pitfalls dimension
**Ready for:** Roadmap creation for v1.1 Production Readiness milestone
