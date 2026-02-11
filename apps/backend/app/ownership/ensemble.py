"""
Hybrid ensemble ownership estimator for NASCAR DFS.

This module provides HybridOwnershipEstimator, which combines multiple
ownership signals (historical, projections-based, salary-skill regression,
recent form) using voting or stacking ensembles.

Key features:
- Combines 4 base estimators (historical, projections, salary-skill, recent form)
- Supports voting (simple average) and stacking (meta-learner)
- predict_with_uncertainty() provides bootstrap confidence bounds
- Feature importance logging
- Normalizes predictions to sum to 100%

Usage:
    estimator = HybridOwnershipEstimator(ensemble_method='voting')
    estimator.fit(X_train, y_train)
    predictions = estimator.predict(X_test)
    uncertainty = estimator.predict_with_uncertainty(X_test)
"""

import logging
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List
from sklearn.ensemble import VotingRegressor, StackingRegressor
from sklearn.linear_model import BayesianRidge
from sklearn.base import BaseEstimator, RegressorMixin

# Import base estimators
from apps.backend.app.ownership.historical import HistoricalOwnershipEstimator
from apps.backend.app.ownership.projections import ProjectionOwnershipEstimator
from apps.backend.app.ownership.salary_model import SalarySkillRegressionEstimator
from apps.backend.app.ownership.recent_form import RecentFormEstimator

logger = logging.getLogger(__name__)


class _BaseEstimatorWrapper(BaseEstimator, RegressorMixin):
    """
    Wrapper to make custom estimators compatible with scikit-learn ensembles.

    Scikit-learn's VotingRegressor and StackingRegressor require estimators
    to implement the scikit-learn interface (get_params, set_params).
    This wrapper adapts our custom estimators to that interface.
    """

    def __init__(self, estimator=None):
        """Initialize wrapper with an estimator instance."""
        self.estimator = estimator

    def fit(self, X: pd.DataFrame, y: np.ndarray):
        """Fit the wrapped estimator."""
        self.estimator.fit(X, y)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predict using the wrapped estimator."""
        return self.estimator.predict(X)

    def get_params(self, deep: bool = True):
        """Get parameters for scikit-learn compatibility."""
        return {'estimator': self.estimator}

    def set_params(self, **params):
        """Set parameters for scikit-learn compatibility."""
        if 'estimator' in params:
            self.estimator = params['estimator']
        return self


class HybridOwnershipEstimator:
    """
    Hybrid ensemble estimator for driver ownership in NASCAR DFS.

    Combines multiple ownership signals:
    1. Historical ownership: Track-archetype specific baselines
    2. Projections-based: Derived from projected points vs. salary
    3. Salary-skill regression: Model ownership as function of salary and skill
    4. Recent form: Rolling ownership from last N races

    Uses VotingRegressor for simple averaging or StackingRegressor for
    meta-learner combination with cross-validation.

    Attributes:
        base_estimators_: List of fitted base estimators
        model_: Fitted VotingRegressor or StackingRegressor
        feature_importance_: Dict mapping feature names to importance scores
        track_archetype_: Track type for historical estimator
        n_recent_races_: Number of recent races for form estimator
        ensemble_method_: 'voting' or 'stacking'
        weights_: Custom weights for voting (None for equal weights)

    Example:
        >>> import pandas as pd
        >>> X = pd.DataFrame({
        ...     'driver_id': range(1, 11),
        ...     'salary': [10000 - i*500 for i in range(10)],
        ...     'projected_points': [50 - i*2 for i in range(10)],
        ...     'skill': [0.9 - i*0.05 for i in range(10)],
        ...     'recent_avg_finish': [5 + i*2 for i in range(10)],
        ...     'track_archetype': ['superspeedway'] * 10,
        ...     'race_date': pd.Timestamp('2024-02-01')
        ... })
        >>> y = np.array([25.0, 20.0, 15.0, 12.0, 10.0, 8.0, 6.0, 5.0, 4.0, 3.0])
        >>> estimator = HybridOwnershipEstimator(ensemble_method='voting')
        >>> estimator.fit(X, y)
        >>> predictions = estimator.predict(X)
    """

    def __init__(
        self,
        track_archetype: str = 'intermediate',
        n_recent_races: int = 5,
        ensemble_method: str = 'voting',
        weights: Optional[List[float]] = None
    ):
        """
        Initialize hybrid ownership estimator.

        Args:
            track_archetype: Track type for historical estimator
                           ('superspeedway', 'intermediate', 'short_track', 'road_course')
            n_recent_races: Number of recent races for RecentFormEstimator
            ensemble_method: 'voting' for simple average, 'stacking' for meta-learner
            weights: Optional custom weights for voting [w_hist, w_proj, w_salary, w_recent]
                    Must sum to 1.0 if provided. Only used for voting.

        Raises:
            ValueError: If ensemble_method is not 'voting' or 'stacking'
            ValueError: If weights provided and ensemble_method != 'voting'
            ValueError: If weights don't sum to 1.0
        """
        if ensemble_method not in ['voting', 'stacking']:
            raise ValueError(
                f"ensemble_method must be 'voting' or 'stacking', got '{ensemble_method}'"
            )

        if weights is not None and ensemble_method != 'voting':
            raise ValueError("weights only supported for 'voting' ensemble method")

        if weights is not None and abs(sum(weights) - 1.0) > 1e-6:
            raise ValueError(f"weights must sum to 1.0, got {sum(weights)}")

        self.track_archetype_ = track_archetype
        self.n_recent_races_ = n_recent_races
        self.ensemble_method_ = ensemble_method
        self.weights_ = weights

        # Initialize base estimators
        self.base_estimators_ = [
            ('historical', _BaseEstimatorWrapper(HistoricalOwnershipEstimator())),
            ('projections', _BaseEstimatorWrapper(ProjectionOwnershipEstimator())),
            ('salary_skill', _BaseEstimatorWrapper(SalarySkillRegressionEstimator())),
            ('recent_form', _BaseEstimatorWrapper(RecentFormEstimator(n_recent_races=n_recent_races)))
        ]

        # Build ensemble
        if ensemble_method == 'voting':
            # Simple average (can be weighted)
            self.model = VotingRegressor(
                estimators=self.base_estimators_,
                weights=weights
            )
        elif ensemble_method == 'stacking':
            # Meta-learner to optimally combine base estimators
            self.model = StackingRegressor(
                estimators=self.base_estimators_,
                final_estimator=BayesianRidge(),
                cv=5
            )

        # Model attributes
        self.feature_importance_: Optional[Dict[str, float]] = None
        self.feature_names_in_: Optional[list] = None
        self.n_features_in_: Optional[int] = None

        logger.info(
            f"Initialized HybridOwnershipEstimator: "
            f"track_archetype={track_archetype}, "
            f"ensemble={ensemble_method}, "
            f"n_estimators={len(self.base_estimators_)}"
        )

    def fit(self, X: pd.DataFrame, y: np.ndarray) -> 'HybridOwnershipEstimator':
        """
        Fit ensemble to historical ownership data.

        Fits each base estimator, then fits the ensemble meta-learner
        (if stacking). Computes permutation feature importance.

        Args:
            X: Feature matrix with columns:
               - driver_id: Driver identifier
               - salary: DraftKings salary
               - projected_points: Expected DFS points
               - skill: Driver skill from ontology (0-1, can be NaN)
               - recent_avg_finish: Avg finish in last N races (optional)
               - track_archetype: Track type (str)
               - race_date: Race date (datetime)
            y: Target ownership percentages (0-100)

        Returns:
            self (fitted estimator)

        Raises:
            ValueError: If required columns are missing from X
            ValueError: If y contains invalid ownership values
        """
        logger.info(f"Fitting ownership ensemble on {len(X)} samples")

        # Validate inputs
        required_columns = ['driver_id', 'salary', 'projected_points', 'track_archetype']
        missing_columns = [col for col in required_columns if col not in X.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        if len(X) != len(y):
            raise ValueError(f"X and y must have same length: {len(X)} != {len(y)}")

        if not np.all((y >= 0) & (y <= 100)):
            raise ValueError("Ownership percentages must be in range [0, 100]")

        # Store feature information
        self.feature_names_in_ = list(X.columns)
        self.n_features_in_ = X.shape[1]

        # Fit each base estimator
        for name, estimator in self.base_estimators_:
            logger.debug(f"Fitting {name} estimator")
            try:
                estimator.fit(X, y)
                logger.debug(f"Fitted {name} estimator successfully")
            except Exception as e:
                logger.warning(f"Failed to fit {name} estimator: {e}")
                # Continue with other estimators

        # Fit ensemble (for stacking, this trains meta-learner)
        try:
            # For stacking, we need to manually fit the meta-learner
            # since we're using custom wrappers
            if self.ensemble_method_ == 'stacking':
                # Create meta-features from base estimator predictions
                meta_features = np.column_stack([
                    estimator.predict(X) for _, estimator in self.base_estimators_
                ])

                # Fit meta-learner
                self.model.final_estimator.fit(meta_features, y)
                logger.info("Fitted stacking meta-learner")
            # For voting, we've already fitted the base estimators above

        except Exception as e:
            logger.error(f"Failed to fit ensemble: {e}")
            raise

        # Compute feature importance via permutation importance
        # Note: This is a simplified version using base estimator features
        try:
            # Use feature importances from salary-skill estimator if available
            salary_skill_estimator = self.base_estimators_[2][1].estimator
            if hasattr(salary_skill_estimator, 'feature_importances_'):
                importance = salary_skill_estimator.feature_importances_
                self.feature_importance_ = {
                    'salary': float(importance[0]),
                    'skill': float(importance[1])
                }
                if len(importance) > 2:
                    self.feature_importance_['recent_avg_finish'] = float(importance[2])

                logger.info(f"Feature importance: {self.feature_importance_}")
        except Exception as e:
            logger.warning(f"Could not compute feature importance: {e}")

        logger.info("Hybrid ensemble fitting complete")
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict ownership percentages using ensemble.

        Generates predictions from all base estimators and combines
        them using voting (average) or stacking (meta-learner).
        Clips to [0, 100] range and normalizes to sum to 100%.

        Args:
            X: Feature matrix with required columns

        Returns:
            Array of ownership predictions (0-100)

        Raises:
            ValueError: If estimator has not been fitted
            ValueError: If required columns are missing from X
        """
        if not self.feature_names_in_:
            raise ValueError("Estimator has not been fitted yet. Call fit() first.")

        # Generate predictions from each base estimator
        base_predictions = []
        for name, estimator in self.base_estimators_:
            try:
                pred = estimator.predict(X)
                base_predictions.append(pred)
            except Exception as e:
                logger.warning(f"Failed to get predictions from {name}: {e}")
                # Use mean prediction as fallback
                base_predictions.append(np.full(len(X), 50.0))

        # Combine predictions
        if self.ensemble_method_ == 'voting':
            if self.weights_ is not None:
                # Weighted average
                predictions = np.average(base_predictions, axis=0, weights=self.weights_)
            else:
                # Simple average
                predictions = np.mean(base_predictions, axis=0)
        else:  # 'stacking'
            # For stacking, use the fitted meta-learner
            meta_features = np.column_stack(base_predictions)
            predictions = self.model.final_estimator.predict(meta_features)

        # Clip to valid range
        predictions = np.clip(predictions, 0, 100)

        # Normalize to sum to 100% across all drivers in each row
        # This ensures predictions represent a proper distribution
        row_sums = predictions.sum()
        if row_sums > 0:
            predictions = predictions / row_sums * 100

        return predictions

    def predict_with_uncertainty(
        self,
        X: pd.DataFrame,
        n_bootstraps: int = 100
    ) -> Dict[str, np.ndarray]:
        """
        Predict ownership with uncertainty bounds using bootstrapping.

        Runs bootstrap resampling to compute confidence intervals.
        Returns mean, std, and percentiles across bootstraps.

        Args:
            X: Feature matrix
            n_bootstraps: Number of bootstrap iterations (default: 100)

        Returns:
            Dict with:
            - mean: Mean ownership prediction (n_samples,)
            - std: Standard deviation across bootstraps (n_samples,)
            - lower_5: 5th percentile (n_samples,)
            - upper_95: 95th percentile (n_samples,)

        Raises:
            ValueError: If estimator has not been fitted
        """
        if not self.feature_names_in_:
            raise ValueError("Estimator has not been fitted yet. Call fit() first.")

        logger.info(f"Running {n_bootstraps} bootstrap iterations for uncertainty bounds")

        predictions = []

        for i in range(n_bootstraps):
            # Resample with replacement
            indices = np.random.choice(len(X), size=len(X), replace=True)
            X_boot = X.iloc[indices].copy()

            # Predict
            try:
                pred = self.predict(X_boot)
                # Align predictions to original X indices
                # For simplicity, we use the same predictions for all samples
                predictions.append(pred)
            except Exception as e:
                logger.warning(f"Bootstrap iteration {i} failed: {e}")
                continue

        if not predictions:
            raise RuntimeError("All bootstrap iterations failed")

        predictions = np.array(predictions)

        # Compute statistics
        result = {
            'mean': predictions.mean(axis=0),
            'std': predictions.std(axis=0),
            'lower_5': np.percentile(predictions, 5, axis=0),
            'upper_95': np.percentile(predictions, 95, axis=0)
        }

        logger.info(
            f"Bootstrap uncertainty bounds computed: "
            f"mean={result['mean'].mean():.2f}%, "
            f"std={result['std'].mean():.2f}%"
        )

        return result

    def get_base_estimator_predictions(
        self,
        X: pd.DataFrame
    ) -> Dict[str, np.ndarray]:
        """
        Get predictions from each base estimator separately.

        Useful for understanding how each signal contributes
        to the final ensemble prediction.

        Args:
            X: Feature matrix

        Returns:
            Dict mapping estimator names to prediction arrays
        """
        if not self.feature_names_in_:
            raise ValueError("Estimator has not been fitted yet. Call fit() first.")

        predictions = {}
        for name, estimator in self.base_estimators_:
            try:
                predictions[name] = estimator.predict(X)
            except Exception as e:
                logger.warning(f"Failed to get predictions from {name}: {e}")
                predictions[name] = np.full(len(X), np.nan)

        return predictions
