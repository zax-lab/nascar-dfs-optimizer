# Phase 1: Feasible-by-Design NASCAR Simulation Core - Context

**Gathered:** 2026-01-27
**Status:** Ready for planning

## Phase Boundary

Build a simulation engine that produces mechanically plausible joint NASCAR race outcomes with conserved dominator resources. Delivers state space model with transition operators, Causal Bayesian Network constrained by ontology, Skeleton Narrative scenario generator (1,000+ scenarios), outcome realization (laps led, fastest laps, finish position, place differential, incidents), and Kernel invariants for dominator conservation.

## Implementation Decisions

### Simulation Fidelity

**Time granularity approach:** Hybrid model - detailed granularity for key segments, coarse granularity otherwise

**Key segments (fine granularity):** All three critical race periods
- Caution-bounded segments (crucible of race strategy)
- Pit cycles (fuel/tire strategy decisions)
- Late race (final ~20% where dominator outcomes concentrate)

**Coarse granularity:** Incidence-bounded - event-driven transitions between incidents/cautions

**Granularity transitions:** Event-triggered - switch to fine granularity on caution/pit, return to coarse after

**Coarse mode transitions:** Latent factors - hidden variables (car speed, strategy) drive probabilistic changes during non-key segments

**Track type handling:** Track-specific state space structure per track archetype (not one-size-fits-all)

### Causal Bayesian Network

**CBN depth:** Claude's discretion - choose between full DBN, simplified DBN, or latent-factor approach based on implementability and effectiveness

**CBN variables to model:** Claude's discretion - determine what race dynamics matter for DFS scoring variance

**Ontology constraints:** Claude's discretion - structure only, hard veto rules, or both based on ontology capabilities

**CBN parameterization:** Claude's discretion - data-driven, domain-encoded, or hybrid based on data readiness

**Temporal modeling:** Claude's discretion - time-sliced DBN, event-based, or hybrid aligned with state space design

**Scenario generation:** Claude's discretion - forward sampling, conditional sampling, or regime-based for diverse plausible scenarios

**Uncertainty handling:** Claude's discretion - heavy tails, regime mixtures, or standard variance for realistic tail estimates

**Kernel integration:** Claude's discretion - post-validation, constrained sampling, or reject-resample for efficiency and correctness

### Conservation Enforcement

**Enforcement timing:** Claude's discretion - during generation (feasible-by-design), post-validation, or hybrid

**Conserved resources:** Claude's discretion - dominator points only, dominator + positions, or full component conservation based on physical meaningfulness

**Violation handling:** Claude's discretion - reject scenario, auto-repair, or penalize based on iteration utility

**Conservation bounds:** Claude's discretion - physical only, physical + historical, or track-aware bounds for realism and tractability

**Place differential coupling:** Claude's discretion - fully deterministic, bounded stochastic, or independent with validation

**Multi-scenario portfolios:** Claude's discretion - independent per scenario, cross-scenario constraints, or hybrid for stable portfolio optimization

**Rule encoding:** Claude's discretion - hardcoded, ontology-derived, or config-driven for maintainability vs performance

**Validation performance:** Claude's discretion - incremental, batch, or hybrid for speed with JAX

### Scenario Data Contract

**Scenario structure:** Claude's discretion - driver array, hierarchical, or full trajectory based on optimizer needs and efficiency

**DFS components:** All DFS components - dominator (laps led, fastest laps) + finishing (finish position, place differential) + incidents + DNF flag

**Serialization format:** Claude's discretion - JSON, Arrow, or Parquet based on performance and compatibility needs

**Scenario metadata:** Full metadata - regime type, scenario weight, random seed, generation parameters for diagnostics and analysis

### Claude's Discretion

The following areas are delegated to Claude's discretion during planning and implementation:

**Simulation Fidelity:**
- State variables to track for each driver
- Scenario count per slate for stable tail estimates

**Causal Bayesian Network:**
- CBN depth (full DBN vs simplified vs latent factors)
- Race dynamics to model causally
- How ontology constrains the CBN
- Parameterization approach (data-driven vs domain vs hybrid)
- Temporal modeling approach
- Scenario generation method
- Uncertainty handling for tail outcomes
- Kernel integration approach

**Conservation Enforcement:**
- Enforcement timing (during generation vs post-validation vs hybrid)
- Which resources to conserve
- How to handle violations
- How bounds are determined
- Place differential coupling to grid/finish
- Multi-scenario portfolio constraints
- Rule encoding approach
- Validation performance approach

**Scenario Data Contract:**
- Scenario data structure
- Serialization format

## Specific Ideas

- **Skeleton Narrative concept:** Race is mostly quiet (coarse mode) until something happens (incident/caution triggers fine mode)
- **Key segments focus:** Cautions shuffle the field, pit cycles determine strategy, late race is where dominator outcomes concentrate
- **Event-driven transitions:** Switch granularity based on race events, not fixed time points
- **Track-specific modeling:** Different track archetypes (superspeedway vs intermediate vs short track) need different state space structures

## Deferred Ideas

None — discussion stayed within Phase 1 scope.

---

*Phase: 01-feasible-by-design-nascar-simulation-core*
*Context gathered: 2026-01-27*
