"""
Projections-based ownership estimator for NASCAR DFS.

This module provides ProjectionOwnershipEstimator, which estimates driver
ownership based on the relationship between value_score (projected_points / salary)
and historical ownership percentages. The model learns a linear relationship
where higher value scores generally correlate with higher ownership.

Key features:
- Linear regression: ownership ~ value_score
- Interpretable slope parameter
- R² logging for regression quality
- Handles zero/negative salary with filtering
- Clips predictions to [0, 100] range

Usage:
    estimator = ProjectionOwnershipEstimator()
    estimator.fit(X_train, y_train)
    predictions = estimator.predict(X_test)
    print(f"Value score slope: {estimator.value_score_slope_:.4f}")
"""

import logging
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

logger = logging.getLogger(__name__)


class ProjectionOwnershipEstimator:
    """
    Estimate driver ownership based on projected points vs. salary ratio.

    This estimator learns the relationship between value_score (projected_points / salary)
    and ownership percentages using linear regression. The intuition is that DFS players
    generally favor drivers with high projected points relative to salary (good value).

    The model handles edge cases:
    - Zero or negative salary: filtered out during training with warning
    - Missing projections: handled via imputation in feature engineering
    - Predictions clipped to [0, 100] range

    Attributes:
        model_: Fitted LinearRegression model
        value_score_slope_: Slope coefficient relating value_score to ownership
        r2_score_: R² score of the regression (goodness of fit)
        feature_names_in_: List of feature names seen during fit
        n_features_in_: Number of features seen during fit
        filtered_samples_: Number of samples filtered due to invalid salary

    Example:
        >>> import pandas as pd
        >>> X = pd.DataFrame({
        ...     'projected_points': [50, 45, 40, 35, 30],
        ...     'salary': [10000, 9000, 8000, 7000, 6000]
        ... })
        >>> y = np.array([25.0, 20.0, 15.0, 10.0, 5.0])
        >>> estimator = ProjectionOwnershipEstimator()
        >>> estimator.fit(X, y)
        >>> predictions = estimator.predict(X)
        >>> print(f"Value score slope: {estimator.value_score_slope_:.4f}")
    """

    def __init__(self):
        """Initialize ProjectionOwnershipEstimator."""
        self.model_: Optional[LinearRegression] = None
        self.value_score_slope_: Optional[float] = None
        self.r2_score_: Optional[float] = None
        self.feature_names_in_: Optional[list] = None
        self.n_features_in_: Optional[int] = None
        self.filtered_samples_: int = 0
        self.mean_value_score_: Optional[float] = None

    def fit(self, X: pd.DataFrame, y: np.ndarray) -> 'ProjectionOwnershipEstimator':
        """
        Fit linear regression: ownership ~ value_score.

        Learns the relationship between value_score (projected_points / salary)
        and ownership percentages. Filters out samples with invalid salary
        (zero or negative) and logs the regression quality.

        Args:
            X: Feature matrix with columns:
                - projected_points: Expected DFS points (float)
                - salary: DraftKings salary (float, must be > 0)
            y: Target ownership percentages (0-100)

        Returns:
            self: Fitted estimator

        Raises:
            ValueError: If required columns are missing from X
            ValueError: If all samples are filtered due to invalid salary
            ValueError: If y contains invalid ownership values
        """
        # Validate inputs
        required_columns = ['projected_points', 'salary']
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

        # Filter out invalid salary (zero or negative)
        valid_salary_mask = X_work['salary'] > 0
        self.filtered_samples_ = (~valid_salary_mask).sum()

        if self.filtered_samples_ > 0:
            logger.warning(
                f"Filtered {self.filtered_samples_} samples with salary <= 0. "
                f"Using {valid_salary_mask.sum()} samples for training."
            )

        if valid_salary_mask.sum() == 0:
            raise ValueError("No valid samples: all salaries are <= 0")

        X_valid = X_work[valid_salary_mask]
        y_valid = y_work[valid_salary_mask]

        # Compute value_score = projected_points / salary
        # Scale by 1000 for numerical stability (salary is typically ~10000)
        value_score = (X_valid['projected_points'] / X_valid['salary']) * 1000

        # Store mean for fallback
        self.mean_value_score_ = value_score.mean()

        # Fit linear regression
        self.model_ = LinearRegression()
        self.model_.fit(value_score.values.reshape(-1, 1), y_valid)

        # Extract slope coefficient for interpretation
        self.value_score_slope_ = float(self.model_.coef_[0])

        # Compute R² score for regression quality
        y_pred = self.model_.predict(value_score.values.reshape(-1, 1))
        self.r2_score_ = float(r2_score(y_valid, y_pred))

        # Log diagnostics
        logger.info(
            f"Fitted ProjectionOwnershipEstimator: "
            f"value_score slope = {self.value_score_slope_:.4f}, "
            f"R² = {self.r2_score_:.4f}, "
            f"n_samples = {len(y_valid)}"
        )

        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict ownership percentages using learned value_score relationship.

        Computes value_score for each driver and applies the learned linear
        relationship. Predictions are clipped to [0, 100] range.

        Args:
            X: Feature matrix with columns:
                - projected_points: Expected DFS points
                - salary: DraftKings salary

        Returns:
            Array of ownership predictions (0-100)

        Raises:
            ValueError: If estimator has not been fitted
            ValueError: If required columns are missing from X
        """
        if self.model_ is None:
            raise ValueError("Estimator has not been fitted yet. Call fit() first.")

        required_columns = ['projected_points', 'salary']
        missing_columns = [col for col in required_columns if col not in X.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        # Create working copy
        X_work = X.copy()

        # Compute value_score
        # Handle zero/negative salary by using mean value_score
        salary_mask = X_work['salary'] > 0
        value_score = np.zeros(len(X_work))

        # Valid salary: compute value_score
        if salary_mask.any():
            value_score[salary_mask] = (
                (X_work.loc[salary_mask, 'projected_points'] /
                 X_work.loc[salary_mask, 'salary']) * 1000
            ).values

        # Invalid salary: use mean value_score from training
        if (~salary_mask).any():
            if self.mean_value_score_ is not None:
                value_score[~salary_mask] = self.mean_value_score_
                logger.warning(
                    f"{(~salary_mask).sum()} samples have salary <= 0, "
                    "using mean value_score for prediction"
                )
            else:
                value_score[~salary_mask] = 0.0

        # Apply linear model
        predictions = self.model_.predict(value_score.reshape(-1, 1))

        # Clip to valid range
        predictions = np.clip(predictions, 0, 100)

        return predictions

    def get_value_score(self, X: pd.DataFrame) -> np.ndarray:
        """
        Compute value_score for drivers (projected_points / salary) * 1000.

        Args:
            X: Feature matrix with projected_points and salary columns

        Returns:
            Array of value scores
        """
        required_columns = ['projected_points', 'salary']
        missing_columns = [col for col in required_columns if col not in X.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        value_score = np.zeros(len(X))
        salary_mask = X['salary'] > 0

        if salary_mask.any():
            value_score[salary_mask] = (
                (X.loc[salary_mask, 'projected_points'] /
                 X.loc[salary_mask, 'salary']) * 1000
            ).values

        return value_score
