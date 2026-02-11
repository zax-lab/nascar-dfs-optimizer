# Axiomatic NASCAR DFS — Causal Simulation + Conditional Upside Optimizer

## What This Is

This project is a **personal-use NASCAR DraftKings DFS optimizer** as a native Mac app for Apple Silicon:

- **Race-flow simulation** (not independent driver regressions): produce probabilistic component outcomes (laps led, fastest laps, place differential, incidents) under explicit state-space dynamics.
- **Ontology-constrained reasoning**: a Neo4j ontology provides priors and *hard veto constraints* on impossible race states.
- **Conditional-upside optimization**: the optimizer targets **top-1% outcomes** (tournament equity / simulated ROI) rather than mean expected points.
- **Native Mac GUI**: Local application with no web exposure, single-user (me).

The system follows the architecture: **Kernel (immutable logic) → Ontology (graph) → Application (local Mac app)**. The Kernel is final arbiter: metaphysical/ML signals may reweight probabilities, but **may not violate hard constraints**.

## Why Now

Standard NASCAR DFS projection stacks often:
- model drivers independently (breaking "conservation of dominator points"),
- optimize for mean EV (which is frequently dominated by conditional-upside strategies in large-field GPPs),
- and fail to encode NASCAR race mechanics (pit cycles, tire falloff, cautions, fuel windows) as constraints.

This project aims to formalize those mechanics into an enforceable logic layer, then optimize *against simulated scenario distributions* — delivered as a personal local Mac application with optional GPU offload to a Windows desktop.

## Users

- **Primary:** Single user (me) — personal use only
- **Platform:** Apple Silicon Mac (M1/M2/M3) running native macOS app
- **Optional:** Windows desktop with GPU for heavy computation offload

## Non-Goals (for v1.2)

- Public SaaS product or web service
- Multi-user support or authentication
- Web API exposure or CORS configuration
- Real-time live telemetry ingestion during races
- Kubernetes or cloud deployment
- Supporting every DFS site/scoring format (DraftKings NASCAR Classic only)

## Current System (Validated Capabilities — v1.0 Complete)

Based on the existing codebase map (v1.0 shipped 2026-01-28):

- ✓ **Kernel validation**: immutable constraint checks / impossible state detection (`apps/backend/app/kernel.py`)
- ✓ **Ontology layer**: Neo4j driver wrapper + Driver/Track/Race nodes with required metaphysical properties (`apps/backend/app/ontology.py`)
- ✓ **Backend API**: FastAPI app with `/optimize` and `/health` (`apps/backend/app/main.py`)
- ✓ **LP optimizer**: PuLP-based optimizer plumbing (`apps/backend/app/optimizer.py`)
- ✓ **ETL scaffold**: Airflow DAGs for ingestion into Neo4j (`apps/airflow/dags/`)
- ✓ **Frontend**: Next.js dashboard for projections / optimization (`apps/frontend/`)

## Vision (What "Bulletproof" Means)

"Bulletproof" means we can **prevent nonsense** and **capture tail outcomes**:

1. **Conservation laws are enforced**:
   - total laps led cannot exceed race length
   - dominator points are conserved (if A dominates, B cannot simultaneously dominate at incompatible levels)
   - pit-cycle and fuel-window constraints gate feasible transitions

2. **Race-flow is modeled explicitly**:
   - not just "Markov-ish": transitions are governed by a **Causal Bayesian Network constrained by the ontology**
   - simulation produces coherent "Skeleton Narratives" (e.g., Dominator race, Chaos race, Fuel-mileage race)

3. **Optimization targets tournament equity**:
   - maximize **conditional upside**: probability mass in the top tail (e.g., top 1% of field)
   - portfolio emerges from scenario simulation, not a single mean projection

## Requirements

### Validated (v1.0 — Complete)

- ✓ Kernel can validate core constraints and veto impossible states — Phase 1 complete
- ✓ Ontology exists and can store required driver metaphysical properties — Phase 2 complete
- ✓ API optimization endpoint exists (`/optimize`) — Phase 3 complete
- ✓ Tail-optimized portfolio generation (top-1% outcomes) — Phase 3 complete
- ✓ Ownership/contest simulation for tournament EV — Phase 4 complete

### Active (v1.2 — Native Mac App)

*To be defined via research and requirements gathering*

## Current Milestone: v1.2 Native Mac App

**Goal:** Build a personal-use NASCAR DFS optimizer as a native Apple Silicon Mac app with optional Windows GPU offload.

**Vision:**
- **Interface:** Native macOS GUI (PySide6/PyQt for Python codebase reuse)
- **Computation:** Local Apple Silicon optimization with optional remote Windows GPU offload
- **Data Ingestion:** API → Web scraping → Manual import (with intelligent fallbacks)
- **Output:** In-app lineup visualization + CSV export for DraftKings upload
- **Deployment:** Local Mac app bundle (.app), no web exposure
- **User model:** Single user (me), no authentication needed

**Target features:**
- Native Mac GUI with menu bar, native controls, macOS look-and-feel
- Apple Silicon-optimized computation (M1/M2/M3 acceleration)
- Optional remote job offload to Windows desktop with GPU
- Automated data ingestion (API preferred, web scraping fallback, manual import last resort)
- Lineup portfolio display with sorting, filtering, export
- CSV export compatible with DraftKings upload
- Local persistence (SQLite/local Neo4j) for races, lineups, results
- Background job processing for long MCMC calibration runs

### Out of Scope (for v1.2)

- Public web API or SaaS deployment
- Multi-user authentication or authorization
- CORS, rate limiting, or public-facing security
- Kubernetes, Docker Compose, or cloud infrastructure
- Real-time live betting or in-race optimization
- Mobile apps (iOS/Android)
- Multiple DFS sites (DraftKings NASCAR Classic only)

## Success Metrics

- **Mechanical validity**: Kernel veto rate is explainable (every veto has a clear rule and inputs).
- **Distribution quality**: simulations produce plausible dominator/chaos regimes and conserve laps led.
- **Tournament alignment**: optimizer can explicitly target and report top-tail probability (e.g., \(P(\text{score} \ge T)\)) and produce diversified portfolios.
- **Operational speed**: optimization runs fast enough for pre-lock workflow (target: seconds-to-low-minutes on Apple Silicon).
- **App usability**: native Mac GUI feels responsive, intuitive, and "native" (not like a wrapped web app).

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use ontology as a **hard constraint/veto system** (and priors) | Enforces physics/race-mechanics; prevents impossible states | ✓ Validated (v1.0) |
| Model as **Causal Bayesian Network + skeleton narrative simulation** | Encodes race flow, not independent driver outcomes | ✓ Validated (v1.0) |
| Optimize for **conditional upside** (top 1% tail) | EV is insufficient for large-field NASCAR GPPs | ✓ Validated (v1.0) |
| Use premium loop/lap-by-lap telemetry | Needed for tire falloff/long-run speed; results-only is insufficient | ✓ Validated (v1.0) |
| **Build as local Mac app, not SaaS** | Personal use tool; if highly profitable, keep proprietary | — New for v1.2 |
| **PySide6/PyQt for native GUI** | Reuse existing Python codebase; native macOS look-and-feel | — New for v1.2 |
| **Optional Windows GPU offload** | Heavy MCMC jobs can run faster on desktop GPU; Apple Silicon for everyday use | — New for v1.2 |

## Constraints & Assumptions

- DraftKings NASCAR Classic rules: **6 drivers**, **salary cap 50,000**, standard DK scoring.
- Neo4j driver properties must include: `skill`, `psyche_aggression`, `shadow_risk`, `realpolitik_pos` (0–1).
- Kernel is authoritative: metaphysical/ML weights may shift probabilities but cannot violate hard logic constraints.
- Target platform: Apple Silicon Mac (M1/M2/M3) running macOS 12+ (Monterey or later).
- Optional remote compute: Windows desktop with NVIDIA GPU (CUDA-supported) on same local network.
- Data sources: NASCAR official data APIs (if available/free), publicly accessible websites, or manual CSV import.
- Single-user assumption: No authentication, authorization, or multi-user isolation needed.

---
*Last updated: 2026-01-29 after v1.2 Native Mac App milestone initialization*

