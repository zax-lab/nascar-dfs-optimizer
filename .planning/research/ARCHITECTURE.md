# Architecture Research

**Domain:** NASCAR DraftKings DFS — causal race simulation + conditional-upside portfolio optimizer
**Researched:** 2026-01-27
**Confidence:** MEDIUM

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                      Application                                     │
├─────────────────────────────────────────────────────────────────────────────────────┤
│  FastAPI/Next/Airflow (orchestration, UI, APIs, scheduling)                          │
│                                                                                     │
│  ┌───────────────┐    ┌──────────────────────────┐    ┌──────────────────────────┐  │
│  │ /simulate     │    │ /optimize                │    │ /explain (debug)          │  │
│  │ scenarios     │    │ tail-portfolio           │    │ kernel veto + BN factors  │  │
│  └──────┬────────┘    └──────────────┬───────────┘    └──────────────┬───────────┘  │
├─────────┴────────────────────────────┴───────────────────────────────┴──────────────┤
│                                      Kernel                                          │
├─────────────────────────────────────────────────────────────────────────────────────┤
│  Axiomatic constraints + validators (final veto)                                     │
│  - lineup constraints (DK 6, salary cap)                                             │
│  - race “conservation” laws (laps led, fastest laps budgets, etc.)                   │
│  - impossible-state detection                                                        │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                              Simulation + Inference (New)                             │
├─────────────────────────────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────┐   ┌──────────────────────────┐   ┌─────────────────┐ │
│  │ Ontology-Constrained BN/DBN│   │ State Space + Transition  │   │ Scenario Engine  │ │
│  │ (causal structure + params)│   │ Operators (Markov)        │   │ (narratives)     │ │
│  └──────────────┬────────────┘   └──────────────┬───────────┘   └────────┬────────┘ │
│                 │                                 │                        │          │
│                 └──────────────┬──────────────────┴──────────────┬────────┘          │
│                                │                                 │                   │
│                    ┌───────────▼───────────┐          ┌──────────▼───────────┐      │
│                    │ Outcome Realizer       │          │ Scoring + Featurizer  │      │
│                    │ (laps led, FL, PD, DNF)│          │ (DK points + attrs)   │      │
│                    └───────────┬───────────┘          └──────────┬───────────┘      │
├────────────────────────────────┴──────────────────────────────────┴──────────────────┤
│                                    Portfolio Optimizer (New)                          │
├─────────────────────────────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────┐   ┌──────────────────────────────┐   ┌─────────────┐ │
│  │ Tail Objective Layer       │   │ MILP/CP-SAT Lineup Solver     │   │ Portfolio    │ │
│  │ (top-1% / CVaR / chance)   │   │ (constraints + exposures)     │   │ Diversifier  │ │
│  └──────────────┬────────────┘   └──────────────┬───────────────┘   └─────┬───────┘ │
│                 │                                 │                         │         │
│                 └─────────────── kernel validate ──┴─────── kernel validate ┘         │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                      Ontology                                         │
├─────────────────────────────────────────────────────────────────────────────────────┤
│  Neo4j graph: Driver/Track/Race + metaphysical properties (priors + constraints)     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| Kernel (existing) | Final arbiter of what is feasible. Validates both simulation states and optimized lineups. Enforces conservation + DK rules. | Pure Python module/package with deterministic functions; no DB/network; unit tests. |
| Ontology (existing) | Stores entities, edges, priors, and “metaphysical” driver props; provides constraints on causal graph structure and allowable parameter ranges. | Neo4j driver wrapper + schema/constraints; query layer returning typed domain objects. |
| Ontology-Constrained BN/DBN (new) | Represents causal dependencies among latent and observed variables; optionally dynamic (2-slice DBN) to couple time steps. Produces conditional distributions used by simulation. | Probabilistic model spec + parameter store. Keep separate from simulator so it can be tested/fit independently. |
| State Space + Transition Operators (new) | Defines the discrete/continuous state, transition kernels, and event operators (green/caution/pit/fuel) with explicit invariants (also checked by Kernel). | “Transition registry” of operators with preconditions/effects; Markov stepper; small composable functions. |
| Scenario Engine (“Skeleton Narratives”) (new) | Generates coherent scenario skeletons (regimes) and seeds the simulator so outcomes are correlated and mechanically plausible. | Narrative sampler producing high-level regime variables + event schedules; drives transitions. |
| Outcome Realizer (new) | Converts state trajectories into DFS-relevant components (laps led, fastest laps, PD, incidents). | Aggregators mapping trajectory → per-driver component totals + uncertainty. |
| Scoring + Featurizer (new) | Turns realized components into DK points and exposes scenario features needed for optimization diagnostics and explanations. | Deterministic scorer; scenario feature vector builder. |
| Tail Objective Layer (new) | Encodes “optimize for top 1%” into an objective over scenario outcomes (chance constraints, quantile proxy, CVaR-like surrogates). | Objective builders that emit solver-ready linear terms/aux vars, plus evaluation metrics. |
| Lineup Solver (existing-ish) | Solves lineup selection under DK + exposures + stacking rules; now consumes scenario outputs and tail objectives. | MILP (PuLP/HiGHS/Gurobi) or CP-SAT (OR-Tools). |
| Portfolio Diversifier (new) | Generates a set of lineups (portfolio) with exposure constraints and scenario-robust diversity while preserving tail goals. | Iterative solve loop with cuts (no-good cuts / overlap caps), exposure bookkeeping, kernel validation. |

## Recommended Project Structure

This maps to your monorepo conventions (apps + packages) and keeps “Kernel as final veto” enforceable.

```
apps/
  backend/
    app/
      api/                       # FastAPI endpoints (simulate/optimize/explain)
      services/
        simulation_service.py     # orchestrates BN+sim, caches scenarios
        optimizer_service.py      # orchestrates tail objective + portfolio solve
packages/
  axiomatic-kernel/
    kernel/
      constraints.py             # immutable rules + conservation laws
      validate.py                # veto interface (states + lineups)
  axiomatic-ontology/
    ontology/
      neo4j_driver.py
      constraints.py             # ontology-provided invariants + priors schema
  axiomatic-sim/
    sim/
      state_space.py             # State definition (typed), minimal
      transitions/
        green_run.py
        caution.py
        pit_cycle.py
        fuel_window.py
      narrative/
        skeleton.py              # scenario regimes + event schedule sampling
      bn/
        structure.py             # allowed DAG/2TBN structure from ontology
        parameters.py            # CPT/CPD parameter store + versioning
        inference.py             # sampling/inference interface
      realize/
        components.py            # laps led/FL/PD/incident realization
        dk_scoring.py            # deterministic DK scoring
  axiomatic-optimizer/
    optimizer/
      objectives/
        tail.py                  # top-1% proxy objectives (chance/CVaR/etc.)
      milp/
        model.py                 # decision vars + constraints + objective hooks
      portfolio/
        generator.py             # iterative lineup generation + exposures
        exposures.py
      evaluate/
        metrics.py               # tail metrics, attribution, calibration
```

### Structure Rationale

- **Separate `axiomatic-sim` from Kernel and Ontology:** simulation can evolve rapidly (new transitions, richer BN), while Kernel remains conservative and easy to test.
- **Make “ontology constraints” explicit code in `axiomatic-ontology/constraints.py`:** the BN/DBN layer should not query Neo4j ad hoc during inner loops; it should compile a constraint spec up front.
- **Keep optimizer objective builders pure and solver-agnostic:** objective definitions should emit a canonical form (aux vars + linear pieces), so you can swap PuLP/HiGHS vs OR-Tools later.

## Architectural Patterns

### Pattern 1: Compiled Constraint Spec (Ontology → Sim/BN)

**What:** At run start (or per slate), compile a “constraint spec” from Neo4j into an in-memory immutable object used by BN structure validation, parameter bounds, and transition/operator preconditions.
**When to use:** Always; it prevents hidden DB calls during simulation/optimization and makes runs reproducible/versionable.
**Trade-offs:** Extra up-front step + versioning work; huge gains in determinism and debuggability.

**Example:**
```typescript
// Pseudocode shape (language-agnostic)
type ConstraintSpec = {
  allowedEdges: Array<[string, string]>,
  parameterBounds: Record<string, [number, number]>,
  vetoRules: string[],
}
```

### Pattern 2: Operator Registry for Markov Transitions

**What:** Model race flow as a state machine where each operator has explicit preconditions, stochastic parameterization, and postconditions checked by Kernel.
**When to use:** When you need coherent scenarios: cautions change pit strategy; pit cycles affect track position; fuel windows cap green runs.
**Trade-offs:** More engineering than i.i.d. sampling; but it’s the only way to guarantee conservation and coherent joint outcomes.

**Example:**
```typescript
// Pseudocode shape
interface TransitionOperator<S> {
  name: string
  pre(s: S): boolean
  step(s: S, rng: RNG, params: Params): S
  post(s: S): boolean // then Kernel.validate_state(s)
}
```

### Pattern 3: Tail Objective as Chance Constraint / CVaR Surrogate

**What:** Convert “maximize top 1%” into a solver-friendly objective:
- **Chance-style:** maximize \( \sum_{k \in scenarios} \mathbb{1}[score(lineup,k) \ge T] \) (typically relaxed/approximated)
- **CVaR-style:** maximize expected score in worst/best tail region depending on framing, or maximize a convex surrogate of tail performance
**When to use:** When mean EV is not the target and you can afford scenario simulation.
**Trade-offs:** Requires scenario generation + extra variables; but aligns directly with GPP outcomes.

## Data Flow

### Request Flow

```
User/API request (slate inputs, priors, constraints, N scenarios, portfolio size)
    ↓
Ontology compile (Neo4j → ConstraintSpec + priors + meta)
    ↓
BN/DBN build + parameter bind (validate structure against ConstraintSpec)
    ↓
Scenario skeleton sampling (regimes + event schedule)
    ↓
Trajectory simulation (operators: green/caution/pit/fuel)  ── kernel validate states
    ↓
Outcome realization (laps led/FL/PD/incidents)              ── kernel validate totals/conservation
    ↓
DK scoring per scenario
    ↓
Tail objective build (top-1% proxy; thresholds; exposure constraints)
    ↓
Portfolio generation loop (solve → validate → add diversity cuts → repeat)
    ↓
Return (lineups + exposures + tail metrics + explanations + kernel veto logs)
```

### Key Data Flows

1. **Ontology → BN/DBN constraints:** Neo4j provides allowed causal edges / parameter bounds / regime priors; BN/DBN compiler rejects disallowed structure before any sampling.
2. **Skeleton Narrative → Transition Operators:** scenario regimes parameterize operators (e.g., higher caution intensity, pit cycle volatility, fuel-save probability).
3. **Kernel veto everywhere it matters:** Kernel validates (a) operator postconditions, (b) conservation totals after realization, and (c) final lineup feasibility.
4. **Simulation → Optimizer:** optimizer consumes scenario matrix of lineup points (and optionally component breakdowns) to evaluate tail metrics and build objectives.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-1k users | Single machine run: compile ontology + simulate + optimize synchronously; cache scenario sets per slate. |
| 1k-100k users | Asynchronous job model: enqueue simulate/optimize jobs; store scenario matrices + results; aggressive caching by (slate, seed, spec version). |
| 100k+ users | Split services: dedicated simulation workers; dedicated optimizer workers; store artifacts in object storage; strict versioning of specs/models. |

### Scaling Priorities

1. **First bottleneck:** scenario simulation volume (N scenarios × drivers × time steps). Fix with operator efficiency, vectorization, and caching of skeleton regimes.
2. **Second bottleneck:** portfolio solving (K lineups × MILP). Fix with warm starts, cut management, and simplifying tail objective proxies.

## Anti-Patterns

### Anti-Pattern 1: “BN samples driver outcomes independently”

**What people do:** sample laps led / fastest laps / PD per driver as independent draws, then clamp totals later.
**Why it's wrong:** produces incoherent joint outcomes and forces heavy-handed post-hoc clipping that destroys tail structure.
**Do this instead:** sample a small set of **race-level latent factors** (regime, caution rate, pit-cycle volatility, dominant-car strength), then realize per-driver components conditionally; enforce conservation via state/trajectory + kernel checks.

### Anti-Pattern 2: “Kernel only validates final lineup”

**What people do:** allow simulation to generate impossible states, then only validate at the end.
**Why it's wrong:** the optimizer will exploit artifacts (impossible tails) and you won’t know why results look great but fail live.
**Do this instead:** validate at three levels: operator postconditions, realized component conservation, and final lineup constraints; persist veto reasons for debugging.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Neo4j | Compile-time constraint/priors extraction | Avoid per-step DB calls; version the compiled spec in artifacts. |
| Solver (HiGHS/Gurobi/OR-Tools) | Solver adapter interface | Keep objective builders solver-agnostic; isolate solver specifics in one module. |
| Airflow ETL | Produces ontology updates + parameter datasets | Treat ETL outputs as inputs to BN parameter fitting + validation. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Kernel ↔ Sim | Direct function calls (pure) | Kernel exposes `validate_state`, `validate_realized_components`, `validate_lineup`. |
| Ontology ↔ BN/Sim | Compiled `ConstraintSpec` + priors | Deterministic artifact; include version hash in every run. |
| Sim ↔ Optimizer | Scenario outcome matrix + features | Contract should be stable: points, components, scenario weights, thresholds. |
| Optimizer ↔ Application | Service interface | Returns portfolio, exposures, scenario diagnostics, and explain artifacts. |

## Suggested Build Order (Roadmap Implications)

1. **Define the explicit state space + transition operator interfaces** (green/caution/pit/fuel) and add Kernel postcondition checks.
2. **Implement “Skeleton Narrative” regime variables + event schedule sampling** (low fidelity), drive operators, and produce coherent trajectories.
3. **Add Outcome Realizer + DK scoring + conservation checks** (laps led, fastest laps budgets) in Kernel; validate distributions on known races.
4. **Introduce ontology-compiled `ConstraintSpec`** and wire it into (a) BN structure validation and (b) operator parameter bounds.
5. **Add BN/DBN layer gradually**: start with race-level latent factors (regime) → conditional component models; only then consider full 2-slice DBN unrolling.
6. **Implement tail objective proxies + portfolio generator**: start with a simple chance-style threshold objective on scenario points; then iterate to stronger surrogates (e.g., CVaR-like) if needed.
7. **Add explainability + veto attribution** as first-class outputs (why a scenario/lineup is good; why Kernel vetoed).

## Sources

- DYNAMAX (JAX state space models / HMMs / inference): `https://probml.github.io/dynamax/` (WebSearch; verify in implementation phase)  
- pyAgrum Dynamic Bayesian Networks docs: `https://pyagrum.readthedocs.io/en/latest/notebooks/22-Models_dynamicBn.html` (WebSearch; verify in implementation phase)
- BayesiaLab DBN overview: `https://www.bayesia.com/bayesialab/user-guide/tools/dynamic-bayesian-networks` (WebSearch; conceptual reference)
- Krokhmal & Uryasev (CVaR portfolio optimization survey/paper entry): `https://www.semanticscholar.org/paper/Portfolio-optimization-with-conditional-objective-Krokhmal-Uryasev/946a347d482fac2692fe795244455302ab2af547` (WebSearch; verify primary source)
- MILP formulations for probabilistic (chance) constraints (overview entry): `https://www.sciencedirect.com/science/article/abs/pii/S0167637712000168` (WebSearch; verify access/primary)

---
*Architecture research for: NASCAR DFS causal simulation + tail-optimized portfolio generation*
*Researched: 2026-01-27*
