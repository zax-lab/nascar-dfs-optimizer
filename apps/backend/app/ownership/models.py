"""
Pydantic models for ownership estimation validation.

This module provides type-safe contracts for ownership estimation:
- Request models with driver/race data validation
- Response models with ownership predictions
- Uncertainty bounds for confidence intervals
- Track archetype validation

Key features:
- Type validation with Pydantic
- Field constraints (min/max values, allowed values)
- Custom validators for business logic
- Track archetype enumeration
"""
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TrackArchetype(str, Enum):
    """Track archetype enumeration for ownership estimation."""
    SUPERPEEDWAY = "superspeedway"
    INTERMEDIATE = "intermediate"
    SHORT_TRACK = "short_track"
    ROAD_COURSE = "road_course"


class EnsembleMethod(str, Enum):
    """Ensemble method enumeration for ownership estimation."""
    VOTING = "voting"
    STACKING = "stacking"


class DriverOwnershipData(BaseModel):
    """
    Driver-specific data for ownership estimation.

    Contains the features needed to estimate ownership for a single driver:
    - Driver identifier and salary
    - Optional: projected points, skill, recent form metrics
    """
    driver_id: int = Field(..., description="Unique driver identifier")
    salary: int = Field(..., gt=0, description="DraftKings salary (must be positive)")
    projected_points: Optional[float] = Field(
        None,
        ge=0,
        description="Expected DFS points for this race"
    )
    skill: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Driver skill from ontology (0-1)"
    )
    recent_avg_finish: Optional[float] = Field(
        None,
        ge=0,
        description="Average finishing position in recent races"
    )

    @validator('salary')
    def salary_must_be_positive(cls, v):
        """Ensure salary is positive."""
        if v <= 0:
            raise ValueError('salary must be positive')
        return v


class RaceOwnershipData(BaseModel):
    """
    Race-specific data for ownership estimation.

    Contains the race context needed for ownership estimation:
    - Race identifier and date
    - Track archetype (superspeedway, intermediate, short_track, road_course)
    """
    race_id: int = Field(..., description="Unique race identifier")
    track_archetype: TrackArchetype = Field(
        ...,
        description="Track type for ownership estimation"
    )
    race_date: datetime = Field(..., description="Scheduled race date")

    @validator('track_archetype')
    def track_archetype_must_be_valid(cls, v):
        """Ensure track_archetype is one of the valid types."""
        valid_types = {'superspeedway', 'intermediate', 'short_track', 'road_course'}
        if v not in valid_types:
            raise ValueError(
                f'track_archetype must be one of {valid_types}, got {v}'
            )
        return v


class OwnershipRequest(BaseModel):
    """
    Request model for ownership estimation.

    Contains all data needed to estimate driver ownership:
    - Driver data for all drivers in the race
    - Race context (track, date)
    - Estimation configuration (ensemble method, recent races, uncertainty)
    """
    driver_data: List[DriverOwnershipData] = Field(
        ...,
        min_items=1,
        description="List of driver data for ownership estimation"
    )
    race_data: RaceOwnershipData = Field(
        ...,
        description="Race context for ownership estimation"
    )
    ensemble_method: EnsembleMethod = Field(
        EnsembleMethod.VOTING,
        description="Ensemble method for combining estimators"
    )
    n_recent_races: int = Field(
        5,
        ge=1,
        le=20,
        description="Number of recent races for form calculation"
    )
    include_uncertainty: bool = Field(
        False,
        description="Whether to include uncertainty bounds in response"
    )
    custom_weights: Optional[List[float]] = Field(
        None,
        description="Custom weights for voting ensemble (must sum to 1.0)"
    )

    @validator('custom_weights')
    def custom_weights_must_sum_to_one(cls, v):
        """Ensure custom weights sum to 1.0."""
        if v is not None:
            if abs(sum(v) - 1.0) > 1e-6:
                raise ValueError(f'custom_weights must sum to 1.0, got {sum(v)}')
            if len(v) != 4:
                raise ValueError(
                    f'custom_weights must have 4 elements (hist, proj, salary, recent), '
                    f'got {len(v)}'
                )
        return v

    @validator('n_recent_races')
    def n_recent_races_must_be_reasonable(cls, v):
        """Ensure n_recent_races is reasonable."""
        if v < 1:
            raise ValueError('n_recent_races must be at least 1')
        if v > 20:
            logger.warning(
                f'n_recent_races={v} is large, may cause data sparsity issues'
            )
        return v


class OwnershipPrediction(BaseModel):
    """
    Single driver ownership prediction.

    Contains the estimated ownership for a single driver:
    - Driver identifier and ownership percentage
    - Optional: uncertainty bounds (lower/upper percentiles)
    """
    driver_id: int = Field(..., description="Unique driver identifier")
    ownership_percent: float = Field(
        ...,
        ge=0,
        le=100,
        description="Estimated ownership percentage (0-100)"
    )
    uncertainty_lower: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="Lower uncertainty bound (e.g., 5th percentile)"
    )
    uncertainty_upper: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="Upper uncertainty bound (e.g., 95th percentile)"
    )

    @validator('ownership_percent')
    def ownership_must_be_in_range(cls, v):
        """Ensure ownership is in valid range."""
        if not (0 <= v <= 100):
            raise ValueError('ownership_percent must be in range [0, 100]')
        return v

    @validator('uncertainty_upper')
    def uncertainty_upper_must_be_gte_lower(cls, v, values):
        """Ensure uncertainty_upper >= uncertainty_lower."""
        if 'uncertainty_lower' in values and values['uncertainty_lower'] is not None:
            if v is not None and v < values['uncertainty_lower']:
                raise ValueError(
                    'uncertainty_upper must be >= uncertainty_lower'
                )
        return v


class OwnershipResponse(BaseModel):
    """
    Response model for ownership estimation.

    Contains ownership predictions for all drivers:
    - List of ownership predictions with uncertainty bounds
    - Ensemble method used
    - Optional: feature importance from ensemble
    """
    model_config = {'protected_namespaces': ()}

    ownership_predictions: List[OwnershipPrediction] = Field(
        ...,
        description="Ownership predictions for all drivers"
    )
    ensemble_method: EnsembleMethod = Field(
        ...,
        description="Ensemble method used for estimation"
    )
    feature_importance: Optional[Dict[str, float]] = Field(
        None,
        description="Feature importance scores from ensemble"
    )
    n_recent_races: int = Field(
        ...,
        description="Number of recent races used for form calculation"
    )
    model_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata about the estimation"
    )

    @validator('ownership_predictions')
    def ownership_must_sum_to_100(cls, v):
        """Ensure ownership predictions sum to approximately 100%."""
        total_ownership = sum(pred.ownership_percent for pred in v)
        # Allow small tolerance for floating-point errors
        if abs(total_ownership - 100.0) > 1.0:
            logger.warning(
                f'Ownership predictions sum to {total_ownership:.2f}%, '
                f'expected 100% (tolerance: 1%)'
            )
        return v

    @validator('feature_importance')
    def feature_importance_must_be_normalized(cls, v):
        """Ensure feature importance scores are reasonable."""
        if v is not None:
            for feature, importance in v.items():
                if not (0 <= importance <= 1):
                    logger.warning(
                        f'Feature importance for {feature} is {importance}, '
                        f'expected range [0, 1]'
                    )
        return v
