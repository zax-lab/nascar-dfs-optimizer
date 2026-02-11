"""
Salary-skill regression estimator for NASCAR DFS.

This module provides SalarySkillRegressionEstimator, which estimates driver
ownership using a non-linear relationship between salary, skill (from ontology),
and recent form. The model uses RandomForestRegressor to capture complex
interactions between these features.

Key features:
- RandomForestRegressor for non-linear relationships
- Feature importance for interpretation
- Handles missing skill with mean imputation
- Clips predictions to [0, 100] range

Usage:
    estimator = SalarySkillRegressionEstimator()
    estimator.fit(X_train, y_train)
    predictions = estimator.predict(X_test)
    print(f"Feature importance: {estimator.feature_importances_}")
"""

import logging
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
from sklearn.ensemble import RandomForestRegressor

logger = logging.getLogger(__name__)


class SalarySkillRegressionEstimator:
    """
    Estimate driver ownership using salary, skill, and recent form.

    This estimator learns a non-linear relationship between:
    - salary: DraftKings salary
    - skill: Driver skill from ontology (0-1)
    - recent_avg_finish: Average finishing position in recent races

    The model uses RandomForestRegressor to capture complex interactions
    between these features. For example, high salary + high skill may have
    a non-linear effect on ownership (not just additive).

    The model handles missing skill values via mean imputation and clips
    predictions to [0, 100] range.

    Attributes:
        model_: Fitted RandomForestRegressor model
        feature_importances_: Array of feature importance scores
        feature_names_in_: List of feature names seen during fit
        n_features_in_: Number of features seen during fit
        mean_skill_: Mean skill value for imputation

    Example:
        >>> import pandas as pd
        >>> X = pd.DataFrame({
        ...     'salary': [10000, 9000, 8000, 7000, 6000],
        ...     'skill': [0.9, 0.8, 0.7, 0.6, 0.5],
        ...     'recent_avg_finish': [5.0, 10.0, 15.0, 20.0, 25.0]
        ... })
        >>> y = np.array([25.0, 20.0, 15.0, 10.0, 5.0])
        >>> estimator = SalarySkillRegressionEstimator()
        >>> estimator.fit(X, y)
        >>> predictions = estimator.predict(X)
        >>> print(f"Feature importance: {estimator.feature_importances_}")
    """

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: Optional[int] = None,
        min_samples_split: int = 2,
        min_samples_leaf: int = 1,
        random_state: int = 42
    ):
        """
        Initialize SalarySkillRegressionEstimator.

        Args:
            n_estimators: Number of trees in the forest
            max_depth: Maximum depth of trees (None for unlimited)
            min_samples_split: Minimum samples required to split a node
            min_samples_leaf: Minimum samples required at a leaf node
            random_state: Random seed for reproducibility
        """
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.min_samples_leaf = min_samples_leaf
        self.random_state = random_state

        # Model attributes
        self.model_: Optional[RandomForestRegressor] = None
        self.feature_importances_: Optional[np.ndarray] = None
        self.feature_names_in_: Optional[list] = None
        self.n_features_in_: Optional[int] = None
        self.mean_skill_: Optional[float] = None
        self.mean_recent_finish_: Optional[float] = None

    def fit(self, X: pd.DataFrame, y: np.ndarray) -> 'SalarySkillRegressionEstimator':
        """
        Fit RandomForest on salary, skill, and recent form features.

        Learns a non-linear relationship between salary, skill, and
        recent_avg_finish to predict ownership percentages. Handles
        missing skill values via mean imputation.

        Args:
            X: Feature matrix with columns:
                - salary: DraftKings salary (float)
                - skill: Driver skill from ontology (0-1, float, can be NaN)
                - recent_avg_finish: Average finish position (float, can be NaN)
            y: Target ownership percentages (0-100)

        Returns:
            self: Fitted estimator

        Raises:
            ValueError: If required columns are missing from X
            ValueError: If y contains invalid ownership values
        """
        # Validate inputs
        required_columns = ['salary', 'skill']
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

        # Impute missing skill with mean
        if 'skill' in X_work.columns:
            self.mean_skill_ = X_work['skill'].mean()
            n_missing_skill = X_work['skill'].isna().sum()

            if n_missing_skill > 0:
                logger.warning(
                    f"Imputing {n_missing_skill} missing skill values "
                    f"with mean: {self.mean_skill_:.3f}"
                )
                X_work['skill'] = X_work['skill'].fillna(self.mean_skill_)

        # Impute missing recent_avg_finish with mean
        if 'recent_avg_finish' in X_work.columns:
            self.mean_recent_finish_ = X_work['recent_avg_finish'].mean()
            n_missing_finish = X_work['recent_avg_finish'].isna().sum()

            if n_missing_finish > 0:
                logger.warning(
                    f"Imputing {n_missing_finish} missing recent_avg_finish values "
                    f"with mean: {self.mean_recent_finish_:.2f}"
                )
                X_work['recent_avg_finish'] = X_work['recent_avg_finish'].fillna(
                    self.mean_recent_finish_
                )

        # Select features for training
        feature_cols = ['salary', 'skill']
        if 'recent_avg_finish' in X_work.columns:
            feature_cols.append('recent_avg_finish')

        X_features = X_work[feature_cols]

        # Fit RandomForest
        self.model_ = RandomForestRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            min_samples_split=self.min_samples_split,
            min_samples_leaf=self.min_samples_leaf,
            random_state=self.random_state,
            n_jobs=-1  # Use all cores
        )
        self.model_.fit(X_features, y)

        # Extract feature importances
        self.feature_importances_ = self.model_.feature_importances_

        # Log diagnostics
        logger.info(
            f"Fitted SalarySkillRegressionEstimator: "
            f"n_estimators={self.n_estimators}, "
            f"n_samples={len(y)}, "
            f"features={feature_cols}"
        )

        # Log feature importance ranking
        importance_dict = dict(zip(feature_cols, self.feature_importances_))
        sorted_importance = sorted(
            importance_dict.items(),
            key=lambda x: x[1],
            reverse=True
        )
        importance_str = ', '.join([f'{f}={i:.3f}' for f, i in sorted_importance])
        logger.debug(f"Feature importance: {importance_str}")

        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict ownership percentages using trained RandomForest.

        Applies the trained model to new data, using mean imputation
        for missing skill or recent_avg_finish values.

        Args:
            X: Feature matrix with columns:
                - salary: DraftKings salary
                - skill: Driver skill (can be NaN)
                - recent_avg_finish: Average finish position (optional, can be NaN)

        Returns:
            Array of ownership predictions (0-100)

        Raises:
            ValueError: If estimator has not been fitted
            ValueError: If required columns are missing from X
        """
        if self.model_ is None:
            raise ValueError("Estimator has not been fitted yet. Call fit() first.")

        required_columns = ['salary', 'skill']
        missing_columns = [col for col in required_columns if col not in X.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        # Create working copy
        X_work = X.copy()

        # Impute missing skill
        if 'skill' in X_work.columns and X_work['skill'].isna().any():
            if self.mean_skill_ is not None:
                n_missing = X_work['skill'].isna().sum()
                logger.debug(
                    f"Imputing {n_missing} missing skill values with mean "
                    f"({self.mean_skill_:.3f}) for prediction"
                )
                X_work['skill'] = X_work['skill'].fillna(self.mean_skill_)

        # Impute missing recent_avg_finish
        if 'recent_avg_finish' in X_work.columns and X_work['recent_avg_finish'].isna().any():
            if self.mean_recent_finish_ is not None:
                n_missing = X_work['recent_avg_finish'].isna().sum()
                logger.debug(
                    f"Imputing {n_missing} missing recent_avg_finish values with mean "
                    f"({self.mean_recent_finish_:.2f}) for prediction"
                )
                X_work['recent_avg_finish'] = X_work['recent_avg_finish'].fillna(
                    self.mean_recent_finish_
                )

        # Select features
        feature_cols = ['salary', 'skill']
        if 'recent_avg_finish' in X_work.columns:
            feature_cols.append('recent_avg_finish')

        X_features = X_work[feature_cols]

        # Predict
        predictions = self.model_.predict(X_features)

        # Clip to valid range
        predictions = np.clip(predictions, 0, 100)

        return predictions

    def get_feature_importance_dict(self) -> Dict[str, float]:
        """
        Get feature importance as a dictionary.

        Returns:
            Dictionary mapping feature names to importance scores
        """
        if self.feature_importances_ is None:
            raise ValueError("Model not fitted yet")

        feature_cols = ['salary', 'skill']
        # Only add recent_avg_finish if it was used in training
        if self.n_features_in_ and self.n_features_in_ >= 3:
            feature_cols.append('recent_avg_finish')

        return dict(zip(feature_cols, self.feature_importances_))
