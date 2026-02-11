"""
Historical ownership estimator for NASCAR DFS.

This module provides HistoricalOwnershipEstimator, which estimates driver
ownership based on historical track-archetype specific baselines. The model
learns average ownership by (driver_id, track_archetype) pairs from historical
data and provides fallback to overall mean for unseen combinations.

Key features:
- Track-archetype specific ownership baselines (superspeedway, intermediate, short_track, road_course)
- Graceful handling of unseen drivers and track types
- Efficient pandas groupby aggregation
- Logging for diagnostics

Usage:
    estimator = HistoricalOwnershipEstimator()
    estimator.fit(X_train, y_train)
    predictions = estimator.predict(X_test)
"""

import logging
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class HistoricalOwnershipEstimator:
    """
    Estimate driver ownership based on historical track-archetype specific baselines.

    This estimator learns average ownership percentages for each (driver_id, track_archetype)
    combination from historical data. It provides fallback mechanisms for:
    - Unseen drivers: returns overall mean ownership
    - Driver seen but not at this track: returns driver's overall mean
    - Missing track_archetype: uses overall mean fallback

    The model uses pandas groupby for efficient aggregation and stores learned
    ownership patterns in pandas Series for fast lookup.

    Attributes:
        historical_ownership_: DataFrame with mean ownership by (driver_id, track_archetype)
        driver_mean_ownership_: Series with mean ownership by driver_id
        overall_mean_: Overall mean ownership across all training data
        feature_names_in_: List of feature names seen during fit
        n_features_in_: Number of features seen during fit

    Example:
        >>> import pandas as pd
        >>> X = pd.DataFrame({
        ...     'driver_id': [1, 1, 2, 2, 3],
        ...     'track_archetype': ['superspeedway', 'superspeedway', 'superspeedway', 'short_track', 'superspeedway'],
        ...     'race_date': pd.date_range('2024-01-01', periods=5)
        ... })
        >>> y = np.array([25.0, 23.0, 15.0, 8.0, 5.0])
        >>> estimator = HistoricalOwnershipEstimator()
        >>> estimator.fit(X, y)
        >>> predictions = estimator.predict(X)
    """

    def __init__(self):
        """Initialize HistoricalOwnershipEstimator."""
        self.historical_ownership_: Optional[pd.DataFrame] = None
        self.driver_mean_ownership_: Optional[pd.Series] = None
        self.overall_mean_: Optional[float] = None
        self.feature_names_in_: Optional[list] = None
        self.n_features_in_: Optional[int] = None
        self.track_archetypes_seen_: Optional[set] = None
        self.drivers_seen_: Optional[set] = None

    def fit(self, X: pd.DataFrame, y: np.ndarray) -> 'HistoricalOwnershipEstimator':
        """
        Fit historical ownership estimator using track-archetype specific baselines.

        Learns mean ownership percentages for each (driver_id, track_archetype)
        combination from historical data. Computes fallback statistics for
        graceful handling of unseen combinations.

        Args:
            X: Feature matrix with columns:
                - driver_id: Driver identifier (int or str)
                - track_archetype: Track type (str): 'superspeedway', 'intermediate',
                  'short_track', 'road_course', or None
                - race_date: Race date (datetime, not used but logged for context)
            y: Target ownership percentages (0-100)

        Returns:
            self: Fitted estimator

        Raises:
            ValueError: If required columns are missing from X
            ValueError: If y contains invalid ownership values
        """
        # Validate inputs
        required_columns = ['driver_id', 'track_archetype']
        missing_columns = [col for col in required_columns if col not in X.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        if len(X) != len(y):
            raise ValueError(f"X and y must have same length: {len(X)} != {len(y)}")

        if not np.all((y >= 0) & (y <= 100)):
            raise ValueError("Ownership percentages must be in range [0, 100]")

        # Store feature information for scikit-learn compatibility
        self.feature_names_in_ = list(X.columns)
        self.n_features_in_ = X.shape[1]

        # Create working copy
        X_work = X.copy()
        y_work = pd.Series(y, index=X_work.index)

        # Handle missing track_archetype
        has_missing_track = X_work['track_archetype'].isna().any()
        if has_missing_track:
            logger.warning(
                f"{X_work['track_archetype'].isna().sum()} samples have missing track_archetype, "
                "using overall mean for these samples"
            )
            # Mark missing for special handling
            X_work['_missing_track'] = X_work['track_archetype'].isna()
            # Fill with placeholder for groupby
            X_work['track_archetype'] = X_work['track_archetype'].fillna('UNKNOWN')

        # Compute historical mean ownership by (driver_id, track_archetype)
        ownership_data = X_work.copy()
        ownership_data['ownership'] = y_work

        self.historical_ownership_ = ownership_data.groupby(
            ['driver_id', 'track_archetype']
        )['ownership'].mean().reset_index()
        self.historical_ownership_ = self.historical_ownership_.pivot(
            index='driver_id',
            columns='track_archetype',
            values='ownership'
        )

        # Compute driver mean ownership (fallback for unseen track)
        self.driver_mean_ownership_ = ownership_data.groupby('driver_id')['ownership'].mean()

        # Compute overall mean ownership (fallback for unseen driver)
        self.overall_mean_ = y_work.mean()

        # Store seen drivers and tracks for diagnostics
        self.drivers_seen_ = set(self.driver_mean_ownership_.index)
        self.track_archetypes_seen_ = set(ownership_data['track_archetype'].unique())
        if 'UNKNOWN' in self.track_archetypes_seen_:
            self.track_archetypes_seen_.remove('UNKNOWN')

        # Log diagnostics
        n_driver_track_combos = len(self.historical_ownership_)
        n_drivers = len(self.drivers_seen_)
        n_tracks = len(self.track_archetypes_seen_)

        logger.info(
            f"Fitted HistoricalOwnershipEstimator: "
            f"{n_drivers} drivers, {n_tracks} track archetypes, "
            f"{n_driver_track_combos} driver-track combinations"
        )

        # Log coverage by track type
        for track in self.track_archetypes_seen_:
            track_data = ownership_data[ownership_data['track_archetype'] == track]
            avg_ownership = track_data['ownership'].mean()
            logger.debug(
                f"Track archetype '{track}': {len(track_data)} samples, "
                f"avg ownership {avg_ownership:.2f}%"
            )

        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict ownership percentages using historical baselines.

        For each driver-track combination, returns:
        1. Historical mean for that specific driver-track pair (if seen)
        2. Driver's overall mean if driver seen but not at this track
        3. Overall mean if driver not seen before

        Args:
            X: Feature matrix with columns:
                - driver_id: Driver identifier
                - track_archetype: Track type (can be None)

        Returns:
            Array of ownership predictions (0-100)

        Raises:
            ValueError: If estimator has not been fitted
            ValueError: If required columns are missing from X
        """
        if self.historical_ownership_ is None:
            raise ValueError("Estimator has not been fitted yet. Call fit() first.")

        required_columns = ['driver_id', 'track_archetype']
        missing_columns = [col for col in required_columns if col not in X.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        # Create working copy
        X_work = X.copy()

        # Handle missing track_archetype
        has_missing_track = X_work['track_archetype'].isna().any()
        if has_missing_track:
            X_work['track_archetype'] = X_work['track_archetype'].fillna('UNKNOWN')

        # Initialize predictions with overall mean
        predictions = np.full(len(X_work), self.overall_mean_)

        # For each row, apply lookup logic
        for idx, row in X_work.iterrows():
            driver_id = row['driver_id']
            track_archetype = row['track_archetype']

            # Case 1: Driver seen before
            if driver_id in self.drivers_seen_:
                # Case 1a: Driver-track combination seen
                if driver_id in self.historical_ownership_.index:
                    if track_archetype in self.historical_ownership_.columns:
                        ownership = self.historical_ownership_.loc[driver_id, track_archetype]
                        if pd.notna(ownership):
                            predictions[idx] = ownership
                            continue

                # Case 1b: Driver seen but not at this track
                if driver_id in self.driver_mean_ownership_.index:
                    predictions[idx] = self.driver_mean_ownership_.loc[driver_id]
                    continue

            # Case 2: Unseen driver - use overall mean (already initialized)

        # Ensure predictions are in valid range
        predictions = np.clip(predictions, 0, 100)

        return predictions

    def get_driver_track_ownership(self, driver_id: Any, track_archetype: str) -> Optional[float]:
        """
        Get historical ownership for a specific driver-track combination.

        Args:
            driver_id: Driver identifier
            track_archetype: Track type

        Returns:
            Historical ownership if available, None otherwise
        """
        if self.historical_ownership_ is None:
            raise ValueError("Estimator has not been fitted yet.")

        if driver_id in self.historical_ownership_.index:
            if track_archetype in self.historical_ownership_.columns:
                ownership = self.historical_ownership_.loc[driver_id, track_archetype]
                return float(ownership) if pd.notna(ownership) else None

        return None

    def get_driver_mean_ownership(self, driver_id: Any) -> Optional[float]:
        """
        Get mean ownership for a driver across all track types.

        Args:
            driver_id: Driver identifier

        Returns:
            Mean ownership if driver seen, None otherwise
        """
        if self.driver_mean_ownership_ is None:
            raise ValueError("Estimator has not been fitted yet.")

        if driver_id in self.driver_mean_ownership_.index:
            return float(self.driver_mean_ownership_.loc[driver_id])

        return None
