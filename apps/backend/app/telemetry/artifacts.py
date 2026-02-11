"""
Parquet artifact persistence module for telemetry data.

Provides efficient storage and loading of telemetry artifacts with Snappy
compression for fast I/O and reduced disk usage.
"""

import polars as pl
from pathlib import Path
from typing import Optional, List, Dict
import logging
import os

logger = logging.getLogger(__name__)


# Valid compression formats for Polars Parquet writer
VALID_COMPRESSION_FORMATS = {"snappy", "gzip", "brotli", "lz4"}


def persist_telemetry_artifact(
    telemetry_df: pl.DataFrame,
    artifact_path: str,
    compression: str = "snappy"
) -> str:
    """
    Persist telemetry DataFrame as Parquet artifact with compression.

    Args:
        telemetry_df: DataFrame to persist
        artifact_path: Output path for Parquet file (must end with .parquet)
        compression: Compression format (snappy, gzip, brotli, lz4)

    Returns:
        Path to persisted artifact

    Raises:
        ValueError: If artifact_path doesn't end with .parquet or compression invalid
        IOError: If write operation fails

    Examples:
        >>> df = pl.DataFrame({'driver_id': ['d1', 'd2'], 'avg_position': [10.5, 15.3]})
        >>> path = persist_telemetry_artifact(df, 'data/telemetry/daytona.parquet')
        >>> print(path)
        data/telemetry/daytona.parquet
    """
    # Validate file extension
    if not artifact_path.endswith(".parquet"):
        raise ValueError(
            f"Artifact path must end with .parquet extension. Got: {artifact_path}"
        )

    # Validate compression format
    if compression not in VALID_COMPRESSION_FORMATS:
        raise ValueError(
            f"Invalid compression format: '{compression}'. "
            f"Must be one of: {sorted(VALID_COMPRESSION_FORMATS)}"
        )

    # Create parent directories if needed
    artifact_file = Path(artifact_path)
    artifact_file.parent.mkdir(parents=True, exist_ok=True)

    logger.info(
        f"Persisting telemetry artifact: {artifact_path} "
        f"({telemetry_df.height} rows, {telemetry_df.width} columns, "
        f"compression={compression})"
    )

    try:
        # Write Parquet with compression
        telemetry_df.write_parquet(artifact_path, compression=compression)

        # Log artifact size
        file_size = artifact_file.stat().st_size
        logger.info(
            f"Artifact persisted successfully: {artifact_path} "
            f"(size: {file_size / 1024:.2f} KB)"
        )

    except Exception as e:
        logger.error(f"Failed to persist artifact: {e}")
        raise IOError(f"Failed to write Parquet artifact to {artifact_path}: {e}")

    return artifact_path


def load_telemetry_artifact(artifact_path: str) -> pl.DataFrame:
    """
    Load telemetry artifact from Parquet file.

    Args:
        artifact_path: Path to Parquet artifact file

    Returns:
        DataFrame with loaded telemetry data

    Raises:
        FileNotFoundError: If artifact_path doesn't exist
        IOError: If read operation fails

    Examples:
        >>> df = load_telemetry_artifact('data/telemetry/daytona.parquet')
        >>> print(df.shape)
        (500, 10)
    """
    artifact_file = Path(artifact_path)

    # Validate file exists
    if not artifact_file.exists():
        raise FileNotFoundError(
            f"Telemetry artifact not found: {artifact_path}"
        )

    logger.info(f"Loading telemetry artifact: {artifact_path}")

    try:
        # Read Parquet
        telemetry_df = pl.read_parquet(artifact_path)

        logger.info(
            f"Artifact loaded successfully: {artifact_path} "
            f"({telemetry_df.height} rows, {telemetry_df.width} columns)"
        )

    except Exception as e:
        logger.error(f"Failed to load artifact: {e}")
        raise IOError(f"Failed to read Parquet artifact from {artifact_path}: {e}")

    return telemetry_df


def list_artifacts(artifacts_dir: str) -> List[Dict[str, any]]:
    """
    List all Parquet artifacts in directory with metadata.

    Args:
        artifacts_dir: Directory containing Parquet artifact files

    Returns:
        List of dictionaries with artifact metadata:
        - path: Full file path
        - name: Filename
        - size: File size in bytes
        - modified: Last modified timestamp

    Raises:
        FileNotFoundError: If artifacts_dir doesn't exist

    Examples:
        >>> artifacts = list_artifacts('data/telemetry/')
        >>> for artifact in artifacts:
        ...     print(f\"{artifact['name']}: {artifact['size']} bytes\")
    """
    artifacts_path = Path(artifacts_dir)

    # Validate directory exists
    if not artifacts_path.exists():
        raise FileNotFoundError(f"Artifacts directory not found: {artifacts_dir}")

    if not artifacts_path.is_dir():
        raise ValueError(f"Path is not a directory: {artifacts_dir}")

    logger.info(f"Listing artifacts in directory: {artifacts_dir}")

    artifacts = []

    # Find all .parquet files
    for parquet_file in artifacts_path.glob("*.parquet"):
        stat = parquet_file.stat()

        artifact_metadata = {
            "path": str(parquet_file.absolute()),
            "name": parquet_file.name,
            "size": stat.st_size,
            "modified": stat.st_mtime,
        }

        artifacts.append(artifact_metadata)

    logger.info(f"Found {len(artifacts)} Parquet artifacts")

    # Sort by modification time (newest first)
    artifacts.sort(key=lambda x: x["modified"], reverse=True)

    return artifacts


def validate_artifact_schema(
    telemetry_df: pl.DataFrame,
    required_columns: Optional[List[str]] = None
) -> bool:
    """
    Validate that telemetry artifact has expected schema.

    Args:
        telemetry_df: DataFrame to validate
        required_columns: Optional list of required column names

    Returns:
        True if schema is valid

    Raises:
        ValueError: If required columns are missing

    Examples:
        >>> df = pl.DataFrame({'driver_id': ['d1'], 'position': [10]})
        >>> validate_artifact_schema(df, required_columns=['driver_id', 'position'])
        True
    """
    if required_columns:
        missing = set(required_columns) - set(telemetry_df.columns)
        if missing:
            raise ValueError(
                f"Artifact missing required columns: {sorted(missing)}. "
                f"Has columns: {sorted(telemetry_df.columns)}"
            )

    logger.debug("Artifact schema validation passed")
    return True
