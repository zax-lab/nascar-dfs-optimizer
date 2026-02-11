# Phase 3: Tail Metrics + Tail-Objective Portfolio Optimizer - Context

**Gathered:** 2026-01-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a portfolio optimizer that targets top-tail outcomes (tournament equity) rather than mean points. Takes calibrated scenario outputs from Phase 2 as input, produces DFS lineups with exposure controls as output. This is algorithmic optimization infrastructure, not UI.

</domain>

<decisions>
## Implementation Decisions

### Tail objective formulation
- **Approach:** CVaR (Conditional Value at Risk) optimization
- **Multi-CVaR:** Weighted combination of CVaR(99%) + CVaR(95%) for stability while still targeting top 1%
- **Target threshold:** Top 1% aggressive optimization for large-field NASCAR GPPs
- **Adaptive scenario handling:** Threshold adjusts based on scenario count to prevent instability from insufficient samples
- **Hybrid portfolio approach:** Each lineup optimized for top-tail independently, then portfolio post-processing for diversity

### Portfolio generation strategy
- **No warm starting:** Each lineup is an independent fresh solve — slower but more diverse exploration (avoids local optima)
- **Correlation penalty:** Minimize pairwise correlation as secondary objective for diversity — softer enforcement than hard no-good constraints

### Claude's Discretion
- **Multi-CVaR weights:** Choose weights combining CVaR(99%) and CVaR(95%) based on empirical testing of stability vs upside
- **Adaptive threshold rule:** Choose sensible default based on research into stability of tail estimators (consider tiered thresholds or continuous formula)
- **Tail metric caching:** Choose approach (pre-compute all tails vs lazy evaluation) based on typical scenario counts and memory constraints
- **CVaR implementation formulation:** Choose solver formulation (Rockafellar-Uryasev MILP vs CP-SAT native) based on what integrates best with existing optimizer infrastructure
- **Tail objective validation:** Choose practical validation approach to confirm optimizer targets tails not mean (post-hoc analysis vs in-process monitoring)

</decisions>

<specifics>
## Specific Ideas

- **CVaR preference:** Standard approach for coherent risk measures, well-established in optimization literature
- **No warm starting:** Avoids getting stuck in local optima — important for tail optimization which may have multiple distinct high-tail regions
- **Correlation penalty:** Softer than hard no-good constraints — allows some similarity if justified by tail exposure

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope (tail objective formulation for portfolio optimizer)

</deferred>

---

*Phase: 03-tail-metrics-tail-objective-portfolio-optimizer*
*Context gathered: 2026-01-27*
