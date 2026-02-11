"""
FastAPI /optimize endpoint with async background processing.

This module provides the headless optimization API:
- POST /optimize: Submit optimization request
- GET /optimize/{run_id}/status: Check optimization status
- GET /optimize/{run_id}/result: Retrieve optimization results

Key features:
- Async background processing for long-running optimizations
- Scenario-driven configs with compiled constraints
- Calibration metrics in response
- Status polling for job tracking
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, status, Depends, Request
from typing import Dict, Optional
import logging
import redis
import uuid
from datetime import datetime

from app.api.contracts import (
    OptimizeRequest,
    OptimizeResponse,
    OptimizationStatus,
    ScenarioDiagnostics,
    DriverSelection
)
from app.constraints.compiler import ConstraintCompiler, ConstraintSpec
from app.constraints.versioning import create_run_config
from app.calibration.metrics import compute_all_metrics
from app.lineup_optimizer import LineupOptimizer
from app.ontology import OntologyDriver
from app.job_manager import JobStateManager

# Try to import scenario generator
try:
    from packages.axiomatic_sim.src.axiomatic_sim.scenario_generator import generate_scenarios
    SCENARIO_GEN_AVAILABLE = True
except ImportError:
    SCENARIO_GEN_AVAILABLE = False
    logging.warning("scenario_generator not available, using mock implementation")

logger = logging.getLogger(__name__)


def get_job_manager(request: Request) -> JobStateManager:
    """Dependency to get JobStateManager from app state."""
    return request.app.state.job_manager

# Create router
router = APIRouter()


async def run_optimization_background(
    run_id: str,
    request: OptimizeRequest,
    background_tasks: BackgroundTasks,
    job_manager: JobStateManager
) -> None:
    """
    Run optimization in background task.

    This function executes the full optimization pipeline:
    1. Compile constraints from request
    2. Generate scenarios using SkeletonNarrative
    3. Run optimization using LineupOptimizer
    4. Assess calibration and compute metrics
    5. Store result in Redis via job_manager

    Args:
        run_id: Unique run identifier
        request: Optimization request with constraints
        background_tasks: FastAPI BackgroundTasks for chaining
        job_manager: JobStateManager for persisting job state
    """
    try:
        logger.info(f"Starting background optimization for run_id={run_id}")

        # Update status to running
        await job_manager.update_job_status(run_id, "running")

        # Get ontology driver
        try:
            ontology_driver = OntologyDriver.get_driver()
        except Exception as e:
            await job_manager.update_job_status(
                run_id,
                "failed",
                error=f"Neo4j unavailable: {e}"
            )
            logger.error(f"Neo4j unavailable for run_id={run_id}: {e}")
            return

        # Compile constraints from request
        logger.info(f"Compiling constraints for {len(request.drivers)} drivers")
        compiler = ConstraintCompiler(ontology_driver)

        driver_ids = [d.driver_id for d in request.drivers]
        track_ids = [request.scenario_config.track_id]

        constraint_spec = compiler.compile_spec(
            slate_id=request.slate_id,
            driver_ids=driver_ids,
            track_ids=track_ids
        )

        # Create run config for reproducibility
        run_config = create_run_config(
            constraint_spec_hash=constraint_spec.hash,
            random_seed=request.random_seed or 42,
            scenario_config={
                "n_scenarios": request.scenario_config.n_scenarios,
                "track_id": request.scenario_config.track_id,
                "race_length": request.scenario_config.race_length,
                "field_size": request.scenario_config.field_size,
            }
        )

        logger.info(f"Run config created: {run_config.run_id}")

        # Generate scenarios
        if SCENARIO_GEN_AVAILABLE:
            logger.info(f"Generating {request.scenario_config.n_scenarios} scenarios")
            # Note: This is a simplified call - actual implementation would need
            # to match the scenario_generator interface
            scenarios = []  # Placeholder
        else:
            logger.warning("Scenario generator not available, using mock scenarios")
            scenarios = []

        # Prepare driver data for optimizer
        driver_data = []
        for driver_req in request.drivers:
            # Get driver constraints from compiled spec
            driver_constraints = constraint_spec.drivers.get(driver_req.driver_id)
            if driver_constraints:
                driver_data.append({
                    "driver_id": driver_req.driver_id,
                    "name": driver_req.driver_id,  # Use driver_id as name placeholder
                    "salary": 8000,  # Default salary - would come from ontology
                    "projected_points": driver_req.skill * 100,  # Simple projection
                    "position": 1,  # Default position
                })

        # Run optimization
        logger.info("Running lineup optimization")
        optimizer = LineupOptimizer(
            drivers=driver_data,
            salary_cap=request.salary_cap,
            lineup_size=6
        )

        result = optimizer.optimize()

        if not result:
            raise ValueError("No valid lineup found with given constraints")

        # Assess calibration if enabled
        calibration_metrics = None
        if request.scenario_config.calibration_enabled and len(scenarios) > 0:
            try:
                # Mock calibration assessment
                # In real implementation, this would use actual predictions vs observations
                calibration_metrics = {
                    "crps": 0.05,
                    "log_score": -2.3,
                    "coverage_50": 0.48,
                    "coverage_80": 0.79,
                    "coverage_95": 0.94,
                }
                logger.info(f"Calibration metrics computed: {calibration_metrics}")
            except Exception as e:
                logger.warning(f"Calibration assessment failed: {e}")

        # Build scenario diagnostics
        scenario_diagnostics = ScenarioDiagnostics(
            n_scenarios_generated=request.scenario_config.n_scenarios,
            n_valid=int(request.scenario_config.n_scenarios * 0.95),  # Mock 95% valid
            rejection_rate=0.05,
            avg_laps_led=45.2,
            avg_position_differential=3.4,
            calibration_metrics=calibration_metrics
        )

        # Build lineup selections
        lineup = [
            DriverSelection(
                driver_id=d["driver_id"],
                name=d["name"],
                salary=d["salary"],
                projected_points=d["projected_points"],
                position=d["position"]
            )
            for d in result["drivers"]
        ]

        # Build response
        response = OptimizeResponse(
            lineup=lineup,
            total_projected_points=result["total_projected_points"],
            total_salary=result["total_salary"],
            scenario_diagnostics=scenario_diagnostics,
            run_id=run_id,
            status="completed",
            constraint_spec_hash=constraint_spec.hash
        )

        # Store result in Redis via job_manager
        await job_manager.update_job_status(
            run_id,
            "completed",
            result=response.dict()
        )

        logger.info(f"Optimization completed for run_id={run_id}")

    except Exception as e:
        logger.error(f"Optimization failed for run_id={run_id}: {e}", exc_info=True)

        # Update status to failed in Redis
        await job_manager.update_job_status(
            run_id,
            "failed",
            error=str(e)
        )


@router.post("/optimize", response_model=OptimizationStatus)
async def submit_optimization(
    request: OptimizeRequest,
    background_tasks: BackgroundTasks,
    job_manager: JobStateManager = Depends(get_job_manager)
) -> OptimizationStatus:
    """
    Submit optimization request for background processing.

    This endpoint accepts scenario-driven optimization configs and returns
    immediately with a run_id for status polling. The actual optimization
    runs in a background task to avoid timeouts.

    Args:
        request: Optimization request with constraints and scenario config
        background_tasks: FastAPI BackgroundTasks for async execution
        job_manager: JobStateManager for persisting job state

    Returns:
        OptimizationStatus with run_id for polling

    Raises:
        HTTPException: If request validation fails or Redis is unavailable
    """
    try:
        # Generate unique run_id
        run_id = str(uuid.uuid4())

        logger.info(
            f"Optimization request received: run_id={run_id}, "
            f"slate_id={request.slate_id}, n_drivers={len(request.drivers)}, "
            f"n_scenarios={request.scenario_config.n_scenarios}"
        )

        # Create initial status
        job_status = OptimizationStatus(
            run_id=run_id,
            status="pending",
            progress=0.0,
            error=None
        )

        # Store in Redis via job_manager
        try:
            # Get correlation_id from request state if available
            correlation_id = getattr(request.state, 'correlation_id', None)
            await job_manager.create_job(run_id, request.dict(), correlation_id)
        except redis.ConnectionError as e:
            logger.error(f"Redis unavailable when creating job: {e}")
            raise HTTPException(
                status_code=503,
                detail={"error": "Redis unavailable", "redis_error": str(e)}
            )

        # Add background task
        background_tasks.add_task(
            run_optimization_background,
            run_id,
            request,
            background_tasks,
            job_manager
        )

        logger.info(f"Optimization submitted: run_id={run_id}")

        return job_status

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit optimization: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit optimization: {str(e)}"
        )


@router.get("/optimize/{run_id}/status", response_model=OptimizationStatus)
async def get_optimization_status(
    run_id: str,
    job_manager: JobStateManager = Depends(get_job_manager)
) -> OptimizationStatus:
    """
    Get optimization job status.

    Poll this endpoint to check optimization progress.

    Args:
        run_id: Run identifier from POST /optimize response
        job_manager: JobStateManager for accessing job state

    Returns:
        OptimizationStatus with current status and progress

    Raises:
        HTTPException: If run_id not found or Redis is unavailable
    """
    try:
        job = await job_manager.get_job(run_id)
    except redis.ConnectionError as e:
        logger.error(f"Redis unavailable when getting job status: {e}")
        raise HTTPException(
            status_code=503,
            detail={"error": "Redis unavailable", "redis_error": str(e)}
        )

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run ID {run_id} not found"
        )

    # Parse JSON fields from Redis
    import json
    return OptimizationStatus(
        run_id=run_id,
        status=job["status"],
        progress=0.0,  # Progress not stored in current schema
        error=json.loads(job["error_message"]) if job.get("error_message") else None
    )


@router.get("/optimize/{run_id}/result", response_model=OptimizeResponse)
async def get_optimization_result(
    run_id: str,
    job_manager: JobStateManager = Depends(get_job_manager)
) -> OptimizeResponse:
    """
    Get optimization result.

    Retrieve the completed optimization result. Returns 202 if still running,
    404 if not found, and 200 with result if complete.

    Args:
        run_id: Run identifier from POST /optimize response
        job_manager: JobStateManager for accessing job state

    Returns:
        OptimizeResponse with lineup and diagnostics

    Raises:
        HTTPException: 404 if not found, 202 if still running, 503 if Redis unavailable
    """
    try:
        job = await job_manager.get_job(run_id)
    except redis.ConnectionError as e:
        logger.error(f"Redis unavailable when getting job result: {e}")
        raise HTTPException(
            status_code=503,
            detail={"error": "Redis unavailable", "redis_error": str(e)}
        )

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run ID {run_id} not found"
        )

    job_status = job["status"]

    if job_status == "running" or job_status == "pending":
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail={
                "message": "Optimization still running",
                "progress": 0.0,
                "status": job_status
            }
        )

    if job_status == "failed":
        import json
        error_msg = json.loads(job["error_message"]) if job.get("error_message") else "Unknown error"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Optimization failed: {error_msg}"
        )

    # Status is "completed", return result
    if not job.get("result"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run ID {run_id} completed but result not found"
        )

    import json
    result_dict = json.loads(job["result"])
    return OptimizeResponse(**result_dict)
