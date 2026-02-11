"""
Recent form estimator for NASCAR DFS ownership.

This module provides RecentFormEstimator, which estimates driver ownership
based on recent race performance (rolling ownership from last N races).
The model uses weighted averaging with configurable decay (exponential, linear, or none).

Key features:
- Rolling ownership from last N races
- Configurable decay (exponential, linear, none)
- Handles drivers with <N races using all available data
- Coverage statistics logging
- Fallback to overall mean for unseen drivers

Usage:
    estimator = RecentFormEstimator(n_recent_races=5, decay='exponential')
    estimator.fit(X_train, y_train)
    predictions = estimator.predict(X_test)
"""

import logging
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class RecentFormEstimator:
    """
    Estimate driver ownership based on recent form (rolling ownership).

    This estimator computes weighted average ownership percentages from
    the most recent N races for each driver. Uses configurable decay
    to give more weight to very recent races.

    The model handles:
    - Drivers with <N races: uses all available data
    - Unseen drivers: returns overall mean ownership
    - Missing track_archetype: ignored (not used in recent form)

    Decay options:
    - 'exponential': weight = decay_rate^i where i is races ago (0=most recent)
    - 'linear': weight decreases linearly with recency
    - 'none': equal weights for all recent races

    Attributes:
        n_recent_races_: Number of recent races to consider
        decay_: Decay type ('exponential', 'linear', 'none')
        decay_rate_: Decay rate (higher = less decay)
        recent_ownership_: Dict mapping driver_id to recent ownership
        overall_mean_: Overall mean ownership across all training data
        feature_names_in_: List of feature names seen during fit
        n_features_in_: Number of features seen during fit
        coverage_: Statistics on how many drivers have sufficient race history

    Example:
        >>> import pandas as pd
        >>> X = pd.DataFrame({
        ...     'driver_id': [1, 1, 1, 2, 2, 2],
        ...     'race_date': pd.to_datetime(['2024-01-01', '2024-01-15', '2024-02-01'] * 2),
        ...     'track_archetype': ['superspeedway'] * 6
        ... })
        >>> y = np.array([25.0, 23.0, 20.0, 15.0, 13.0, 10.0])
        >>> estimator = RecentFormEstimator(n_recent_races=3, decay='exponential')
        >>> estimator.fit(X, y)
        >>> predictions = estimator.predict(X)
    """

    def __init__(
        self,
        n_recent_races: int = 5,
        decay: str = 'exponential',
        decay_rate: float = 0.9
    ):
        """
        Initialize RecentFormEstimator.

        Args:
            n_recent_races: Number of recent races to consider (default: 5)
            decay: Decay type - 'exponential', 'linear', or 'none' (default: 'exponential')
            decay_rate: Decay rate for exponential decay (default: 0.9)
                       Higher = less decay, lower = more decay
                       Only used when decay='exponential'

        Raises:
            ValueError: If decay_type is not one of 'exponential', 'linear', 'none'
            ValueError: If n_recent_races < 1
            ValueError: If decay_rate not in (0, 1]
        """
        if n_recent_races < 1:
            raise ValueError(f"n_recent_races must be >= 1, got {n_recent_races}")

        if decay not in ['exponential', 'linear', 'none']:
            raise ValueError(
                f"decay must be 'exponential', 'linear', or 'none', got '{decay}'"
            )

        if not (0 < decay_rate <= 1):
            raise ValueError(f"decay_rate must be in (0, 1], got {decay_rate}")

        self.n_recent_races_ = n_recent_races
        self.decay_ = decay
        self.decay_rate_ = decay_rate

        # Model attributes
        self.recent_ownership_: Optional[Dict[Any, float]] = None
        self.overall_mean_: Optional[float] = None
        self.feature_names_in_: Optional[list] = None
        self.n_features_in_: Optional[int] = None
        self.coverage_: Optional[Dict[str, float]] = None

    def fit(self, X: pd.DataFrame, y: np.ndarray) -> 'RecentFormEstimator':
        """
        Fit recent form estimator using rolling ownership from recent races.

        Computes weighted average ownership for each driver based on their
        last N races. Uses exponential, linear, or no decay based on configuration.

        Args:
            X: Feature matrix with columns:
                - driver_id: Driver identifier (int or str)
                - race_date: Race date (datetime, for sorting by recency)
                - track_archetype: Track type (str, not used but logged for context)
            y: Target ownership percentages (0-100)

        Returns:
            self: Fitted estimator

        Raises:
            ValueError: If required columns are missing from X
            ValueError: If y contains invalid ownership values
        """
        # Validate inputs
        required_columns = ['driver_id', 'race_date']
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

        # Combine for processing
        ownership_data = X_work.copy()
        ownership_data['ownership'] = y_work

        # Ensure race_date is datetime
        if not pd.api.types.is_datetime64_any_dtype(ownership_data['race_date']):
            ownership_data['race_date'] = pd.to_datetime(ownership_data['race_date'])

        # Compute recent ownership for each driver
        self.recent_ownership_ = {}
        drivers_with_full_history = 0
        drivers_with_partial_history = 0

        for driver_id in ownership_data['driver_id'].unique():
            # Get driver's races sorted by date (most recent last)
            driver_data = ownership_data[
                ownership_data['driver_id'] == driver_id
            ].sort_values('race_date', ascending=True)

            # Take last N races
            recent_races = driver_data.tail(self.n_recent_races_)

            # Compute decay weights
            n_races = len(recent_races)
            if self.decay_ == 'exponential':
                # Weight = decay_rate^i where i=0 is most recent
                # Reverse so most recent gets highest weight
                weights = np.array([
                    self.decay_rate_ ** (n_races - 1 - i)
                    for i in range(n_races)
                ])
            elif self.decay_ == 'linear':
                # Weight decreases linearly: most recent = 1, oldest = 1/n
                weights = np.linspace(1 / n_races, 1, n_races)
            else:  # 'none'
                # Equal weights
                weights = np.ones(n_races)

            # Normalize weights
            weights = weights / weights.sum()

            # Compute weighted average ownership
            weighted_ownership = (recent_races['ownership'].values * weights).sum()

            self.recent_ownership_[driver_id] = float(weighted_ownership)

            # Track coverage
            if n_races == self.n_recent_races_:
                drivers_with_full_history += 1
            else:
                drivers_with_partial_history += 1

        # Compute overall mean (fallback for unseen drivers)
        self.overall_mean_ = y_work.mean()

        # Compute coverage statistics
        total_drivers = len(self.recent_ownership_)
        self.coverage_ = {
            'total_drivers': total_drivers,
            'full_history': drivers_with_full_history,
            'partial_history': drivers_with_partial_history,
            'full_history_pct': drivers_with_full_history / total_drivers if total_drivers > 0 else 0,
            'partial_history_pct': drivers_with_partial_history / total_drivers if total_drivers > 0 else 0
        }

        # Log diagnostics
        logger.info(
            f"Fitted RecentFormEstimator: "
            f"n_recent_races={self.n_recent_races_}, "
            f"decay={self.decay_}, "
            f"total_drivers={total_drivers}, "
            f"full_history={drivers_with_full_history} ({self.coverage_['full_history_pct']:.1%}), "
            f"partial_history={drivers_with_partial_history} ({self.coverage_['partial_history_pct']:.1%})"
        )

        logger.debug(
            f"Coverage: {drivers_with_full_history}/{total_drivers} drivers "
            f"have {self.n_recent_races_}+ races, "
            f"{drivers_with_partial_history}/{total_drivers} have <{self.n_recent_races_} races"
        )

        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict ownership percentages using recent form.

        Looks up recent ownership for each driver based on their
        last N races in the training data. Returns overall mean
        for unseen drivers.

        Args:
            X: Feature matrix with columns:
                - driver_id: Driver identifier
                - race_date: Race date (not used, kept for interface consistency)
                - track_archetype: Track type (not used)

        Returns:
            Array of ownership predictions (0-100)

        Raises:
            ValueError: If estimator has not been fitted
            ValueError: If required columns are missing from X
        """
        if self.recent_ownership_ is None:
            raise ValueError("Estimator has not been fitted yet. Call fit() first.")

        required_columns = ['driver_id']
        missing_columns = [col for col in required_columns if col not in X.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        # Initialize predictions with overall mean
        predictions = np.full(len(X), self.overall_mean_)

        # Look up recent ownership for each driver
        unseen_drivers = 0
        for idx, row in X.iterrows():
            driver_id = row['driver_id']

            if driver_id in self.recent_ownership_:
                predictions[idx] = self.recent_ownership_[driver_id]
            else:
                # Unseen driver - use overall mean (already initialized)
                unseen_drivers += 1

        if unseen_drivers > 0:
            logger.debug(
                f"{unseen_drivers} drivers not seen during training, "
                f"using overall mean ({self.overall_mean_:.2f}%)"
            )

        # Ensure predictions are in valid range
        predictions = np.clip(predictions, 0, 100)

        return predictions

    def get_recent_ownership(self, driver_id: Any) -> Optional[float]:
        """
        Get recent ownership for a specific driver.

        Args:
            driver_id: Driver identifier

        Returns:
            Recent ownership if driver seen, None otherwise
        """
        if self.recent_ownership_ is None:
            raise ValueError("Estimator has not been fitted yet.")

        return self.recent_ownership_.get(driver_id)

    def get_coverage_stats(self) -> Dict[str, float]:
        """
        Get coverage statistics from fitting.

        Returns:
            Dict with:
            - total_drivers: Total number of drivers
            - full_history: Drivers with N+ races
            - partial_history: Drivers with <N races
            - full_history_pct: Percentage with full history
            - partial_history_pct: Percentage with partial history
        """
        if self.coverage_ is None:
            raise ValueError("Estimator has not been fitted yet.")

        return self.coverage_.copy()
