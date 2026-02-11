"""
FastAPI application for NASCAR DFS optimization.

This module provides a REST API for optimizing NASCAR DFS lineups using
kernel-based validation and constraint optimization.

Phase 4 endpoints:
- /ownership: Ownership estimation using ensemble methods
- /contest-sim: Contest simulation with ownership-based field generation
- /optimize-with-leverage: Leverage-aware optimization with ownership constraints

Phase 5 infrastructure:
- Redis-based job state persistence via JobStateManager
- Connection pooling for efficient Redis access
"""

import logging
import os
import time
import asyncio
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status, BackgroundTasks, Body
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator, constr
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import redis

# Import structured logging and middleware
from app.logging_config import configure_logging, get_logger
from app.middleware import CorrelationIDMiddleware

# Configure structured logging at module level
configure_logging(log_level="INFO")
logger = get_logger(__name__)

try:
    from app.lineup_optimizer import LineupOptimizer
except ImportError:
    LineupOptimizer = None
try:
    from app.kernel import KernelLogic
except ImportError:
    KernelLogic = None
import numpy as np

# Import optimize routers
try:
    from app.api.optimize import router as optimize_router
except ImportError:
    optimize_router = None
try:
    from app.api.optimize_portfolio import optimize_endpoint, OptimizeRequest
except ImportError:
    optimize_endpoint = None
    OptimizeRequest = None

# Import Phase 5 infrastructure
try:
    from app.job_manager import JobStateManager
except ImportError:
    JobStateManager = None
try:
    from app.api.health import router as health_router
except ImportError:
    health_router = None

# Import Phase 4 components
try:
    from app.ownership.ensemble import HybridOwnershipEstimator
    from app.ownership.models import (
        OwnershipRequest,
        OwnershipResponse,
        OwnershipPrediction,
    )
    from app.contest.contest_sim import ContestSimulator
    from app.contest.field_sim import FieldLineupSampler
    from app.contest.payout_curve import PayoutCurveFitter
    from app.optimizer.leverage_aware import LeverageAwareOptimizer
    from app.api.contracts import (
        ContestSimRequest,
        ContestSimResponse,
        LeverageOptimizeRequest,
        LeverageOptimizeResponse,
        LineupWithLeverage,
        DriverInLineup,
        PortfolioMetrics,
        OwnershipMetrics,
        ConstraintSpecForLeverage,
    )

    PHASE_4_AVAILABLE = True
except ImportError as e:
    logger = get_logger(__name__)
    logger.warning("Phase 4 components not available", error=str(e))
    PHASE_4_AVAILABLE = False
    # Create dummy classes for type hints
    OwnershipRequest = None
    OwnershipResponse = None
    ContestSimRequest = None
    ContestSimResponse = None
    LeverageOptimizeRequest = None
    LeverageOptimizeResponse = None

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


async def graceful_shutdown(job_manager, shutdown_event, timeout: int = 90) -> None:
    """
    Graceful shutdown function that waits for in-flight jobs to complete.

    Args:
        job_manager: JobStateManager instance for checking running jobs
        shutdown_event: asyncio.Event to signal shutdown
        timeout: Maximum seconds to wait for jobs to complete (default: 90)

    This function:
    1. Sets shutdown_event to signal job submission to stop
    2. Polls running job count until 0 or timeout
    3. Logs warning if timeout exceeded with jobs still running
    """
    logger.info("Shutdown initiated", timeout_seconds=timeout)
    shutdown_event.set()  # Signal job submission to stop

    start_time = time.time()
    while time.time() - start_time < timeout:
        running = await job_manager.get_running_job_count()
        if running == 0:
            logger.info("All jobs complete, shutting down")
            return
        logger.info("Waiting for jobs to complete", running=running)
        await asyncio.sleep(1)

    remaining = await job_manager.get_running_job_count()
    logger.warning("Shutdown timeout with jobs still running", remaining=remaining)


limiter = Limiter(key_func=get_remote_address)

# OpenAPI tags metadata
tags_metadata = [
    {
        "name": "optimization",
        "description": "Operations for DFS lineup optimization with scenario-driven configs",
    },
    {
        "name": "portfolio",
        "description": "CVaR portfolio optimization with tail metrics and calibration",
    },
    {
        "name": "ownership",
        "description": "Phase 4: Ownership estimation using ensemble methods",
    },
    {
        "name": "contest",
        "description": "Phase 4: Contest simulation with ownership-based field generation",
    },
    {
        "name": "leverage",
        "description": "Phase 4: Leverage-aware optimization with ownership constraints",
    },
    {"name": "health", "description": "Health check and system status"},
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifespan with Redis connection pool.

    Startup:
    - Set APP_START_TIME environment variable for uptime tracking
    - Create Redis connection pool with health checks
    - Initialize JobStateManager for job persistence
    - Initialize Neo4j driver and store in app.state for readiness checks
    - Store in app.state for endpoint access

    Shutdown:
    - Close Redis client connection
    - Disconnect connection pool
    """
    # Startup - Set APP_START_TIME for health endpoint uptime tracking
    import time

    os.environ["APP_START_TIME"] = str(int(time.time()))

    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))

    logger.info("Connecting to Redis", redis_host=redis_host, redis_port=redis_port)

    try:
        # Create Redis connection pool with health checks
        redis_pool = redis.ConnectionPool(
            host=redis_host,
            port=redis_port,
            db=0,
            health_check_interval=30,
            socket_timeout=3,
            socket_connect_timeout=3,
            decode_responses=True,
        )
        app.state.redis_pool = redis_pool

        # Create Redis client
        redis_client = redis.Redis(connection_pool=redis_pool)
        app.state.redis_client = redis_client

        # Initialize JobStateManager if available
        if JobStateManager is not None:
            job_manager = JobStateManager(redis_pool)
            app.state.job_manager = job_manager
            logger.info("Redis connected, JobStateManager initialized")
        else:
            logger.warning("JobStateManager not available, job persistence disabled")
            app.state.job_manager = None

        # Create shutdown event for graceful shutdown
        shutdown_event = asyncio.Event()
        app.state.shutdown_event = shutdown_event

    except Exception as e:
        logger.error("Failed to connect to Redis", error=str(e))
        # Continue without Redis - will be handled in endpoints
        app.state.redis_pool = None
        app.state.redis_client = None
        app.state.job_manager = None

    # Initialize Neo4j driver for readiness checks
    try:
        from app.ontology import OntologyDriver

        # Get Neo4j credentials from environment
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "neo4j")

        # Initialize OntologyDriver singleton with credentials
        ontology_driver = OntologyDriver(neo4j_uri, neo4j_user, neo4j_password)

        if ontology_driver and hasattr(ontology_driver, "_driver"):
            app.state.neo4j_driver = ontology_driver._driver
            logger.info("Neo4j driver stored in app.state for readiness checks")
        else:
            logger.warning("Neo4j driver not available for readiness checks")
            app.state.neo4j_driver = None
    except Exception as e:
        logger.warning(
            "Failed to initialize Neo4j driver for readiness checks", error=str(e)
        )
        app.state.neo4j_driver = None

    # Log API startup information
    logger.info("Axiomatic NASCAR DFS API starting up")
    logger.info("Phase 3: Tail Metrics + Tail-Objective Portfolio Optimizer")
    if PHASE_4_AVAILABLE:
        logger.info("Phase 4: Field / Ownership / Contest-Sim EV endpoints available")
    else:
        logger.warning("Phase 4 endpoints not available (missing dependencies)")
    logger.info("Phase 5: Redis-based job persistence enabled")

    yield

    # Shutdown
    logger.info("Axiomatic NASCAR DFS API shutting down")
    logger.info("Shutting down Redis connection")

    # Graceful shutdown - wait for running jobs to complete
    if hasattr(app.state, "job_manager") and app.state.job_manager:
        await graceful_shutdown(
            job_manager=app.state.job_manager,
            shutdown_event=app.state.shutdown_event,
            timeout=90,
        )

    if hasattr(app.state, "redis_client") and app.state.redis_client:
        try:
            app.state.redis_client.close()
        except Exception as e:
            logger.warning("Error closing Redis client", error=str(e))

    if hasattr(app.state, "redis_pool") and app.state.redis_pool:
        try:
            app.state.redis_pool.disconnect()
        except Exception as e:
            logger.warning("Error disconnecting Redis pool", error=str(e))


app = FastAPI(
    title="Axiomatic NASCAR DFS API",
    version="0.3.0",
    description="Scenario-based causal race simulation + conditional upside optimizer",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add correlation ID middleware for distributed tracing
# app.add_middleware(CorrelationIDMiddleware)  # Temporarily disabled due to compatibility issues


class ErrorResponse(BaseModel):
    """Pydantic model for error responses."""

    error: str
    detail: str
    status_code: int


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with structured logging."""
    logger.error(
        "Unhandled exception",
        exc_info=exc,
        exception_type=type(exc).__name__,
        exception_message=str(exc),
        path=request.url.path,
        method=request.method,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred. Please try again later.",
            "status_code": 500,
        },
    )


# Include optimize router with /api/v1 prefix
if optimize_router is not None:
    app.include_router(optimize_router, prefix="/api/v1", tags=["optimization"])

# Include health router (should be first for reliability)
if health_router is not None:
    app.include_router(health_router, tags=["health"])
    logger.info("Health check endpoints registered")


@app.post("/optimize", tags=["portfolio"])
async def optimize_portfolio(request: dict = Body(...), export_csv: bool = False):
    """
    Generate CVaR-optimized portfolio for NASCAR DFS.

    Pipeline:
    1. Generate scenarios using Phase 2 CBN with constraint spec
    2. Run portfolio optimization using Phase 3 CVaR objectives
    3. Validate tail objective (optimizer targets tails, not mean)
    4. Compute calibration metrics (optional)
    5. Generate explain artifacts

    Args:
        request: Optimization request with constraint spec and parameters
        export_csv: Export lineups to CSV (returns path in response)

    Returns:
        OptimizeResponse with lineups, metrics, and explain artifacts
    """
    if optimize_endpoint is None or OptimizeRequest is None:
        raise HTTPException(
            status_code=501, detail="Portfolio optimization not available"
        )

    from fastapi import BackgroundTasks

    # Parse request dict into OptimizeRequest model
    try:
        parsed_request = OptimizeRequest(**request)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid request: {str(e)}")

    background_tasks = BackgroundTasks()
    return await optimize_endpoint(parsed_request, background_tasks, export_csv)


# =============================================================================
# Phase 4 Endpoints: Ownership, Contest Simulation, Leverage Optimization
# =============================================================================

# Global caches for Phase 4 components
_ownership_estimator_cache: Dict[str, Any] = {}
_payout_curve_cache: Dict[str, Any] = {}


@app.post("/ownership", tags=["ownership"])
async def estimate_ownership(request: Any) -> Any:
    """
    Estimate driver ownership using ensemble methods.

    Combines multiple ownership signals (historical, projections-based,
    salary-skill regression, recent form) using voting or stacking ensembles.

    Pipeline:
    1. Create feature matrix from driver_data and race_data
    2. Initialize HybridOwnershipEstimator with specified parameters
    3. If no training data provided, use pre-trained model (cached)
    4. Generate ownership predictions
    5. If include_uncertainty: predict with bootstrap confidence bounds

    Args:
        request: Ownership estimation request with driver/race data

    Returns:
        OwnershipResponse with predictions and optional uncertainty bounds

    Raises:
        HTTPException: If ownership estimation fails
    """
    if not PHASE_4_AVAILABLE:
        raise HTTPException(
            status_code=501, detail="Phase 4 ownership estimation not available"
        )

    try:
        logger.info(
            f"Ownership estimation request: {len(request.driver_data)} drivers, "
            f"track={request.race_data.track_archetype}, "
            f"ensemble={request.ensemble_method}"
        )

        # Create feature matrix from request
        import pandas as pd

        driver_data_list = [
            {
                "driver_id": d.driver_id,
                "salary": d.salary,
                "projected_points": d.projected_points or 50.0,
                "skill": d.skill or 0.5,
                "recent_avg_finish": d.recent_avg_finish or 20.0,
                "track_archetype": request.race_data.track_archetype,
                "race_date": request.race_data.race_date,
            }
            for d in request.driver_data
        ]

        X = pd.DataFrame(driver_data_list)

        # Check cache for pre-trained model
        cache_key = f"{request.race_data.track_archetype}_{request.ensemble_method}"
        estimator = _ownership_estimator_cache.get(cache_key)

        if estimator is None:
            # Initialize new estimator
            estimator = HybridOwnershipEstimator(
                track_archetype=request.race_data.track_archetype,
                n_recent_races=request.n_recent_races,
                ensemble_method=request.ensemble_method.value,
                weights=request.custom_weights,
            )

            # For now, fit on minimal data (in production, load from DB)
            # Use mock training data
            y_mock = np.linspace(30, 0, len(X))  # Decreasing ownership
            estimator.fit(X, y_mock)

            # Cache estimator
            _ownership_estimator_cache[cache_key] = estimator
            logger.info(f"Cached ownership estimator: {cache_key}")

        # Generate predictions
        if request.include_uncertainty:
            # Predict with uncertainty bounds
            uncertainty_results = estimator.predict_with_uncertainty(
                X, n_bootstraps=100
            )

            predictions = uncertainty_results["mean"]
        else:
            # Simple predictions
            predictions = estimator.predict(X)

        # Build response
        ownership_predictions = [
            {
                "driver_id": int(d.driver_id),
                "ownership_percent": float(pred),
                "uncertainty_lower": float(uncertainty_results["lower_5"][i])
                if getattr(request, 'include_uncertainty', False)
                else None,
                "uncertainty_upper": float(uncertainty_results["upper_95"][i])
                if getattr(request, 'include_uncertainty', False)
                else None,
            }
            for i, (d, pred) in enumerate(zip(request.driver_data, predictions))
        ]

        response = {
            "ownership_predictions": ownership_predictions,
            "ensemble_method": getattr(request, 'ensemble_method', 'voting'),
            "feature_importance": getattr(estimator, "feature_importance_", None),
            "n_recent_races": getattr(request, 'n_recent_races', 5),
            "model_metadata": {
                "track_archetype": request.race_data.track_archetype,
                "n_drivers": len(request.driver_data),
                "cached": cache_key in _ownership_estimator_cache,
            },
        }

        logger.info(
            f"Ownership estimation complete: avg_ownership={np.mean(predictions):.1f}%"
        )

        return response

    except Exception as e:
        logger.error(f"Ownership estimation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Ownership estimation failed: {str(e)}"
        )


@app.post("/contest-sim", tags=["contest"])
async def simulate_contest(request: ContestSimRequest):
    """
    Simulate contest outcomes with ownership-based field generation.

    Runs Monte Carlo simulations to estimate ROI, cash%, and win probability
    for DFS lineups against ownership-weighted field lineups.

    Pipeline:
    1. Convert scenario_driver_scores to numpy array
    2. Create FieldLineupSampler (uses ownership from context or defaults)
    3. Load or fit PayoutCurveFitter for contest_size_tier
    4. Create ContestSimulator with field sampler and payout curve
    5. Run simulate_portfolio() with my_lineup_scores and scenarios
    6. Compute metrics (ROI, cash%, win probability) with confidence intervals

    Args:
        request: Contest simulation request with lineup scores and scenarios

    Returns:
        ContestSimResponse with ROI, cash%, win probability, and confidence intervals

    Raises:
        HTTPException: If contest simulation fails
    """
    if not PHASE_4_AVAILABLE:
        raise HTTPException(
            status_code=501, detail="Phase 4 contest simulation not available"
        )

    try:
        logger.info(
            f"Contest sim request: {len(request.my_lineup_scores)} lineups, "
            f"{len(request.scenario_driver_scores)} scenarios, "
            f"field_size={request.field_size}"
        )

        # Convert scenario scores to numpy array
        scenario_scores = np.array(request.scenario_driver_scores)
        my_scores = np.array(request.my_lineup_scores)

        n_scenarios, n_drivers = scenario_scores.shape

        # Create driver pool for field sampler (mock data)
        driver_pool = [
            {"driver_id": i, "salary": 7500 + (i % 5) * 500, "projected_points": 45.0}
            for i in range(n_drivers)
        ]

        # Create default ownership (uniform distribution)
        ownership = np.full(n_drivers, 100.0 / n_drivers)

        # Create field sampler
        field_sampler = FieldLineupSampler(
            ownership=ownership, driver_pool=driver_pool, salary_cap=50000, n_drivers=6
        )

        # Load or create payout curve
        payout_curve = _payout_curve_cache.get(request.contest_size_tier)

        if payout_curve is None:
            # Use default payout structure
            logger.info(
                f"Using default payout structure for '{request.contest_size_tier}'"
            )
            payout_curve = None  # Simulator will use defaults

        # Create simulator
        simulator = ContestSimulator(
            field_sampler=field_sampler,
            payout_curve=payout_curve,
            field_size=request.field_size,
            n_scenarios=n_scenarios,
            n_contest_sims=request.n_contest_sims,
            default_payout_structure="standard_gpp",
        )

        # Run simulation
        results = simulator.simulate_portfolio(
            my_lineup_scores=my_scores,
            scenario_driver_scores=scenario_scores,
            buyin=request.contest_buyin,
        )

        # Compute metrics
        metrics = simulator.compute_contest_metrics(
            results, buyin=request.contest_buyin
        )

        # Calculate confidence intervals
        payouts = results["payouts"]
        roi_values = (payouts - request.contest_buyin) / request.contest_buyin * 100

        response = ContestSimResponse(
            roi=float(metrics["roi"]),
            roi_std=float(roi_values.std()),
            roi_lower_5=float(np.percentile(roi_values, 5)),
            roi_upper_95=float(np.percentile(roi_values, 95)),
            cash_pct=float(metrics["cash_pct"]),
            cash_se=float(metrics["cash_pct"] * 0.1),  # Approximate SE
            win_prob=float(metrics["win_prob"]),
            win_se=float(metrics["win_prob"] * 0.1),  # Approximate SE
            best_rank=int(results["ranks"].min()),
            worst_rank=int(results["ranks"].max()),
            best_payout=float(payouts.max()),
            n_simulations=int(len(results["ranks"].flatten())),
        )

        logger.info(
            f"Contest sim complete: ROI={response.roi:.2f}%, "
            f"Cash%={response.cash_pct:.1f}%, "
            f"Win%={response.win_prob:.2f}%"
        )

        return response

    except Exception as e:
        logger.error(f"Contest simulation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Contest simulation failed: {str(e)}"
        )


@app.post("/optimize-with-leverage", tags=["leverage"])
async def optimize_with_leverage(request: LeverageOptimizeRequest):
    """
    Generate leverage-aware optimized lineups with ownership constraints.

    Extends CVaR portfolio optimization with ownership-based leverage to
    generate lineups that differentiate from the field by targeting
    low-ownership drivers.

    Pipeline:
    1. Convert ownership_estimates to numpy array
    2. Create LeverageAwareOptimizer with ownership and leverage parameters
    3. Generate driver_data from constraint specification
    4. If use_regime_allocation: call generate_regime_aware_portfolio()
    5. Else: call optimize_lineup_with_leverage()
    6. Calculate portfolio-level and ownership metrics

    Args:
        request: Leverage optimization request with ownership and constraints

    Returns:
        LeverageOptimizeResponse with lineups and metrics

    Raises:
        HTTPException: If leverage optimization fails
    """
    if not PHASE_4_AVAILABLE:
        raise HTTPException(
            status_code=501, detail="Phase 4 leverage optimization not available"
        )

    try:
        logger.info(
            f"Leverage optimization request: {request.n_lineups} lineups, "
            f"leverage_penalty={request.leverage_penalty:.2f}, "
            f"n_scenarios={request.n_scenarios}"
        )

        # Convert ownership to numpy array
        ownership = np.array(request.ownership_estimates)

        # Create leverage-aware optimizer
        leverage_optimizer = LeverageAwareOptimizer(
            ownership=ownership,
            leverage_penalty=request.leverage_penalty,
            max_ownership_per_driver=request.max_ownership_per_driver,
            min_low_ownership_drivers=request.min_low_ownership_drivers,
            max_total_ownership=request.max_total_ownership,
        )

        # Create driver data (mock for now)
        n_drivers = len(ownership)
        driver_data = [
            {
                "driver_id": i,
                "name": f"Driver_{i}",
                "salary": 7500 + (i % 5) * 500,
                "team": f"team_{i % 3}",
            }
            for i in range(n_drivers)
        ]

        # Create mock scenarios
        np.random.seed(42)
        scenarios = np.random.gamma(20, 2, size=(request.n_scenarios, n_drivers))

        # Generate lineups
        if request.use_regime_allocation:
            # Regime-aware allocation
            # For now, use mock regimes
            regimes = np.random.choice(
                ["dominator", "chaos", "fuel_mileage"], size=request.n_scenarios
            )

            portfolio_by_regime = leverage_optimizer.generate_regime_aware_portfolio(
                driver_data=driver_data,
                scenarios=scenarios,
                regimes=regimes,
                salary_cap=request.constraint_spec.salary_cap,
                n_drivers=request.constraint_spec.n_drivers,
                n_lineups_per_regime=max(1, request.n_lineups // 3),
            )

            # Flatten regime portfolios
            all_lineups = []
            for regime, lineups in portfolio_by_regime.items():
                all_lineups.extend(lineups)

        else:
            # Standard leverage optimization
            all_lineups = leverage_optimizer.optimize_lineup_with_leverage(
                driver_data=driver_data,
                scenarios=scenarios,
                salary_cap=request.constraint_spec.salary_cap,
                n_drivers=request.constraint_spec.n_drivers,
                n_lineups=request.n_lineups,
            )

        if not all_lineups:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate any leverage-optimized lineups",
            )

        # Limit to requested number
        all_lineups = all_lineups[: request.n_lineups]

        # Convert to API response format
        response_lineups = []
        for lineup in all_lineups:
            drivers = [
                DriverInLineup(
                    driver_id=int(d["driver_id"]),
                    name=driver_data[d["driver_id"]]["name"],
                    salary=driver_data[d["driver_id"]]["salary"],
                    projected_points=float(
                        lineup.get("total_projected_points", 150) / 6
                    ),
                    ownership=float(ownership[d["driver_id"]]),
                )
                for d in [{"driver_id": i} for i in lineup["drivers"]]
            ]

            response_lineups.append(
                LineupWithLeverage(
                    drivers=drivers,
                    total_projected_points=float(
                        lineup.get("total_projected_points", 150)
                    ),
                    total_salary=int(lineup.get("total_salary", 48000)),
                    avg_ownership=float(lineup.get("avg_ownership", 15)),
                    max_ownership=float(lineup.get("max_ownership", 25)),
                    total_ownership=float(lineup.get("total_ownership", 90)),
                    leverage_score=float(lineup.get("leverage_score", 50)),
                    regime=lineup.get("regime"),
                )
            )

        # Calculate portfolio metrics
        avg_points = np.mean([l.total_projected_points for l in response_lineups])
        avg_salary = np.mean([l.total_salary for l in response_lineups])

        portfolio_metrics = PortfolioMetrics(
            avg_projected_points=float(avg_points),
            avg_salary=int(avg_salary),
            portfolio_correlation=0.3,  # Mock value
            diversification_score=0.7,  # Mock value
        )

        # Calculate ownership metrics
        avg_lineup_ownership = np.mean([l.avg_ownership for l in response_lineups])
        min_lineup_ownership = np.min([l.avg_ownership for l in response_lineups])
        max_lineup_ownership = np.max([l.avg_ownership for l in response_lineups])
        low_ownership_count = sum(
            1 for l in response_lineups for d in l.drivers if d.ownership < 10
        )

        ownership_metrics = OwnershipMetrics(
            avg_lineup_ownership=float(avg_lineup_ownership),
            min_lineup_ownership=float(min_lineup_ownership),
            max_lineup_ownership=float(max_lineup_ownership),
            low_ownership_driver_count=low_ownership_count,
            diversification_score=0.7,  # Mock value
        )

        response = LeverageOptimizeResponse(
            lineups=response_lineups,
            portfolio_metrics=portfolio_metrics,
            ownership_metrics=ownership_metrics,
        )

        logger.info(
            f"Leverage optimization complete: {len(response_lineups)} lineups, "
            f"avg_ownership={avg_lineup_ownership:.1f}%"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Leverage optimization failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Leverage optimization failed: {str(e)}"
        )
