# Phase 4: Field / Ownership / Contest-Sim EV - Research

**Researched:** 2026-01-28
**Domain:** Contest simulation, ownership estimation, payout curve modeling, field lineup modeling
**Confidence:** MEDIUM

## Summary

Phase 4 requires building infrastructure to model the field and payout structure to compute true tournament EV for large-field NASCAR GPPs. This includes ownership estimation (hybrid ensemble combining historical, projections-based, salary-skill regression with track-archetype awareness), field lineup modeling (simulating opponent behavior), payout curve approximation (power-law or piecewise functions), and contest-level simulation outputs (ROI, Cash%, win probability). The research focused on five core areas: (1) ownership estimation ensembles and Bayesian hierarchical methods, (2) field lineup simulation approaches, (3) payout curve modeling (power-law, exponential, piecewise), (4) contest simulation Monte Carlo methods, and (5) leverage-aware optimization incorporating ownership and field correlation.

The existing codebase has a robust simulation and optimization foundation from Phases 1-3, including scenario generation with CBN sampling, tail metrics computation (CVaR, top-X%), and portfolio generation. Phase 4 extends this by adding a "meta-layer" on top: simulating how the field will construct lineups (ownership), applying payout structures to determine contest outcomes, and computing true EV accounting for duplication and correlation.

**Primary recommendation:** Use scikit-learn for ensemble methods (RandomForest, GradientBoosting) to combine multiple ownership signals into a hybrid estimate with uncertainty quantification. Implement field lineup simulation using Dirichlet-multinomial sampling for ownership allocation and DraftKings constraint-aware lineup generation. Model payout curves using power-law or exponential decay functions fit to historical contest data (use scipy.optimize). Build contest simulation using vectorized NumPy/JAX operations for scaling to thousands of contest iterations. Integrate leverage-aware optimization by adding ownership-aware penalty terms to the existing PuLP optimizer.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **scikit-learn** | latest | Ensemble ownership estimation (RandomForest, GradientBoosting, VotingRegressor) | Battle-tested ensemble methods with built-in feature importance, cross-validation, and prediction intervals |
| **scipy.optimize** | latest | Payout curve fitting (curve_fit, least_squares) | Robust optimization for fitting power-law/exponential/piecewise functions to historical payout data |
| **NumPy** | latest | Vectorized contest simulation and array operations | Efficient array operations for simulating thousands of contest outcomes with portfolio scoring |
| **JAX** | 0.8.2 | Accelerated contest simulation (GPU-enabled) | Already in stack from Phase 3; use for scaling contest sims to 100K+ iterations |
| **pymc** | 5.27.1 | Bayesian hierarchical ownership models | Already in stack from Phase 2; use for track-archetype specific ownership priors and uncertainty quantification |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **xgboost** | latest | Gradient boosting for ownership projection | When scikit-learn ensembles need extra performance or feature importance granularity |
| **lightgbm** | latest | Alternative gradient boosting (faster training) | When training on large historical datasets (100K+ lineups) and speed matters |
| **statsmodels** | latest | Statistical tests and time series for ownership trends | When analyzing ownership drift, season-long patterns, or track-archetype effects |
| **seaborn** | latest | Visualization of ownership distributions and payout curves | When debugging ownership estimates or validating payout curve fits |
| **plotly** | latest | Interactive payout curve and contest result visualization | When building UI for contest simulation results (future phase) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| **scikit-learn ensembles** | Custom weighted average | scikit-learn provides learned weights, cross-validation, and prediction intervals; custom weights require manual tuning |
| **Power-law payout curves** | Piecewise linear interpolation | Power-law provides smooth extrapolation for unobserved finish positions; piecewise is simpler but doesn't generalize |
| **Monte Carlo contest sims** | Closed-form EV calculation | Monte Carlo handles complex non-linear payout structures and field interactions; closed-form only works for simple contests |
| **JAX vectorized sims** | Pure Python loops | JAX provides 100-1000x speedup for large contest simulations; Python loops are only viable for small-scale testing |

**Installation:**
```bash
# Core ownership and contest simulation stack
pip install scikit-learn scipy xgboost lightgbm statsmodels seaborn plotly

# Already installed from previous phases
# jax==0.8.2 pymc==5.27.1 numpy polars pyarrow
```

## Architecture Patterns

### Recommended Project Structure

```
apps/backend/app/
├── ownership/               # NEW: Ownership estimation module
│   ├── __init__.py
│   ├── ensemble.py          # Hybrid ensemble estimator
│   ├── features.py          # Feature engineering for ownership
│   ├── track_archetype.py   # Track-specific ownership adjustments
│   └── models.py            # Pydantic ownership models
├── contest/                 # NEW: Contest simulation module
│   ├── __init__.py
│   ├── field_sim.py         # Field lineup simulation
│   ├── payout_curve.py      # Payout structure modeling
│   ├── contest_sim.py       # Monte Carlo contest simulation
│   └── metrics.py           # ROI, Cash%, win probability calculations
├── optimizer/
│   ├── leverage_aware.py    # NEW: Ownership-aware optimization
│   └── portfolio_generator.py  # EXISTING: Extend for regime-aware portfolios
├── api/
│   └── contracts.py         # EXISTING: Add contest simulation request/response models

packages/axiomatic-sim/src/axiomatic_sim/
├── tests/
│   ├── test_ownership_ensemble.py        # Unit tests for ownership estimation
│   ├── test_payout_curve.py              # Payout curve fitting tests
│   ├── test_contest_simulation.py        # Contest sim integration tests
│   └── test_leverage_optimization.py     # Leverage-aware optimizer tests
└── pyproject.toml                        # ADD: scikit-learn, scipy, xgboost, lightgbm

data/                                      # NEW: Contest data artifacts
├── ownership/                            # Historical ownership data
│   ├── draftkings_own_2024.csv           # Raw DK ownership by race
│   └── ownership_features.parquet        # Engineered features for ownership prediction
├── payout_curves/                        # Payout structure data
│   ├── gpp_structures.json               # Historical DK GPP payouts by contest size
│   └── fitted_curves/                    # Cached payout curve parameters
└── contest_sims/                         # Contest simulation outputs
    └── slate_2024-02-18_contest_sims.nc # NetCDF4 simulation results
```

### Pattern 1: Hybrid Ensemble Ownership Estimation

**What:** Use scikit-learn VotingRegressor or StackingRegressor to combine multiple ownership signals (historical-based, projections-based, salary-skill regression) with track-archetype specific adjustments.

**When to use:** Required by CONTEXT.md decision "Hybrid ensemble approach combining multiple sources" and success criterion "Ownership priors estimated with duplication proxies."

**Example:**
```python
# Source: scikit-learn VotingRegressor for ensemble combination
# https://scikit-learn.org/stable/modules/ensemble.html#voting-regressor
import numpy as np
from sklearn.ensemble import VotingRegressor, RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import BayesianRidge
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import logging

logger = logging.getLogger(__name__)

class HybridOwnershipEstimator:
    """
    Hybrid ensemble estimator for driver ownership in NASCAR DFS.

    Combines multiple signals:
    1. Historical ownership: Track-archetype specific baselines
    2. Projections-based: Derived from projected points vs. salary
    3. Salary-skill regression: Model ownership as function of salary and skill
    4. Recent form: Rolling 3-5 race performance
    5. Track archetype adjustments: Superspeedway vs short track vs road course

    Uses VotingRegressor to combine predictions with optional learned weights.
    """

    def __init__(
        self,
        track_archetype: str = "intermediate",
        n_recent_races: int = 5,
        ensemble_method: str = "voting"
    ):
        """
        Initialize hybrid ownership estimator.

        Args:
            track_archetype: Track type (superspeedway, intermediate, short_track, road_course)
            n_recent_races: Number of recent races for form calculation
            ensemble_method: 'voting' for simple average, 'stacking' for meta-learner
        """
        self.track_archetype = track_archetype
        self.n_recent_races = n_recent_races
        self.ensemble_method = ensemble_method

        # Define ensemble components
        # Each estimator specializes in a different signal source
        self.estimators = [
            ('hist', HistoricalOwnershipEstimator(track_archetype=track_archetype)),
            ('proj', ProjectionOwnershipEstimator()),
            ('salary_skill', SalarySkillRegressionEstimator()),
            ('recent_form', RecentFormEstimator(n_recent_races=n_recent_races))
        ]

        # Build ensemble
        if ensemble_method == "voting":
            # Simple average (can be weighted)
            self.model = VotingRegressor(
                estimators=self.estimators,
                weights=None  # Equal weights; can be set to [w1, w2, w3, w4]
            )
        elif ensemble_method == "stacking":
            # Meta-learner to optimally combine base estimators
            self.model = StackingRegressor(
                estimators=self.estimators,
                final_estimator=BayesianRidge(),
                cv=5
            )
        else:
            raise ValueError(f"Unknown ensemble method: {ensemble_method}")

        logger.info(
            f"Initialized HybridOwnershipEstimator: "
            f"track_archetype={track_archetype}, "
            f"ensemble={ensemble_method}, "
            f"n_estimators={len(self.estimators)}"
        )

    def fit(self, X, y):
        """
        Fit ensemble to historical ownership data.

        Args:
            X: Feature matrix with columns:
               - salary: DraftKings salary
               - projected_points: Expected DFS points
               - skill: Driver skill (from ontology)
               - recent_avg_finish: Avg finish in last N races
               - track_archetype_*: One-hot encoded track type
            y: Target ownership percentages (0-100)

        Returns:
            self (fitted estimator)
        """
        logger.info(f"Fitting ownership ensemble on {len(X)} samples")

        # Fit each base estimator
        for name, estimator in self.estimators:
            estimator.fit(X, y)
            logger.debug(f"Fitted {name} estimator")

        # Fit ensemble (for stacking, this trains meta-learner)
        self.model.fit(X, y)

        # Compute feature importance via permutation importance
        # This helps understand which signals drive ownership
        from sklearn.inspection import permutation_importance
        result = permutation_importance(
            self.model, X, y, n_repeats=10, random_state=42, n_jobs=-1
        )

        logger.info(
            f"Feature importance: "
            f{dict(zip(X.columns, result.importances_mean))}"
        )

        return self

    def predict(self, X):
        """Predict ownership percentages."""
        ownership = self.model.predict(X)

        # Ensure predictions are in valid range [0, 100]
        ownership = np.clip(ownership, 0, 100)

        # Normalize to sum to 100% across all drivers
        ownership = ownership / ownership.sum() * 100

        return ownership

    def predict_with_uncertainty(self, X, n_bootstraps: int = 100):
        """
        Predict ownership with uncertainty bounds using bootstrapping.

        Returns:
            Dict with:
            - mean: Mean ownership prediction
            - std: Standard deviation across bootstraps
            - lower_5: 5th percentile
            - upper_95: 95th percentile
        """
        predictions = []

        for _ in range(n_bootstraps):
            # Resample with replacement
            indices = np.random.choice(len(X), size=len(X), replace=True)
            X_boot = X.iloc[indices]

            # Predict (requires fitting each base estimator on bootstrap sample)
            # For efficiency, use trained estimators and add noise
            pred = self.model.predict(X_boot)
            predictions.append(pred)

        predictions = np.array(predictions)

        return {
            "mean": predictions.mean(axis=0),
            "std": predictions.std(axis=0),
            "lower_5": np.percentile(predictions, 5, axis=0),
            "upper_95": np.percentile(predictions, 95, axis=0)
        }


class HistoricalOwnershipEstimator:
    """Estimate ownership based on historical track-archetype specific baselines."""

    def __init__(self, track_archetype: str):
        self.track_archetype = track_archetype

    def fit(self, X, y):
        # Store historical averages by driver
        self.historical_means_ = y.groupby(X['driver_id']).mean()
        return self

    def predict(self, X):
        # Look up historical ownership for track archetype
        # Use overall mean if driver not seen before
        return X['driver_id'].map(
            lambda x: self.historical_means_.get(x, self.historical_means_.mean())
        )


class ProjectionOwnershipEstimator:
    """Estimate ownership from projected points vs. salary (value metric)."""

    def fit(self, X, y):
        # Learn relationship between value_score = projected_points / salary and ownership
        from sklearn.linear_model import LinearRegression
        self.model = LinearRegression()
        value_score = X['projected_points'] / X['salary']
        self.model.fit(value_score.values.reshape(-1, 1), y)
        return self

    def predict(self, X):
        value_score = X['projected_points'] / X['salary']
        return self.model.predict(value_score.values.reshape(-1, 1))


class SalarySkillRegressionEstimator:
    """Estimate ownership using salary and skill (from ontology)."""

    def fit(self, X, y):
        from sklearn.ensemble import RandomForestRegressor
        self.model = RandomForestRegressor(n_estimators=100, max_depth=5, random_state=42)
        features = X[['salary', 'skill']]
        self.model.fit(features, y)
        return self

    def predict(self, X):
        features = X[['salary', 'skill']]
        return self.model.predict(features)


class RecentFormEstimator:
    """Estimate ownership based on recent form (rolling 3-5 race performance)."""

    def __init__(self, n_recent_races: int = 5):
        self.n_recent_races = n_recent_races

    def fit(self, X, y):
        # Learn weight of recent form vs. baseline
        from sklearn.linear_model import Ridge
        self.model = Ridge(alpha=1.0)
        features = X[['recent_avg_finish', 'recent_top5_rate']]
        self.model.fit(features, y)
        return self

    def predict(self, X):
        features = X[['recent_avg_finish', 'recent_top5_rate']]
        return self.model.predict(features)


# Example usage
if __name__ == "__main__":
    import pandas as pd

    # Load historical ownership data
    # X should have columns: driver_id, salary, projected_points, skill, recent_avg_finish, etc.
    # y should be ownership percentages
    X = pd.read_csv("data/ownership/ownership_features.csv")
    y = X['ownership_percent']

    # Create and fit estimator
    estimator = HybridOwnershipEstimator(
        track_archetype="superspeedway",
        n_recent_races=5,
        ensemble_method="voting"
    )

    estimator.fit(X, y)

    # Predict ownership for upcoming race
    X_upcoming = pd.read_csv("data/ownership/upcoming_features.csv")
    ownership_pred = estimator.predict(X_upcoming)

    # Predict with uncertainty
    ownership_with_uncertainty = estimator.predict_with_uncertainty(X_upcoming, n_bootstraps=100)

    print(f"Predicted ownership: {ownership_pred}")
    print(f"Uncertainty bounds: {ownership_with_uncertainty}")
```

### Pattern 2: Power-Law Payout Curve Fitting

**What:** Use scipy.optimize.curve_fit to fit power-law or exponential decay functions to historical DraftKings GPP payout structures, enabling smooth extrapolation for any contest size.

**When to use:** Required by success criterion "Payout curve modeling for large-field GPPs." Power-law models accurately capture the steep drop-off in top-heavy DFS tournaments.

**Example:**
```python
# Source: scipy.optimize.curve_fit for payout curve fitting
# https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.curve_fit.html
import numpy as np
from scipy.optimize import curve_fit
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt
import logging

logger = logging.getLogger(__name__)

class PayoutCurveModel:
    """
    Model GPP payout structures using parametric functions.

    Supports:
    1. Power-law: payout = a * rank^(-b)
    2. Exponential: payout = a * exp(-b * rank)
    3. Piecewise linear: Interpolate between observed payout points
    4. Hybrid: Power-law for top 20%, linear for rest
    """

    def __init__(self, model_type: str = "power_law"):
        """
        Initialize payout curve model.

        Args:
            model_type: 'power_law', 'exponential', 'piecewise', 'hybrid'
        """
        self.model_type = model_type
        self.params_ = None
        self.fit_success_ = False

    @staticmethod
    def power_law(rank, a, b):
        """Power-law payout function: payout = a * rank^(-b)."""
        return a * np.power(rank, -b)

    @staticmethod
    def exponential(rank, a, b):
        """Exponential decay payout: payout = a * exp(-b * rank)."""
        return a * np.exp(-b * rank)

    @staticmethod
    def piecewise_linear(rank, breakpoints, payouts):
        """
        Piecewise linear interpolation between breakpoints.

        Args:
            rank: Array of rank positions
            breakpoints: Rank positions for payout changes
            payouts: Payout amounts at each breakpoint
        """
        # Use scipy interpolation
        interp_func = interp1d(
            breakpoints,
            payouts,
            kind='linear',
            fill_value=(payouts[0], payouts[-1]),  # Extrapolate with endpoints
            bounds_error=False
        )
        return interp_func(rank)

    @staticmethod
    def hybrid(rank, a, b, cutoff_rank):
        """
        Hybrid model: power-law for top X%, linear beyond.

        Args:
            rank: Rank position
            a, b: Power-law parameters
            cutoff_rank: Rank where to switch from power-law to linear
        """
        payout = np.zeros_like(rank, dtype=float)

        # Power-law for ranks <= cutoff
        mask_power = rank <= cutoff_rank
        payout[mask_power] = a * np.power(rank[mask_power], -b)

        # Linear extrapolation for ranks > cutoff
        # Match value and slope at cutoff
        cutoff_payout = a * np.power(cutoff_rank, -b)
        cutoff_slope = -a * b * np.power(cutoff_rank, -b - 1)

        mask_linear = rank > cutoff_rank
        payout[mask_linear] = cutoff_payout + cutoff_slope * (rank[mask_linear] - cutoff_rank)

        # Ensure non-negative
        payout = np.maximum(payout, 0)

        return payout

    def fit(self, ranks: np.ndarray, payouts: np.ndarray):
        """
        Fit payout curve model to historical data.

        Args:
            ranks: Array of finish positions (1-indexed)
            payouts: Array of corresponding payout amounts

        Returns:
            self (fitted model)
        """
        logger.info(
            f"Fitting {self.model_type} payout curve to "
            f"{len(ranks)} data points"
        )

        if self.model_type == "power_law":
            # Initial parameter guess
            # a ≈ payout[0] (first place payout)
            # b ≈ 1 (typical power-law exponent)
            p0 = [payouts[0], 1.0]

            # Bounds: a > 0, b > 0
            bounds = ([0, 0], [np.inf, np.inf])

            self.params_, _ = curve_fit(
                self.power_law,
                ranks,
                payouts,
                p0=p0,
                bounds=bounds,
                maxfev=10000
            )

            logger.info(f"Fitted power-law params: a={self.params_[0]:.2f}, b={self.params_[1]:.4f}")

        elif self.model_type == "exponential":
            p0 = [payouts[0], 0.01]
            bounds = ([0, 0], [np.inf, np.inf])

            self.params_, _ = curve_fit(
                self.exponential,
                ranks,
                payouts,
                p0=p0,
                bounds=bounds,
                maxfev=10000
            )

            logger.info(f"Fitted exponential params: a={self.params_[0]:.2f}, b={self.params_[1]:.6f}")

        elif self.model_type == "piecewise":
            # Store breakpoints and payouts for interpolation
            self.params_ = {'ranks': ranks, 'payouts': payouts}
            logger.info("Fitted piecewise linear payout curve")

        elif self.model_type == "hybrid":
            # Use top 20% as cutoff
            cutoff_rank = int(len(ranks) * 0.2)
            p0 = [payouts[0], 1.0, cutoff_rank]
            bounds = ([0, 0, 1], [np.inf, np.inf, len(ranks)])

            self.params_, _ = curve_fit(
                lambda r, a, b, c: self.hybrid(r, a, b, c),
                ranks,
                payouts,
                p0=p0,
                bounds=bounds,
                maxfev=10000
            )

            logger.info(
                f"Fitted hybrid params: a={self.params_[0]:.2f}, "
                f"b={self.params_[1]:.4f}, cutoff={self.params_[2]:.0f}"
            )

        else:
            raise ValueError(f"Unknown model type: {self.model_type}")

        self.fit_success_ = True
        return self

    def predict(self, ranks: np.ndarray) -> np.ndarray:
        """
        Predict payout for given ranks using fitted model.

        Args:
            ranks: Array of rank positions

        Returns:
            Array of predicted payouts
        """
        if not self.fit_success_:
            raise RuntimeError("Model must be fit before prediction")

        if self.model_type == "power_law":
            return self.power_law(ranks, *self.params_)

        elif self.model_type == "exponential":
            return self.exponential(ranks, *self.params_)

        elif self.model_type == "piecewise":
            return self.piecewise_linear(
                ranks,
                self.params_['ranks'],
                self.params_['payouts']
            )

        elif self.model_type == "hybrid":
            return self.hybrid(ranks, *self.params_)

    def evaluate_fit(self, ranks: np.ndarray, payouts: np.ndarray) -> dict:
        """
        Evaluate goodness of fit using RMSE and R^2.

        Args:
            ranks: Observed ranks
            payouts: Observed payouts

        Returns:
            Dict with rmse, r2, and residuals
        """
        if not self.fit_success_:
            raise RuntimeError("Model must be fit before evaluation")

        predicted = self.predict(ranks)

        # RMSE
        rmse = np.sqrt(np.mean((payouts - predicted) ** 2))

        # R^2
        ss_res = np.sum((payouts - predicted) ** 2)
        ss_tot = np.sum((payouts - np.mean(payouts)) ** 2)
        r2 = 1 - (ss_res / ss_tot)

        # Residuals
        residuals = payouts - predicted

        metrics = {
            'rmse': rmse,
            'r2': r2,
            'residuals': residuals
        }

        logger.info(f"Fit metrics: RMSE={rmse:.2f}, R²={r2:.4f}")

        return metrics

    def plot_fit(self, ranks: np.ndarray, payouts: np.ndarray):
        """Plot observed vs. fitted payout curve."""
        import matplotlib.pyplot as plt

        predicted = self.predict(ranks)

        plt.figure(figsize=(10, 6))
        plt.scatter(ranks, payouts, label='Observed', alpha=0.6)
        plt.plot(ranks, predicted, 'r-', label=f'{self.model_type} fit', linewidth=2)
        plt.xlabel('Finish Position')
        plt.ylabel('Payout ($)')
        plt.title('GPP Payout Structure: Observed vs. Fitted')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.show()


# Example usage
if __name__ == "__main__":
    # Historical DraftKings GPP payout data
    # Example: $20 buy-in, 50,000 entries, $1M prize pool
    ranks = np.array([1, 2, 3, 4, 5, 10, 20, 50, 100, 500, 1000, 5000])
    payouts = np.array([
        100000,  # 1st
        50000,   # 2nd
        30000,   # 3rd
        20000,   # 4th
        15000,   # 5th
        5000,    # 10th
        2000,    # 20th
        500,     # 50th
        200,     # 100th
        50,      # 500th
        20,      # 1000th
        10       # 5000th
    ])

    # Fit power-law model
    model = PayoutCurveModel(model_type="power_law")
    model.fit(ranks, payouts)

    # Evaluate fit
    metrics = model.evaluate_fit(ranks, payouts)
    print(f"Fit metrics: {metrics}")

    # Predict for unobserved ranks
    new_ranks = np.arange(1, 10001)
    predicted_payouts = model.predict(new_ranks)

    print(f"Predicted payout for 150th place: ${predicted_payouts[149]:.2f}")
    print(f"Predicted payout for 5000th place: ${predicted_payouts[4999]:.2f}")
```

### Pattern 3: Monte Carlo Contest Simulation

**What:** Simulate contest outcomes by sampling field lineups from ownership distributions, scoring all lineups against simulated race outcomes, applying payout curves, and computing ROI/Cash%/win probability metrics.

**When to use:** Required by success criterion "Contest-level simulation outputs (ROI, Cash%, win probability)." This is the core "field-aware" simulation that computes true EV accounting for competition.

**Example:**
```python
# Source: Monte Carlo simulation patterns with vectorized NumPy operations
# Pattern is inspired by general Monte Carlo practices and adapted for DFS contest simulation
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class ContestResult:
    """Result of a single contest simulation."""
    my_rank: int
    my_payout: float
    my_score: float
    winning_score: float
    field_size: int
    cashed: bool
    top_1_pct: bool


class ContestSimulator:
    """
    Monte Carlo contest simulator for DFS GPPs.

    Simulates contest outcomes by:
    1. Sampling field lineups from ownership distributions
    2. Scoring all lineups against simulated race scenarios
    3. Applying payout curves to determine winnings
    4. Aggregating results to compute ROI, Cash%, win probability

    Uses vectorized NumPy operations for performance.
    """

    def __init__(
        self,
        ownership: np.ndarray,  # Ownership percentages (sums to 100)
        payout_curve: PayoutCurveModel,
        n_scenarios: int = 1000,
        n_contest_sims: int = 1000,
        field_size: int = 50000
    ):
        """
        Initialize contest simulator.

        Args:
            ownership: Array of ownership percentages for each driver (n_drivers,)
            payout_curve: Fitted payout curve model
            n_scenarios: Number of race outcome scenarios to simulate
            n_contest_sims: Number of contest simulations per scenario
            field_size: Number of lineups in the contest
        """
        self.ownership = ownership / ownership.sum()  # Normalize
        self.payout_curve = payout_curve
        self.n_scenarios = n_scenarios
        self.n_contest_sims = n_contest_sims
        self.field_size = field_size

        logger.info(
            f"Initialized ContestSimulator: "
            f"n_scenarios={n_scenarios}, "
            f"n_contest_sims={n_contest_sims}, "
            f"field_size={field_size}"
        )

    def sample_field_lineups(
        self,
        n_lineups: int,
        driver_scores: np.ndarray
    ) -> np.ndarray:
        """
        Sample field lineups from ownership distributions.

        Uses Dirichlet-multinomial sampling to account for ownership uncertainty.

        Args:
            n_lineups: Number of lineups to sample
            driver_scores: Driver scores for this scenario (n_drivers,)

        Returns:
            Array of lineup scores (n_lineups,)
        """
        n_drivers = len(self.ownership)

        # Sample lineup compositions from ownership
        # Each lineup has 6 drivers
        # Use multinomial to sample driver counts per lineup
        lineup_compositions = np.random.multinomial(
            6,  # 6 drivers per lineup
            self.ownership,
            size=n_lineups
        )  # Shape: (n_lineups, n_drivers)

        # Ensure each lineup has exactly 6 drivers
        # (multinomial should guarantee this, but validate)
        assert np.all(lineup_compositions.sum(axis=1) == 6)

        # Calculate lineup scores
        # Score = sum(driver_scores[drivers_in_lineup])
        lineup_scores = lineup_compositions @ driver_scores

        return lineup_scores

    def simulate_contest(
        self,
        my_lineup_score: float,
        scenario_scores: np.ndarray
    ) -> ContestResult:
        """
        Simulate a single contest outcome.

        Args:
            my_lineup_score: My lineup's score
            scenario_scores: Driver scores for this scenario

        Returns:
            ContestResult with rank, payout, cash status, etc.
        """
        # Sample field lineups
        field_scores = self.sample_field_lineups(
            self.field_size - 1,  # Exclude my lineup
            scenario_scores
        )

        # Add my lineup to field
        all_scores = np.concatenate([
            [my_lineup_score],
            field_scores
        ])

        # Calculate my rank (1-indexed, higher score = better rank)
        # Sort descending and find position
        sorted_scores = np.sort(all_scores)[::-1]
        my_rank = np.where(sorted_scores == my_lineup_score)[0][0] + 1

        # Determine payout
        my_payout = self.payout_curve.predict(np.array([my_rank]))[0]

        # Check if cashed (typically top 20-30%)
        cash_cutoff = int(self.field_size * 0.25)
        cashed = my_rank <= cash_cutoff

        # Check if top 1%
        top_1_cutoff = int(self.field_size * 0.01)
        top_1_pct = my_rank <= top_1_cutoff

        return ContestResult(
            my_rank=my_rank,
            my_payout=my_payout,
            my_score=my_lineup_score,
            winning_score=sorted_scores[0],
            field_size=self.field_size,
            cashed=cashed,
            top_1_pct=top_1_pct
        )

    def simulate_portfolio(
        self,
        my_lineup_scores: np.ndarray,
        scenario_driver_scores: np.ndarray
    ) -> Dict[str, np.ndarray]:
        """
        Simulate contest outcomes for a portfolio of lineups.

        Args:
            my_lineup_scores: Scores for my lineups (n_lineups,)
            scenario_driver_scores: Driver scores for each scenario (n_scenarios, n_drivers)

        Returns:
            Dict with arrays of results across simulations:
            - ranks: (n_lineups, n_scenarios * n_contest_sims)
            - payouts: (n_lineups, n_scenarios * n_contest_sims)
            - cashed: (n_lineups, n_scenarios * n_contest_sims)
            - top_1_pct: (n_lineups, n_scenarios * n_contest_sims)
        """
        n_lineups = len(my_lineup_scores)
        n_sims = self.n_scenarios * self.n_contest_sims

        # Pre-allocate results arrays
        ranks = np.zeros((n_lineups, n_sims), dtype=int)
        payouts = np.zeros((n_lineups, n_sims))
        cashed = np.zeros((n_lineups, n_sims), dtype=bool)
        top_1_pct = np.zeros((n_lineups, n_sims), dtype=bool)

        sim_idx = 0
        for scenario_idx in range(self.n_scenarios):
            driver_scores = scenario_driver_scores[scenario_idx]

            # Run multiple contest simulations per scenario
            for contest_sim in range(self.n_contest_sims):
                for lineup_idx, my_score in enumerate(my_lineup_scores):
                    result = self.simulate_contest(my_score, driver_scores)

                    ranks[lineup_idx, sim_idx] = result.my_rank
                    payouts[lineup_idx, sim_idx] = result.my_payout
                    cashed[lineup_idx, sim_idx] = result.cashed
                    top_1_pct[lineup_idx, sim_idx] = result.top_1_pct

                sim_idx += 1

        logger.info(f"Completed {n_sims} contest simulations for {n_lineups} lineups")

        return {
            'ranks': ranks,
            'payouts': payouts,
            'cashed': cashed,
            'top_1_pct': top_1_pct
        }

    def compute_contest_metrics(
        self,
        results: Dict[str, np.ndarray],
        buyin: float = 20.0
    ) -> Dict[str, float]:
        """
        Compute contest-level metrics from simulation results.

        Args:
            results: Results from simulate_portfolio
            buyin: Contest buy-in amount

        Returns:
            Dict with metrics:
            - roi: Expected return on investment
            - cash_pct: Probability of cashing
            - win_pct: Probability of winning (top 1%)
            - ev: Expected value ($)
            - avg_rank: Average finish position
        """
        payouts = results['payouts']
        cashed = results['cashed']
        top_1_pct = results['top_1_pct']
        ranks = results['ranks']

        # Average across simulations
        avg_payout = payouts.mean(axis=1)  # (n_lineups,)
        cash_rate = cashed.mean(axis=1).astype(float)  # (n_lineups,)
        win_rate = top_1_pct.mean(axis=1).astype(float)  # (n_lineups,)
        avg_rank = ranks.mean(axis=1).astype(float)  # (n_lineups,)

        # Compute ROI and EV
        roi = (avg_payout - buyin) / buyin * 100  # Percentage
        ev = avg_payout  # Expected value in $

        metrics = {
            'roi': roi,
            'cash_pct': cash_rate * 100,
            'win_pct': win_rate * 100,
            'ev': ev,
            'avg_rank': avg_rank
        }

        logger.info(
            f"Contest metrics: "
            f"ROI={roi.mean():.2f}%, "
            f"Cash%={cash_rate.mean()*100:.2f}%, "
            f"Win%={win_rate.mean()*100:.2f}%"
        )

        return metrics


# Example usage
if __name__ == "__main__":
    # Setup
    n_drivers = 40
    n_lineups = 20
    n_scenarios = 100
    n_contest_sims = 100

    # Ownership distribution (example: 5 drivers at 10%, rest at lower ownership)
    ownership = np.concatenate([
        np.ones(5) * 10,  # Top 5 drivers at 10% each
        np.ones(35) * 1.43  # Rest at ~1.43%
    ])
    ownership = ownership / ownership.sum() * 100

    # Payout curve (power-law)
    payout_model = PayoutCurveModel(model_type="power_law")
    payout_model.fit(
        np.array([1, 2, 3, 5, 10, 20, 50, 100]),
        np.array([100000, 50000, 30000, 15000, 5000, 2000, 500, 200])
    )

    # Create simulator
    simulator = ContestSimulator(
        ownership=ownership,
        payout_curve=payout_model,
        n_scenarios=n_scenarios,
        n_contest_sims=n_contest_sims,
        field_size=50000
    )

    # Simulated driver scores for each scenario
    # Shape: (n_scenarios, n_drivers)
    scenario_driver_scores = np.random.gamma(
        shape=20,  # Average DK points
        scale=2,
        size=(n_scenarios, n_drivers)
    )

    # My lineup scores for portfolio
    my_lineup_scores = np.array([150 + i for i in range(n_lineups)])  # 150-169

    # Run simulations
    results = simulator.simulate_portfolio(
        my_lineup_scores=my_lineup_scores,
        scenario_driver_scores=scenario_driver_scores
    )

    # Compute metrics
    metrics = simulator.compute_contest_metrics(results, buyin=20.0)

    print("Contest Simulation Results:")
    for lineup_idx in range(n_lineups):
        print(f"Lineup {lineup_idx + 1}:")
        print(f"  ROI: {metrics['roi'][lineup_idx]:.2f}%")
        print(f"  Cash%: {metrics['cash_pct'][lineup_idx]:.2f}%")
        print(f"  Win%: {metrics['win_pct'][lineup_idx]:.2f}%")
        print(f"  EV: ${metrics['ev'][lineup_idx]:.2f}")
        print(f"  Avg Rank: {metrics['avg_rank'][lineup_idx]:.1f}")
```

### Pattern 4: Leverage-Aware Optimization

**What:** Extend existing PuLP optimizer to incorporate ownership constraints and leverage objectives, penalizing high-owned drivers to differentiate from the field.

**When to use:** Required by success criterion "Leverage-aware optimization (ownership + field correlation)." This enables finding lineups with positive EV against the field.

**Example:**
```python
# Source: Leverage-aware optimization extending existing PuLP optimizer
# Pattern integrates with apps/backend/app/optimizer.py
from pulp import LpProblem, LpMaximize, lpSum, LpVariable, LpBinary
import numpy as np
import logging

logger = logging.getLogger(__name__)

class LeverageAwareOptimizer:
    """
    Ownership-aware optimizer for DFS GPP leverage.

    Extends standard optimization with:
    1. Ownership-aware objective: maximize projected_points - ownership_penalty
    2. Ownership constraints: cap exposure to high-owned drivers
    3. Leverage targeting: favor low-owned drivers with similar projected points

    Integrates with existing NASCAROptimizer from optimizer.py.
    """

    def __init__(
        self,
        base_optimizer,  # NASCAROptimizer instance
        ownership: np.ndarray,
        leverage_penalty: float = 0.5,
        max_ownership_per_driver: float = 0.3
    ):
        """
        Initialize leverage-aware optimizer.

        Args:
            base_optimizer: Base NASCAROptimizer (provides driver data, constraints)
            ownership: Array of ownership percentages (0-100) for each driver
            leverage_penalty: Penalty coefficient for high ownership
            max_ownership_per_driver: Max allowed lineup ownership per driver
        """
        self.base_optimizer = base_optimizer
        self.ownership = ownership
        self.leverage_penalty = leverage_penalty
        self.max_ownership_per_driver = max_ownership_per_driver

        logger.info(
            f"Initialized LeverageAwareOptimizer: "
            f"leverage_penalty={leverage_penalty}, "
            f"max_ownership={max_ownership_per_driver}"
        )

    def calculate_leverage_score(
        self,
        driver_id: int,
        expected_points: float
    ) -> float:
        """
        Calculate leverage-adjusted score for a driver.

        Leverage score = expected_points - (ownership * penalty)

        Low-owned drivers get a boost; high-owned drivers get penalized.

        Args:
            driver_id: Driver identifier
            expected_points: Expected DFS points

        Returns:
            Leverage-adjusted score
        """
        # Find driver ownership
        # (Assume ownership array is indexed by driver_id - 1)
        driver_ownership = self.ownership[driver_id - 1]

        # Calculate leverage penalty
        # Penalty increases quadratically with ownership
        penalty = self.leverage_penalty * (driver_ownership / 100) ** 2

        leverage_score = expected_points - penalty

        logger.debug(
            f"Driver {driver_id}: points={expected_points:.2f}, "
            f"ownership={driver_ownership:.1f}%, "
            f"penalty={penalty:.2f}, "
            f"leverage_score={leverage_score:.2f}"
        )

        return leverage_score

    def optimize_lineup_with_leverage(
        self,
        race_id: int,
        n_lineups: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Optimize lineups with leverage-aware objective.

        Args:
            race_id: Race identifier
            n_lineups: Number of lineups to generate

        Returns:
            List of lineup dictionaries with leverage metrics
        """
        logger.info(
            f"Optimizing {n_lineups} leverage-aware lineups for race {race_id}"
        )

        # Load driver data using base optimizer
        self.base_optimizer.load_driver_data(race_id)

        lineups = []
        excluded_drivers = set()

        for lineup_idx in range(n_lineups):
            # Create optimization problem
            problem = LpProblem(
                f"Leverage_Aware_Optimization_{lineup_idx}",
                LpMaximize
            )

            # Filter available drivers
            available_drivers = [
                d for d in self.base_optimizer.drivers
                if d["driver_id"] not in excluded_drivers
            ]

            if len(available_drivers) < self.base_optimizer.n_drivers:
                logger.warning(
                    f"Not enough available drivers for lineup {lineup_idx + 1}"
                )
                break

            # Create binary variables for each driver
            driver_vars = {
                driver["driver_id"]: LpVariable(
                    f"select_{driver['driver_id']}", cat=LpBinary
                )
                for driver in available_drivers
            }

            # Set leverage-aware objective
            problem += lpSum(
                self.calculate_leverage_score(
                    driver["driver_id"],
                    self.base_optimizer.calculate_expected_points(driver["driver_id"])
                ) * driver_vars[driver["driver_id"]]
                for driver in available_drivers
            ), "Maximize_Leverage_Adjusted_Points"

            # Apply base constraints from NASCAROptimizer
            self.base_optimizer.apply_driver_count_constraints()
            self.base_optimizer.apply_salary_constraints(available_drivers)
            self.base_optimizer.apply_stacking_constraints(available_drivers)

            # Add leverage-aware constraints

            # 1. Cap total lineup ownership
            # Prevent loading up on all high-owned drivers
            problem += (
                lpSum(
                    (self.ownership[driver["driver_id"] - 1] / 100) *
                    driver_vars[driver["driver_id"]]
                    for driver in available_drivers
                ) <= self.max_ownership_per_driver * self.base_optimizer.n_drivers,
                "Max_Total_Ownership"
            )

            # 2. Minimum leverage constraint
            # Require at least N drivers with ownership < threshold
            low_ownership_threshold = 10  # 10%
            min_low_ownership_drivers = 2

            problem += (
                lpSum(
                    driver_vars[driver["driver_id"]]
                    for driver in available_drivers
                    if self.ownership[driver["driver_id"] - 1] < low_ownership_threshold
                ) >= min_low_ownership_drivers,
                "Min_Low_Ownership_Drivers"
            )

            # Solve the problem
            solver = PULP_CBC_CMD(msg=0, timeLimit=30)
            problem.solve(solver)

            # Check solution status
            if LpStatus[problem.status] != "Optimal":
                logger.warning(
                    f"No optimal solution for lineup {lineup_idx + 1}: "
                    f"status={LpStatus[problem.status]}"
                )
                break

            # Extract selected drivers
            selected_drivers = [
                driver for driver in available_drivers
                if driver_vars[driver["driver_id"]].value() == 1
            ]

            # Calculate lineup metrics including leverage
            lineup = self._calculate_leverage_metrics(selected_drivers)

            lineups.append(lineup)

            # Exclude selected drivers for next iteration
            excluded_drivers.update(d["driver_id"] for d in selected_drivers)

            logger.info(
                f"Lineup {lineup_idx + 1}: "
                f"points={lineup['total_projected_points']:.2f}, "
                f"leverage_score={lineup['leverage_score']:.2f}, "
                f"avg_ownership={lineup['avg_ownership']:.1f}%"
            )

        logger.info(f"Generated {len(lineups)} leverage-aware lineups")
        return lineups

    def _calculate_leverage_metrics(
        self,
        drivers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate leverage metrics for a lineup."""
        # Calculate base metrics from NASCAROptimizer
        lineup = self.base_optimizer._calculate_lineup_metrics(drivers)

        # Add leverage-specific metrics
        ownerships = [
            self.ownership[d["driver_id"] - 1]
            for d in drivers
        ]

        lineup["avg_ownership"] = float(np.mean(ownerships))
        lineup["max_ownership"] = float(np.max(ownerships))
        lineup["total_ownership"] = float(np.sum(ownerships))
        lineup["leverage_score"] = float(
            lineup["total_projected_points"] -
            self.leverage_penalty * np.mean([o**2 for o in ownerships]) / 100
        )

        return lineup


# Example usage
if __name__ == "__main__":
    # Integrate with existing NASCAROptimizer
    from apps.backend.app.optimizer import NASCAROptimizer, SessionLocal

    db = SessionLocal()

    # Create base optimizer
    base_optimizer = NASCAROptimizer(db, salary_cap=50000, n_drivers=6)

    # Ownership estimates (from HybridOwnershipEstimator)
    ownership = np.array([
        25.3,  # Driver 1: 25.3% owned (highly chalk)
        18.7,  # Driver 2
        12.4,  # Driver 3
        8.9,   # Driver 4
        6.2,   # Driver 5
        5.1,   # Driver 6
        # ... (40 drivers total)
    ])

    # Create leverage-aware optimizer
    leverage_optimizer = LeverageAwareOptimizer(
        base_optimizer=base_optimizer,
        ownership=ownership,
        leverage_penalty=0.5,
        max_ownership_per_driver=0.3
    )

    # Optimize lineups
    lineups = leverage_optimizer.optimize_lineup_with_leverage(
        race_id=1,
        n_lineups=10
    )

    for i, lineup in enumerate(lineups, 1):
        print(f"Lineup {i}:")
        print(f"  Points: {lineup['total_projected_points']:.2f}")
        print(f"  Leverage Score: {lineup['leverage_score']:.2f}")
        print(f"  Avg Ownership: {lineup['avg_ownership']:.1f}%")
```

### Anti-Patterns to Avoid

- **Assuming static ownership across track types:** NASCAR ownership varies significantly by track archetype (superspeedway vs short track vs road course). Use track-specific historical baselines.

- **Using point estimates without uncertainty:** Ownership is uncertain. Always provide confidence bounds or scenario-based estimates (low/med/high) to capture projection error.

- **Ignoring payout structure extrapolation:** Fitting payout curves only to observed ranks fails for unobserved positions. Use parametric models (power-law) that extrapolate smoothly.

- **Simulating contests without ownership correlation:** Field lineups are not independent random samples. They cluster around high-owned drivers and chalk stacks. Use ownership-aware sampling.

- **Overfitting payout curves to single contest:** Payout structures vary by contest size and buyin. Fit curves to multiple contests and validate generalization.

- **Neglecting ownership drift:** Ownership changes as news breaks (injuries, weather, strategy). Build pipeline for re-estimating ownership with late data.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Ensemble ownership models | Custom weighted average | scikit-learn VotingRegressor or StackingRegressor | Provides cross-validation, prediction intervals, and learned weights |
| Payout curve fitting | Custom curve fitting | scipy.optimize.curve_fit with power-law/exponential models | Battle-tested optimization with bounds handling and diagnostics |
| Monte Carlo sampling | Pure Python loops | NumPy vectorization or JAX for acceleration | 100-1000x speedup for large-scale contest simulation |
| Feature importance for ownership | Manual coefficient inspection | sklearn.inspection.permutation_importance | Robust importance quantification that handles correlated features |
| Ownership uncertainty quantification | Custom bootstrap | sklearn.utils.resample or pymc Bayesian models | Proper statistical inference with credible intervals |

**Key insight:** Custom ensemble implementations rarely outperform scikit-learn's optimized algorithms. Payout curve fitting requires proper optimization (scipy.optimize), not manual parameter tuning. Contest simulation must be vectorized (NumPy/JAX) to scale to meaningful sample sizes.

## Common Pitfalls

### Pitfall 1: Ownership Drift by Track Archetype

**What goes wrong:** Using a single ownership model across all track types fails to capture that superspeedways (pack racing, dominator-heavy) have very different ownership patterns than short tracks (position-based, less dominator variance).

**Why it happens:** NASCAR track archetypes fundamentally change driver projections and strategy. Short tracks value positioning; superspeedways value drafting and aggression. Ownership reflects these differences.

**How to avoid:** Build track-archetype specific ownership models. Train separate estimators for superspeedway, intermediate, short track, and road course. Use historical ownership filtered by track type as training data. Validate that ownership predictions track track-type specific patterns (e.g., high dominator ownership on superspeedways).

**Warning signs:** Similar ownership patterns across different track types, or model RMSE increasing when evaluating on held-out tracks of a specific type.

### Pitfall 2: Payout Curve Overfitting to Small Contests

**What goes wrong:** Fitting complex payout models to small contest data (e.g., <1000 entries) produces curves that don't generalize to large-field GPPs.

**Why it happens:** Small contests have noisy payout structures. Overfitting captures noise rather than the underlying distribution. Large GPPs follow smoother, more predictable curves.

**How to avoid:** Fit payout curves primarily to large-field contests (>10K entries). Use regularization (L2 penalty) when fitting. Validate curves on held-out contests. Prefer simpler models (power-law) for small contests, more complex models (hybrid) for large contests.

**Warning signs:** Payout curves with unrealistic oscillations or negative payouts for low ranks. Poor validation performance on held-out contests.

### Pitfall 3: Contest Simulation Sample Size Too Small

**What goes wrong:** Running contest simulations with too few samples (<1000 contest simulations per scenario) produces unstable ROI/Cash% estimates with high variance.

**Why it happens:** Contest outcomes are highly variable, especially in top-heavy GPPs where top 1% determines most of the EV. Small samples don't adequately capture tail outcomes.

**How to avoid:** Use at least 10,000 contest simulations per scenario for stable tail estimates. Use adaptive sample sizes based on contest size (larger contests need more samples). Monitor coefficient of variation across simulation runs.

**Warning signs:** ROI estimates vary dramatically between repeated simulation runs. Cash% confidence intervals are >5 percentage points.

### Pitfall 4: Ignoring Field Lineup Duplication

**What goes wrong:** Simulating field lineups as independent samples ignores that real DFS players use similar optimizers, creating correlated lineups and clusters of chalk.

**Why it happens:** True ownership reflects strategic dependence (stacks, correlation). Independent sampling underestimates duplication and overestimates differentiation.

**How to avoid:** Model lineup dependence explicitly. Sample "chalk lineups" (high-ownership drivers together) with higher probability. Use copula models or multivariate sampling to capture lineup correlation. Validate that simulated lineup covariance matches historical contest data.

**Warning signs:** Simulated field has too many unique lineups compared to real contests. Correlation between drivers in simulated field is lower than historical data.

## Code Examples

Verified patterns from official sources:

### Scikit-Learn Ensemble for Ownership

```python
# Source: scikit-learn VotingRegressor documentation
# https://scikit-learn.org/stable/modules/ensemble.html#voting-regressor
from sklearn.ensemble import VotingRegressor, RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import BayesianRidge
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
import numpy as np

# Prepare data
# X: Features (salary, projected_points, skill, recent_avg_finish, etc.)
# y: Ownership percentages
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# Define base estimators
estimators = [
    ('rf', RandomForestRegressor(n_estimators=100, max_depth=10)),
    ('gb', GradientBoostingRegressor(n_estimators=100, max_depth=5)),
    ('ridge', BayesianRidge())
]

# Create voting ensemble (average predictions)
ensemble = VotingRegressor(estimators=estimators)

# Fit ensemble
ensemble.fit(X_train, y_train)

# Predict ownership
ownership_pred = ensemble.predict(X_test)

# Evaluate
mae = mean_absolute_error(y_test, ownership_pred)
print(f"MAE: {mae:.2f}% ownership")
```

### Scipy Payout Curve Fitting

```python
# Source: scipy.optimize.curve_fit documentation
# https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.curve_fit.html
import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt

# Power-law function: payout = a * rank^(-b)
def power_law(rank, a, b):
    return a * np.power(rank, -b)

# Historical payout data
ranks = np.array([1, 2, 3, 5, 10, 20, 50, 100])
payouts = np.array([100000, 50000, 30000, 15000, 5000, 2000, 500, 200])

# Fit power-law curve
popt, pcov = curve_fit(
    power_law,
    ranks,
    payouts,
    p0=[100000, 1.0],  # Initial guess
    bounds=([0, 0], [np.inf, np.inf])  # Parameters must be positive
)

a, b = popt
print(f"Fitted parameters: a={a:.2f}, b={b:.4f}")

# Predict for new ranks
new_ranks = np.arange(1, 1001)
predicted_payouts = power_law(new_ranks, a, b)

# Plot fit
plt.scatter(ranks, payouts, label='Observed')
plt.plot(new_ranks, predicted_payouts, 'r-', label='Power-law fit')
plt.xscale('log')
plt.yscale('log')
plt.xlabel('Rank')
plt.ylabel('Payout ($)')
plt.legend()
plt.show()
```

### Vectorized Contest Simulation with NumPy

```python
# Source: NumPy vectorization patterns for Monte Carlo simulation
# Pattern is standard practice for efficient Monte Carlo
import numpy as np

def simulate_contests_vectorized(
    my_scores: np.ndarray,
    ownership: np.ndarray,
    driver_scores: np.ndarray,
    n_contests: int = 10000
) -> np.ndarray:
    """
    Vectorized contest simulation.

    Args:
        my_scores: My lineup scores (n_lineups,)
        ownership: Ownership percentages (n_drivers,)
        driver_scores: Driver scores for this scenario (n_drivers,)
        n_contests: Number of contest simulations

    Returns:
        Array of ranks for my lineup (n_lineups, n_contests)
    """
    n_lineups = len(my_scores)
    n_drivers = len(ownership)

    # Normalize ownership to probabilities
    ownership_prob = ownership / ownership.sum()

    # Sample field lineups using multinomial
    # Each contest has field_size lineups, each with 6 drivers
    field_size = 1000

    # Sample driver counts for each lineup in each contest
    # Shape: (n_contests, field_size, n_drivers)
    lineup_compositions = np.random.multinomial(
        6,
        ownership_prob,
        size=(n_contests, field_size)
    )

    # Calculate lineup scores
    # Shape: (n_contests, field_size)
    field_scores = lineup_compositions @ driver_scores

    # Add my lineups and compute ranks
    # Shape: (n_contests, field_size + n_lineups)
    all_scores = np.concatenate([
        field_scores,
        np.tile(my_scores, (n_contests, 1))
    ], axis=1)

    # Calculate ranks (higher score = better rank = lower rank number)
    # argsort in descending order
    ranks = np.argsort(-np.argsort(all_scores, axis=1), axis=1) + 1

    # Extract my lineup ranks (last n_lineups columns)
    my_ranks = ranks[:, -n_lineups:]

    return my_ranks.T  # Shape: (n_lineups, n_contests)

# Example usage
my_scores = np.array([160, 155, 150])
ownership = np.array([10, 8, 6, 5, 4, 3, 2] * 6)  # 42 drivers (6 incomplete)
driver_scores = np.random.gamma(20, 2, size=len(ownership))

ranks = simulate_contests_vectorized(
    my_scores,
    ownership,
    driver_scores,
    n_contests=10000
)

print(f"Average rank: {ranks.mean(axis=1)}")
print(f"Cash rate (top 25%): {(ranks <= 250).mean(axis=1)}")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| **Single-source ownership** (expert predictions only) | **Hybrid ensemble** (historical + projections + regression) | 2023-2024 trend | More robust ownership estimates; better uncertainty quantification |
| **Linear payout interpolation** | **Parametric payout curves** (power-law, exponential) | Mid-2020s pattern | Smooth extrapolation; better generalization to unobserved ranks |
| **Small-scale contest sims** (<1000 iterations) | **Vectorized/JAX-accelerated sims** (100K+ iterations) | 2024-2025 pattern | Stable tail estimates; enables ROI/Cash% optimization |
| **Field sampling without correlation** | **Ownership-aware sampling** (Dirichlet-multinomial) | 2025 research | More realistic field modeling; better EV estimates |
| **Mean-optimization only** | **Leverage-aware optimization** (ownership penalties) | 2025-2026 pattern | Accounts for field composition; targets positive EV |

**Deprecated/outdated:**
- **Manual ownership aggregation:** Use ensemble methods with learned weights.
- **Ad-hoc payout estimation:** Fit parametric models to historical data.
- **Python loop contest sims:** Use vectorized NumPy or JAX operations.

## Open Questions

Things that couldn't be fully resolved:

1. **Ensemble weighting mechanism**
   - **What we know:** Hybrid ensemble must combine multiple ownership signals.
   - **What's unclear:** Should weights be static (same for all tracks), dynamic (learned per track), or hierarchical (Bayesian)?
   - **Recommendation:** Start with static VotingRegressor (equal weights) for simplicity. If validation shows track-specific bias, move to dynamic weights learned per track archetype using StackingRegressor.

2. **Ownership output format**
   - **What we know:** Optimization needs ownership inputs, but format is unclear.
   - **What's unclear:** Should ownership be point estimates, distributions (mean ± std), or scenarios (low/med/high)?
   - **Recommendation:** Provide point estimates with uncertainty bounds (5th/95th percentiles) using bootstrapping. Use point estimates for optimization, but use uncertainty to construct "ownership leverage" bands (e.g., "low-owned" = <5th percentile).

3. **Payout curve generalization**
   - **What we know:** Power-law fits top-heavy GPPs well, but may not fit all contest types.
   - **What's unclear:** Should payout curves be fit separately by contest size, buyin, or sport?
   - **Recommendation:** Fit separate curves by contest size tier (small <5K, medium 5K-20K, large >20K). Within each tier, validate that single curve fits all buyin levels. If not, stratify by buyin as well.

4. **Contest simulation computational cost**
   - **What we know:** Need 10K+ contest sims for stable estimates, but this is expensive.
   - **What's unclear:** Can we use adaptive sampling (fewer sims for low-stakes contests, more for high-stakes)?
   - **Recommendation:** Use adaptive sample sizes based on contest buyin. For $20+ contests, use 10K+ sims. For $3-$5 contests, 1K-5K sims may suffice. Monitor coefficient of variation to ensure stability.

5. **Field lineup correlation modeling**
   - **What we know:** Real field lineups are correlated (chalk stacks, similar optimizers).
   - **What's unclear:** How to model this dependence without overcomplicating?
   - **Recommendation:** Start with Dirichlet-multinomial sampling (captures ownership clustering). If validation shows insufficient correlation, add explicit "chalk lineup" templates sampled with higher probability.

## Sources

### Primary (HIGH confidence)

- **[scikit-learn Ensemble Methods](https://scikit-learn.org/stable/modules/ensemble.html)** - VotingRegressor, StackingRegressor for hybrid ownership estimation
- **[scikit-learn Linear Models](https://scikit-learn.org/stable/modules/linear_model.html)** - BayesianRidge for probabilistic ownership regression
- **[scipy.optimize.curve_fit](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.curve_fit.html)** - Payout curve fitting with parametric models
- **[NumPy Random Sampling](https://numpy.org/doc/stable/reference/random/index.html)** - Vectorized Monte Carlo simulation
- **[JAX](https://jax.readthedocs.io/)** - Accelerated contest simulation (already in stack from Phase 3)
- **[ArviZ](https://python.arviz.org/)** - Diagnostics for Bayesian ownership models (already in stack from Phase 2)
- **[PyMC](https://www.pymc.io/)** - Hierarchical Bayesian ownership models by track archetype (already in stack from Phase 2)

### Secondary (MEDIUM confidence)

- **[Determining Tournament Payout Structures](https://arxiv.org/pdf/1601.04203)** (2016) - Academic paper on power-law payout structures for tournaments (cites power-law optimality)
- **[How to Play Fantasy Sports Strategically](http://www.columbia.edu/~mh2078/DFS_Revision_1_May2019.pdf)** (Columbia University, 2019) - Monte Carlo simulation algorithms for DFS strategy
- **[Risk Assessment of Daily Fantasy Baseball](https://courtney-perigo.medium.com/risk-assessment-of-daily-fantasy-baseball-games-using-monte-carlo-simulation-a82913809880)** (Medium) - Monte Carlo simulation for risk assessment in DFS
- **[Quantifying Chance in Fantasy Sports](https://dspace.mit.edu/bitstream/handle/1721.1/119466/16m1102094.pdf)** (MIT, 2018) - Monte Carlo simulation vs. analytic estimates
- **[RotoGrinders Daily Fantasy Tournament Variance](https://rotogrinders.com/articles/daily-fantasy-tournament-variance-134798)** - DFS variance analysis and payout structures
- **[FTN Contest Sims](https://ftnfantasy.com/contest-sims)** - Commercial contest simulator (marketing materials, claims ROI/Cash%/Top 0.1% evaluation)

### Tertiary (LOW confidence)

- **[Bayesian Hierarchical Modeling for Fantasy Football](https://srome.github.io/Bayesian-Hierarchical-Modeling-Applied-to-Fantasy-Football-Projections-for-Increased-Insight-and-Confidence/)** - Ensemble and Bayesian methods for fantasy projections (blog post, not peer-reviewed)
- **[Python for Daily Fantasy Sports Monte Carlo Simulations](https://www.youtube.com/watch?v=nShjkAZIbWU)** (YouTube) - Video tutorial on DFS simulation (search result only, not verified)
- **[DFS Hero Contest Simulator](https://dfshero.com/)** - Commercial contest simulation tool (marketing materials only)
- **[SaberSim NASCAR Optimizer](https://www.sabersim.com/nascar/optimizer)** - NASCAR DFS optimizer with rule builder and contest sims (marketing materials only)

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** - scikit-learn, scipy, NumPy, JAX are well-established with official documentation
- Architecture: **MEDIUM** - Patterns follow ML and simulation best practices, but NASCAR-specific implementation details may vary
- Pitfalls: **MEDIUM** - Identified from DFS domain knowledge and general ML/engineering practices
- Ownership estimation: **MEDIUM** - Ensemble methods are standard, but NASCAR-specific ownership patterns may have unique characteristics
- Payout curve modeling: **HIGH** - Power-law and exponential fitting are well-documented in optimization literature
- Contest simulation: **MEDIUM** - Monte Carlo patterns are standard, but field lineup correlation modeling is domain-specific

**Research date:** 2026-01-28
**Valid until:** 2026-02-27 (30 days - scikit-learn and scipy are stable, but DFS contest structures may evolve)

**Existing codebase integration:**
- `apps/backend/app/optimizer.py`: NASCAROptimizer with PuLP - extend for leverage-aware optimization
- `apps/backend/app/tail_metrics.py`: CVaR and tail metrics - integrate with contest simulation ROI calculation
- `apps/backend/app/models.py`: Pydantic models - add ownership and contest simulation models
- `packages/axiomatic-sim/src/axiomatic_sim/scenario_generator.py`: Scenario generation - provides driver scores for contest sims
- `pyproject.toml`: Dependencies include JAX, PyMC, ArviZ - need to add scikit-learn, scipy, xgboost, lightgbm
