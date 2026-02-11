"""
Pydantic models for contest data validation.

This module provides Pydantic models for validating and structuring
contest-related data including payout structures, contest metadata,
and historical contest records.

Models:
- PayoutData: Single rank/payout pair
- PayoutCurveFit: Fitted payout curve parameters and quality metrics
- ContestSize: Contest size classification and tier
- HistoricalContestData: Complete historical contest record

All models include validation to ensure data integrity.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class PayoutData(BaseModel):
    """
    Single payout data point for a finish position.

    Represents the payout amount for a specific finishing position
    in a contest.

    Attributes:
        rank: Finishing position (1-indexed, must be positive)
        payout: Payout amount in dollars (must be non-negative)
        contest_id: Optional contest identifier for tracking

    Example:
        >>> payout = PayoutData(rank=1, payout=100000, contest_id='dk-2024-02-18')
        >>> print(f"${payout.payout:,.0f} for {payout.rank}st place")
    """

    rank: int = Field(..., gt=0, description="Finishing position (1-indexed)")
    payout: float = Field(..., ge=0, description="Payout amount in dollars")
    contest_id: Optional[str] = Field(None, description="Contest identifier")

    @field_validator('payout')
    def payout_must_be_finite(cls, v):
        """Validate that payout is a finite number."""
        if not isinstance(v, (int, float)) or v != v:  # Check for NaN
            raise ValueError("Payout must be a finite number")
        return float(v)

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "rank": 1,
                    "payout": 100000.0,
                    "contest_id": "dk-2024-02-18-gpp"
                },
                {
                    "rank": 50,
                    "payout": 500.0,
                    "contest_id": "dk-2024-02-18-gpp"
                }
            ]
        }


class PayoutCurveFit(BaseModel):
    """
    Fitted payout curve model with parameters and quality metrics.

    Stores the results of fitting a payout curve model to historical
    contest data, including fitted parameters and validation metrics.

    Attributes:
        curve_type: Type of curve ('power_law' or 'exponential')
        parameters: Fitted parameters {'a': scaling, 'b': decay}
        fit_quality: Quality metrics {'r_squared': R², 'rmse': error}
        contest_size_tier: Contest size tier ('small', 'medium', 'large')
        n_observations: Number of data points used to fit curve
        fitted_at: Timestamp when curve was fitted

    Example:
        >>> fit = PayoutCurveFit(
        ...     curve_type='power_law',
        ...     parameters={'a': 100000, 'b': 1.5},
        ...     fit_quality={'r_squared': 0.95, 'rmse': 500},
        ...     contest_size_tier='large',
        ...     n_observations=100,
        ...     fitted_at=datetime.now()
        ... )
    """

    curve_type: str = Field(
        ...,
        description="Type of payout curve model"
    )
    parameters: Dict[str, float] = Field(
        ...,
        min_length=2,
        max_length=2,
        description="Fitted curve parameters (a, b)"
    )
    fit_quality: Dict[str, float] = Field(
        ...,
        description="Fit quality metrics (r_squared, rmse, n_observations)"
    )
    contest_size_tier: str = Field(
        ...,
        description="Contest size tier classification"
    )
    n_observations: int = Field(
        ...,
        gt=0,
        description="Number of data points used for fitting"
    )
    fitted_at: datetime = Field(
        ...,
        description="Timestamp when curve was fitted"
    )

    @field_validator('curve_type')
    def curve_type_must_be_valid(cls, v):
        """Validate that curve_type is supported."""
        valid_types = ['power_law', 'exponential']
        if v not in valid_types:
            raise ValueError(
                f"Invalid curve_type '{v}'. Must be one of: {valid_types}"
            )
        return v

    @field_validator('parameters')
    def parameters_must_be_positive(cls, v):
        """Validate that parameters are positive."""
        for key, value in v.items():
            if value <= 0:
                raise ValueError(
                    f"Parameter '{key}' must be positive, got {value}"
                )
        return v

    @field_validator('fit_quality')
    def fit_quality_must_have_required_keys(cls, v):
        """Validate that fit_quality contains required metrics."""
        required_keys = ['r_squared', 'rmse']
        for key in required_keys:
            if key not in v:
                raise ValueError(f"fit_quality must contain '{key}'")

        # Validate R² is in [0, 1]
        r_squared = v.get('r_squared', 0)
        if not 0 <= r_squared <= 1:
            raise ValueError(
                f"r_squared must be in [0, 1], got {r_squared}"
            )

        # Validate RMSE is non-negative
        rmse = v.get('rmse', 0)
        if rmse < 0:
            raise ValueError(f"rmse must be non-negative, got {rmse}")

        return v

    @field_validator('contest_size_tier')
    def tier_must_be_valid(cls, v):
        """Validate that contest_size_tier is supported."""
        valid_tiers = ['small', 'medium', 'large']
        if v not in valid_tiers:
            raise ValueError(
                f"Invalid contest_size_tier '{v}'. Must be one of: {valid_tiers}"
            )
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "curve_type": "power_law",
                "parameters": {"a": 100000.0, "b": 1.5},
                "fit_quality": {"r_squared": 0.95, "rmse": 500.0, "n_observations": 100},
                "contest_size_tier": "large",
                "n_observations": 100,
                "fitted_at": "2024-02-18T12:00:00Z"
            }
        }


class ContestSize(BaseModel):
    """
    Contest size classification and metadata.

    Classifies a contest by size tier and stores relevant metadata
    including buy-in, prize pool, and number of paid positions.

    Tier definitions:
    - small: <5,000 entries
    - medium: 5,000-20,000 entries
    - large: >20,000 entries

    Attributes:
        contest_size: Total number of entries in contest
        tier: Size tier classification ('small', 'medium', 'large')
        buyin: Buy-in amount in dollars
        total_prize_pool: Total prize pool in dollars
        n_paid: Number of positions that cash (receive payout)

    Example:
        >>> size = ContestSize(
        ...     contest_size=10000,
        ...     tier='large',
        ...     buyin=20.0,
        ...     total_prize_pool=200000,
        ...     n_paid=1500
        ... )
    """

    contest_size: int = Field(..., gt=0, description="Total number of entries")
    tier: str = Field(..., description="Contest size tier")
    buyin: float = Field(..., gt=0, description="Buy-in amount in dollars")
    total_prize_pool: float = Field(
        ...,
        gt=0,
        description="Total prize pool in dollars"
    )
    n_paid: int = Field(
        ...,
        gt=0,
        description="Number of positions that cash"
    )

    @field_validator('tier')
    def tier_must_be_valid(cls, v):
        """Validate that tier is supported."""
        valid_tiers = ['small', 'medium', 'large']
        if v not in valid_tiers:
            raise ValueError(
                f"Invalid tier '{v}'. Must be one of: {valid_tiers}"
            )
        return v

    @field_validator('contest_size', 'n_paid')
    def n_paid_must_not_exceed_contest_size(cls, v, info):
        """Validate that n_paid doesn't exceed contest_size."""
        if info.field_name == 'n_paid':
            # This will be checked during model validation
            # We can't access contest_size here directly in Pydantic v2
            pass
        return v

    def model_post_init(self, __context):
        """Post-init validation to check n_paid vs contest_size."""
        if self.n_paid > self.contest_size:
            raise ValueError(
                f"n_paid ({self.n_paid}) cannot exceed contest_size "
                f"({self.contest_size})"
            )

    class Config:
        json_schema_extra = {
            "example": {
                "contest_size": 10000,
                "tier": "large",
                "buyin": 20.0,
                "total_prize_pool": 200000.0,
                "n_paid": 1500
            }
        }


class HistoricalContestData(BaseModel):
    """
    Complete historical contest record.

    Stores all relevant data for a historical contest including
    payouts, metadata, and track information. Used for fitting
    payout curves and analyzing contest structures.

    Attributes:
        contest_id: Unique contest identifier
        contest_size: Total number of entries
        buyin: Buy-in amount in dollars
        payouts: List of payout data points (rank/payout pairs)
        contest_date: Date when contest was held
        track_archetype: Optional track type classification

    Example:
        >>> contest = HistoricalContestData(
        ...     contest_id='dk-2024-02-18-gpp',
        ...     contest_size=10000,
        ...     buyin=20.0,
        ...     payouts=[PayoutData(rank=1, payout=100000)],
        ...     contest_date=datetime(2024, 2, 18),
        ...     track_archetype='superspeedway'
        ... )
    """

    contest_id: str = Field(..., min_length=1, description="Contest identifier")
    contest_size: int = Field(..., gt=0, description="Total number of entries")
    buyin: float = Field(..., gt=0, description="Buy-in amount in dollars")
    payouts: List[PayoutData] = Field(
        ...,
        min_length=1,
        description="List of payout data points"
    )
    contest_date: datetime = Field(..., description="Contest date")
    track_archetype: Optional[str] = Field(
        None,
        description="Track type classification"
    )

    @field_validator('track_archetype')
    def track_archetype_must_be_valid(cls, v):
        """Validate track_archetype if provided."""
        if v is not None:
            valid_archetypes = [
                'superspeedway',
                'intermediate',
                'short_track',
                'road_course'
            ]
            if v not in valid_archetypes:
                raise ValueError(
                    f"Invalid track_archetype '{v}'. Must be one of: {valid_archetypes}"
                )
        return v

    @field_validator('payouts')
    def payouts_must_be_sorted_and_unique(cls, v):
        """Validate that payouts are sorted by rank with no duplicates."""
        ranks = [payout.rank for payout in v]

        # Check for duplicate ranks
        if len(ranks) != len(set(ranks)):
            raise ValueError("Payouts must have unique ranks (no duplicates)")

        # Check if sorted
        if ranks != sorted(ranks):
            raise ValueError("Payouts must be sorted by rank")

        return v

    class Config:
        json_schema_extra = {
            "example": {
                "contest_id": "dk-2024-02-18-gpp",
                "contest_size": 10000,
                "buyin": 20.0,
                "payouts": [
                    {"rank": 1, "payout": 100000.0},
                    {"rank": 2, "payout": 50000.0},
                    {"rank": 3, "payout": 30000.0}
                ],
                "contest_date": "2024-02-18T12:00:00Z",
                "track_archetype": "superspeedway"
            }
        }
