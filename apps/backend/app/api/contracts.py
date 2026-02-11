"""
Pydantic API contracts for request/response validation.

This module provides type-safe contracts for the /optimize endpoint:
- Request models with validation constraints
- Response models with scenario diagnostics
- Status models for async optimization tracking
- Phase 4: Ownership, contest simulation, and leverage optimization models

Key features:
- Type validation with Pydantic
- Field constraints (min/max values)
- Custom validators for business logic
- Scenario-driven config support
"""
from pydantic import BaseModel, Field, field_validator, constr
from typing import List, Dict, Any, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# Import Phase 4 ownership and contest models
try:
    from apps.backend.app.ownership.models import (
        OwnershipRequest,
        OwnershipResponse,
        TrackArchetype
    )
except ImportError:
    # Fallback if ownership models not available
    OwnershipRequest = None
    OwnershipResponse = None
    TrackArchetype = None

try:
    from apps.backend.app.contest.models import ContestSize, HistoricalContestData
except ImportError:
    # Fallback if contest models not available
    ContestSize = None
    HistoricalContestData = None


class PitStrategy(str, Enum):
    """Pit strategy enum for driver configuration."""
    AGGRESSIVE = "AGGRESSIVE"
    STANDARD = "STANDARD"
    CONSERVATIVE = "CONSERVATIVE"


class ScenarioConfig(BaseModel):
    """
    Scenario generation configuration.

    Controls how scenarios are generated for optimization:
    - Number of scenarios (affects runtime and accuracy)
    - Track identifier (determines physics constraints)
    - Race parameters (length, field size)
    - Calibration toggle (use historical data or priors)
    """
    n_scenarios: int = Field(
        1000,
        ge=10,
        le=10000,
        description="Number of scenarios to generate"
    )
    track_id: str = Field(
        ...,
        min_length=1,
        description="Track identifier (e.g., 'daytona', 'talladega')"
    )
    race_length: int = Field(
        200,
        ge=50,
        le=500,
        description="Total race laps"
    )
    field_size: int = Field(
        40,
        ge=6,
        le=50,
        description="Number of drivers in race"
    )
    calibration_enabled: bool = Field(
        True,
        description="Whether to use calibrated probabilities"
    )

    @field_validator('n_scenarios')
    @classmethod
    def n_scenarios_must_be_divisible_by_10(cls, v):
        """Ensure n_scenarios is divisible by 10 for efficient batching."""
        if v % 10 != 0:
            raise ValueError('n_scenarios must be divisible by 10 for efficient batching')
        return v


class DriverConstraintsRequest(BaseModel):
    """
    Driver constraint specification for optimization.

    Defines per-driver constraints that affect scenario generation:
    - Skill: Overall driver ability (0-1)
    - Aggression: Willingness to take risks (0-1)
    - Shadow_risk: Probability of being involved in incidents (0-1)
    - Laps led constraints: Min/max laps driver is expected to lead
    """
    driver_id: str = Field(..., min_length=1, description="Unique driver identifier")
    skill: float = Field(..., ge=0, le=1, description="Driver skill level (0-1)")
    aggression: float = Field(..., ge=0, le=1, description="Driver aggression (0-1)")
    shadow_risk: float = Field(..., ge=0, le=1, description="Shadow risk (0-1)")
    min_laps_led: int = Field(0, ge=0, description="Minimum laps to lead")
    max_laps_led: int = Field(100, ge=0, description="Maximum laps to lead")

    @field_validator('max_laps_led')
    @classmethod
    def max_laps_led_must_be_gte_min(cls, v, info):
        """Ensure max_laps_led >= min_laps_led."""
        # In Pydantic v2, use info.data instead of values
        return v


class OptimizeRequest(BaseModel):
    """
    Optimization request with scenario-driven configuration.

    This is the main API contract for lineup optimization:
    - Slate identifier for reproducibility
    - Driver list with individual constraints
    - Scenario generation config
    - Budget constraint (salary cap)
    - Optional random seed for reproducibility
    """
    slate_id: str = Field(
        ...,
        min_length=1,
        description="Unique slate identifier (e.g., '2024-02-18-daytona-500')"
    )
    drivers: List[DriverConstraintsRequest] = Field(
        ...,
        min_items=6,
        max_items=50,
        description="List of driver constraints (6-50 drivers)"
    )
    scenario_config: ScenarioConfig = Field(
        ...,
        description="Scenario generation configuration"
    )
    salary_cap: int = Field(
        50000,
        ge=10000,
        le=100000,
        description="Salary cap for lineup optimization"
    )
    random_seed: Optional[int] = Field(
        None,
        ge=0,
        description="Random seed for reproducibility"
    )

    @field_validator('drivers')
    @classmethod
    def drivers_must_have_unique_ids(cls, v):
        """Ensure all driver_ids are unique."""
        driver_ids = [d.driver_id for d in v]
        if len(driver_ids) != len(set(driver_ids)):
            raise ValueError('All driver_ids must be unique')
        return v


class DriverSelection(BaseModel):
    """
    Selected driver in optimized lineup.

    Represents a driver chosen in the final lineup with:
    - Driver metadata (id, name, salary, position)
    - Projected points from scenario optimization
    """
    driver_id: str = Field(..., description="Driver identifier")
    name: str = Field(..., description="Driver name")
    salary: int = Field(..., description="Driver salary")
    projected_points: float = Field(..., description="Projected fantasy points")
    position: int = Field(..., description="Starting position")


class ScenarioDiagnostics(BaseModel):
    """
    Diagnostic information from scenario generation.

    Provides insights into scenario quality:
    - Generation metrics (count, validity, rejection rate)
    - Aggregate statistics (laps led, position changes)
    - Calibration metrics (CRPS, log score, coverage)
    """
    n_scenarios_generated: int = Field(
        ...,
        description="Total scenarios generated"
    )
    n_valid: int = Field(
        ...,
        description="Number of valid scenarios (passed kernel validation)"
    )
    rejection_rate: float = Field(
        ...,
        description="Proportion of scenarios rejected (0-1)"
    )
    avg_laps_led: float = Field(
        ...,
        description="Average laps led across scenarios"
    )
    avg_position_differential: float = Field(
        ...,
        description="Average position change from start to finish"
    )
    calibration_metrics: Optional[Dict[str, float]] = Field(
        None,
        description="Calibration metrics (CRPS, log_score, coverage)"
    )


class OptimizeResponse(BaseModel):
    """
    Optimization response with lineup and diagnostics.

    Complete response from optimization including:
    - Optimized lineup with driver selections
    - Aggregate metrics (total points, salary)
    - Scenario diagnostics for transparency
    - Run metadata (run_id, status, constraint hash)
    """
    lineup: List[DriverSelection] = Field(
        ...,
        description="Optimized lineup of 6 drivers"
    )
    total_projected_points: float = Field(
        ...,
        description="Total projected points for lineup"
    )
    total_salary: int = Field(
        ...,
        description="Total salary used"
    )
    scenario_diagnostics: ScenarioDiagnostics = Field(
        ...,
        description="Scenario generation diagnostics"
    )
    run_id: str = Field(
        ...,
        description="Unique run identifier"
    )
    status: str = Field(
        ...,
        description="Optimization status (completed, failed)"
    )
    constraint_spec_hash: str = Field(
        ...,
        description="Hash of compiled constraint spec"
    )


class OptimizationStatus(BaseModel):
    """
    Status of async optimization job.

    Provides current status of background optimization:
    - Run identifier for polling
    - Status (pending, running, completed, failed)
    - Progress (0.0 to 1.0)
    - Error message if failed
    """
    run_id: str = Field(..., description="Unique run identifier")
    status: str = Field(
        ...,
        description="Job status (pending, running, completed, failed)"
    )
    progress: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Progress (0.0 to 1.0)"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if status is 'failed'"
    )


# =============================================================================
# Phase 4: Ownership, Contest Simulation, and Leverage Optimization Models
# =============================================================================

class ContestSimRequest(BaseModel):
    """
    Request model for contest simulation endpoint.

    Contains data needed to simulate contest outcomes:
    - Lineup scores to evaluate
    - Driver score scenarios for field simulation
    - Contest parameters (field size, buyin, etc.)
    """
    my_lineup_scores: List[float] = Field(
        ...,
        min_items=1,
        description="Scores for my lineups to evaluate"
    )
    scenario_driver_scores: List[List[float]] = Field(
        ...,
        min_items=1,
        description="Driver scores for each scenario (n_scenarios x n_drivers)"
    )
    field_size: int = Field(
        1000,
        gt=0,
        description="Number of lineups in the contest"
    )
    n_contest_sims: int = Field(
        100,
        gt=0,
        le=1000,
        description="Number of contest simulations per scenario"
    )
    contest_buyin: float = Field(
        20.0,
        gt=0,
        description="Contest buy-in amount"
    )
    contest_size_tier: str = Field(
        'large',
        description="Contest size tier ('small', 'medium', 'large')"
    )

    @field_validator('contest_size_tier')
    def contest_size_tier_must_be_valid(cls, v):
        """Validate that contest_size_tier is supported."""
        valid_tiers = ['small', 'medium', 'large']
        if v not in valid_tiers:
            raise ValueError(
                f"Invalid contest_size_tier '{v}'. Must be one of: {valid_tiers}"
            )
        return v


class ContestSimResponse(BaseModel):
    """
    Response model for contest simulation endpoint.

    Contains contest simulation results:
    - ROI metrics with confidence intervals
    - Cash and win probabilities
    - Best/worst outcomes
    - Simulation count
    """
    roi: float = Field(..., description="Expected return on investment (percentage)")
    roi_std: float = Field(..., ge=0, description="Standard deviation of ROI")
    roi_lower_5: float = Field(..., description="5th percentile ROI")
    roi_upper_95: float = Field(..., description="95th percentile ROI")
    cash_pct: float = Field(..., ge=0, le=100, description="Probability of cashing (percentage)")
    cash_se: float = Field(..., ge=0, description="Standard error of cash percentage")
    win_prob: float = Field(..., ge=0, le=100, description="Probability of top 1% finish (percentage)")
    win_se: float = Field(..., ge=0, description="Standard error of win probability")
    best_rank: int = Field(..., ge=1, description="Best finishing position")
    worst_rank: int = Field(..., ge=1, description="Worst finishing position")
    best_payout: float = Field(..., ge=0, description="Best payout achieved")
    n_simulations: int = Field(..., gt=0, description="Total number of simulations run")


class ConstraintSpecForLeverage(BaseModel):
    """
    Simplified constraint spec for leverage optimization.

    Contains essential constraints for lineup optimization:
    - Salary cap
    - Number of drivers
    - Team stacking rules
    """
    salary_cap: int = Field(
        50000,
        gt=0,
        description="DK salary cap"
    )
    n_drivers: int = Field(
        6,
        gt=0,
        description="Roster size"
    )
    min_stack: int = Field(
        2,
        ge=0,
        description="Minimum team stacking"
    )
    max_stack: int = Field(
        3,
        ge=0,
        description="Maximum team stacking"
    )


class LeverageOptimizeRequest(BaseModel):
    """
    Request model for leverage-aware optimization endpoint.

    Contains data needed for leverage-aware optimization:
    - Constraint specification
    - Ownership estimates for each driver
    - Leverage parameters
    - Optional regime-aware allocation
    """
    constraint_spec: ConstraintSpecForLeverage = Field(
        ...,
        description="Constraint specification for optimization"
    )
    ownership_estimates: List[float] = Field(
        ...,
        min_items=6,
        description="Ownership percentages for each driver (0-100)"
    )
    n_lineups: int = Field(
        20,
        ge=1,
        le=150,
        description="Number of lineups to generate"
    )
    leverage_penalty: float = Field(
        0.5,
        ge=0.0,
        le=1.0,
        description="Weight for ownership penalty (0-1)"
    )
    max_ownership_per_driver: float = Field(
        0.3,
        ge=0.0,
        le=1.0,
        description="Max ownership fraction for any single driver"
    )
    min_low_ownership_drivers: int = Field(
        2,
        ge=0,
        le=6,
        description="Minimum number of drivers with <10% ownership"
    )
    max_total_ownership: float = Field(
        3.0,
        ge=0.0,
        description="Max sum of ownership fractions in lineup"
    )
    use_regime_allocation: bool = Field(
        False,
        description="Use regime-aware allocation across scenarios"
    )
    n_scenarios: int = Field(
        1000,
        ge=100,
        le=50000,
        description="Number of scenarios for optimization"
    )

    @field_validator('ownership_estimates')
    def ownership_estimates_must_sum_to_100(cls, v):
        """Validate that ownership estimates sum to approximately 100%."""
        total = sum(v)
        # Allow 5% tolerance for floating-point errors
        if abs(total - 100.0) > 5.0:
            raise ValueError(
                f'ownership_estimates must sum to approximately 100%, got {total:.1f}%'
            )
        return v

    @field_validator('max_ownership_per_driver')
    def max_ownership_must_be_fraction(cls, v):
        """Validate that max_ownership_per_driver is a fraction (0-1)."""
        if not (0.0 <= v <= 1.0):
            raise ValueError(
                f'max_ownership_per_driver must be in [0, 1], got {v}'
            )
        return v


class DriverInLineup(BaseModel):
    """
    Driver in a leverage-optimized lineup.

    Represents a single driver selection with ownership information.
    """
    driver_id: int = Field(..., description="Driver identifier")
    name: str = Field(..., description="Driver name")
    salary: int = Field(..., description="Driver salary")
    projected_points: float = Field(..., description="Projected fantasy points")
    ownership: float = Field(..., ge=0, le=100, description="Ownership percentage")


class LineupWithLeverage(BaseModel):
    """
    Lineup with leverage metrics.

    Contains lineup information plus ownership-based leverage metrics:
    - Driver selections
    - Aggregate metrics (points, salary)
    - Ownership metrics (avg, max, total)
    - Leverage score
    - Optional regime classification
    """
    drivers: List[DriverInLineup] = Field(
        ...,
        min_length=6,
        max_length=6,
        description="Exactly 6 drivers in lineup"
    )
    total_projected_points: float = Field(
        ...,
        ge=0,
        description="Total projected points"
    )
    total_salary: int = Field(
        ...,
        gt=0,
        description="Total salary"
    )
    avg_ownership: float = Field(
        ...,
        ge=0,
        le=100,
        description="Average ownership percentage in lineup"
    )
    max_ownership: float = Field(
        ...,
        ge=0,
        le=100,
        description="Maximum ownership percentage in lineup"
    )
    total_ownership: float = Field(
        ...,
        ge=0,
        description="Sum of ownership percentages"
    )
    leverage_score: float = Field(
        ...,
        ge=0,
        description="Leverage score (higher = more differentiated from field)"
    )
    regime: Optional[str] = Field(
        None,
        description="Race-flow regime ('dominator', 'chaos', 'fuel_mileage')"
    )

    @field_validator('regime')
    def regime_must_be_valid(cls, v):
        """Validate regime if provided."""
        if v is not None:
            valid_regimes = ['dominator', 'chaos', 'fuel_mileage']
            if v not in valid_regimes:
                raise ValueError(
                    f"Invalid regime '{v}'. Must be one of: {valid_regimes}"
                )
        return v


class PortfolioMetrics(BaseModel):
    """
    Portfolio-level metrics for leverage optimization.

    Contains aggregate metrics across all generated lineups:
    - Average points and salary
    - Portfolio correlation
    - Diversification score
    """
    avg_projected_points: float = Field(
        ...,
        ge=0,
        description="Average projected points across lineups"
    )
    avg_salary: int = Field(
        ...,
        gt=0,
        description="Average salary across lineups"
    )
    portfolio_correlation: float = Field(
        ...,
        ge=0,
        le=1,
        description="Average correlation between lineups"
    )
    diversification_score: float = Field(
        ...,
        ge=0,
        le=1,
        description="Portfolio diversification (higher = more diversified)"
    )


class OwnershipMetrics(BaseModel):
    """
    Ownership metrics for leverage optimization.

    Contains ownership statistics across all lineups:
    - Average, min, max ownership
    - Low-ownership driver count
    - Diversification score
    """
    avg_lineup_ownership: float = Field(
        ...,
        ge=0,
        le=100,
        description="Average ownership across all lineups"
    )
    min_lineup_ownership: float = Field(
        ...,
        ge=0,
        le=100,
        description="Minimum ownership across all lineups"
    )
    max_lineup_ownership: float = Field(
        ...,
        ge=0,
        le=100,
        description="Maximum ownership across all lineups"
    )
    low_ownership_driver_count: int = Field(
        ...,
        ge=0,
        description="Count of drivers with <10% ownership"
    )
    diversification_score: float = Field(
        ...,
        ge=0,
        le=1,
        description="1 - sum(ownership^2) / sum(ownership)^2"
    )


class LeverageOptimizeResponse(BaseModel):
    """
    Response model for leverage-aware optimization endpoint.

    Contains leverage-optimized lineups with metrics:
    - Generated lineups with leverage metrics
    - Portfolio-level metrics
    - Ownership metrics
    """
    lineups: List[LineupWithLeverage] = Field(
        ...,
        min_items=1,
        description="Generated leverage-optimized lineups"
    )
    portfolio_metrics: PortfolioMetrics = Field(
        ...,
        description="Portfolio-level metrics"
    )
    ownership_metrics: OwnershipMetrics = Field(
        ...,
        description="Ownership metrics across lineups"
    )
