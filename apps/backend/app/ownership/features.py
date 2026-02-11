"""
Feature engineering utilities for ownership estimation.

This module provides functions for creating ownership prediction features
from driver and race data. Features include salary, projected points, skill,
value scores, track archetype encodings, and recent form statistics.

Key features:
- create_ownership_features: Build feature matrix from driver/race data
- add_track_archetype_features: One-hot encode track type
- add_recent_form_features: Compute rolling finish statistics
- Handles missing data gracefully with imputation

Usage:
    X = create_ownership_features(driver_data, race_data)
    X_with_tracks = add_track_archetype_features(X, 'superspeedway')
    X_with_form = add_recent_form_features(X, historical_finishes)
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Union

logger = logging.getLogger(__name__)

# Valid track archetypes
VALID_TRACK_ARCHETYPES = [
    'superspeedway',
    'intermediate',
    'short_track',
    'road_course'
]

# Default track archetype for unknown types
DEFAULT_TRACK_ARCHETYPE = 'intermediate'


def create_ownership_features(
    driver_data: pd.DataFrame,
    race_data: pd.DataFrame
) -> pd.DataFrame:
    """
    Create ownership prediction feature matrix from driver and race data.

    Creates a feature matrix with columns:
    - driver_id: Driver identifier
    - salary: DraftKings salary
    - projected_points: Expected DFS points
    - skill: Driver skill from ontology (0-1)
    - value_score: projected_points / salary (scaled by 1000)
    - track_archetype: Track type (categorical)

    Handles missing data:
    - Missing projected_points: imputed using salary-based heuristic
    - Missing skill: imputed with 0.5 (neutral)
    - Missing salary: error (required field)

    Args:
        driver_data: DataFrame with columns:
            - driver_id: Driver identifier
            - salary: DraftKings salary (required)
            - projected_points: Expected DFS points (optional)
            - skill: Driver skill from ontology (optional)
        race_data: DataFrame with columns:
            - race_id: Race identifier
            - track_archetype: Track type (optional)

    Returns:
        Feature matrix X as pandas DataFrame

    Raises:
        ValueError: If required columns are missing
        ValueError: If salary contains missing values

    Example:
        >>> driver_data = pd.DataFrame({
        ...     'driver_id': [1, 2, 3],
        ...     'salary': [10000, 9000, 8000],
        ...     'projected_points': [50, 45, 40],
        ...     'skill': [0.9, 0.8, 0.7]
        ... })
        >>> race_data = pd.DataFrame({
        ...     'race_id': [1],
        ...     'track_archetype': ['superspeedway']
        ... })
        >>> X = create_ownership_features(driver_data, race_data)
    """
    # Validate inputs
    required_driver_cols = ['driver_id', 'salary']
    missing_driver_cols = [
        col for col in required_driver_cols
        if col not in driver_data.columns
    ]
    if missing_driver_cols:
        raise ValueError(
            f"Missing required columns in driver_data: {missing_driver_cols}"
        )

    if driver_data['salary'].isna().any():
        raise ValueError("Salary cannot contain missing values")

    # Create working copy
    X = driver_data.copy()

    # Ensure required columns exist
    if 'projected_points' not in X.columns:
        X['projected_points'] = np.nan
        logger.warning("projected_points not in driver_data, using NaN")

    if 'skill' not in X.columns:
        X['skill'] = np.nan
        logger.warning("skill not in driver_data, using NaN")

    # Impute missing projected_points
    # Use salary-based heuristic: higher salary -> higher projected points
    if X['projected_points'].isna().any():
        n_missing = X['projected_points'].isna().sum()
        logger.info(
            f"Imputing {n_missing} missing projected_points values "
            "using salary-based heuristic"
        )

        # Simple heuristic: projected_points = salary / 200
        # (e.g., $10000 salary -> 50 points)
        salary_based_points = X['salary'] / 200.0
        X['projected_points'] = X['projected_points'].fillna(salary_based_points)

    # Impute missing skill with 0.5 (neutral)
    if X['skill'].isna().any():
        n_missing = X['skill'].isna().sum()
        logger.info(
            f"Imputing {n_missing} missing skill values with 0.5 (neutral)"
        )
        X['skill'] = X['skill'].fillna(0.5)

    # Compute value_score = (projected_points / salary) * 1000
    # Scale by 1000 for numerical stability
    X['value_score'] = (X['projected_points'] / X['salary']) * 1000

    # Add track_archetype from race_data
    if 'track_archetype' in race_data.columns:
        # Assume single race in race_data
        track = race_data['track_archetype'].iloc[0]
        X['track_archetype'] = track
    else:
        X['track_archetype'] = DEFAULT_TRACK_ARCHETYPE
        logger.warning(
            "track_archetype not in race_data, "
            f"using default: {DEFAULT_TRACK_ARCHETYPE}"
        )

    # Log feature creation diagnostics
    logger.info(
        f"Created ownership features: {len(X)} drivers, "
        f"{len(X.columns)} columns"
    )

    return X


def add_track_archetype_features(
    X: pd.DataFrame,
    track_archetype: str
) -> pd.DataFrame:
    """
    Add one-hot encoded track archetype features.

    Creates binary columns for each track archetype:
    - track_superspeedway: 1 if superspeedway, else 0
    - track_intermediate: 1 if intermediate, else 0
    - track_short_track: 1 if short_track, else 0
    - track_road_course: 1 if road_course, else 0

    Handles unknown archetypes by defaulting to 'intermediate'.

    Args:
        X: Feature matrix (may or may not have track_archetype column)
        track_archetype: Track type string

    Returns:
        X with added track archetype columns

    Example:
        >>> X = pd.DataFrame({'driver_id': [1, 2, 3]})
        >>> X = add_track_archetype_features(X, 'superspeedway')
        >>> # X now has track_superspeedway=1, track_intermediate=0, etc.
    """
    # Validate track archetype
    if track_archetype not in VALID_TRACK_ARCHETYPES:
        logger.warning(
            f"Unknown track archetype: '{track_archetype}', "
            f"defaulting to '{DEFAULT_TRACK_ARCHETYPE}'"
        )
        track_archetype = DEFAULT_TRACK_ARCHETYPE

    # Create working copy
    X_out = X.copy()

    # Add one-hot encoded columns
    for valid_archetype in VALID_TRACK_ARCHETYPES:
        col_name = f'track_{valid_archetype}'
        X_out[col_name] = 1 if track_archetype == valid_archetype else 0

    # Update track_archetype column if it exists
    if 'track_archetype' in X_out.columns:
        X_out['track_archetype'] = track_archetype

    logger.debug(
        f"Added track archetype features for '{track_archetype}'"
    )

    return X_out


def add_recent_form_features(
    X: pd.DataFrame,
    historical_finishes: pd.DataFrame,
    n_races: int = 5
) -> pd.DataFrame:
    """
    Add recent form features based on historical finishing positions.

    Computes rolling statistics for each driver:
    - recent_avg_finish: Average finish over last N races
    - recent_std_finish: Standard deviation of finish over last N races
    - recent_best_finish: Best finish over last N races
    - recent_top5_rate: Proportion of top-5 finishes over last N races

    Handles drivers with <3 races by using overall mean.

    Args:
        X: Feature matrix with driver_id column
        historical_finishes: DataFrame with columns:
            - driver_id: Driver identifier
            - finish_position: Finishing position (1=best)
            - race_date: Race date for ordering
        n_races: Number of recent races to consider

    Returns:
        X with added recent form columns

    Raises:
        ValueError: If required columns are missing from historical_finishes

    Example:
        >>> finishes = pd.DataFrame({
        ...     'driver_id': [1, 1, 1, 2, 2, 2],
        ...     'finish_position': [5, 10, 3, 15, 8, 12],
        ...     'race_date': pd.date_range('2024-01-01', periods=6)
        ... })
        >>> X = pd.DataFrame({'driver_id': [1, 2]})
        >>> X = add_recent_form_features(X, finishes, n_races=3)
    """
    # Validate inputs
    required_cols = ['driver_id', 'finish_position']
    missing_cols = [
        col for col in required_cols
        if col not in historical_finishes.columns
    ]
    if missing_cols:
        raise ValueError(
            f"Missing required columns in historical_finishes: {missing_cols}"
        )

    if 'driver_id' not in X.columns:
        raise ValueError("X must have 'driver_id' column")

    # Create working copy
    X_out = X.copy()

    # Sort by race_date if available
    if 'race_date' in historical_finishes.columns:
        finishes_sorted = historical_finishes.sort_values('race_date')
    else:
        logger.warning(
            "race_date not in historical_finishes, using original order"
        )
        finishes_sorted = historical_finishes

    # Compute recent form statistics for each driver
    recent_stats = []

    for driver_id in X_out['driver_id'].unique():
        driver_finishes = finishes_sorted[
            finishes_sorted['driver_id'] == driver_id
        ]['finish_position']

        # Take last N races
        recent_finishes = driver_finishes.tail(n_races)

        # Compute statistics
        if len(recent_finishes) >= 3:
            # Use actual recent form if enough data
            avg_finish = recent_finishes.mean()
            std_finish = recent_finishes.std()
            best_finish = recent_finishes.min()
            top5_rate = (recent_finishes <= 5).mean()
        else:
            # Fallback to overall mean if insufficient data
            avg_finish = driver_finishes.mean()
            std_finish = driver_finishes.std() if len(driver_finishes) > 1 else 0.0
            best_finish = driver_finishes.min()
            top5_rate = (driver_finishes <= 5).mean()

            logger.debug(
                f"Driver {driver_id}: only {len(recent_finishes)} recent races, "
                f"using overall statistics"
            )

        recent_stats.append({
            'driver_id': driver_id,
            'recent_avg_finish': avg_finish,
            'recent_std_finish': std_finish if not np.isnan(std_finish) else 0.0,
            'recent_best_finish': best_finish,
            'recent_top5_rate': top5_rate
        })

    # Create DataFrame and merge
    stats_df = pd.DataFrame(recent_stats)
    X_out = X_out.merge(stats_df, on='driver_id', how='left')

    # Fill any remaining NaN (drivers with no history)
    if X_out['recent_avg_finish'].isna().any():
        n_missing = X_out['recent_avg_finish'].isna().sum()
        logger.warning(
            f"{n_missing} drivers have no finish history, "
            "using default values (avg=20, std=0, best=20, top5=0)"
        )
        X_out['recent_avg_finish'] = X_out['recent_avg_finish'].fillna(20.0)
        X_out['recent_std_finish'] = X_out['recent_std_finish'].fillna(0.0)
        X_out['recent_best_finish'] = X_out['recent_best_finish'].fillna(20.0)
        X_out['recent_top5_rate'] = X_out['recent_top5_rate'].fillna(0.0)

    logger.info(
        f"Added recent form features for {len(X_out)} drivers "
        f"(using last {n_races} races)"
    )

    return X_out


def get_feature_importance_ranking(
    feature_importances: np.ndarray,
    feature_names: List[str],
    top_n: int = 10
) -> List[tuple]:
    """
    Rank features by importance and return top N.

    Args:
        feature_importances: Array of importance scores
        feature_names: List of feature names
        top_n: Number of top features to return

    Returns:
        List of (feature_name, importance) tuples sorted by importance
    """
    if len(feature_importances) != len(feature_names):
        raise ValueError(
            f"feature_importances ({len(feature_importances)}) and "
            f"feature_names ({len(feature_names)}) must have same length"
        )

    # Create list of (name, importance) tuples
    ranking = list(zip(feature_names, feature_importances))

    # Sort by importance (descending)
    ranking.sort(key=lambda x: x[1], reverse=True)

    # Return top N
    return ranking[:top_n]
