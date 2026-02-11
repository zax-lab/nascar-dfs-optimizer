"""
Polars transformation module for telemetry data with rolling window features.

Computes aggregate features over rolling time windows (10l, 20l, 50l) for
driver performance metrics like position, laps led, and falloff rate.
"""

import polars as pl
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


def compute_aggregate_features(
    telemetry_df: pl.DataFrame,
    time_windows: List[str] = ["10l", "20l", "50l"]
) -> pl.DataFrame:
    """
    Compute rolling aggregate features over specified time windows.

    Calculates per-driver rolling aggregations for position, laps led, and
    other metrics. Features are computed over the last N laps to capture
    recent performance without leaking future information.

    Args:
        telemetry_df: DataFrame with lap-by-lap telemetry
        time_windows: List of time window sizes (e.g., ["10l", "20l", "50l"])

    Returns:
        DataFrame with original columns plus rolling aggregate features

    Raises:
        ValueError: If required columns missing or time_windows format invalid

    Examples:
        >>> df = pl.DataFrame({
        ...     'lap': [1, 2, 3, 4, 5],
        ...     'driver_id': ['driver_1'] * 5,
        ...     'position': [10, 9, 8, 12, 11],
        ...     'laps_led': [0, 2, 5, 5, 7]
        ... })
        >>> aggregated = compute_aggregate_features(df, ['3l'])
        >>> print(aggregated.columns)
        [..., 'avg_position_last_3l', 'best_position_last_3l', 'laps_led_last_3l']
    """
    # Validate required columns
    required_cols = {"lap", "driver_id"}
    missing = required_cols - set(telemetry_df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Validate time windows format
    for window in time_windows:
        if not window.endswith("l"):
            raise ValueError(
                f"Invalid time window format: '{window}'. "
                f"Time windows must end with 'l' (e.g., '10l', '20l')."
            )

    # Sort by lap to ensure temporal ordering
    telemetry_df = telemetry_df.sort("lap")
    logger.info(f"Computing aggregate features over time windows: {time_windows}")

    # Compute rolling features for each time window
    for window in time_windows:
        window_size = int(window.replace("l", ""))
        logger.debug(f"Computing rolling features for window: {window}")

        # Compute rolling position features if column exists
        if "position" in telemetry_df.columns:
            telemetry_df = telemetry_df.with_columns(
                pl.col("position")
                .rolling_mean(window_size=window_size, min_samples=1)
                .over("driver_id")
                .alias(f"avg_position_last_{window}")
            )
            telemetry_df = telemetry_df.with_columns(
                pl.col("position")
                .rolling_min(window_size=window_size, min_samples=1)
                .over("driver_id")
                .alias(f"best_position_last_{window}")
            )

        # Compute rolling laps led if column exists
        if "laps_led" in telemetry_df.columns:
            telemetry_df = telemetry_df.with_columns(
                pl.col("laps_led")
                .rolling_sum(window_size=window_size, min_samples=1)
                .over("driver_id")
                .alias(f"laps_led_last_{window}")
            )

    logger.info(f"Computed aggregate features. Columns: {telemetry_df.columns}")
    return telemetry_df


def rolling_statistics(
    telemetry_df: pl.DataFrame,
    metric: str,
    window: int
) -> pl.DataFrame:
    """
    Compute rolling mean, std, min, max for specified metric.

    Args:
        telemetry_df: DataFrame with lap-by-lap telemetry
        metric: Column name to compute rolling statistics for
        window: Rolling window size in laps

    Returns:
        DataFrame with rolling statistics columns

    Raises:
        ValueError: If metric column not found

    Examples:
        >>> df = pl.DataFrame({
        ...     'lap': [1, 2, 3, 4, 5],
        ...     'driver_id': ['driver_1'] * 5,
        ...     'lap_time': [48.5, 48.3, 48.7, 48.9, 48.6]
        ... })
        >>> rolling_stats = rolling_statistics(df, 'lap_time', 3)
        >>> print(rolling_stats.columns)
        [..., 'lap_time_mean_3', 'lap_time_std_3', 'lap_time_min_3', 'lap_time_max_3']
    """
    if metric not in telemetry_df.columns:
        raise ValueError(f"Metric column '{metric}' not found in DataFrame")

    logger.debug(f"Computing rolling statistics for {metric} over {window} laps")

    # Compute rolling statistics
    rolling_stats = telemetry_df.select(
        pl.col(metric)
        .rolling_mean(window_size=window, min_samples=1)
        .alias(f"{metric}_mean_{window}"),
        pl.col(metric)
        .rolling_std(window_size=window, min_samples=1)
        .alias(f"{metric}_std_{window}"),
        pl.col(metric)
        .rolling_min(window_size=window, min_samples=1)
        .alias(f"{metric}_min_{window}"),
        pl.col(metric)
        .rolling_max(window_size=window, min_samples=1)
        .alias(f"{metric}_max_{window}"),
    )

    # Concatenate with original DataFrame
    result = pl.concat([telemetry_df, rolling_stats], how="horizontal")

    return result


def compute_falloff_metrics(telemetry_df: pl.DataFrame) -> pl.DataFrame:
    """
    Compute tire falloff metrics from lap time degradation.

    Identifies slow laps (lap time > rolling_mean + 2*rolling_std) which
    indicate tire degradation or fuel load effects.

    Args:
        telemetry_df: DataFrame with lap-by-lap telemetry

    Returns:
        DataFrame with falloff indicators

    Examples:
        >>> df = pl.DataFrame({
        ...     'lap': [1, 2, 3, 4, 5],
        ...     'driver_id': ['driver_1'] * 5,
        ...     'lap_time': [48.5, 48.3, 49.2, 49.8, 50.1]
        ... })
        >>> falloff = compute_falloff_metrics(df)
        >>> 'is_slow_lap' in falloff.columns
        True
    """
    if "lap_time" not in telemetry_df.columns:
        logger.warning("lap_time column not found, skipping falloff metrics")
        return telemetry_df

    logger.debug("Computing tire falloff metrics")

    # Compute lap time degradation (difference from previous lap)
    telemetry_df = telemetry_df.with_columns(
        pl.col("lap_time")
        .diff()
        .alias("lap_time_delta")
    )

    # Compute rolling mean and std for lap time
    telemetry_df = rolling_statistics(telemetry_df, "lap_time", window=5)

    # Identify slow laps (lap time > mean + 2*std)
    telemetry_df = telemetry_df.with_columns(
        pl.when(
            pl.col("lap_time") > (pl.col("lap_time_mean_5") + 2 * pl.col("lap_time_std_5"))
        )
        .then(True)
        .otherwise(False)
        .alias("is_slow_lap")
    )

    logger.debug(f"Computed falloff metrics. Slow laps: {telemetry_df['is_slow_lap'].sum()}")

    return telemetry_df


def handle_missing_data(telemetry_df: pl.DataFrame) -> pl.DataFrame:
    """
    Handle missing data in telemetry DataFrame with forward-fill and mean interpolation.

    Args:
        telemetry_df: DataFrame with potential missing values

    Returns:
        DataFrame with missing values filled

    Examples:
        >>> df = pl.DataFrame({
        ...     'lap': [1, 2, 3],
        ...     'driver_id': ['driver_1'] * 3,
        ...     'position': [10.0, None, 8.0]
        ... })
        >>> cleaned = handle_missing_data(df)
        >>> print(cleaned['position'].to_list())
        [10.0, 10.0, 8.0]
    """
    null_counts = telemetry_df.null_count().row(0)
    total_nulls = sum(null_counts)

    if total_nulls == 0:
        logger.debug("No missing data found")
        return telemetry_df

    logger.info(f"Handling {total_nulls} missing values across {len(telemetry_df.columns)} columns")

    # Forward-fill missing values (propagate last valid observation)
    telemetry_df = telemetry_df.fill_null(strategy="forward")

    # Fill remaining nulls with mean for numeric columns
    for col in telemetry_df.columns:
        if telemetry_df[col].dtype in [pl.Float64, pl.Float32]:
            # Fill remaining nulls with column mean
            col_mean = telemetry_df[col].mean()
            telemetry_df = telemetry_df.with_columns(
                pl.col(col).fill_null(col_mean)
            )
        elif telemetry_df[col].dtype in [pl.Int64, pl.Int32]:
            # Fill integer nulls with 0
            telemetry_df = telemetry_df.with_columns(
                pl.col(col).fill_null(0)
            )

    # Verify no nulls remain
    remaining_nulls = telemetry_df.null_count().row(0)
    if sum(remaining_nulls) > 0:
        logger.warning(f"{sum(remaining_nulls)} null values remain after filling")

    return telemetry_df
