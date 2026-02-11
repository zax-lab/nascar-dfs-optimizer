# Pitfalls Research: Production Readiness for ML/Optimization APIs

**Domain:** ML/Optimization API Production Readiness
**Researched:** 2026-01-28
**Confidence:** MEDIUM

## Critical Pitfalls

### Pitfall 1: In-Memory Job State Loss on Restart

**What goes wrong:**
Job state stored in Python dictionaries (`optimization_jobs`, `optimization_results`) is lost when the process restarts. Active jobs disappear, users can't retrieve results, and there's no way to recover incomplete work.

**Why it happens:**
FastAPI's built-in `BackgroundTasks` stores state in memory. Developers prototype with in-memory state because it's simple, then forget to migrate to persistent storage before production deployment.

**How to avoid:**
- Use Redis or PostgreSQL for job state storage from day one
- Implement job persistence before deploying to production
- Store job metadata (status, progress, error, result) in a database
- Use a proper task queue (Celery + Redis, ARQ, or RQ) for background jobs

**Warning signs:**
- Job state stored in global Python dictionaries
- No database schema for jobs table
- "Jobs disappear when we restart the service"
- No recovery mechanism for crashed workers

**Phase to address:**
Phase 1: Job Queue & Persistence — This must be addressed first before any other production features

---

### Pitfall 2: Missing Health Checks for Dependencies

**What goes wrong:**
API returns 200 OK at `/health` but critical dependencies (Neo4j, Redis) are unreachable. Optimization requests fail with connection errors, load balancers direct traffic to unhealthy instances, and users experience cascading failures.

**Why it happens:**
Developers implement a shallow health check that only checks the API process itself. External dependencies require additional logic, so they're omitted for simplicity.

**How to avoid:**
- Implement deep health checks that verify all dependencies
- Check Neo4j connectivity with a simple query
- Check Redis connectivity with a PING
- Return 503 if any critical dependency is down
- Make health checks lightweight (<1s timeout)

**Warning signs:**
- `/health` endpoint returns static `{"status": "ok"}`
- No dependency checks in health endpoint
- Health check completes instantly without any I/O
- Load balancer shows healthy instances that can't serve requests

**Phase to address:**
Phase 1: Infrastructure Foundations — Health checks must be implemented before scaling

---

### Pitfall 3: Silent Error Masking (200 OK on Failure)

**What goes wrong:**
API returns HTTP 200 with `null` values when calibration, tail validation, or optimization fails. Errors are logged but not surfaced to callers, making debugging nearly impossible and leading to silent data quality issues.

**Why it happens:**
Developers use try-except blocks that catch exceptions and return None to avoid "breaking" the API response. This is particularly common in ML pipelines where calibration or validation can fail.

**How to avoid:**
- Return appropriate HTTP status codes (500 for errors, 503 for degraded service)
- Include error details in response body
- Never return 200 OK when a critical operation failed
- Use partial response patterns for optional components
- Log errors with full context for debugging

**Warning signs:**
- Try-except blocks that return None without re-raising
- Response fields that are "optional" but should be required
- Logs showing errors that aren't reflected in API responses
- Frontend code checking `if (result.calibration_metrics === null)` to detect errors

**Phase to address:**
Phase 1: Error Handling & API Contracts — Must be fixed before production deployment

---

### Pitfall 4: Long-Running Job Timeouts

**What goes wrong:**
MCMC calibration (30-60s) and scenario generation (10-50s) exceed typical HTTP timeouts (30s). Clients receive 504 Gateway Timeout errors, but the job continues running on the server, wasting resources and producing results that can't be retrieved.

**Why it happens:**
Developers test locally where timeouts don't occur, then deploy behind reverse proxies (nginx, load balancers) with default timeout settings. Long-running ML jobs are treated like standard HTTP requests.

**How to avoid:**
- Use async job patterns for anything >5 seconds
- Implement job queue with polling or webhook callbacks
- Set appropriate timeouts at all layers (API, proxy, client)
- Document expected job durations for each endpoint
- Provide progress updates via status polling

**Warning signs:**
- API endpoints taking >10 seconds to respond
- Intermittent 504 errors in production
- Load balancer timeout warnings
- "It works locally but fails in production"

**Phase to address:**
Phase 1: Async Job Processing — Critical for any ML/optimization API

---

### Pitfall 5: Missing Rate Limiting & Resource Exhaustion

**What goes wrong:**
No rate limiting allows a single client to submit thousands of optimization jobs, exhausting CPU/memory and causing denial of service for all users. Expensive operations (MCMC, scenario generation) are particularly vulnerable to abuse.

**Why it happens:**
Developers assume "trusted users" during development. Rate limiting is viewed as an "add later" feature, but production traffic patterns quickly expose this vulnerability.

**How to avoid:**
- Implement rate limiting at the API gateway level
- Use different limits for expensive vs. cheap endpoints
- Rate limit by user ID, not just IP address
- Queue jobs when capacity is reached rather than rejecting
- Monitor resource usage per user

**Warning signs:**
- No rate limiter configuration
- Single user can submit unlimited requests
- API slows down under load from one client
- No metrics on requests per user

**Phase to address:**
Phase 2: Security & Resource Management — Must be in place before public launch

---

### Pitfall 6: No Job Cancellation Mechanism

**What goes wrong:**
Users submit optimization jobs, realize they made a mistake, but have no way to cancel. Jobs continue consuming resources for 30-60 seconds, wasting money and blocking other users from getting results.

**Why it happens:**
Cancellation is an afterthought. Background jobs run to completion by default, and implementing cancellation requires coordination between the API, job queue, and worker processes.

**How to avoid:**
- Design job system with cancellation from the start
- Use task queues that support cancellation (Celery, ARQ)
- Implement cooperative cancellation in long-running tasks
- Check cancellation status periodically in MCMC/optimization loops
- Provide UI/API endpoint for cancellation

**Warning signs:**
- No DELETE or POST `/jobs/{id}/cancel` endpoint
- Jobs run to completion even if user navigates away
- No way to stop a "stuck" job
- Worker processes can't be interrupted

**Phase to address:**
Phase 2: Job Management — Cancellation is a basic user expectation

---

### Pitfall 7: Alert Fatigue from Noisy Metrics

**What goes wrong:**
Monitoring dashboards show hundreds of metrics, most of which are noise. Operators ignore alerts because 99% are false positives, missing real issues like kernel rejection rates spiking or calibration failing.

**Why it happens:**
Developers instrument everything without thinking about signal-to-noise ratio. Generic monitoring templates include CPU, memory, and request rate, but not ML-specific signals.

**How to avoid:**
- Focus on domain-specific metrics (kernel rejection rate, calibration CRPS)
- Set intelligent thresholds based on baseline measurements
- Use anomaly detection instead of static thresholds
- Create separate dashboards for operations vs. ML quality
- Implement alert silencing for known transient issues

**Warning signs:**
- Alerts firing every day that get ignored
- Dashboards with >20 metrics
- No distinction between "system is down" vs. "model degraded"
- No ML-specific metrics in monitoring

**Phase to address:**
Phase 3: Observability — Must be designed, not just "add all metrics"

---

### Pitfall 8: Duplicate Jobs from Retry Storms

**What goes wrong:**
Client retries a failed optimization request, but the original job is still running. Multiple identical jobs consume resources, and the client receives multiple results with different run_ids, causing confusion and wasted compute.

**Why it happens:**
Clients implement retry logic for robustness, but the API doesn't have idempotency. Network timeouts or slow responses trigger automatic retries, creating duplicate work.

**How to avoid:**
- Implement idempotency keys for all POST/PUT operations
- Return existing job ID if duplicate request detected
- Document retry behavior in API spec
- Use HTTP 409 Conflict to indicate duplicate job
- Consider automatic deduplication based on request hash

**Warning signs:**
- Multiple identical jobs in job queue
- Same optimization appearing multiple times
- No idempotency key in API request schema
- Clients showing "job already running" errors

**Phase to address:**
Phase 2: API Reliability — Idempotency is critical for production APIs

---

### Pitfall 9: Missing Authentication on Job Results

**What goes wrong:**
Job submission requires authentication, but job result retrieval does not. Anyone can access `/optimize/{run_id}/result` if they guess or brute-force run IDs, exposing proprietary optimization strategies and user data.

**Why it happens:**
Developers secure the "mutation" endpoints but forget "query" endpoints. UUID run_ids feel "unguessable," leading to a false sense of security.

**How to avoid:**
- Require authentication for ALL endpoints, including GET
- Implement ownership checks: users can only access their own jobs
- Use cryptographically secure job IDs (UUIDs are NOT sufficient)
- Consider signed URLs for result retrieval
- Audit all endpoints for missing auth

**Warning signs:**
- GET endpoints work without authentication
- No ownership check in result retrieval
- Job IDs are sequential or predictable
- Security scan shows "unauthorized access" on GET endpoints

**Phase to address:**
Phase 2: Security — Must be completed before storing any user data

---

### Pitfall 10: No Graceful Shutdown for In-Flight Jobs

**What goes wrong:**
During deployment, workers are killed immediately. In-progress MCMC calibrations (30s+) and optimizations are aborted, leaving jobs in "running" state forever. Users lose work and must resubmit.

**Why it happens:**
Default deployment configurations send SIGTERM and wait only a few seconds before SIGKILL. FastAPI's shutdown event doesn't wait for background tasks to complete.

**How to avoid:**
- Implement graceful shutdown with sufficient timeout (60-120s)
- Track in-flight jobs and wait for completion or safe checkpoint
- Mark workers as "draining" to stop accepting new jobs
- Use job queue with graceful shutdown support
- Test shutdown procedures in staging

**Warning signs:**
- Jobs fail during every deployment
- No "draining" state in job queue
- Workers killed immediately on deploy
- No shutdown timeout configuration

**Phase to address:**
Phase 1: Deployment Infrastructure — Required for zero-downtime deployments

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| In-memory job state | Fast prototyping, no infrastructure setup | Data loss on restart, can't scale horizontally | Only for local development |
| Mock health check | Simple implementation | Outages not detected, bad traffic routing | Never in production |
| BackgroundTasks for >5s jobs | Built-in, no dependencies | No job recovery, no cancellation, blocks workers | Only for <5s tasks |
| Global caches without TTL | Fast responses, simple code | Stale data, memory leaks, no invalidation | Only for truly immutable data |
| Silent error returns (200 OK) | API never throws 500, simple client code | Hidden failures, impossible debugging | Never acceptable |
| No rate limiting | Faster development, no user friction | DoS vulnerability, unfair resource allocation | Only for single-user internal tools |
| Exception logging without metrics | Simple error tracking | No visibility into error rates, can't alert | Never in production |
| Hardcoded timeouts | Simple configuration | Wrong for different environments, can't tune | Only with documented override mechanism |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| **Neo4j** | No connection pool, one query per connection | Use connection pool with `max_connection_lifetime=30m` |
| **Redis** | No connection retry, single point of failure | Implement retry with exponential backoff, use Redis Sentinel |
| **PostgreSQL** | No prepared statements, SQL injection risk | Use parameterized queries via SQLAlchemy core |
| **Celery** | Tasks not registered, workers can't find jobs | Use `@app.task` decorator, verify with `celery inspect registered` |
| **MCMC (NumPyro)** | No progress reporting, 60s black box | Implement progress callbacks, report every 10% |
| **Object Storage (S3)** | No multipart upload, large files timeout | Use `upload_fileobj` with multipart for >100MB |
| **Prometheus** | No histogram buckets, all metrics "same" | Define domain-specific buckets (e.g., latency: [0.1, 1, 5, 30, 60]s) |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| **Synchronous MCMC in request handler** | API timeouts at 100 concurrent users | Move to async job queue with workers | >10 concurrent requests |
| **Scenario generation on every request** | End-to-end latency >60s | Cache scenarios by (race_id, n_scenarios) key | >100 requests/hour |
| **No connection pooling to Neo4j** | "Too many connections" errors | Use Bolt connection pool with limits | >50 concurrent requests |
| **Global Python caches without locking** | Race conditions, corrupted data | Use thread-safe data structures or Redis | Multiple workers |
| **Loading models per request** | Memory growth, OOM kills | Load once at worker startup | Any production traffic |
| **No pagination on list endpoints** | Response times grow with data | Implement cursor-based pagination | >1000 records |
| **Database N+1 queries** | Optimization slowdown as drivers increase | Use JOIN or batch queries | >50 drivers per slate |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| **Run ID enumeration** | Users can access each other's results | Use cryptographically random job IDs (128-bit), check ownership |
| **No input sanitization on driver IDs** | SQL injection via driver parameters | Validate all IDs against whitelist, use parameterized queries |
| **CORS wildcard in production** | Any origin can call API, CSRF risk | Specify exact allowed origins, use SameSite cookies |
| **No rate limiting on expensive endpoints** | Resource exhaustion via /optimize abuse | Per-user rate limits, stricter on expensive operations |
| **Logging sensitive data** | Driver salaries, strategies exposed in logs | Redact sensitive fields before logging |
| **No API key rotation** | Compromised keys remain valid forever | Implement key expiration and rotation mechanism |
| **Missing audit logs** | Can't investigate security incidents | Log all auth, job submission, result access events |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| **No progress indication** | Users don't know if job is stuck or running | Return progress percentage, estimated completion |
| **Error messages like "Optimization failed"** | No way to fix or retry intelligently | Include specific reason (e.g., "No valid lineup: salary constraints too tight") |
| **No job history** | Lost results if page refreshed | Persist job list, allow re-querying past results |
| **Binary success/fail feedback** | Can't distinguish between "calibration failed but lineup valid" vs. "total failure" | Partial success with component-level status |
| **No preview mode** | Users waste compute on bad parameters | Provide "dry run" that validates constraints without full optimization |
| **Hidden API errors** | Frontend shows generic error | Surface API error details in UI |
| **No cost indication** | Users don't know resource impact | Show estimated compute time/cost before submission |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Job persistence:** Often missing restart recovery — verify jobs survive container restart
- [ ] **Health checks:** Often missing dependency checks — verify Neo4j/Redis connectivity tested
- [ ] **Error handling:** Often missing proper HTTP status codes — verify 500 on errors, not 200 with null
- [ ] **Timeout handling:** Often missing async job pattern — verify 30-60s jobs use polling
- [ ] **Cancellation:** Often missing abort mechanism — verify jobs can be cancelled
- [ ] **Idempotency:** Often missing duplicate request detection — verify retry safety
- [ ] **Authentication:** Often missing on GET endpoints — verify all endpoints protected
- [ ] **Rate limiting:** Often missing on expensive endpoints — verify /optimize has limits
- [ ] **Monitoring:** Often missing ML-specific metrics — verify calibration CRPS, kernel rejection rate tracked
- [ ] **Logging:** Often missing structured context — verify logs include job_id, user_id for correlation
- [ ] **Graceful shutdown:** Often missing in-flight job handling — verify deployment doesn't kill active jobs
- [ ] **Secrets management:** Often missing proper env var handling — verify no hardcoded credentials

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| **In-memory job state loss** | HIGH | Impossible to recover lost jobs. Migrate to persistent storage immediately. Inform users of data loss. |
| **Silent error masking** | MEDIUM | Review logs for suppressed errors. Add error tracking (Sentry). Fix API to return proper status codes. |
| **Timeout disasters** | MEDIUM | Kill stuck jobs. Implement job queue. Add time estimates to API responses. |
| **Rate limiting absence** | HIGH | Enable rate limiting immediately. Blacklist abusive IPs. Implement user-level quotas. |
| **Alert fatigue** | LOW | Disable noisy alerts. Reconfigure thresholds. Focus on 3-5 critical signals. |
| **Duplicate jobs** | MEDIUM | Cancel duplicates. Implement idempotency keys. Add client-side retry backoff. |
| **Missing auth** | CRITICAL | Disable public access immediately. Add auth to all endpoints. Audit access logs for breaches. |
| **Poor shutdown** | MEDIUM | No recovery for killed jobs. Fix shutdown procedure for next deployment. |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| In-memory job state loss | Phase 1: Job Queue & Persistence | Restart workers, verify jobs still queryable |
| Missing health checks | Phase 1: Infrastructure Foundations | Stop Neo4j, verify health check returns 503 |
| Silent error masking | Phase 1: Error Handling | Send invalid request, verify 400 not 200 |
| Long-running timeouts | Phase 1: Async Job Processing | Submit 60s job, verify no 504 error |
| No rate limiting | Phase 2: Security & Resources | Send 100 req/s, verify rate-limited |
| No job cancellation | Phase 2: Job Management | Submit job, verify cancellation works |
| Alert fatigue | Phase 3: Observability | Verify <5 alerts/week, all actionable |
| Duplicate jobs | Phase 2: API Reliability | Retry same request twice, verify one job |
| Missing result auth | Phase 2: Security | Try accessing other user's job, verify 403 |
| No graceful shutdown | Phase 1: Deployment | Deploy, verify in-flight jobs complete |

## Domain-Specific ML/Optimization Pitfalls

Issues unique to machine learning and optimization APIs.

### Calibration Drift

**What goes wrong:** Models trained on historical data degrade over time as track conditions, car configurations, and driver performance change. Calibration metrics (CRPS, coverage) slowly worsen, but API continues returning results with degraded accuracy.

**Detection:**
- Monitor calibration CRPS trend over time
- Track coverage probability (should be ~0.5 for 50% interval)
- Alert when CRPS increases >20% from baseline
- Compare predicted vs. actual finish positions

**Prevention:**
- Schedule weekly recalibration with recent race data
- Track model age and warn when >30 days old
- Implement A/B testing for new calibration models
- Log calibration metrics with every optimization

---

### Kernel Rejection Rate Spikes

**What goes wrong:** Constraint configuration errors cause kernel rejection rates to spike from normal ~5% to >50%. This wastes compute resources and may indicate impossible constraint combinations.

**Detection:**
- Monitor rejection rate per optimization
- Alert when rejection rate >30%
- Track which constraints are vetoing most often
- Log veto reasons for analysis

**Prevention:**
- Validate constraint combinations before optimization
- Provide "preview mode" to check feasibility
- Document known incompatible constraint patterns
- Use rejection rate as signal for constraint tuning

---

### Scenario Cache Invalidation

**What goes wrong:** Scenario matrices cached by (race_id, n_scenarios) become stale when track conditions or driver lineups change. API returns outdated scenarios, leading to suboptimal lineups.

**Detection:**
- Monitor cache hit rate (should be >80%)
- Track scenario age, warn when >24 hours old
- Compare cached vs. fresh scenario correlation
- Log cache invalidation events

**Prevention:**
- Include constraint_spec_hash in cache key
- Implement TTL-based invalidation (e.g., 6 hours)
- Provide cache flush endpoint for emergency updates
- Document cache behavior in API docs

---

## Sources

- [How to Build Background Task Processing in FastAPI](https://oneuptime.com/blog/post/2026-01-25-background-task-processing-fastapi/view) — Background task implementation patterns
- [FastAPI Deployment Guide for 2026](https://www.zestminds.com/blog/fastapi-deployment-guide/) — Production deployment best practices
- [FastAPI Production Deployment Best Practices](https://render.com/articles/fastapi-production-deployment-best-practices) — Long-running job handling
- [Managing Background Tasks in FastAPI: BackgroundTasks vs ARQ](https://davidmuraya.com/blog/fastapi-background-tasks-arq-vs-built-in/) — Task queue comparison
- [How I Handled Heavy Background Jobs in FastAPI](https://medium.com/@connect.hashblock/how-i-handled-heavy-background-jobs-in-fastapi-without-killing-my-api-7cf4136af8de) — Real-world heavy job experience
- [Handling Background Tasks and Long-Running Jobs in FastAPI](https://python.plainenglish.io/handling-background-tasks-and-long-running-jobs-in-fastapi-the-complete-guide-b197d38145d7) — Complete background task guide
- [FastAPI Background Tasks Documentation](https://fastapi.tiangolo.com/tutorial/background-tasks/) — Official background tasks reference
- Current codebase analysis (main.py, optimize.py) — Identified existing issues with job state, error handling, health checks

---
**Pitfalls research for: ML/Optimization API Production Readiness**
**Researched: 2026-01-28**
**Confidence: MEDIUM** — Based on current codebase analysis and recent FastAPI/ML deployment literature
