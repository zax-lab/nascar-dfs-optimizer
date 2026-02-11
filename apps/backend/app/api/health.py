"""
Health check endpoints for Kubernetes-style liveness and readiness probes.

This module provides health check endpoints for orchestrator monitoring:
- GET /health: Liveness probe (always returns 200 if process is running)
- GET /ready: Readiness probe (returns 200 only when dependencies are available)

Key features:
- Liveness checks process health (uptime, version)
- Readiness checks Redis and Neo4j connectivity
- 3-second timeout per dependency check (prevents slow startup)
- Returns 503 with diagnostic detail when dependencies are down

Usage:
    from app.api.health import router as health_router
    app.include_router(health_router, tags=["health"])
"""

import logging
import os
import time
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


async def get_app_state(request: Request) -> Any:
    """
    Dependency to get app state.

    Args:
        request: FastAPI Request object

    Returns:
        App state containing redis_client and neo4j_driver
    """
    return request.app.state


@router.get("/health")
async def liveness() -> Dict[str, Any]:
    """
    Liveness probe endpoint.

    This endpoint always returns 200 if the process is running.
    Used by Kubernetes to check if the container needs restart.

    Returns:
        Dictionary with status, timestamp, version, and uptime_seconds

    Example response:
        {
            "status": "ok",
            "timestamp": "2025-01-28T16:20:00Z",
            "version": "0.3.0",
            "uptime_seconds": 12345
        }
    """
    start_time = os.getenv("APP_START_TIME", int(time.time()))
    uptime = int(time.time() - int(start_time))

    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": os.getenv("APP_VERSION", "0.3.0"),
        "uptime_seconds": uptime,
    }


@router.get("/ready")
def readiness(app_state=Depends(get_app_state)) -> Dict[str, Any]:
    """
    Readiness probe endpoint.

    This endpoint returns 200 only when all dependencies (Redis, Neo4j)
    are available. Returns 503 with diagnostic detail if any dependency is down.

    Used by Kubernetes to check if the container can receive traffic.

    Args:
        app_state: Application state containing redis_client and neo4j_driver

    Returns:
        Dictionary with status and dependency health

    Raises:
        HTTPException: 503 if any dependency is unavailable

    Example response (all ok):
        {
            "status": "ready",
            "dependencies": {
                "redis": "ok",
                "neo4j": "ok"
            }
        }

    Example response (redis down):
        HTTP 503
        {
            "dependencies": {
                "redis": "down: Error connecting to Redis",
                "neo4j": "ok"
            }
        }
    """
    dependencies = {}
    all_ok = True

    # Check Redis (synchronous client)
    try:
        if hasattr(app_state, "redis_client") and app_state.redis_client:
            app_state.redis_client.ping()
            dependencies["redis"] = "ok"
            logger.debug("Redis health check passed")
        else:
            dependencies["redis"] = "down: Client not initialized"
            all_ok = False
            logger.warning("Redis health check failed: Client not initialized")
    except Exception as e:
        dependencies["redis"] = f"down: {str(e)}"
        all_ok = False
        logger.warning(f"Redis health check failed: {e}")

    # Check Neo4j (synchronous driver)
    try:
        # Verify Neo4j driver is available and can connect
        if hasattr(app_state, "neo4j_driver") and app_state.neo4j_driver:
            app_state.neo4j_driver.verify_connectivity()
            dependencies["neo4j"] = "ok"
            logger.debug("Neo4j health check passed")
        else:
            dependencies["neo4j"] = "down: Driver not initialized"
            all_ok = False
            logger.warning("Neo4j health check failed: Driver not initialized")
    except Exception as e:
        dependencies["neo4j"] = f"down: {str(e)}"
        all_ok = False
        logger.warning(f"Neo4j health check failed: {e}")

    # If any dependency is down, return 503 with diagnostic detail
    if not all_ok:
        raise HTTPException(status_code=503, detail={"dependencies": dependencies})

    return {"status": "ready", "dependencies": dependencies}
