# Phase 4: Field / Ownership / Contest-Sim EV - Context

**Gathered:** 2026-01-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Model the field and payout structure to compute true tournament EV. This includes ownership estimation, field lineup modeling, payout curve approximation, and contest-level simulation outputs (ROI, Cash%, win probability). Regime-aware portfolios and leverage-aware optimization are included.

</domain>

<decisions>
## Implementation Decisions

### Ownership Estimation
- Hybrid ensemble approach combining multiple sources
- Mixture of all approaches: historical-based, projections-based, salary-skill regression, with track-archetype awareness, recent form consideration, and seasonal averaging
- Primary signal is hybrid ensemble (not single source)

### Track-Archetype Handling
- Mixture of: track-archetype aware (separate per superspeedway/short track/road course), recent form (rolling 3-5 race window), season average with outlier adjustment, simple track type grouping
- All factors should contribute to ownership estimates in some combination

### Ensemble Weights
- Claude's discretion: determine best approach for combining signals
- Consider static vs dynamic weighting based on data quality/availability
- Consider making configurable per contest vs learned weights

### Ownership Output Format
- Claude's discretion: determine format based on downstream optimization needs
- Options include point estimates, distributions with uncertainty bounds, or scenario-based (low/med/high)
- Choose what best serves contest simulation and leverage-aware optimization

### Claude's Discretion
- Exact ensemble weighting mechanism (static, dynamic, learned, or configurable)
- Ownership output format (point estimates vs distributions vs scenarios)
- How to combine track archetype, recent form, and seasonal signals
- How to handle missing data (e.g., no projections available)

</decisions>

<specifics>
## Specific Ideas

- Mix of all approaches for ownership — don't rely on single signal
- Track archetype should matter (superspeedway vs short track vs road course behavior differs)
- Recent form matters but shouldn't dominate
- Seasonal baseline provides stability, adjust for outliers

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-field-ownership-contest-sim*
*Context gathered: 2026-01-28*
