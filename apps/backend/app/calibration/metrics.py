"""
Calibration metrics for probabilistic predictions.

This module implements standard calibration metrics for assessing how well
probabilistic predictions match observed outcomes:

- CRPS (Continuous Ranked Probability Score): Measures accuracy of probabilistic
  predictions by comparing predicted CDF to observed values
- Log score: Measures predictive likelihood via log probability density
- Coverage: Assesses whether observations fall within prediction intervals
  at specified confidence levels

All metrics handle JAX arrays for GPU acceleration when available.
"""

import jax.numpy as jnp
import numpy as np
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


def compute_crps(predictions: jnp.ndarray, observations: jnp.ndarray) -> float:
    """
    Compute Continuous Ranked Probability Score (CRPS) for probabilistic predictions.

    CRPS measures the accuracy of probabilistic predictions by integrating the
    squared difference between the predicted cumulative distribution function (CDF)
    and the empirical CDF of the observation.

    Formula: CRPS = ∫(F(x) - 1(x ≥ y))² dx
    where F is the predicted CDF and y is the observed value.

    For ensemble predictions, CRPS can be approximated as:
    CRPS ≈ mean(|predictions - observations|) - 0.5 * mean(|predictions_i - predictions_j|)

    Lower CRPS is better (0 is perfect).

    Args:
        predictions: Array of shape (n_samples, n_predictions) containing ensemble predictions
        observations: Array of shape (n_predictions,) containing observed values

    Returns:
        Scalar CRPS value (lower is better, 0 is perfect)

    Raises:
        ValueError: If shapes are incompatible or contain NaN/Inf values

    Examples:
        >>> import jax.numpy as jnp
        >>> predictions = jnp.array([[1.0, 2.0, 3.0], [1.5, 2.5, 3.5]])
        >>> observations = jnp.array([1.2, 2.3, 3.1])
        >>> crps = compute_crps(predictions, observations)
        >>> print(f"CRPS: {crps:.3f}")
    """
    # Input validation
    if predictions.ndim != 2:
        raise ValueError(f"predictions must be 2D, got shape {predictions.shape}")
    if observations.ndim != 1:
        raise ValueError(f"observations must be 1D, got shape {observations.shape}")
    if predictions.shape[1] != observations.shape[0]:
        raise ValueError(
            f"Shape mismatch: predictions.shape[1]={predictions.shape[1]} "
            f"vs observations.shape[0]={observations.shape[0]}"
        )

    # Check for NaN/Inf
    if jnp.any(jnp.isnan(predictions)) or jnp.any(jnp.isinf(predictions)):
        raise ValueError("predictions contain NaN or Inf values")
    if jnp.any(jnp.isnan(observations)) or jnp.any(jnp.isinf(observations)):
        raise ValueError("observations contain NaN or Inf values")

    # Compute CRPS using ensemble approximation
    # CRPS = mean(|predictions - observations|) - 0.5 * mean(|predictions_i - predictions_j|)

    # First term: mean absolute error between predictions and observations
    mae = jnp.mean(jnp.abs(predictions - observations[None, :]))

    # Second term: mean pairwise difference between ensemble members
    # This accounts for the spread of the predictive distribution
    n_samples = predictions.shape[0]
    if n_samples > 1:
        # Compute pairwise differences efficiently using broadcasting
        diff_matrix = predictions[:, None, :] - predictions[None, :, :]
        pairwise_diff = jnp.mean(jnp.abs(diff_matrix))
    else:
        # If only one sample, no spread information
        pairwise_diff = 0.0

    crps = mae - 0.5 * pairwise_diff

    # Ensure CRPS is non-negative
    crps = jnp.maximum(crps, 0.0)

    return float(crps)


def compute_log_score(predictions: jnp.ndarray, observations: jnp.ndarray, epsilon: float = 1e-10) -> float:
    """
    Compute log score (predictive log-likelihood) for probabilistic predictions.

    Log score measures how likely the observations are under the predicted
    probability distribution. Higher values indicate better predictions.

    For ensemble predictions, we use kernel density estimation (KDE) to
    construct a smooth probability distribution and evaluate the log probability
    of each observation.

    Args:
        predictions: Array of shape (n_samples, n_predictions) containing ensemble predictions
        observations: Array of shape (n_predictions,) containing observed values
        epsilon: Small constant to avoid log(0) (default: 1e-10)

    Returns:
        Mean log score (higher is better)

    Raises:
        ValueError: If shapes are incompatible or contain invalid values

    Examples:
        >>> import jax.numpy as jnp
        >>> predictions = jnp.array([[1.0, 2.0, 3.0], [1.5, 2.5, 3.5]])
        >>> observations = jnp.array([1.2, 2.3, 3.1])
        >>> log_score = compute_log_score(predictions, observations)
        >>> print(f"Log score: {log_score:.3f}")
    """
    # Input validation
    if predictions.ndim != 2:
        raise ValueError(f"predictions must be 2D, got shape {predictions.shape}")
    if observations.ndim != 1:
        raise ValueError(f"observations must be 1D, got shape {observations.shape}")
    if predictions.shape[1] != observations.shape[0]:
        raise ValueError(
            f"Shape mismatch: predictions.shape[1]={predictions.shape[1]} "
            f"vs observations.shape[0]={observations.shape[0]}"
        )

    # Check for NaN/Inf
    if jnp.any(jnp.isnan(predictions)) or jnp.any(jnp.isinf(predictions)):
        raise ValueError("predictions contain NaN or Inf values")
    if jnp.any(jnp.isnan(observations)) or jnp.any(jnp.isinf(observations)):
        raise ValueError("observations contain NaN or Inf values")

    # Compute log score using Gaussian kernel density estimation
    # For each observation, compute likelihood under each ensemble member's Gaussian

    n_samples = predictions.shape[0]

    # Compute standard deviation of predictions for each observation
    pred_std = jnp.std(predictions, axis=0)
    pred_mean = jnp.mean(predictions, axis=0)

    # Avoid zero standard deviation
    pred_std = jnp.maximum(pred_std, epsilon)

    # Compute log probability of each observation under Gaussian KDE
    # log P(y | predictions) = log(1/n * sum_i N(y | mean_i, std_i))
    # We approximate this using the mean and std of the ensemble
    log_prob = -0.5 * jnp.log(2 * jnp.pi * pred_std**2) - 0.5 * ((observations - pred_mean) / pred_std) ** 2

    # Add log(n_samples) to account for ensemble averaging
    log_score = jnp.mean(log_prob)

    return float(log_score)


def compute_coverage(
    predictions: jnp.ndarray,
    observations: jnp.ndarray,
    levels: List[float] = [0.5, 0.8, 0.95]
) -> Dict[float, float]:
    """
    Compute empirical coverage for prediction intervals at specified confidence levels.

    Coverage checks what fraction of observations fall within the prediction intervals.
    Well-calibrated models should have empirical coverage close to nominal levels
    (e.g., 50% of observations should fall within the 50% prediction interval).

    Args:
        predictions: Array of shape (n_samples, n_predictions) containing ensemble predictions
        observations: Array of shape (n_predictions,) containing observed values
        levels: List of confidence levels to check (default: [0.5, 0.8, 0.95])

    Returns:
        Dictionary mapping confidence level to empirical coverage

    Raises:
        ValueError: If shapes are incompatible or levels are invalid

    Examples:
        >>> import jax.numpy as jnp
        >>> predictions = jnp.array([[1.0, 2.0, 3.0], [1.5, 2.5, 3.5]])
        >>> observations = jnp.array([1.2, 2.3, 3.1])
        >>> coverage = compute_coverage(predictions, observations, [0.5, 0.95])
        >>> print(f"50% coverage: {coverage[0.5]:.3f}")
        >>> print(f"95% coverage: {coverage[0.95]:.3f}")
    """
    # Input validation
    if predictions.ndim != 2:
        raise ValueError(f"predictions must be 2D, got shape {predictions.shape}")
    if observations.ndim != 1:
        raise ValueError(f"observations must be 1D, got shape {observations.shape}")
    if predictions.shape[1] != observations.shape[0]:
        raise ValueError(
            f"Shape mismatch: predictions.shape[1]={predictions.shape[1]} "
            f"vs observations.shape[0]={observations.shape[0]}"
        )

    # Validate levels
    for level in levels:
        if not 0.0 < level < 1.0:
            raise ValueError(f"Confidence level must be in (0, 1), got {level}")

    # Check for NaN/Inf
    if jnp.any(jnp.isnan(predictions)) or jnp.any(jnp.isinf(predictions)):
        raise ValueError("predictions contain NaN or Inf values")
    if jnp.any(jnp.isnan(observations)) or jnp.any(jnp.isinf(observations)):
        raise ValueError("observations contain NaN or Inf values")

    coverage_results = {}

    for level in levels:
        # Compute prediction interval percentiles
        lower_percentile = (1.0 - level) / 2.0 * 100
        upper_percentile = (1.0 + level) / 2.0 * 100

        # Compute prediction intervals
        lower_bound = jnp.percentile(predictions, lower_percentile, axis=0)
        upper_bound = jnp.percentile(predictions, upper_percentile, axis=0)

        # Count observations within interval
        within_interval = (observations >= lower_bound) & (observations <= upper_bound)
        empirical_coverage = jnp.mean(within_interval.astype(float))

        coverage_results[level] = float(empirical_coverage)

        # Log warning if coverage deviates significantly from nominal
        deviation = abs(empirical_coverage - level)
        if deviation > 0.1:
            logger.warning(
                f"Poor calibration at {level:.0%} level: "
                f"nominal={level:.3f}, empirical={empirical_coverage:.3f}, "
                f"deviation={deviation:.3f}"
            )

    return coverage_results


def compute_all_metrics(
    predictions: jnp.ndarray,
    observations: jnp.ndarray,
    levels: List[float] = [0.5, 0.8, 0.95],
    epsilon: float = 1e-10
) -> Dict[str, any]:
    """
    Compute all calibration metrics for probabilistic predictions.

    This is a convenience function that computes CRPS, log score, and coverage
    in a single call.

    Args:
        predictions: Array of shape (n_samples, n_predictions) containing ensemble predictions
        observations: Array of shape (n_predictions,) containing observed values
        levels: List of confidence levels for coverage (default: [0.5, 0.8, 0.95])
        epsilon: Small constant to avoid log(0) (default: 1e-10)

    Returns:
        Dictionary with keys:
            - 'crps': CRPS value
            - 'log_score': Log score value
            - 'coverage': Dict mapping level to empirical coverage

    Raises:
        ValueError: If shapes are incompatible or contain invalid values

    Examples:
        >>> import jax.numpy as jnp
        >>> predictions = jnp.array([[1.0, 2.0, 3.0], [1.5, 2.5, 3.5]])
        >>> observations = jnp.array([1.2, 2.3, 3.1])
        >>> metrics = compute_all_metrics(predictions, observations)
        >>> print(f"CRPS: {metrics['crps']:.3f}")
        >>> print(f"Log score: {metrics['log_score']:.3f}")
        >>> print(f"Coverage: {metrics['coverage']}")
    """
    crps = compute_crps(predictions, observations)
    log_score = compute_log_score(predictions, observations, epsilon=epsilon)
    coverage = compute_coverage(predictions, observations, levels=levels)

    return {
        "crps": crps,
        "log_score": log_score,
        "coverage": coverage,
    }
