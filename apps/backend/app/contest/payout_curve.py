"""
Payout curve modeling for DraftKings GPP contests.

This module implements parametric payout curve models that approximate
DraftKings GPP payout structures. The models enable smooth extrapolation
to unobserved finish positions and support contest simulation.

Supported models:
- Power-law: payout = a * rank^(-b)
- Exponential: payout = a * exp(-b * rank)

The power-law model is recommended for top-heavy GPPs as it accurately
captures the steep drop-off in payout structure.
"""

import logging
import numpy as np
from abc import ABC, abstractmethod
from scipy.optimize import curve_fit
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime

logger = logging.getLogger(__name__)


class PayoutCurve(ABC):
    """
    Abstract base class for payout curve models.

    All payout curve models must implement the predict() method to
    generate payouts for given finish positions.
    """

    @abstractmethod
    def predict(self, ranks: np.ndarray) -> np.ndarray:
        """
        Predict payout for given finish positions.

        Args:
            ranks: Array of finish positions (1-indexed)

        Returns:
            Array of predicted payouts

        Raises:
            ValueError: If ranks contain invalid values (zero or negative)
        """
        pass


class PowerLawPayoutCurve(PayoutCurve):
    """
    Power-law payout curve model.

    Models payout decay as: payout = a * rank^(-b)

    where:
    - a: Scaling parameter (payout at rank=1)
    - b: Decay exponent (higher = faster decay)

    This model is recommended for top-heavy GPP contests as it captures
    the steep drop-off in payout structure.

    Example:
        >>> curve = PowerLawPayoutCurve(a=100000, b=1.5)
        >>> curve.predict(np.array([1, 2, 5, 10]))
        array([100000., 35355.34,  8944.27,  3162.28])
    """

    def __init__(self, a: float, b: float):
        """
        Initialize power-law payout curve.

        Args:
            a: Scaling parameter (payout at rank=1)
            b: Decay exponent (must be positive)

        Raises:
            ValueError: If parameters are invalid
        """
        if a <= 0:
            raise ValueError(f"Scaling parameter 'a' must be positive, got {a}")
        if b <= 0:
            raise ValueError(f"Decay exponent 'b' must be positive, got {b}")

        self.a = a
        self.b = b

        logger.debug(f"Initialized PowerLawPayoutCurve: a={a:.2f}, b={b:.4f}")

    def predict(self, ranks: np.ndarray) -> np.ndarray:
        """
        Predict payout using power-law formula.

        Args:
            ranks: Array of finish positions (1-indexed)

        Returns:
            Array of predicted payouts

        Raises:
            ValueError: If ranks contain zero or negative values
        """
        ranks_array = np.asarray(ranks, dtype=float)

        if np.any(ranks_array <= 0):
            raise ValueError("Ranks must be positive (1-indexed)")

        # Power-law formula: payout = a * rank^(-b)
        payouts = self.a * np.power(ranks_array, -self.b)

        return payouts

    def __repr__(self) -> str:
        return f"PowerLawPayoutCurve(a={self.a:.2f}, b={self.b:.4f})"


class ExponentialPayoutCurve(PayoutCurve):
    """
    Exponential payout curve model.

    Models payout decay as: payout = a * exp(-b * rank)

    where:
    - a: Scaling parameter
    - b: Decay rate

    This model provides faster decay than power-law and may be more
    appropriate for certain contest structures.

    Example:
        >>> curve = ExponentialPayoutCurve(a=100000, b=0.05)
        >>> curve.predict(np.array([1, 2, 5, 10]))
        array([95122.94, 60653.07,  7357.59,   673.79])
    """

    def __init__(self, a: float, b: float):
        """
        Initialize exponential payout curve.

        Args:
            a: Scaling parameter
            b: Decay rate (must be positive)

        Raises:
            ValueError: If parameters are invalid
        """
        if a <= 0:
            raise ValueError(f"Scaling parameter 'a' must be positive, got {a}")
        if b <= 0:
            raise ValueError(f"Decay rate 'b' must be positive, got {b}")

        self.a = a
        self.b = b

        logger.debug(f"Initialized ExponentialPayoutCurve: a={a:.2f}, b={b:.6f}")

    def predict(self, ranks: np.ndarray) -> np.ndarray:
        """
        Predict payout using exponential formula.

        Args:
            ranks: Array of finish positions (1-indexed)

        Returns:
            Array of predicted payouts
        """
        ranks_array = np.asarray(ranks, dtype=float)

        if np.any(ranks_array <= 0):
            raise ValueError("Ranks must be positive (1-indexed)")

        # Exponential formula: payout = a * exp(-b * rank)
        payouts = self.a * np.exp(-self.b * ranks_array)

        return payouts

    def __repr__(self) -> str:
        return f"ExponentialPayoutCurve(a={self.a:.2f}, b={self.b:.6f})"


class PayoutCurveFitter:
    """
    Fits payout curve models to historical contest data.

    Supports fitting power-law and exponential decay models to historical
    payout structures. Computes fit quality metrics (R², RMSE) for validation.

    Usage:
        >>> fitter = PayoutCurveFitter(curve_type='power_law')
        >>> ranks = np.array([1, 2, 3, 5, 10, 20])
        >>> payouts = np.array([100000, 50000, 30000, 15000, 5000, 2000])
        >>> fitter.fit(ranks, payouts)
        >>> predictions = fitter.predict(np.array([1, 2, 7, 15]))
        >>> quality = fitter.get_fit_quality()
    """

    # Define model type constants
    CURVE_TYPE_POWER_LAW = 'power_law'
    CURVE_TYPE_EXPONENTIAL = 'exponential'

    # Define contest size tiers
    TIER_SMALL = 'small'
    TIER_MEDIUM = 'medium'
    TIER_LARGE = 'large'

    # Tier thresholds
    TIER_SMALL_MAX = 5000
    TIER_MEDIUM_MIN = 5000
    TIER_MEDIUM_MAX = 20000
    TIER_LARGE_MIN = 20000

    def __init__(
        self,
        curve_type: str = CURVE_TYPE_POWER_LAW,
        contest_size_tier: str = TIER_LARGE
    ):
        """
        Initialize payout curve fitter.

        Args:
            curve_type: Type of curve to fit ('power_law' or 'exponential')
            contest_size_tier: Contest size tier ('small', 'medium', 'large')

        Raises:
            ValueError: If curve_type or contest_size_tier is invalid
        """
        if curve_type not in [self.CURVE_TYPE_POWER_LAW, self.CURVE_TYPE_EXPONENTIAL]:
            raise ValueError(
                f"Invalid curve_type: {curve_type}. "
                f"Must be '{self.CURVE_TYPE_POWER_LAW}' or '{self.CURVE_TYPE_EXPONENTIAL}'"
            )

        if contest_size_tier not in [self.TIER_SMALL, self.TIER_MEDIUM, self.TIER_LARGE]:
            raise ValueError(
                f"Invalid contest_size_tier: {contest_size_tier}. "
                f"Must be '{self.TIER_SMALL}', '{self.TIER_MEDIUM}', or '{self.TIER_LARGE}'"
            )

        self.curve_type = curve_type
        self.contest_size_tier = contest_size_tier
        self.params_: Optional[Tuple[float, float]] = None
        self.fit_success_: bool = False
        self.fit_quality_: Optional[Dict[str, float]] = None
        self.n_observations_: int = 0

        logger.info(
            f"Initialized PayoutCurveFitter: "
            f"curve_type={curve_type}, "
            f"contest_size_tier={contest_size_tier}"
        )

    def _power_law_func(self, rank: np.ndarray, a: float, b: float) -> np.ndarray:
        """Power-law function for curve fitting."""
        return a * np.power(rank, -b)

    def _exponential_func(self, rank: np.ndarray, a: float, b: float) -> np.ndarray:
        """Exponential function for curve fitting."""
        return a * np.exp(-b * rank)

    def fit(
        self,
        ranks: np.ndarray,
        payouts: np.ndarray
    ) -> 'PayoutCurveFitter':
        """
        Fit payout curve model to historical data.

        Uses scipy.optimize.curve_fit to fit parametric model to historical
        payout data. Computes R² and RMSE for fit quality assessment.

        Args:
            ranks: Array of finish positions (1-indexed)
            payouts: Array of corresponding payout amounts

        Returns:
            self (fitted fitter)

        Raises:
            ValueError: If input data is invalid
            RuntimeError: If curve fitting fails
        """
        ranks_array = np.asarray(ranks, dtype=float)
        payouts_array = np.asarray(payouts, dtype=float)

        # Validate input
        if len(ranks_array) != len(payouts_array):
            raise ValueError(
                f"Ranks and payouts must have same length: "
                f"got {len(ranks_array)} and {len(payouts_array)}"
            )

        if len(ranks_array) < 2:
            raise ValueError("Need at least 2 data points to fit curve")

        if np.any(ranks_array <= 0):
            raise ValueError("Ranks must be positive (1-indexed)")

        if np.any(payouts_array < 0):
            raise ValueError("Payouts must be non-negative")

        self.n_observations_ = len(ranks_array)

        logger.info(
            f"Fitting {self.curve_type} payout curve to "
            f"{self.n_observations_} data points "
            f"(tier: {self.contest_size_tier})"
        )

        # Select fitting function based on curve type
        if self.curve_type == self.CURVE_TYPE_POWER_LAW:
            func = self._power_law_func
            # Initial guess: a ≈ first payout, b ≈ 1
            p0 = [payouts_array[0], 1.0]
        else:  # exponential
            func = self._exponential_func
            # Initial guess: a ≈ first payout, b ≈ 0.01
            p0 = [payouts_array[0], 0.01]

        # Parameter bounds: a > 0, b > 0
        bounds = ([0, 0], [np.inf, np.inf])

        try:
            # Fit curve using scipy.optimize.curve_fit
            self.params_, pcov = curve_fit(
                func,
                ranks_array,
                payouts_array,
                p0=p0,
                bounds=bounds,
                maxfev=10000
            )

            # Extract parameter standard errors from covariance matrix
            perr = np.sqrt(np.diag(pcov))

            a_fit, b_fit = self.params_
            logger.info(
                f"Fitted {self.curve_type} params: "
                f"a={a_fit:.2f} ± {perr[0]:.2f}, "
                f"b={b_fit:.4f} ± {perr[1]:.4f}"
            )

        except RuntimeError as e:
            raise RuntimeError(f"Curve fitting failed: {e}")

        # Compute fit quality metrics
        predicted = func(ranks_array, *self.params_)

        # R² (coefficient of determination)
        ss_res = np.sum((payouts_array - predicted) ** 2)
        ss_tot = np.sum((payouts_array - np.mean(payouts_array)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # RMSE (root mean squared error)
        rmse = np.sqrt(np.mean((payouts_array - predicted) ** 2))

        self.fit_quality_ = {
            'r_squared': r_squared,
            'rmse': rmse,
            'n_observations': self.n_observations_
        }

        logger.info(
            f"Fit quality: R²={r_squared:.4f}, RMSE=${rmse:.2f}, "
            f"n={self.n_observations_}"
        )

        # Validate fit quality
        if r_squared < 0.90:
            logger.warning(
                f"Low R² ({r_squared:.4f}) - payout curve may not fit data well. "
                f"Consider using different curve type or checking data quality."
            )

        self.fit_success_ = True
        return self

    def predict(self, ranks: np.ndarray) -> np.ndarray:
        """
        Predict payouts for given finish positions using fitted curve.

        Interpolates/extrapolates for unobserved ranks using the fitted
        parametric model.

        Args:
            ranks: Array of finish positions

        Returns:
            Array of predicted payouts

        Raises:
            RuntimeError: If model has not been fit
        """
        if not self.fit_success_:
            raise RuntimeError("Model must be fit before prediction. Call fit() first.")

        ranks_array = np.asarray(ranks, dtype=float)

        # Use fitted curve to predict
        if self.curve_type == self.CURVE_TYPE_POWER_LAW:
            payouts = self._power_law_func(ranks_array, *self.params_)
        else:  # exponential
            payouts = self._exponential_func(ranks_array, *self.params_)

        return payouts

    def get_curve(self) -> Union[PowerLawPayoutCurve, ExponentialPayoutCurve]:
        """
        Return fitted curve object.

        Returns:
            Fitted curve instance (PowerLawPayoutCurve or ExponentialPayoutCurve)

        Raises:
            RuntimeError: If model has not been fit
        """
        if not self.fit_success_:
            raise RuntimeError("Model must be fit before getting curve. Call fit() first.")

        a, b = self.params_

        if self.curve_type == self.CURVE_TYPE_POWER_LAW:
            return PowerLawPayoutCurve(a=a, b=b)
        else:  # exponential
            return ExponentialPayoutCurve(a=a, b=b)

    def get_fit_quality(self) -> Dict[str, float]:
        """
        Return fit quality metrics.

        Returns:
            Dict with keys:
            - r_squared: Coefficient of determination (0-1, higher is better)
            - rmse: Root mean squared error (in dollars, lower is better)
            - n_observations: Number of data points used to fit curve

        Raises:
            RuntimeError: If model has not been fit
        """
        if not self.fit_success_:
            raise RuntimeError(
                "Model must be fit before getting fit quality. Call fit() first."
            )

        return self.fit_quality_

    def __repr__(self) -> str:
        if self.fit_success_:
            a, b = self.params_
            return (
                f"PayoutCurveFitter("
                f"curve_type={self.curve_type}, "
                f"contest_size_tier={self.contest_size_tier}, "
                f"a={a:.2f}, b={b:.4f}, "
                f"R²={self.fit_quality_['r_squared']:.4f})"
            )
        else:
            return (
                f"PayoutCurveFitter("
                f"curve_type={self.curve_type}, "
                f"contest_size_tier={self.contest_size_tier}, "
                f"unfit)"
            )


def get_payout_curve_for_contest(
    contest_size: int,
    curves_by_tier: Dict[str, PayoutCurveFitter]
) -> Optional[PayoutCurveFitter]:
    """
    Get appropriate payout curve fitter for a given contest size.

    Determines contest size tier and returns corresponding curve fitter.

    Args:
        contest_size: Number of entries in the contest
        curves_by_tier: Dict mapping tier names to PayoutCurveFitter instances

    Returns:
        PayoutCurveFitter for the contest size tier, or None if tier not found

    Example:
        >>> curves = fit_payout_curves_by_tier(historical_contests)
        >>> curve = get_payout_curve_for_contest(10000, curves)
        >>> # Returns 'large' tier curve for 10K contest
    """
    # Determine tier from contest size
    if contest_size < PayoutCurveFitter.TIER_SMALL_MAX:
        tier = PayoutCurveFitter.TIER_SMALL
    elif contest_size < PayoutCurveFitter.TIER_LARGE_MIN:
        tier = PayoutCurveFitter.TIER_MEDIUM
    else:
        tier = PayoutCurveFitter.TIER_LARGE

    logger.debug(f"Contest size {contest_size} -> tier '{tier}'")

    return curves_by_tier.get(tier)


def interpolate_payout_for_rank(
    rank: int,
    curve: PayoutCurveFitter
) -> float:
    """
    Predict payout for a specific finish position using fitted curve.

    Args:
        rank: Finish position (1-indexed)
        curve: Fitted PayoutCurveFitter instance

    Returns:
        Predicted payout amount

    Raises:
        ValueError: If rank is invalid
        RuntimeError: If curve has not been fit

    Example:
        >>> fitter = PayoutCurveFitter()
        >>> fitter.fit(ranks, payouts)
        >>> payout = interpolate_payout_for_rank(150, fitter)
        >>> print(f"Predicted payout for 150th place: ${payout:.2f}")
    """
    if rank <= 0:
        raise ValueError(f"Rank must be positive (1-indexed), got {rank}")

    if not curve.fit_success_:
        raise RuntimeError("Curve must be fit before interpolation. Call fit() first.")

    # Warn if extrapolating far beyond fitted data
    if rank > curve.n_observations_ * 2:
        logger.warning(
            f"Extrapolating far beyond fitted data: "
            f"rank={rank} vs n_observations={curve.n_observations_}. "
            f"Payout estimates may be unreliable."
        )

    # Predict payout for single rank
    payout = curve.predict(np.array([rank]))[0]

    return float(payout)


def load_historical_payouts(contest_id: str, db):
    """
    Query historical contest payout data from database.

    This function retrieves historical payout data for a specific contest
    from the database. It requires a contest_results table to be set up.

    Args:
        contest_id: Contest identifier to query
        db: SQLAlchemy database session

    Returns:
        Tuple of (ranks_array, payouts_array) containing historical payout data

    Raises:
        ValueError: If contest_id is not found in database

    Note:
        This is a placeholder function. The actual implementation requires:
        1. A contest_results table in the database
        2. SQLAlchemy ORM models for contest data
        3. Historical payout data to be loaded

    Example:
        >>> from apps.backend.app.models import SessionLocal
        >>> db = SessionLocal()
        >>> ranks, payouts = load_historical_payouts('dk-2024-02-18-gpp', db)
        >>> fitter = PayoutCurveFitter()
        >>> fitter.fit(ranks, payouts)
    """
    # TODO: Implement database query once contest_results table is set up
    # Expected implementation:
    # contest = db.query(ContestResult).filter(ContestResult.contest_id == contest_id).first()
    # if not contest:
    #     raise ValueError(f"Contest '{contest_id}' not found in database")
    # ranks = np.array([p.rank for p in contest.payouts])
    # payouts = np.array([p.payout for p in contest.payouts])
    # return ranks, payouts

    raise NotImplementedError(
        "load_historical_payouts requires contest_results table to be set up. "
        "Use HistoricalContestData objects directly for now."
    )


def fit_payout_curves_by_tier(
    historical_contests: List
) -> Dict[str, PayoutCurveFitter]:
    """
    Fit separate payout curves for each contest size tier.

    Groups historical contests by size tier (small, medium, large) and
    fits a payout curve for each tier using aggregated payout data.

    Args:
        historical_contests: List of HistoricalContestData objects

    Returns:
        Dict mapping tier names ('small', 'medium', 'large') to
        fitted PayoutCurveFitter instances

    Example:
        >>> contests = load_historical_contests()  # List of HistoricalContestData
        >>> curves = fit_payout_curves_by_tier(contests)
        >>> print(f"Fitted {len(curves)} tier curves")
        >>> for tier, fitter in curves.items():
        ...     quality = fitter.get_fit_quality()
        ...     print(f"{tier}: R²={quality['r_squared']:.4f}")
    """
    # Group contests by tier
    tier_contests = {
        PayoutCurveFitter.TIER_SMALL: [],
        PayoutCurveFitter.TIER_MEDIUM: [],
        PayoutCurveFitter.TIER_LARGE: []
    }

    for contest in historical_contests:
        # Determine tier from contest size
        if contest.contest_size < PayoutCurveFitter.TIER_SMALL_MAX:
            tier = PayoutCurveFitter.TIER_SMALL
        elif contest.contest_size < PayoutCurveFitter.TIER_LARGE_MIN:
            tier = PayoutCurveFitter.TIER_MEDIUM
        else:
            tier = PayoutCurveFitter.TIER_LARGE

        tier_contests[tier].append(contest)

    # Fit curve for each tier
    curves_by_tier = {}

    for tier, contests in tier_contests.items():
        if len(contests) == 0:
            logger.warning(f"No contests found for tier '{tier}', skipping")
            continue

        logger.info(
            f"Fitting payout curve for '{tier}' tier "
            f"({len(contests)} contests)"
        )

        # Aggregate payout data from all contests in this tier
        all_ranks = []
        all_payouts = []

        for contest in contests:
            # Extract ranks and payouts from contest data
            for payout_data in contest.payouts:
                all_ranks.append(payout_data.rank)
                all_payouts.append(payout_data.payout)

        if len(all_ranks) == 0:
            logger.warning(f"No payout data found for tier '{tier}', skipping")
            continue

        # Convert to numpy arrays
        ranks_array = np.array(all_ranks)
        payouts_array = np.array(all_payouts)

        # Fit curve (default to power-law)
        fitter = PayoutCurveFitter(
            curve_type=PayoutCurveFitter.CURVE_TYPE_POWER_LAW,
            contest_size_tier=tier
        )

        try:
            fitter.fit(ranks_array, payouts_array)

            # Log fit quality
            quality = fitter.get_fit_quality()
            logger.info(
                f"'{tier}' tier curve fitted: "
                f"R²={quality['r_squared']:.4f}, "
                f"RMSE=${quality['rmse']:.2f}, "
                f"n={quality['n_observations']}"
            )

            curves_by_tier[tier] = fitter

        except Exception as e:
            logger.error(f"Failed to fit curve for tier '{tier}': {e}")
            continue

    logger.info(f"Fitted {len(curves_by_tier)} payout curves (by tier)")

    return curves_by_tier
