# Milestones: Axiomatic NASCAR DFS

## v1.0 — Core Simulation & Optimization Engine

**Completed:** 2026-01-28

**What Shipped:**

### Phase 1: Feasible-by-Design NASCAR Simulation Core (6 plans)
- State space model with explicit transition operators (green, caution, pit, fuel)
- Ontology-constrained Causal Bayesian Network with veto rules
- Skeleton Narrative scenario generator (1,000+ scenarios)
- Kernel dominator conservation validation with JAX acceleration
- CBN forward sampling (gap closure)
- CBN integration into scenario generation (gap closure)

### Phase 2: Ontology-Compiled Constraints + Calibration Harness (5 plans)
- ConstraintSpec compilation from Neo4j (immutable artifacts)
- Telemetry pipeline with Polars and feature availability contracts
- Track-archetype calibration harness (NumPyro + ArviZ)
- Headless /optimize API with scenario-driven contracts
- Kernel instrumentation and end-to-end integration

### Phase 3: Tail Metrics + Tail-Objective Portfolio Optimizer (9 plans)
- Tail metrics computation (CVaR, Top X%, conditional upside)
- CVaR objective builders (Rockafellar-Uryasev MILP formulation)
- Portfolio generation with scenario optimization
- API integration and end-to-end optimization
- Bounded CVaR for upper-tail maximization (gap closure)
- Real mean-optimized baseline (gap closure)
- Missing test files created (gap closure)
- Portfolio generator integration tests (gap closure)
- API integration tests (gap closure)

### Phase 4: Field / Ownership / Contest-Sim EV (6 plans)
- Individual ownership estimators (historical, projections, salary-skill)
- Hybrid ensemble with recent form and uncertainty quantification
- Payout curve modeling (power-law, exponential)
- Field lineup simulation and Monte Carlo contest engine
- Leverage-aware optimization with ownership constraints
- API integration and end-to-end testing

**Requirements Validated (14 total):**
- SIM-01, SIM-02, SIM-03: State space, CBN, Skeleton Narratives ✓
- KRN-01: Dominator conservation constraints ✓
- DATA-01: Premium telemetry ingestion ✓
- API-01: Headless execution contract ✓
- OPT-01, OPT-02: Conditional-upside objective, portfolio generation ✓
- DFS-01 through DFS-06: Table stakes DFS optimizer features ✓

**Total Plans:** 24 (including 8 gap closures)
**Total Phases:** 4

---

## v1.1 — Production Readiness (ARCHIVED)

**Status:** Archived 2026-01-29 — Direction change to local Mac app

**What was planned:**
- Phase 5.1: Critical Infrastructure (Redis, health checks, structured logging) — 3/3 plans complete
- Phase 5.2: Security & Reliability (JWT auth, rate limiting) — not started
- Phase 5.3: Observability (Prometheus, Grafana) — not started
- Phase 5.4: Background Task Processing (Celery) — not started

**Why archived:** Project vision clarified as personal local Mac app, not SaaS service. Authentication, rate limiting, and public web API are unnecessary for single-user local application.

**Reusable work:** Phase 5.1 (Redis job persistence, health checks, structured logging) may be useful for local app reliability.

---

## v1.2 — Native Mac App (CURRENT MILESTONE)

**Started:** 2026-01-29
**Goal:** Personal-use NASCAR DFS optimizer as native Apple Silicon Mac app with optional Windows GPU offload

**Vision:**
- **Interface:** Native macOS GUI (PySide6/PyQt recommended)
- **Computation:** Local Apple Silicon (M1/M2/M3) with optional Windows GPU offload
- **Data Ingestion:** API → Web scraping → Manual import (with fallbacks)
- **Output:** In-app viewing + CSV export for DraftKings upload
- **User model:** Single user (local only, no web exposure)
- **Security:** None needed (local-only application)

**Planned phases:** TBD (defining requirements)

---
