"""
Telemetry ingestion module using Polars lazy API for efficient Parquet scanning.

Provides lap-by-lap telemetry ingestion with feature availability validation
to prevent data leakage from future race information.
"""

import polars as pl
from typing import List, Optional
from pathlib import Path
import logging

from app.telemetry.features import FeatureAvailabilityContract

logger = logging.getLogger(__name__)


class TelemetryIngestor:
    """
    Ingests lap-by-lap telemetry from Parquet files using Polars lazy evaluation.

    Uses lazy scanning (pl.scan_parquet) for efficient processing of large files,
    with feature availability validation to prevent data leakage.
    """

    # Required metadata columns that must be present in Parquet files
    REQUIRED_METADATA_COLUMNS = {"lap", "driver_id", "timestamp", "track_id"}

    def __init__(
        self,
        feature_contract: Optional[FeatureAvailabilityContract] = None
    ):
        """
        Initialize telemetry ingestor with feature availability contract.

        Args:
            feature_contract: Contract for validating feature availability.
                            If None, creates default FeatureAvailabilityContract.
        """
        self.feature_contract = feature_contract or FeatureAvailabilityContract()
        logger.info("TelemetryIngestor initialized with feature availability contract")

    def ingest_parquet(
        self,
        parquet_path: str,
        driver_ids: List[str]
    ) -> pl.DataFrame:
        """
        Ingest lap-by-lap telemetry from Parquet file using lazy scan.

        Args:
            parquet_path: Path to Parquet file containing telemetry data
            driver_ids: List of driver IDs to filter data for

        Returns:
            Polars DataFrame with lap-by-lap telemetry for requested drivers

        Raises:
            FileNotFoundError: If parquet_path doesn't exist
            ValueError: If required metadata columns missing or forbidden features present

        Examples:
            >>> ingestor = TelemetryIngestor()
            >>> telemetry = ingestor.ingest_parquet('data/telemetry/daytona.parquet', ['driver_1', 'driver_2'])
            >>> print(telemetry.shape)
            (500, 10)
        """
        # Validate file exists
        if not Path(parquet_path).exists():
            raise FileNotFoundError(f"Parquet file not found: {parquet_path}")

        logger.info(f"Ingesting telemetry from {parquet_path} for {len(driver_ids)} drivers")

        # Use lazy scan for efficient evaluation
        lazy_df = pl.scan_parquet(parquet_path)

        # Validate schema columns against feature availability contract
        schema_columns = lazy_df.collect_schema().names()
        self._validate_schema(schema_columns)

        # Validate feature availability (check for forbidden features)
        self.feature_contract.validate_dataframe(schema_columns)

        # Filter to requested drivers
        lazy_df = lazy_df.filter(pl.col("driver_id").is_in(driver_ids))

        # Get allowed features (filter out forbidden race telemetry)
        allowed_features = self.feature_contract.get_allowed_features(schema_columns)

        # Always include metadata columns
        metadata_cols = list(self.REQUIRED_METADATA_COLUMNS & set(schema_columns))
        selected_columns = metadata_cols + [col for col in allowed_features if col not in metadata_cols]

        # Select only allowed columns
        lazy_df = lazy_df.select(selected_columns)

        # Execute lazy query
        telemetry_df = lazy_df.collect()

        # Handle missing data
        telemetry_df = self._handle_missing_data(telemetry_df)

        record_count = telemetry_df.height
        logger.info(f"Ingested {record_count} telemetry records from {parquet_path}")

        # Warn if no data found for requested drivers
        if record_count == 0:
            logger.warning(
                f"No telemetry data found for requested drivers: {driver_ids}. "
                f"Check driver_ids match data in Parquet file."
            )

        return telemetry_df

    def _validate_schema(self, columns: List[str]) -> None:
        """
        Validate that required metadata columns are present in schema.

        Args:
            columns: List of column names from Parquet schema

        Raises:
            ValueError: If required metadata columns are missing
        """
        missing = self.REQUIRED_METADATA_COLUMNS - set(columns)
        if missing:
            raise ValueError(
                f"Missing required metadata columns: {sorted(missing)}. "
                f"Parquet file must contain: {sorted(self.REQUIRED_METADATA_COLUMNS)}"
            )

    def _handle_missing_data(self, telemetry_df: pl.DataFrame) -> pl.DataFrame:
        """
        Handle missing data in telemetry DataFrame.

        Args:
            telemetry_df: DataFrame with potential missing values

        Returns:
            DataFrame with missing values filled
        """
        # Forward-fill missing lap times (common for intermittent sensors)
        if "lap_time" in telemetry_df.columns:
            telemetry_df = telemetry_df.with_columns(
                pl.col("lap_time").fill_null(strategy="forward")
            )

        # Fill missing numeric metrics with 0
        numeric_cols = [
            col for col in telemetry_df.columns
            if telemetry_df[col].dtype in [pl.Float64, pl.Float32, pl.Int64, pl.Int32]
        ]
        for col in numeric_cols:
            telemetry_df = telemetry_df.with_columns(
                pl.col(col).fill_null(0)
            )

        return telemetry_df


def ingest_lap_by_lap_telemetry(
    parquet_path: str,
    driver_ids: List[str],
    feature_contract: Optional[FeatureAvailabilityContract] = None
) -> pl.DataFrame:
    """
    Standalone function to ingest lap-by-lap telemetry from Parquet file.

    Convenience function that creates TelemetryIngestor and calls ingest_parquet.

    Args:
        parquet_path: Path to Parquet file containing telemetry data
        driver_ids: List of driver IDs to filter data for
        feature_contract: Optional feature availability contract

    Returns:
        Polars DataFrame with lap-by-lap telemetry for requested drivers

    Examples:
        >>> telemetry = ingest_lap_by_lap_telemetry(
        ...     'data/telemetry/daytona.parquet',
        ...     ['driver_1', 'driver_2']
        ... )
        >>> print(telemetry.head())
    """
    ingestor = TelemetryIngestor(feature_contract=feature_contract)
    return ingestor.ingest_parquet(parquet_path, driver_ids)
