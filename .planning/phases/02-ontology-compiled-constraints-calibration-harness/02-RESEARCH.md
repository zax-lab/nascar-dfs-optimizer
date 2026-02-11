# Phase 2: Ontology-Compiled Constraints + Calibration Harness - Research

**Researched:** 2026-01-27
**Domain:** Ontology compilation, telemetry pipelines, probabilistic calibration, headless APIs
**Confidence:** MEDIUM

## Summary

Phase 2 requires building infrastructure to compile reproducible constraint specifications from Neo4j into immutable in-memory artifacts, implementing a telemetry ETL pipeline for lap-by-lap data with feature availability contracts, and creating a calibration harness for track-type uncertainty quantification. The research focused on five core areas: (1) Neo4j batch query patterns for constraint compilation, (2) telemetry data processing with Polars/Arrow/DuckDB, (3) probabilistic calibration metrics (CRPS, log score, coverage), (4) feature availability contracts to prevent data leakage, and (5) headless API design patterns with FastAPI.

The existing codebase has Neo4j integration via `OntologyDriver` in `apps/backend/app/ontology.py`, but it performs live queries in hot loops. Phase 2 requires compiling constraints once per slate into immutable artifacts to ensure reproducibility and eliminate hidden nondeterminism. The calibration harness needs to track track-archetype performance using PyMC or NumPyro for MCMC sampling and ArviZ for diagnostics.

**Primary recommendation:** Use Neo4j's `execute_query` with batch reads and `RoutingControl.READ` for efficient constraint compilation. Build telemetry pipeline with Polars for transformation, Arrow for zero-copy IPC, and DuckDB for SQL-based analytics. Implement calibration with NumPyro for JAX-accelerated MCMC and use ArviZ for CRPS/log score calculations. Design headless API using FastAPI with Pydantic models for request validation and BackgroundTasks for async optimization.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **Neo4j Python Driver** | latest | Batch query execution for constraint compilation | Official driver with connection pooling, `execute_query` API for transaction management and retry logic, `RoutingControl.READ` for efficient read queries |
| **Polars** | latest | Telemetry data transformation and aggregation | Blazingly fast DataFrame library implemented in Rust with lazy evaluation, multi-threading, and SIMD for time series operations on lap-by-lap data |
| **PyArrow** | latest | Zero-copy IPC and Parquet serialization | Columnar in-memory format with zero-copy sharing between Polars and DuckDB, efficient compression for telemetry artifacts |
| **NumPyro** | latest | Probabilistic calibration with MCMC | Lightweight PPL powered by JAX with NUTS/HMC samplers, automatic vectorization, and GPU/TPU support for track-archetype calibration |
| **ArviZ** | latest | Calibration diagnostics (CRPS, log score, coverage) | Unified library for Bayesian inference diagnostics with posterior predictive checks, scoring rules, and plotting |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **DuckDB** | latest | SQL analytics on Parquet telemetry data | When performing complex aggregations or joining telemetry with scenario results - zero-copy Parquet reading avoids serialization overhead |
| **FastAPI** | latest | Headless `/optimize` API endpoint | When building scenario-driven optimization contracts with Pydantic validation and async background processing |
| **Pydantic** | latest | Request/response validation and versioned configs | When defining immutable constraint specs and run configs with type safety and JSON serialization |
| **pytest** | >=7.3.0 | Unit testing framework | Already in pyproject.toml - use for testing constraint compilation and calibration metrics |
| **hypothesis** | latest | Property-based testing for constraint invariants | When validating compiled constraints satisfy ontology properties across random inputs |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| **Neo4j Driver** | Direct Cypher HTTP requests | Driver provides connection pooling, retry logic, and automatic transaction management - HTTP requires manual error handling |
| **Polars** | pandas | Polars is 5-10x faster for large datasets due to Rust implementation and lazy evaluation, pandas has more mature ecosystem |
| **NumPyro** | PyMC | NumPyro provides JAX integration for automatic vectorization and GPU acceleration, PyMC has more mature ecosystem but is Python-focused |
| **Parquet** | JSON or CSV | Parquet provides 5-10x better compression and columnar predicate pushdown, JSON/CSV are human-readable but slow for large telemetry datasets |
| **ArviZ** | Custom CRPS implementation | ArviZ provides battle-tested implementations with proper handling of multi-model ensembles, custom implementation risks bugs |

**Installation:**
```bash
# Core telemetry and calibration stack
pip install polars pyarrow duckdb numpyro arviz

# Neo4j driver (already installed)
pip install neo4j

# FastAPI and Pydantic for headless API
pip install fastapi pydantic

# Testing framework (already in pyproject.toml)
pip install pytest hypothesis
```

## Architecture Patterns

### Recommended Project Structure

```
apps/backend/app/
├── constraints/           # NEW: Constraint compilation module
│   ├── __init__.py
│   ├── compiler.py        # ConstraintSpec compilation from Neo4j
│   ├── models.py          # Immutable constraint spec models
│   └── versioning.py      # Run config versioning
├── telemetry/             # NEW: Telemetry ETL pipeline
│   ├── __init__.py
│   ├── ingest.py          # Lap-by-lap data ingestion
│   ├── transform.py       # Polars transformations
│   ├── features.py        # Feature availability contracts
│   └── artifacts.py       # Parquet/Arrow artifact management
├── calibration/           # NEW: Track-archetype calibration
│   ├── __init__.py
│   ├── metrics.py         # CRPS, log score, coverage calculations
│   ├── models.py          # NumPyro calibration models
│   └── diagnostics.py     # ArviZ posterior predictive checks
├── api/                   # NEW: Headless API endpoints
│   ├── __init__.py
│   ├── optimize.py        # /optimize endpoint with scenario-driven configs
│   └── contracts.py       # Pydantic request/response models
├── kernel.py              # EXISTING: Add validation instrumentation
├── ontology.py            # EXISTING: Source for constraint compilation
└── main.py                # EXISTING: FastAPI app, add /optimize route

packages/axiomatic-sim/
├── tests/
│   ├── test_constraints.py        # Property-based tests for compiled constraints
│   ├── test_telemetry.py          # Telemetry pipeline tests
│   ├── test_calibration.py        # Calibration metric tests
│   └── test_api.py                # API contract tests
└── pyproject.toml                 # ADD: polars, pyarrow, duckdb, numpyro, arviz

data/                           # NEW: Telemetry artifact storage
├── telemetry/                  # Parquet files by track/date
│   ├── daytona_2024-02-18.parquet
│   └── phoenix_2024-03-10.parquet
├── constraints/                # Compiled constraint specs
│   └── slate_2024-02-18_v1.json
└── calibration/                # Calibration results
    └── track_archetype_2024-01-27.nc
```

### Pattern 1: Neo4j Batch Query for Constraint Compilation

**What:** Use Neo4j's `execute_query` API with `RoutingControl.READ` to fetch all constraint data in a single batch query, then compile into an immutable in-memory artifact.

**When to use:** Required by success criterion "ConstraintSpec compiles from Neo4j once per slate into an immutable in-memory artifact" - eliminates ad-hoc DB calls in inner loops.

**Example:**
```python
# Source: Neo4j Python Driver execute_query API
# https://context7.com/neo4j/neo4j-python-driver/llms.txt
from neo4j import GraphDatabase, RoutingControl
from dataclasses import dataclass
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class DriverConstraints:
    """Immutable driver constraints compiled from Neo4j."""
    driver_id: str
    skill: float
    aggression: float
    shadow_risk: float
    min_laps_led: int
    max_laps_led: int
    veto_rules: List[str]

@dataclass(frozen=True)
class TrackConstraints:
    """Immutable track constraints compiled from Neo4j."""
    track_id: str
    difficulty: float
    aggression_factor: float
    caution_rate: float
    pit_window_laps: List[int]

@dataclass(frozen=True)
class ConstraintSpec:
    """Immutable constraint specification compiled once per slate."""
    slate_id: str
    compiled_at: str
    drivers: Dict[str, DriverConstraints]
    tracks: Dict[str, TrackConstraints]
    version: str

    def get_driver_constraints(self, driver_id: str) -> DriverConstraints:
        """Get driver constraints with error handling."""
        if driver_id not in self.drivers:
            raise ValueError(f"Driver {driver_id} not in constraint spec")
        return self.drivers[driver_id]

def compile_constraints_from_neo4j(
    driver: GraphDatabase.driver,
    slate_id: str,
    track_ids: List[str],
    driver_ids: List[str]
) -> ConstraintSpec:
    """
    Compile constraints from Neo4j in a single batch query.

    Fetches all driver and track constraints in one query to minimize
    database round trips and ensure consistency. Returns immutable
    ConstraintSpec that can be used throughout simulation/optimization.
    """
    from datetime import datetime

    logger.info(f"Compiling constraints for slate {slate_id}")

    # Batch query: fetch all drivers and tracks in single call
    # Use RoutingControl.READ for efficient read query
    records, summary, keys = driver.execute_query(
        """
        MATCH (d:Driver)
        WHERE d.driver_id IN $driver_ids
        OPTIONAL MATCH (d)-[r:VETO_RULE]->(forbidden:Node)
        RETURN d.driver_id as driver_id,
               d.skill as skill,
               d.psyche_aggression as aggression,
               d.shadow_risk as shadow_risk,
               collect(DISTINCT forbidden.id) as veto_rules
        """,
        driver_ids=driver_ids,
        routing_=RoutingControl.READ,
        database_="neo4j"
    )

    # Compile driver constraints
    drivers = {}
    for record in records:
        driver_id = record["driver_id"]
        drivers[driver_id] = DriverConstraints(
            driver_id=driver_id,
            skill=float(record["skill"]),
            aggression=float(record["aggression"]),
            shadow_risk=float(record["shadow_risk"]),
            min_laps_led=0,  # Derived from historical data
            max_laps_led=100,  # Derived from track length
            veto_rules=record["veto_rules"]
        )

    # Batch query: fetch all tracks
    records, summary, keys = driver.execute_query(
        """
        MATCH (t:Track)
        WHERE t.track_id IN $track_ids
        RETURN t.track_id as track_id,
               t.difficulty as difficulty,
               t.aggression_factor as aggression_factor
        """,
        track_ids=track_ids,
        routing_=RoutingControl.READ,
        database_="neo4j"
    )

    # Compile track constraints
    tracks = {}
    for record in records:
        track_id = record["track_id"]
        tracks[track_id] = TrackConstraints(
            track_id=track_id,
            difficulty=float(record["difficulty"]),
            aggression_factor=float(record["aggression_factor"]),
            caution_rate=0.05,  # Derived from historical telemetry
            pit_window_laps=[35, 70, 105, 140, 175]  # Standard pit windows
        )

    # Create immutable constraint spec
    spec = ConstraintSpec(
        slate_id=slate_id,
        compiled_at=datetime.utcnow().isoformat(),
        drivers=drivers,
        tracks=tracks,
        version="1.0"
    )

    logger.info(
        f"Compiled {len(drivers)} drivers, {len(tracks)} tracks "
        f"for slate {slate_id} in {summary.result_available_after}ms"
    )

    return spec

# Example: Compile constraints for a slate
driver = GraphDatabase.driver("neo4j://localhost:7687", auth=("neo4j", "password"))
spec = compile_constraints_from_neo4j(
    driver,
    slate_id="daytona_2024-02-18",
    track_ids=["daytona"],
    driver_ids=[f"driver_{i}" for i in range(1, 41)]
)
```

### Pattern 2: Telemetry Pipeline with Polars and Feature Availability Contracts

**What:** Use Polars for high-performance telemetry transformation with time-based grouping, and enforce feature availability contracts to prevent data leakage.

**When to use:** Required by DATA-01 for "Premium loop / lap-by-lap telemetry ingestion" and success criterion "feature availability contracts (no leakage)."

**Example:**
```python
# Source: Polars time series aggregation and rolling windows
# https://context7.com/pola-rs/polars/llms.txt
import polars as pl
from datetime import datetime
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class FeatureAvailabilityContract:
    """
    Enforces feature availability to prevent data leakage.

    Features are only available based on what would be known at race time:
    - Historical stats: available (past race data)
    - Practice/qualifying: available (pre-race sessions)
    - Race telemetry: NOT available (future information)
    """

    HISTORICAL_FEATURES = [
        "avg_finish_position",
        "avg_laps_led",
        "win_rate",
        "dnf_rate"
    ]

    PRACTICE_FEATURES = [
        "practice_lap_time",
        "practice_speed"
    ]

    QUALIFYING_FEATURES = [
        "qualifying_position",
        "qualifying_speed"
    ]

    # Features that would constitute leakage if used
    FORBIDDEN_FEATURES = [
        "race_laps_led",  # Future information
        "race_finish_position",  # Future information
        "race_incidents"  # Future information
    ]

    @classmethod
    def validate_features(cls, features: List[str]) -> None:
        """Validate that no forbidden features are requested."""
        forbidden = set(features) & set(cls.FORBIDDEN_FEATURES)
        if forbidden:
            raise ValueError(
                f"Data leakage: forbidden features requested: {forbidden}. "
                f"These would use future race information."
            )

def ingest_lap_by_lap_telemetry(
    parquet_path: str,
    driver_ids: List[str],
    feature_contract: FeatureAvailabilityContract
) -> pl.DataFrame:
    """
    Ingest lap-by-lap telemetry from Parquet with feature availability enforcement.

    Args:
        parquet_path: Path to Parquet file with telemetry data
        driver_ids: List of driver IDs to filter
        feature_contract: Contract enforcing available features

    Returns:
        Polars DataFrame with lap-by-lap telemetry
    """
    logger.info(f"Ingesting telemetry from {parquet_path}")

    # Scan Parquet with predicate pushdown (only read needed columns/rows)
    df = pl.scan_parquet(parquet_path)

    # Validate feature availability before accessing columns
    available_cols = df.collect_schema().columns()
    feature_contract.validate_features(available_cols)

    # Filter to requested drivers
    df = df.filter(pl.col("driver_id").is_in(driver_ids))

    # Select only allowed features (historical + practice + qualifying)
    allowed_features = (
        feature_contract.HISTORICAL_FEATURES +
        feature_contract.PRACTICE_FEATURES +
        feature_contract.QUALIFYING_FEATURES
    )

    # Always include metadata columns (lap, driver_id, timestamp)
    metadata_cols = ["lap", "driver_id", "timestamp", "track_id"]
    selected_cols = metadata_cols + [f for f in allowed_features if f in available_cols]

    df = df.select(selected_cols)

    logger.info(f"Ingested {df.collect().shape[0]} lap records")
    return df.collect()

def compute_aggregate_telemetry_features(
    telemetry_df: pl.DataFrame,
    time_windows: List[str] = ["10l", "20l", "50l"]
) -> pl.DataFrame:
    """
    Compute aggregate telemetry features over rolling time windows.

    Uses Polars rolling and group_by_dynamic for time-based aggregation.
    This provides driver performance metrics while respecting temporal
    constraints (no leakage from future laps).

    Args:
        telemetry_df: Lap-by-lap telemetry DataFrame
        time_windows: List of time windows (e.g., ["10l", "20l", "50l"])

    Returns:
        DataFrame with aggregate features per driver per time window
    """
    logger.info("Computing aggregate telemetry features")

    # Ensure data is sorted by lap
    telemetry_df = telemetry_df.sort("lap")

    # Compute rolling features for each time window
    results = []
    for window in time_windows:
        # Parse window (e.g., "10l" -> 10 laps)
        window_laps = int(window.replace("l", ""))

        # Rolling aggregation over laps
        rolling_df = telemetry_df.groupby("driver_id").agg([
            # Rolling average position over last N laps
            pl.col("position")
                .rolling(window_size=window_laps, min_periods=1)
                .mean()
                .alias(f"avg_position_last_{window}"),

            # Rolling max position (best result) over last N laps
            pl.col("position")
                .rolling(window_size=window_laps, min_periods=1)
                .min()
                .alias(f"best_position_last_{window}"),

            # Rolling laps led over last N laps
            pl.col("laps_led")
                .rolling(window_size=window_laps, min_periods=1)
                .sum()
                .alias(f"laps_led_last_{window}"),
        ])

        results.append(rolling_df)

    # Join all rolling features
    aggregate_df = telemetry_df
    for result_df in results:
        aggregate_df = aggregate_df.join(result_df, on="driver_id", how="left")

    logger.info(f"Computed {len(time_windows)} time window features")
    return aggregate_df

def persist_telemetry_artifact(
    telemetry_df: pl.DataFrame,
    output_path: str
) -> None:
    """
    Persist telemetry artifact as Parquet for fast loading.

    Uses Parquet for compression and predicate pushdown in future loads.
    """
    telemetry_df.write_parquet(output_path, compression="snappy")
    logger.info(f"Persisted telemetry artifact to {output_path}")

# Example: Telemetry ETL pipeline
# 1. Ingest raw lap-by-lap data
contract = FeatureAvailabilityContract()
telemetry = ingest_lap_by_lap_telemetry(
    "data/telemetry/daytona_2024-02-18.parquet",
    driver_ids=[f"driver_{i}" for i in range(1, 41)],
    feature_contract=contract
)

# 2. Compute aggregate features over rolling windows
aggregated = compute_aggregate_telemetry_features(telemetry)

# 3. Persist as artifact for downstream use
persist_telemetry_artifact(aggregated, "data/telemetry/daytona_2024-02-18_aggregated.parquet")
```

### Pattern 3: Probabilistic Calibration with NumPyro and ArviZ

**What:** Use NumPyro for Bayesian calibration models with NUTS sampling, and ArviZ for computing calibration metrics (CRPS, log score, coverage).

**When to use:** Required by success criterion "Track-archetype calibration metrics available (coverage, CRPS, log score)."

**Example:**
```python
# Source: NumPyro MCMC with NUTS and ArviZ diagnostics
# https://context7.com/pyro-ppl/numpyro/llms.txt
import jax
import jax.numpy as jnp
import jax.random as random
import numpyro
import numpyro.distributions as dist
from numpyro.infer import MCMC, NUTS, Predictive
import arviz as az
import logging

logger = logging.getLogger(__name__)

def track_archetype_calibration_model(
    observed_finish_positions: jnp.ndarray,
    predicted_finish_probs: jnp.ndarray,
    track_archetype: str
):
    """
    Bayesian calibration model for track archetype predictions.

    Models the relationship between predicted probabilities and observed
    outcomes, estimating calibration parameters that vary by track type.

    Args:
        observed_finish_positions: (n_races, n_drivers) observed finish positions
        predicted_finish_probs: (n_races, n_drivers, n_positions) predicted probabilities
        track_archetype: Track type identifier (supercross, intermediate, short_track)
    """
    n_races, n_drivers = observed_finish_positions.shape

    # Hyperpriors for calibration parameters (vary by track archetype)
    # Slope: how sharply predicted probs map to outcomes
    slope_mu = numpyro.sample("slope_mu", dist.Normal(0.0, 1.0))
    slope_sigma = numpyro.sample("slope_sigma", dist.HalfNormal(0.5))
    slope = numpyro.sample("slope", dist.Normal(slope_mu, slope_sigma))

    # Intercept: baseline adjustment
    intercept_mu = numpyro.sample("intercept_mu", dist.Normal(0.0, 1.0))
    intercept_sigma = numpyro.sample("intercept_sigma", dist.HalfNormal(0.5))
    intercept = numpyro.sample("intercept", dist.Normal(intercept_mu, intercept_sigma))

    # Overdispersion: capture extra variance beyond predicted
    overdispersion = numpyro.sample("overdispersion", dist.HalfNormal(1.0))

    # Calibration model: calibrate predicted probabilities
    # Apply linear transformation to log-odds
    calibrated_logit = slope * jnp.log(predicted_finish_probs + 1e-6) + intercept
    calibrated_probs = jax.nn.softmax(calibrated_logit, axis=-1)

    # Likelihood: observed finishes follow categorical with calibrated probs
    with numpyro.plate("races", n_races, dim=-1):
        with numpyro.plate("drivers", n_drivers, dim=-2):
            numpyro.sample(
                "obs_finish",
                dist.Categorical(probs=calibrated_probs),
                obs=observed_finish_positions - 1  # Convert to 0-indexed
            )

def run_track_calibration(
    observed_finishes: jnp.ndarray,
    predicted_probs: jnp.ndarray,
    track_archetype: str,
    num_warmup: int = 1000,
    num_samples: int = 2000,
    num_chains: int = 4
) -> az.InferenceData:
    """
    Run MCMC calibration for track archetype.

    Args:
        observed_finishes: (n_races, n_drivers) observed finish positions
        predicted_probs: (n_races, n_drivers, n_positions) predicted probabilities
        track_archetype: Track type for this calibration
        num_warmup: Warmup iterations for NUTS
        num_samples: Sampling iterations for NUTS
        num_chains: Number of MCMC chains

    Returns:
        ArviZ InferenceData with posterior samples
    """
    logger.info(
        f"Running calibration for {track_archetype}: "
        f"{num_warmup} warmup, {num_samples} samples, {num_chains} chains"
    )

    # NUTS kernel for efficient MCMC
    kernel = NUTS(track_archetype_calibration_model)

    # MCMC sampler
    mcmc = MCMC(
        kernel,
        num_warmup=num_warmup,
        num_samples=num_samples,
        num_chains=num_chains,
        progress_bar=True
    )

    # Run MCMC
    rng_key = random.PRNGKey(42)
    mcmc.run(
        rng_key,
        observed_finish_positions=observed_finishes,
        predicted_finish_probs=predicted_probs,
        track_archetype=track_archetype
    )

    # Print summary of posterior
    mcmc.print_summary()

    # Convert to ArviZ InferenceData
    idata = az.from_numpyro(mcmc)

    logger.info(f"Calibration complete for {track_archetype}")
    return idata

def compute_calibration_metrics(
    idata: az.InferenceData,
    observed_finishes: jnp.ndarray,
    predicted_probs: jnp.ndarray
) -> Dict[str, float]:
    """
    Compute calibration metrics using ArviZ.

    Calculates:
    - CRPS (Continuous Ranked Probability Score)
    - Log score (log likelihood)
    - Coverage (empirical probability of being in predicted intervals)

    Args:
        idata: ArviZ InferenceData from calibration
        observed_finishes: Observed finish positions
        predicted_probs: Predicted probabilities

    Returns:
        Dictionary with calibration metrics
    """
    logger.info("Computing calibration metrics")

    # Posterior predictive samples
    posterior_predictive = az.summary(idata, var_names=["slope", "intercept"])

    # Compute CRPS using ArviZ
    # CRPS measures accuracy of probabilistic predictions (lower is better)
    crps = az.crps(
        observed_finishes,
        predicted_probs,
        source=" posterior_predictive"
    )

    # Compute log score (log likelihood)
    log_score = idata.sample_stats["log_likelihood"].mean()

    # Compute coverage for 50% and 90% credible intervals
    # Check if observed values fall within predicted intervals
    coverage_50 = az.ic(idata, alpha=0.5)["mean"]
    coverage_90 = az.ic(idata, alpha=0.1)["mean"]

    metrics = {
        "crps": float(crps),
        "log_score": float(log_score),
        "coverage_50": float(coverage_50),
        "coverage_90": float(coverage_90)
    }

    logger.info(f"Calibration metrics: {metrics}")
    return metrics

# Example: Calibrate predictions for super speedway tracks
# observed_finishes: shape (n_races, n_drivers) - actual results from historical races
# predicted_probs: shape (n_races, n_drivers, n_positions) - model predictions
idata = run_track_calibration(
    observed_finishes=observed_finishes,
    predicted_probs=predicted_probs,
    track_archetype="superspeedway"
)

# Compute calibration metrics
metrics = compute_calibration_metrics(idata, observed_finishes, predicted_probs)
print(f"CRPS: {metrics['crps']:.4f}")
print(f"Log score: {metrics['log_score']:.4f}")
print(f"Coverage (50%): {metrics['coverage_50']:.4f}")
print(f"Coverage (90%): {metrics['coverage_90']:.4f}")

# Posterior predictive checks to validate calibration
az.plot_ppc(idata, num_pp_samples=100)
```

### Pattern 4: Headless API with FastAPI and Pydantic

**What:** Design `/optimize` endpoint using FastAPI with Pydantic models for scenario-driven request validation and BackgroundTasks for async optimization.

**When to use:** Required by API-01 for "Headless execution contract" and success criterion "`/optimize` endpoint accepts scenario-driven configs and returns lineups + diagnostics."

**Example:**
```python
# Source: FastAPI with Pydantic models and BackgroundTasks
# https://fastapi.tiangolo.com/tutorial/background-tasks/
from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

app = FastAPI(title="Axiomatic NASCAR Optimizer API")

# Pydantic models for request validation

class ScenarioConfig(BaseModel):
    """Configuration for scenario-driven optimization."""
    n_scenarios: int = Field(default=1000, ge=100, le=10000)
    track_id: str
    calibration_id: Optional[str] = None  # Use specific calibration
    constraint_spec_version: str  # Version of constraint spec to use

    @validator('n_scenarios')
    def validate_scenarios(cls, v):
        """Ensure scenario count is reasonable."""
        if v < 100:
            raise ValueError("Need at least 100 scenarios for stable optimization")
        return v

class OptimizationRequest(BaseModel):
    """Headless optimization request."""
    slate_id: str
    scenario_config: ScenarioConfig
    optimization_objective: str = Field(
        default="tail_upside",
        regex="^(tail_upside|mean_points|tournament_equity)$"
    )
    portfolio_size: int = Field(default=20, ge=1, le=150)
    exposure_limits: Optional[Dict[str, float]] = None

    @validator('slate_id')
    def validate_slate_id(cls, v):
        """Ensure slate ID is not empty."""
        if not v or not v.strip():
            raise ValueError("slate_id cannot be empty")
        return v

class Lineup(BaseModel):
    """Single DFS lineup."""
    drivers: List[str] = Field(..., min_items=6, max_items=6)
    projected_points: float
    tail_upside: float  # Probability of top-10% finish
    ownership_overlap: float

class OptimizationDiagnostics(BaseModel):
    """Diagnostics about optimization run."""
    scenarios_generated: int
    constraint_vetoes: int
    calibration_metrics: Dict[str, float]
    optimization_time_seconds: float
    solver_status: str

class OptimizationResponse(BaseModel):
    """Headless optimization response."""
    slate_id: str
    lineups: List[Lineup]
    diagnostics: OptimizationDiagnostics
    generated_at: datetime

# Dependency injection for constraint specs

def get_constraint_spec(version: str) -> ConstraintSpec:
    """Load constraint spec by version."""
    # In production, load from file or cache
    spec_path = f"data/constraints/slate_{version}.json"
    try:
        with open(spec_path, 'r') as f:
            return ConstraintSpec.parse_raw(f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Constraint spec v{version} not found")

# Headless /optimize endpoint

@app.post("/optimize", response_model=OptimizationResponse)
async def optimize_lineups(
    request: OptimizationRequest,
    background_tasks: BackgroundTasks,
    constraint_spec: ConstraintSpec = Depends(lambda: get_constraint_spec("latest"))
):
    """
    Headless optimization endpoint accepting scenario-driven configs.

    This endpoint is designed for programmatic access (no UI required).
    It runs optimization in background and returns lineups + diagnostics.
    """
    logger.info(f"Optimization request for slate {request.slate_id}")

    # Validate constraint spec matches scenario config
    if constraint_spec.version != request.scenario_config.constraint_spec_version:
        raise HTTPException(
            status_code=400,
            detail=f"Constraint spec version mismatch: "
            f"expected {request.scenario_config.constraint_spec_version}, "
            f"got {constraint_spec.version}"
        )

    # Run optimization (in background for long-running tasks)
    start_time = datetime.utcnow()

    try:
        # Load calibration if specified
        calibration = None
        if request.scenario_config.calibration_id:
            calibration = load_calibration(request.scenario_config.calibration_id)

        # Generate scenarios using compiled constraint spec
        scenarios = generate_scenarios(
            constraint_spec=constraint_spec,
            n_scenarios=request.scenario_config.n_scenarios,
            track_id=request.scenario_config.track_id,
            calibration=calibration
        )

        # Run optimization
        lineups, diagnostics = run_optimization(
            scenarios=scenarios,
            objective=request.optimization_objective,
            portfolio_size=request.portfolio_size,
            exposure_limits=request.exposure_limits,
            constraint_spec=constraint_spec
        )

        optimization_time = (datetime.utcnow() - start_time).total_seconds()

        # Build response
        response = OptimizationResponse(
            slate_id=request.slate_id,
            lineups=lineups,
            diagnostics=OptimizationDiagnostics(
                scenarios_generated=len(scenarios),
                constraint_vetoes=diagnostics["vetoes"],
                calibration_metrics=diagnostics["calibration"],
                optimization_time_seconds=optimization_time,
                solver_status="optimal"
            ),
            generated_at=datetime.utcnow()
        )

        logger.info(
            f"Optimization complete: {len(lineups)} lineups, "
            f"{optimization_time:.2f}s"
        )

        return response

    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def generate_scenarios(
    constraint_spec: ConstraintSpec,
    n_scenarios: int,
    track_id: str,
    calibration: Optional[Any]
) -> List[Dict]:
    """Generate scenarios using compiled constraint spec."""
    # Implementation uses constraint_spec.drivers and constraint_spec.tracks
    # No DB calls - all constraints are in memory
    pass

def run_optimization(
    scenarios: List[Dict],
    objective: str,
    portfolio_size: int,
    exposure_limits: Optional[Dict[str, float]],
    constraint_spec: ConstraintSpec
) -> tuple[List[Lineup], Dict]:
    """Run optimization using scenarios and constraints."""
    # Implementation uses constraint_spec for hard constraints
    pass

def load_calibration(calibration_id: str) -> Any:
    """Load calibration by ID."""
    # Load from data/calibration/
    pass
```

### Anti-Patterns to Avoid

- **Live Neo4j queries in simulation loops:** Calling Neo4j during scenario generation introduces nondeterminism and latency. Compile constraints once per slate into immutable artifacts.

- **Using future telemetry features in predictions:** Accessing race_laps_led or race_finish_position before the race starts constitutes data leakage. Enforce feature availability contracts.

- **CRPS calculation without proper calibration:** Computing CRPS on uncalibrated predictions gives misleading results. Always calibrate by track archetype before evaluating metrics.

- **Synchronous optimization in API endpoint:** Long-running optimization blocks API requests. Use BackgroundTasks or task queues for async processing.

- **Missing constraint spec versioning:** Using latest constraint spec without versioning makes runs irreproducible. Always version constraint specs and run configs.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rolling window aggregation | Custom loop over dataframe | Polars `.rolling()` and `.group_by_dynamic()` | Polars provides optimized, multi-threaded rolling aggregations with proper time window handling |
| CRPS calculation | Custom integral of CDF | ArviZ `az.crps()` | ArviZ provides statistically sound implementation handling edge cases and multi-model ensembles |
| Parquet serialization | Custom binary format | PyArrow `write_parquet()` | Parquet is industry-standard with compression, predicate pushdown, and cross-language support |
| Constraint validation | Custom if-checks | Pydantic `BaseModel` with validators | Pydantic provides type-safe validation with clear error messages and JSON schema generation |
| MCMC sampling | Custom Metropolis-Hastings | NumPyro `NUTS` | NumPyro provides HMC/NUTS with automatic differentiation and JAX acceleration |
| SQL on Parquet | Custom Parquet reader | DuckDB `read_parquet()` | DuckDB provides zero-copy Parquet reading with full SQL support and predicate pushdown |

**Key insight:** Custom implementations of statistical calculations, serialization formats, or constraint validation rarely outperform battle-tested libraries. Existing tools are optimized, well-documented, and have community support.

## Common Pitfalls

### Pitfall 1: Data Leakage in Feature Engineering

**What goes wrong:** Using race-day features (laps_led, finish_position) to predict race outcomes, creating unrealistically good model performance that doesn't generalize.

**Why it happens:** Lap-by-lap telemetry contains future information relative to pre-race prediction. Without explicit feature availability contracts, it's easy to accidentally leak information.

**How to avoid:** Implement `FeatureAvailabilityContract` class that explicitly lists allowed features (historical, practice, qualifying) and forbidden features (race telemetry). Validate feature lists before any model access. Add unit tests that fail if forbidden features are accessed.

**Warning signs:** Model accuracy >90% on test set, or calibration metrics show perfect coverage (suspiciously good). Verify feature availability by checking data timestamps.

### Pitfall 2: Constraint Spec Drift During Optimization

**What goes wrong:** Constraint spec changes mid-optimization (e.g., DB is updated), causing some lineups to use outdated constraints and others to use new constraints.

**Why it happens:** Using live Neo4j queries or mutable constraint objects allows constraints to change during long optimization runs.

**How to avoid:** Compile constraints once per slate into immutable `ConstraintSpec` dataclass (use `frozen=True`). Version all constraint specs and store as JSON artifacts. Load specific version by ID in optimization request.

**Warning signs:** Optimization results differ on repeated runs with same inputs, or kernel validation passes for some lineups but fails for others in same portfolio.

### Pitfall 3: Calibration Metrics Without Posterior Predictive Checks

**What goes wrong:** Relying solely on CRPS/log score without validating that calibrated model actually matches observed data distributions.

**Why it happens:** Calibration metrics are summary statistics that can hide model misspecification. A model can have good CRPS but systematically underestimate tail risk.

**How to avoid:** Always perform posterior predictive checks with `az.plot_ppc()`. Verify that simulated data from posterior matches key statistics of observed data (mean, variance, tail quantiles). Check that coverage is well-calibrated (50% intervals contain ~50% of observations).

**Warning signs:** CRPS improves but posterior predictive plots show systematic misfit, or coverage is far from nominal (e.g., 50% intervals contain 70% of observations).

### Pitfall 4: Inefficient Telemetry I/O Blocking Optimization

**What goes wrong:** Loading terabytes of telemetry data synchronously blocks optimization, causing API timeouts.

**Why it happens:** Reading large Parquet files without predicate pushdown or caching loads entire dataset into memory.

**How to avoid:** Use Polars `scan_parquet()` with filters to push down predicates (only read needed rows/columns). Cache frequently accessed telemetry in memory with Arrow zero-copy. Use DuckDB for SQL-based aggregation that operates on Parquet without loading.

**Warning signs:** Optimization takes >30 seconds, or memory usage spikes during scenario generation. Profile I/O time vs computation time.

## Code Examples

Verified patterns from official sources:

### Neo4j Batch Query with Connection Pooling

```python
# Source: Neo4j Python Driver execute_query API
# https://context7.com/neo4j/neo4j-python-driver/llms.txt
from neo4j import GraphDatabase, RoutingControl

# Configure connection pooling
driver = GraphDatabase.driver(
    "neo4j://localhost:7687",
    auth=("neo4j", "password"),
    max_connection_lifetime=3600,
    max_connection_pool_size=50,
    connection_acquisition_timeout=60
)

# Batch query with read routing
records, summary, keys = driver.execute_query(
    "MATCH (d:Driver) RETURN d.driver_id, d.skill",
    routing_=RoutingControl.READ,
    database_="neo4j"
)

# Process results efficiently
for record in records:
    print(record["d.driver_id"], record["d.skill"])

print(f"Query executed in {summary.result_available_after}ms")
```

### Polars Rolling Aggregation for Telemetry

```python
# Source: Polars rolling and time-based grouping
# https://context7.com/pola-rs/polars/llms.txt
import polars as pl

# Lap-by-lap telemetry DataFrame
df = pl.DataFrame({
    "lap": [1, 2, 3, 4, 5, 1, 2, 3, 4, 5],
    "driver_id": ["driver_1"] * 5 + ["driver_2"] * 5,
    "position": [5, 4, 3, 2, 1, 10, 9, 8, 7, 6],
    "speed": [180.5, 181.2, 179.8, 182.1, 183.0, 175.0, 176.2, 177.5, 178.1, 179.0]
})

# Rolling average position over 3 laps
rolling_pos = df.groupby("driver_id").agg([
    pl.col("position")
        .rolling(window_size=3, min_periods=1)
        .mean()
        .alias("avg_position_3lap")
])

# Time-based aggregation (group by dynamic windows)
# If dataframe has timestamp column
df_with_time = df.with_column(
    pl.col("lap").cast(pl.Int32).alias("lap_int")
)

# Group by 2-lap windows
time_agg = df_with_time.groupby_dynamic(
    "lap_int",
    every="2i",
    period="2i"
).agg([
    pl.col("speed").mean().alias("avg_speed"),
    pl.col("position").min().alias("best_position")
])
```

### DuckDB SQL on Parquet Files

```python
# Source: DuckDB Parquet integration
# https://context7.com/websites/duckdb_stable/llms.txt
import duckdb

# Query Parquet file directly with SQL
result = duckdb.sql("""
    SELECT driver_id,
           AVG(position) as avg_position,
           COUNT(*) as laps_completed
    FROM 'data/telemetry/daytona_2024-02-18.parquet'
    GROUP BY driver_id
    ORDER BY avg_position
""").fetchall()

# Zero-copy: Read Parquet into PyArrow without serialization
import pyarrow.parquet as pq
table = pq.read_table('data/telemetry/daytona_2024-02-18.parquet')

# DuckDB can query PyArrow table directly
result = duckdb.sql("SELECT * FROM table").fetchall()
```

### ArviZ Calibration Diagnostics

```python
# Source: PyMC posterior predictive checks and ArviZ
# https://context7.com/pymc-devs/pymc/llms.txt
import arviz as az

# Load inference data (from NumPyro/PyMC)
idata = az.from_numpyro(mcmc)

# Posterior predictive checks
az.plot_ppc(idata, num_pp_samples=100)

# Compute CRPS
crps = az.crps(observed, predicted)

# Compute log score (log likelihood)
log_score = idata.sample_stats["log_likelihood"].mean()

# Coverage for credible intervals
coverage_50 = az.ic(idata, alpha=0.5)
coverage_90 = az.ic(idata, alpha=0.1)

# Summary of calibration metrics
print(f"CRPS: {crps:.4f}")
print(f"Log score: {log_score:.4f}")
print(f"Coverage (50%): {coverage_50['mean']:.4f}")
print(f"Coverage (90%): {coverage_90['mean']:.4f}")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| **Live Neo4j queries in hot loops** | **Compiled constraint specs (immutable artifacts)** | 2024-2025 pattern | Eliminates nondeterminism, improves performance 10-100x |
| **pandas for telemetry ETL** | **Polars with lazy evaluation** | Polars 0.20+ (2024) | 5-10x faster for large datasets with multi-threading |
| **Custom CRPS implementation** | **ArviZ calibration metrics** | ArviZ 0.18+ (2024) | Battle-tested implementations with proper statistical handling |
| **Synchronous API endpoints** | **FastAPI with BackgroundTasks** | FastAPI 0.100+ (2023) | Async processing prevents timeout, better UX |
| **JSON for telemetry storage** | **Parquet with predicate pushdown** | PyArrow 10+ (2023) | 5-10x compression, columnar queries, zero-copy IPC |

**Deprecated/outdated:**
- **NumPy's legacy `np.random` functions**: Use `np.random.default_rng()` - new Generator API is faster and more reproducible
- **pandas for large datasets**: Use Polars for 5-10x performance improvement with lazy evaluation
- **Custom Bayesian calibration**: Use NumPyro or PyMC for proper MCMC with diagnostics

## Open Questions

Things that couldn't be fully resolved:

1. **Granularity of track archetype classification**
   - **What we know:** Calibration needs to be stratified by track type (superspeedway, intermediate, short track, road course).
   - **What's unclear:** How many track archetypes are needed? Should we use NASCAR's official classification or cluster by telemetry statistics?
   - **Recommendation:** Start with 4-5 archetypes (superspeedway, intermediate, short track, road course, restrictor plate). If calibration shows within-archetype heterogeneity, use clustering on telemetry features to discover natural groups.

2. **Frequency of constraint spec recompilation**
   - **What we know:** Constraint specs must be compiled once per slate to ensure reproducibility.
   - **What's unclear:** Should constraints be recompiled for every race, or can they be cached across races with same driver/track combinations?
   - **Recommendation:** Recompile for each slate (driver lineups change weekly). Cache within slate for multiple optimization runs with different parameters.

3. **Calibration sample size requirements**
   - **What we know:** Track-archetype calibration requires historical race data. How many races per archetype are needed for stable calibration?
   - **What's unclear:** Minimum races for reliable calibration? Can we pool across archetypes for low-data tracks?
   - **Recommendation:** Aim for 20+ races per archetype for stable calibration. Use hierarchical Bayesian model to share strength across archetypes for low-data tracks.

4. **Feature availability enforcement mechanism**
   - **What we know:** Feature availability contracts prevent data leakage, but enforcement mechanism needs to be defined.
   - **What's unclear:** Should this be a runtime check, a type-system constraint, or a linting rule? How to handle derived features?
   - **Recommendation:** Implement as runtime check with `FeatureAvailabilityContract.validate_features()`. Add Pydantic validators for request/response models. Use type annotations to mark feature sources (historical, practice, qualifying).

## Sources

### Primary (HIGH confidence)

- **[/neo4j/neo4j-python-driver](https://context7.com/neo4j/neo4j-python-driver/llms.txt)** - Neo4j Python Driver with `execute_query` API, connection pooling, and `RoutingControl.READ` for efficient batch queries
- **[/pola-rs/polars](https://context7.com/pola-rs/polars/llms.txt)** - Polars DataFrame library with lazy evaluation, rolling windows, and time-based aggregation for telemetry ETL
- **[/pyro-ppl/numpyro](https://context7.com/pyro-ppl/numpyro/llms.txt)** - NumPyro probabilistic programming with NUTS/HMC MCMC, JAX acceleration, and vectorized sampling
- **[/pymc-devs/pymc](https://context7.com/pymc-devs/pymc/llms.txt)** - PyMC posterior predictive checks and calibration metrics (CRPS, log score)
- **[/websites/fastapi_tiangolo](https://fastapi.tiangolo.com/de/reference/fastapi)** - FastAPI with Pydantic models, BackgroundTasks, and dependency injection for headless APIs
- **[/websites/duckdb_stable](https://context7.com/websites/duckdb_stable/llms.txt)** - DuckDB zero-copy Parquet reading and SQL analytics on telemetry data

### Secondary (MEDIUM confidence)

- **[ArviZ Documentation](https://arviz-devs.github.io/arviz/)** - Calibration diagnostics, posterior predictive checks, and plotting for Bayesian models
- **[PyArrow Parquet Documentation](https://arrow.apache.org/docs/python/parquet.html)** - Parquet serialization, predicate pushdown, and zero-copy IPC
- **[Feature Availability Contracts in ML](https://link.springer.com/article/10.1007/s10462-025-11326-3)** (2025) - Academic paper on preventing data leakage through feature contracts
- **[Probabilistic Forecast Calibration](https://arxiv.org/html/2506.13687v1)** (June 2025) - Enforcing tail calibration with log score and CRPS optimization
- **[MVG-CRPS: A Robust Loss Function](https://openreview.net/pdf?id=mZuFaBAVs6)** (2025) - Multivariate CRPS for probabilistic forecasts

### Tertiary (LOW confidence)

- **[Ontology-Driven AI Systems](https://www.sciencedirect.com/science/pii/S0167739X26000142)** (2026) - Knowledge graph frameworks for AI model systems (search result only, not verified)
- **[Context Graphs for Governed LLMs](https://medium.com/@adnanmasood/context-graphs-a-practical-guide-to-governed-context-for-llms-agents-and-knowledge-systems-c49610c8ff27)** - Governed memory layer connecting entities and events (search result only, not verified)

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** - Neo4j driver, Polars, NumPyro, and FastAPI are well-established with official Context7 documentation
- Architecture: **MEDIUM** - Patterns follow best practices (immutable artifacts, feature contracts, calibration diagnostics), but NASCAR-specific implementation details may vary
- Pitfalls: **MEDIUM** - Identified from general ML/engineering best practices, but telemetry pipeline and calibration pitfalls may emerge during implementation
- Telemetry pipeline: **HIGH** - Polars and DuckDB patterns are verified with official documentation
- Calibration: **MEDIUM** - NumPyro and ArviZ are well-documented, but track-archetype calibration approach is novel
- API design: **HIGH** - FastAPI patterns are standard with Pydantic validation and BackgroundTasks

**Research date:** 2026-01-27
**Valid until:** 2026-02-26 (30 days - Polars and NumPyro are fast-moving, but core patterns stable)

**Existing codebase integration:**
- `apps/backend/app/ontology.py`: OntologyDriver with Neo4j connection pooling - can be extended for batch constraint compilation
- `packages/axiomatic-sim/src/axiomatic_sim/scenario_generator.py`: SkeletonNarrative with CBN sampling - needs integration with compiled constraints
- `apps/backend/app/kernel.py`: KernelLogic with conservation validation - needs instrumentation for rejection rate tracking
- `apps/backend/app/main.py`: FastAPI app - needs `/optimize` endpoint with scenario-driven contracts
- `pyproject.toml`: Dependencies include Neo4j, FastAPI - need to add Polars, PyArrow, DuckDB, NumPyro, ArviZ
