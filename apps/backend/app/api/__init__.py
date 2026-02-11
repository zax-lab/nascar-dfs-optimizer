"""
API module for NASCAR DFS optimization endpoints.

This package provides FastAPI routers and Pydantic contracts for
headless optimization with scenario-driven configs.
"""
from app.api.contracts import (
    PitStrategy,
    ScenarioConfig,
    DriverConstraintsRequest,
    OptimizeRequest,
    DriverSelection,
    ScenarioDiagnostics,
    OptimizeResponse,
    OptimizationStatus
)

__all__ = [
    "PitStrategy",
    "ScenarioConfig",
    "DriverConstraintsRequest",
    "OptimizeRequest",
    "DriverSelection",
    "ScenarioDiagnostics",
    "OptimizeResponse",
    "OptimizationStatus",
]
