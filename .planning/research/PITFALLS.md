# Pitfalls Research

**Domain:** NASCAR DFS causal simulation + top-tail lineup optimization (DraftKings Classic)
**Researched:** 2026-01-27
**Confidence:** MEDIUM

## Critical Pitfalls

### Pitfall 1: Not conserving dominator events (laps led / fastest laps)

**What goes wrong:**
Sim independently samples “laps led” and “fastest laps” per driver (or scales them post-hoc), so totals don’t match race reality (finite laps, cautions, stage breaks). This inflates dominator ceilings, creates impossible multi-dominator outcomes, and corrupts GPP tail selection.

**Why it happens:**
It’s easier to model per-driver marginals than the joint allocation problem. Many projects start from per-driver averages/percentiles and “spray” outcomes without a conservation mechanism.

**How to avoid:**
- Treat dominator points as a **conserved resource** allocated across drivers and segments.
- Model at the right granularity:
  - Total green-flag laps (or “net laps”) and segmentable race states (long-run vs short-run).
  - A latent “control of race” process (lead-share) that allocates **laps led** to 1–3 drivers with realistic handoffs.
  - A separate, correlated “clean-air pace” process that allocates **fastest laps**, constrained by available green-flag laps (sites explicitly subtract caution laps in fast-lap accounting in their own analyses).
- Enforce hard constraints via Kernel veto: totals must match \( \sum_i \text{laps\_led}_i = L \) and \( \sum_i \text{fast\_laps}_i \le L_{\text{green}} \) (or your chosen definition).

**Warning signs:**
- Sim produces multiple drivers each with “near-max” fastest laps on short races.
- Total simulated fastest laps or laps-led routinely exceeds race laps.
- Dominator points distribution is too wide vs historical track distributions (e.g., too many “3-dominator” races at tracks that usually concentrate).

**Phase to address:**
Phase 1 — Simulation core + conserved dominator allocator.

---

### Pitfall 2: Treating finish position and place differential as independent noise

**What goes wrong:**
Finish position is sampled independently from starting position (or PD is added as independent noise), producing impossible trajectories (e.g., backmarkers “teleport” to top-5 too often, or front-row starters gain massive PD).

**Why it happens:**
People reuse generic “projection + random error” frameworks that ignore that PD is a deterministic function of start and finish, and that finish outcomes are heavily constrained by track position dynamics.

**How to avoid:**
- Sample **finish position** (or continuous latent performance rank), then derive PD deterministically from the actual grid.
- Condition performance variance on track type (superspeedway chaos vs intermediate stability) and on driver/team tier.
- Apply Kernel constraints: positions in \([1, \text{field\_size}]\), uniqueness (no ties), and PD derived from the lineup’s actual starting spots.

**Warning signs:**
- Simulated PD distribution is symmetric around 0 for most drivers regardless of start.
- Too many “+25 PD” outcomes on intermediate tracks.
- Duplicate finish positions or finishes outside field size show up pre-kernel.

**Phase to address:**
Phase 1 — Simulation core (finish/PD coupling + kernel validation).

---

### Pitfall 3: Correlation modeling that ignores *shared causes* (hidden correlation)

**What goes wrong:**
Correlation is modeled only via coarse heuristics (same team = +corr; teammates can’t both smash = -corr), missing the dominant driver of correlation: shared underlying race scripts (cautions, long-run pace, pit cycles, aero balance).

**Why it happens:**
Correlation is hard to specify manually; it’s tempting to add a static covariance matrix and move on. Community writing on DFS correlation emphasizes “hidden correlation” driven by shared upstream assumptions and conditional probabilities.

**How to avoid:**
- Prefer **generative correlation**: shared latent variables for race script + team package + track regime, which induces correlation automatically.
- Explicitly separate:
  - **Direct correlation**: teammates drafting at superspeedways, manufacturer alliances, pit strategy coupling.
  - **Hidden correlation**: “we’re wrong about race pace / caution environment,” which moves many drivers together.
- Validate correlation by reproducing historical co-hit frequencies (e.g., “both drivers exceed X DK points” vs independence baseline).

**Warning signs:**
- Pairwise correlation matrix is stable across track types (it shouldn’t be).
- Sims show unrealistic “everyone hits” or “only one driver can hit” behaviors.
- Backtests show great mean RMSE but poor joint event accuracy (top-1% lineup hit rates are wrong).

**Phase to address:**
Phase 1–2 — Build latent-factor sim (Phase 1) and validate joint-event behavior (Phase 2).

---

### Pitfall 4: Uncertainty that is not calibrated to track-type regimes

**What goes wrong:**
Single global error model (same sigma everywhere) makes superspeedways too “predictable” or intermediates too “chaotic,” wrecking ownership leverage and tail outcomes.

**Why it happens:**
Projects calibrate on pooled races to stabilize estimates, accidentally washing out regime differences (drafting tracks vs road courses vs short tracks vs intermediates).

**How to avoid:**
- Calibrate variance and tail behavior **by track archetype** (and optionally by package/era).
- Model incident/DNF/crash risk explicitly as a mixture component rather than fattening the whole distribution with a big sigma.
- Score calibration using proper scoring rules (log score / CRPS) and quantile coverage by track type.

**Warning signs:**
- Predictive intervals are miscalibrated (e.g., 80% intervals cover 95% outcomes).
- Superspeedway sims rarely produce massive negative outcomes across many lineups (underestimating chaos).
- Intermediate track sims overproduce “random winner” outcomes.

**Phase to address:**
Phase 2 — Calibration + backtesting harness (track-type stratified).

---

### Pitfall 5: Conflating *caution environment* with *driver performance*

**What goes wrong:**
The sim bakes “more cautions” into driver projections (or vice versa), so you can’t correctly reason about how cautions change dominator allocation, PD opportunities, and fastest-lap availability.

**Why it happens:**
Loop data features and historical results are entangled with race scripts; without explicit causal separation, models learn “winning drivers cause fewer cautions” style artifacts.

**How to avoid:**
- Represent cautions as an exogenous (or partially exogenous) race-level latent variable, then let it affect:
  - Available green-flag laps (fast-lap budget),
  - Lead-change rate / dominator fragmentation,
  - PD volatility.
- Keep driver “pace/skill” separate from “race chaos” and allow both to vary in the sim.

**Warning signs:**
- When you dial up caution rate, the model still concentrates dominators the same way.
- Drivers who historically survive chaos are modeled as “causing chaos.”
- Sensitivity tests show non-intuitive directions (e.g., more cautions increases fastest laps for everyone).

**Phase to address:**
Phase 1–2 — Causal structure in sim (Phase 1) + sensitivity tests (Phase 2).

---

### Pitfall 6: Using loop/practice signals without leakage controls (post-treatment bias)

**What goes wrong:**
You use signals that already reflect outcomes you’re trying to predict (or near-proxies), inflating backtests and then collapsing live. Example patterns: using post-race loop metrics in training folds, or using practice-derived ranks in a way that implicitly encodes qualifying.

**Why it happens:**
Race-week data arrives in stages; it’s easy to accidentally mix “future” information into “past” features, especially when merging datasets.

**How to avoid:**
- Build a strict **time-aware feature availability contract** (what exists pre-qualifying, post-qualifying, pre-lock).
- Enforce it with dataset versioning and tests (fail pipeline if any feature violates timestamp rules).
- Prefer causal graphs: don’t control for mediators that sit between prior skill and outcome (classic post-treatment bias).

**Warning signs:**
- Backtest AUC/ROI spikes suspiciously when a “race-week” feature is added.
- Model performance does not degrade when you remove qualifying (it should).
- Feature importance is dominated by a small set of leaky variables.

**Phase to address:**
Phase 0–2 — Data contracts (Phase 0), sim inputs (Phase 1), backtest validation (Phase 2).

---

### Pitfall 7: Optimizing the mean (or median) when you claim to optimize the tail

**What goes wrong:**
Optimizer targets expected DK points or a smoothed proxy; it produces “safe” lineups that look good in cash/SE but underperform in large-field GPPs where top-0.1% outcomes matter.

**Why it happens:**
Expected value is easy to compute and stable. Tail objectives are noisy, require more simulations, and can be brittle without regularization.

**How to avoid:**
- Use explicit tail objectives tied to simulations:
  - Maximize \( \mathbb{E}[\text{DK} \mid \text{top }q\%] \),
  - Or maximize probability of exceeding a contest-specific threshold,
  - Or maximize expected payout under a payout curve approximation.
- Add stability controls: objective smoothing, minimum-sample constraints, and robust tie-breakers (e.g., secondary objective on mean).

**Warning signs:**
- Lineups barely change when you switch from cash to GPP settings.
- Best lineups cluster near projection mean with low simulated variance.
- Backtests show strong min-cash but weak top-1% frequency.

**Phase to address:**
Phase 3 — Tail objective + optimizer integration (post calibrated sim).

---

### Pitfall 8: “Dominator stacking” heuristics that fight conservation and correlation

**What goes wrong:**
Rules like “must have 2 dominators” or “max 2 starters in top 10” are applied globally, regardless of track dynamics and the sim’s implied dominator fragmentation, yielding systematically suboptimal portfolios.

**Why it happens:**
Players internalize rules of thumb; engineers codify them as hard constraints, even when the sim already captures the underlying rationale.

**How to avoid:**
- Make stacking rules **soft** (penalties) and conditional on track archetype and simulated dominator distribution.
- Validate against track-specific dominator point distributions (tools like FRCS present track-level “top dominators” distributions to guide strategy).
- Let the sim drive whether “1 vs 2 vs 3 dominators” is optimal, then use constraints only as guardrails (Kernel veto remains final).

**Warning signs:**
- The optimizer selects the same dominator-count mix for Daytona and a 1.5-mile intermediate.
- Removing the heuristic improves simulated top-tail immediately.
- Portfolio has high internal correlation (too many lineups hinge on the same dominator outcome).

**Phase to address:**
Phase 3 — Tail optimizer design + track-conditional constraint policy.

---

### Pitfall 9: Ignoring ownership / field behavior in “top-tail” claims

**What goes wrong:**
You maximize a lineup’s probability of a high raw score, not its probability of winning *given the field*. You miss leverage spots and end up with duplicated, chalky lineups that don’t actually win tournaments.

**Why it happens:**
Ownership is noisy and hard to forecast; many engines stop at “best lineup by score.” Tail optimization without field modeling is an incomplete objective.

**How to avoid:**
- Add a simple field model:
  - Ownership priors + correlation structure (chalk clusters),
  - Duplication risk proxy (sum of ownership, product of ownership, or a learned duplication model).
- Optimize expected payout (or probability of unique win) rather than raw score alone.

**Warning signs:**
- Your “best” lineup is extremely high ownership and wins sims often but loses in historical replays.
- Portfolio duplication is high in backtests (many lineups identical or near-identical).
- Tail performance improves when you add arbitrary ownership caps (sign you were missing field dynamics).

**Phase to address:**
Phase 3–4 — Add field model (Phase 3), validate + monitor drift (Phase 4).

---

### Pitfall 10: Not stress-testing kernel veto interactions (sim produces infeasible worlds)

**What goes wrong:**
The sim generates states that Kernel rejects (impossible positions, invalid totals, inconsistent stage/finish relationships), so tail metrics are computed on a biased subset (accepted worlds) without realizing it.

**Why it happens:**
Kernel is added “after the fact.” If rejection rate is non-trivial, it changes the simulated distribution.

**How to avoid:**
- Track rejection reasons and rates as first-class metrics.
- Prefer constructive generation that is feasible by design (e.g., sampling permutations / allocating conserved resources) rather than reject-sampling.
- Add invariant tests: conservation, uniqueness, bounds, and consistency checks must pass pre-optimizer.

**Warning signs:**
- Kernel rejection rate spikes on certain tracks.
- Tail objective is highly sensitive to small changes in kernel rules (means you’re relying on invalid states).
- Debug logs show frequent “fixups”/normalizations.

**Phase to address:**
Phase 1–2 — Feasible-by-design sim (Phase 1) + invariants/rejection monitoring (Phase 2).

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Use independent per-driver distributions for laps led / fastest laps | Fast to ship a “sim” | Breaks conservation; wrong tails; requires rewrite | Never (use a conserved allocator from day 1) |
| One global variance parameter for all tracks | Simple calibration | Systematic miscalibration by regime | Only for a prototype; must be replaced in Phase 2 |
| Hard-coded dominator-count rules | Quick “NASCAR DFS strategy” | Conflicts with sim; brittle | Only as temporary guardrails while sim is uncalibrated |
| Tail objective without stability controls | Fast “top-1% optimizer” | Noisy, overfits, non-reproducible | Only with strict minimum sim counts + smoothing |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Premium loop data feeds | Mixing post-race metrics into training features | Time-stamped feature contract + tests; stage data availability gates |
| Headless `/optimize` endpoint | Hidden nondeterminism breaks reproducibility | Seeded sims + recorded config hash + deterministic solver settings |
| Ontology priors | Priors override kernel hard constraints | Kernel veto final; priors only affect soft weights/projections |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Too few simulations for tail objective | Optimizer “thrashes,” unstable top lineups | Minimum sim count per contest type; variance-reduced estimators | Immediately (tail needs far more sims than mean) |
| Re-simulating for every lineup in a portfolio | Latency spikes pre-lock | Cache race-world draws; score many lineups against same worlds | At portfolio sizes \(>\) 50–150 |
| Heavy rejection sampling due to kernel veto | Slow + biased sims | Feasible-by-design generation | When rejection \(>\) ~1–2% consistently |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Exposing premium data or model weights via `/optimize` responses | IP/data leakage | Strict response models; never return raw priors/features; audit logs |
| Accepting arbitrary “projection overrides” without validation | Poisoning / bad lineups | Schema validation + allowlist + kernel constraint checks |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| “Simulated ceiling” shown without explaining conservation | Users over-trust impossible outcomes | Show dominator distribution + sanity checks (total laps/fast laps) |
| No track-type context (superspeedway vs intermediate) | Wrong mental model of risk | Track regime banner + variance/chaos indicator + recommended objective |
| No reproducibility controls (seed/config) | Can’t debug why lineup changed | Always display config hash + seed + data timestamp |

## "Looks Done But Isn't" Checklist

- [ ] **Dominator simulation:** Often missing **conservation checks** — verify totals match race laps / green-flag laps.
- [ ] **Correlation:** Often missing **joint-event validation** — verify co-hit rates vs historical for key driver pairs / team stacks.
- [ ] **Calibration:** Often missing **track-type stratification** — verify coverage by track archetype, not just pooled.
- [ ] **Tail optimizer:** Often missing **field/ownership modeling** — verify objective accounts for leverage/duplication, not just raw score.
- [ ] **Kernel integration:** Often missing **rejection-rate monitoring** — verify kernel veto is near-zero and not biasing outputs.

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Non-conserved dominators | HIGH | Replace with conserved allocator; re-run calibration; invalidate prior backtests |
| Miscalibrated uncertainty by track type | MEDIUM | Add regime stratification + mixture component; recalibrate; re-tune tail objective |
| Tail objective overfitting | MEDIUM | Increase sim count; add smoothing/regularization; add secondary mean objective |
| Kernel rejection bias | MEDIUM | Move constraints into generator; instrument and eliminate rejection causes |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Not conserving dominator events | Phase 1 | Invariants: totals conserved in 100% of sims; track-level dominator distributions plausible |
| Finish/PD independence | Phase 1 | No impossible PD; finish positions are permutations; PD derived deterministically |
| Missing hidden correlation | Phase 1–2 | Co-hit frequencies and pairwise correlations match historical by track type |
| Uncalibrated uncertainty | Phase 2 | Quantile coverage + proper scoring rules by track archetype |
| Caution/performance entanglement | Phase 1–2 | Sensitivity tests: changing caution rate has coherent effects on dom/PD/fast laps |
| Leakage / post-treatment bias | Phase 0–2 | Time-aware dataset tests pass; backtests degrade appropriately when “late” info removed |
| Mean-optimized “tail” | Phase 3 | Increased top-1% frequency vs mean baseline in historical replay |
| Brittle dominator stacking rules | Phase 3 | Track-conditional constraint policy improves top-tail without over-constraining |
| No ownership/field model | Phase 3–4 | Higher win-rate proxy vs raw-score-only; duplication risk tracked |
| Kernel rejection bias | Phase 1–2 | Rejection rate near-zero and stable; rejection reasons actionable and diminishing |

## Sources

- FRCS dominator points / fast-lap accounting and track-level dominator distributions: `https://frcs.pro/dfs/draftkings/cup/dominator-points`
- WIN THE RACE loop data (illustrates breadth of loop metrics commonly fed into models): `https://www.wintherace.info/2026-nascar-loop-data/`
- Speed Geeks (probability/simulation-driven DFS optimization framing): `http://speed-geeks.com/`
- FTN correlation article (direct vs hidden correlation; simulations capturing correlation via conditional probabilities): `https://ftnfantasy.com/other/dominate-dfs-pick-em-games-by-understanding-correlation`

---
*Pitfalls research for: NASCAR DFS causal simulation + tail optimization*
*Researched: 2026-01-27*
