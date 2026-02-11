"""
Telemetry ETL pipeline for lap-by-lap NASCAR data.

This module provides:
- Feature availability contracts to prevent data leakage
- Polars-based ingestion with lazy Parquet scanning
- Rolling window transformations for aggregate features
- Parquet artifact persistence with compression
"""

from app.telemetry.features import FeatureAvailabilityContract
from app.telemetry.ingest import TelemetryIngestor, ingest_lap_by_lap_telemetry
from app.telemetry.transform import (
    compute_aggregate_features,
    rolling_statistics,
    compute_falloff_metrics,
    handle_missing_data,
)
from app.telemetry.artifacts import (
    persist_telemetry_artifact,
    load_telemetry_artifact,
    list_artifacts,
    validate_artifact_schema,
)

__all__ = [
    "FeatureAvailabilityContract",
    "TelemetryIngestor",
    "ingest_lap_by_lap_telemetry",
    "compute_aggregate_features",
    "rolling_statistics",
    "compute_falloff_metrics",
    "handle_missing_data",
    "persist_telemetry_artifact",
    "load_telemetry_artifact",
    "list_artifacts",
    "validate_artifact_schema",
]
