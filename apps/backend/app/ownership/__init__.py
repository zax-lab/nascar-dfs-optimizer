"""
Ownership estimation module for NASCAR DFS.

This module provides multiple independent ownership estimation models that
can be combined into an ensemble for robust ownership predictions. Each model
captures different aspects of DFS ownership behavior:

- HistoricalOwnershipEstimator: Track-archetype specific baseline ownership
- ProjectionOwnershipEstimator: Value-based ownership from projected points
- SalarySkillRegressionEstimator: Non-linear salary-skill-ownership relationships

All estimators follow scikit-learn's fit/predict interface for easy ensemble
composition and integration with the optimization pipeline.

Usage:
    from apps.backend.app.ownership import (
        HistoricalOwnershipEstimator,
        ProjectionOwnershipEstimator,
        SalarySkillRegressionEstimator,
        create_ownership_features
    )

    # Fit individual estimators
    hist_est = HistoricalOwnershipEstimator()
    hist_est.fit(X_train, y_train)

    proj_est = ProjectionOwnershipEstimator()
    proj_est.fit(X_train, y_train)

    # Or use feature engineering utilities
    X_features = create_ownership_features(driver_data, race_data)
"""

from apps.backend.app.ownership.historical import HistoricalOwnershipEstimator
from apps.backend.app.ownership.projections import ProjectionOwnershipEstimator
from apps.backend.app.ownership.projections_fetcher import ProjectionsFetcher
from apps.backend.app.ownership.salary_model import SalarySkillRegressionEstimator
from apps.backend.app.ownership.features import (
    create_ownership_features,
    add_track_archetype_features,
    add_recent_form_features,
    get_feature_importance_ranking
)

__all__ = [
    'HistoricalOwnershipEstimator',
    'ProjectionOwnershipEstimator',
    'ProjectionsFetcher',
    'SalarySkillRegressionEstimator',
    'create_ownership_features',
    'add_track_archetype_features',
    'add_recent_form_features',
    'get_feature_importance_ranking',
]
