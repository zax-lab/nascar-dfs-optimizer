# New project setup
_Exported on 1/27/2026 at 05:00:00 EST from Cursor (2.4.21)_

---

**User**

/gsd/new-project 

---

**Cursor**

Got it. I’m going to run the required initialization checks in this directory (abort if already initialized, init a git repo if needed, and detect any existing code/packages) so we know whether to map a brownfield codebase first or proceed with new-project questioning.

The setup step failed because initializing git is blocked in the sandbox here. I’m going to rerun the same required checks with full permissions so `git init` can create `.git/` and we can continue.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 GSD ► QUESTIONING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

What do you want to build?

---

**User**

I don't know how to exactly explain it, but I would like to have a thing that predicts the results of nascar events and an optimizer to go along with it. This will be for building lineups for DraftKings DFS. I want to give myself an edge by factoring in ontology, uncertain markov chains, known unknowns, aleatoric and epistemic uncertainty, state spaces, transition probability, markov properties, etc.

---

**Cursor**

That helps a lot. Let me make it concrete and then we’ll tighten the edges.

### Quick framing (tell me if wrong)
- **Predictor**: produces probabilistic race outcomes (finishes, laps led, fast laps, incidents) with **uncertainty decomposed** (aleatoric vs epistemic) and an explicit **state/transition** story (Markov-ish).
- **Optimizer**: turns those distributions into **DraftKings NASCAR Classic** lineups (6 drivers, \( \le 50{,}000 \) salary), likely optimizing **expected value** with **risk controls** (correlation, tail-risk, exposure limits).

### A few clarifying questions
- **What’s the “edge” output you want most?**  
  - better mean projection (EV)  
  - better *distribution* / tail modeling (win equity, top-1% outcomes)  
  - better ownership leverage (beat the field)  
  - better constraint logic (avoid impossible lineups / capture correlations)

- **What do you want to predict, exactly (primary targets)?**  
  - finishing position distribution  
  - DK points distribution per driver  
  - components: laps led, fastest laps, place diff, incidents/DNF

- **What data sources are you willing to use?**  
  - only public NASCAR results/timing + DK salaries  
  - paid telemetry / loop data  
  - scraping allowed or only CSV/manual imports

- **How should the ontology be used (mechanically)?**  
  - as feature store (driver/track/race relations)  
  - as constraint system (veto/priors)  
  - as causal graph shaping transitions/priors

- **How do you want uncertainty handled in optimization?**  
  - maximize expected points  
  - maximize \( \mathbb{E}[u(\text{points})] \) with risk aversion  
  - chance constraints (e.g., “\(P(\text{lineup} > X) \ge p\)”)  
  - robust optimization (worst-case within epistemic bounds)

- **Operational constraints**: are you running this **locally only**, or do you want a **web UI** (upload slate → run → export CSV)?

If you answer those, I can start turning it into a crisp PROJECT.md with clear scope, success metrics, and the first milestone.

---

**User**

To make this "bulletproof" and ensure the project succeeds based on the "Axiomatic" principles outlined in your architecture, here is the response you should send. It pivots away from standard data science "averages" and focuses on the unique mechanical edges of NASCAR (correlations and physics).

---

### Response

**1. Critique of Framing**
Your framing is close, but we need to sharpen the definition to ensure we aren't just building another regression model.

* **Predictor:** It is not just "Markov-ish" (state transition). It is a **Causal Bayesian Network constrained by Ontology**. We aren't just predicting outcomes; we are simulating *race flows* (Skeleton Narratives). If the Kernel says "Tire Wear is High," the transition probability for "Green Flag Pit Cycle" increases.
* **Optimizer:** It cannot just be "Expected Value with risk controls." In NASCAR DFS, **EV is a trap**. The optimizer must solve for **Conditional Upside**. We are maximizing the probability of a lineup hitting the top 1% of the field distribution (Simulated ROI), not maximizing the mean score.

**2. Answers to Clarifying Questions**

**Q1: What’s the “edge” output you want most?**
**Strategic Choice: Better constraint logic (Correlations/Anti-Correlations) & Tail Modeling.**

* **Why:** The "Edge" in NASCAR is enforcing the **Conservation of Dominator Points**. There are a finite number of laps led available (e.g., 267 at Las Vegas). If Driver A leads 200 laps, Driver B *cannot* lead 100 laps. Standard models fail here because they predict drivers independently.
* **The Fix:** Our Kernel must veto impossible states (e.g., total laps led > race length) before the optimizer sees them.

**Q2: What do you want to predict, exactly (primary targets)?**
**Strategic Choice: Component Distributions (Laps Led, Fastest Laps, Place Differential).**

* **Why:** Finishing position is noise; **Laps Led** and **Fastest Laps** are the signal. A driver finishing 8th who led 100 laps often outscores a driver finishing 2nd who led 0.
* **Target:** We need to predict the **"Dominator State"** (probability of leading >25% of the race) and the **"Chaos State"** (incident probability).

**Q3: What data sources are you willing to use?**
**Strategic Choice: Paid/Premium Telemetry (Loop Data) is Non-Negotiable.**

* **Why:** You cannot model "tire degradation," "fall-off," or "long-run speed" using simple finishing positions. We need **Lap-by-Lap times** to feed the physics equations in the Kernel. Scraping basic results is insufficient.

**Q4: How should the ontology be used (mechanically)?**
**Strategic Choice: As a Hard Constraint System (The Veto).**

* **Why:** This is the project's unique advantage.
* **Mechanism:**
* **The Veto:** If the ML model predicts a result that violates physics (e.g., a car finishing better than its fuel window allows), the Kernel blocks it.
* **The Prior:** The Ontology provides the "Base Rate" for drivers at specific track types before race data exists.



**Q5: How do you want uncertainty handled in optimization?**
**Strategic Choice: Robust Optimization via Scenario Simulation.**

* **Mechanism:** We do not optimize one "mean" projection. We generate 1,000 "Skeleton Narratives" (simulated races). We run the optimizer on *each* simulation.
* **Goal:** The resulting portfolio of lineups captures the "High Chaos" scenario, the "Dominator" scenario, and the "Fuel Mileage" scenario naturally.

**Q6: Operational constraints?**
**Strategic Choice: Headless API Engine with CI/CD.**

* **Why:** Speed is critical for late swap. The Web UI (Next.js) is for **analysis only**.
* **Execution:** The actual lineup generation happens via a headless API endpoint (`/optimize`) called by automated scripts 15 minutes before lock.

---

**Cursor**

Nice — this pins down the differentiator: **ontology-constrained causal simulation** + **conditional-upside optimizer** (top-1% objective) built around NASCAR’s “conservation laws” (dominator points, laps led, pit cycles). Next I’ll confirm we’re ready to lock this into `.planning/PROJECT.md`, then I’ll synthesize it and commit.

Cool — I’m going to read the existing codebase map first (since this repo already has `.planning/codebase/`), then write a PROJECT.md that reflects what already exists as “Validated” and your new causal-simulation + conditional-upside goals as “Active.”

Plan: I’ll draft `.planning/PROJECT.md` grounded in what the codebase already supports (FastAPI `/optimize`, Neo4j ontology, kernel validation, PuLP optimizer, Airflow ETL), then add your new “causal BN + ontology veto + skeleton narratives + conditional-upside optimizer” as the next active milestone. After writing, I’ll commit the doc so it’s durable.

I wrote `.planning/PROJECT.md`, but the commit failed because the command wasn’t running inside the project directory (so git couldn’t see the repo). Next I’ll rerun the commit from the correct workspace path and verify git status afterward.

### Done
- **Created and committed** `.planning/PROJECT.md` capturing your clarified direction: **ontology-constrained causal Bayesian race-flow simulation (“Skeleton Narratives”) + Kernel veto + conditional-upside (top-1%) optimizer**.
- **Initialized git** in this workspace (it had a partial `.git/` but wasn’t a valid repo).

### Files I touched
- `.planning/PROJECT.md`

### Next step
Now we proceed to **workflow preferences** and create/commit `.planning/config.json` (mode/depth/parallelization/agents).

---

**User**

proceed

---

**Cursor**

I’ll encode your choices into `.planning/config.json`, handle git-commit of that file, and then we’ll move on to the research-vs-direct-requirements decision.

### Config set

- **Workflow config created & committed** at `.planning/config.json` with:
  - **Mode**: interactive  
  - **Depth**: comprehensive  
  - **Parallelization**: enabled  
  - **Agents**: research, plan_check, verifier all **on**  
  - **Model profile**: balanced  

Next up: decide whether to run **domain research first** (recommended, given the complexity of your causal/ontology design) or go straight into defining **REQUIREMENTS.md**.

---

**User**

Run domain research first 

---

**Cursor**

Plan: I’ll set up `.planning/research/`, then spawn 4 parallel research agents (stack, features, architecture, pitfalls) tailored to a **subsequent milestone** on top of your existing Axiomatic NASCAR DFS codebase. After they finish, I’ll synthesize into `SUMMARY.md` and commit the research artifacts.

Researching the NASCAR DFS causal-simulation ecosystem now. I’m spawning 4 researchers in parallel (stack, features, architecture, pitfalls) focused on adding your “skeleton narrative + conditional-upside” layer onto the existing monorepo.

Good — all four research artifacts are written. Next I’ll run the synthesizer to produce `.planning/research/SUMMARY.md`, then commit the whole research directory so we can reference it when defining requirements and generating the roadmap.

### Research complete ✓

**Key findings (high signal)**
- **Stack**: Python-first sim/opt stack with **FastAPI + Pydantic v2**, **Neo4j**, **Polars/Arrow/DuckDB** for telemetry artifacts, **JAX** for high-throughput scenario simulation, and **PuLP+HiGHS / OR-Tools CP-SAT** for lineup + portfolio constraints.
- **Table stakes**: DK compliance, driver pool controls, multi-lineup portfolios with exposures/overlap, simulation-based evaluation metrics, DK CSV export.
- **Watch out for**: **dominator conservation** failures (inflated tails), hidden-cause correlations, track-archetype miscalibration, “tail optimization” that’s secretly mean optimization, and kernel veto bias without instrumentation.

**Files written (and committed)**
- `.planning/research/STACK.md`
- `.planning/research/FEATURES.md`
- `.planning/research/ARCHITECTURE.md`
- `.planning/research/PITFALLS.md`
- `.planning/research/SUMMARY.md`

Next we move to **Defining Requirements** and scope v1 feature categories into `.planning/REQUIREMENTS.md`.

---

**User**

continue

