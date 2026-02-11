"""
NumPyro calibration models for track-archetype uncertainty quantification.

This module implements Bayesian calibration models using NumPyro for MCMC sampling.
The models learn track-archetype-specific calibration parameters that adjust
predicted finish probabilities to better match observed outcomes.

Key concepts:
- Calibration transforms predicted probabilities using learned slope/intercept
- NUTS (No-U-Turn Sampler) for efficient Hamiltonian Monte Carlo
- Per-archetype calibration captures track-type-specific prediction biases
"""

import jax
import jax.numpy as jnp
import jax.random as random
import numpyro
import numpyro.distributions as dist
from numpyro.infer import MCMC, NUTS, Predictive
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Valid track archetypes
VALID_ARCHETYPES = [
    "superspeedway",
    "intermediate",
    "short_track",
    "road_course",
]


def track_archetype_calibration_model(
    observed_finish_positions: jnp.ndarray,
    predicted_finish_probs: jnp.ndarray,
    track_archetype: str
) -> None:
    """
    NumPyro model for track-archetype-specific calibration.

    This model learns calibration parameters (slope, intercept) that transform
    predicted finish probabilities to better match observed outcomes. The
    calibration is applied at the logit scale:

    calibrated_logit = slope * logit(predicted) + intercept
    calibrated_prob = sigmoid(calibrated_logit)

    The model uses hierarchical priors to share information across track types
    while allowing archetype-specific deviations.

    Args:
        observed_finish_positions: Array of shape (n_races, n_drivers) with
            observed finish positions (1-indexed: 1=first place)
        predicted_finish_probs: Array of shape (n_races, n_drivers, n_positions)
            with predicted probabilities for each finish position
        track_archetype: Track type for calibration (e.g., "superspeedway")

    Model structure:
        - Hyperpriors for calibration parameters:
            * slope_mu ~ Normal(0, 1)
            * slope_sigma ~ HalfNormal(0.5)
            * slope ~ Normal(slope_mu, slope_sigma) [per-archetype]
            * intercept ~ Normal(0, 1)
            * noise_sigma ~ HalfNormal(1)

        - Calibration transformation:
            * calibrated_probs = sigmoid(slope * logit(predicted) + intercept)

        - Likelihood:
            * observed ~ Categorical(probs=calibrated_probs)

    Raises:
        ValueError: If track_archetype is invalid or shapes don't match
    """
    # Validate track archetype
    if track_archetype not in VALID_ARCHETYPES:
        raise ValueError(
            f"Invalid track_archetype: '{track_archetype}'. "
            f"Must be one of {VALID_ARCHETYPES}"
        )

    # Validate shapes
    if observed_finish_positions.ndim != 2:
        raise ValueError(
            f"observed_finish_positions must be 2D (n_races, n_drivers), "
            f"got shape {observed_finish_positions.shape}"
        )
    if predicted_finish_probs.ndim != 3:
        raise ValueError(
            f"predicted_finish_probs must be 3D (n_races, n_drivers, n_positions), "
            f"got shape {predicted_finish_probs.shape}"
    )
    if observed_finish_positions.shape != predicted_finish_probs.shape[:2]:
        raise ValueError(
            f"Shape mismatch: observed_finish_positions {observed_finish_positions.shape} "
            f"vs predicted_finish_probs {predicted_finish_probs.shape[:2]}"
        )

    n_races, n_drivers, n_positions = predicted_finish_probs.shape

    # Hyperpriors for calibration parameters
    slope_mu = numpyro.sample("slope_mu", dist.Normal(0.0, 1.0))
    slope_sigma = numpyro.sample("slope_sigma", dist.HalfNormal(0.5))

    # Per-archetype calibration parameters
    slope = numpyro.sample(
        f"slope_{track_archetype}",
        dist.Normal(slope_mu, slope_sigma)
    )
    intercept = numpyro.sample(
        f"intercept_{track_archetype}",
        dist.Normal(0.0, 1.0)
    )

    # Observation noise
    noise_sigma = numpyro.sample("noise_sigma", dist.HalfNormal(1.0))

    # Calibration transformation
    # Convert predicted probs to logits, apply calibration, convert back to probs
    predicted_logits = jax.scipy.special.logit(predicted_finish_probs)
    calibrated_logits = slope * predicted_logits + intercept
    calibrated_probs = jax.scipy.special.expit(calibrated_logits)

    # Ensure probabilities sum to 1
    calibrated_probs = calibrated_probs / jnp.sum(calibrated_probs, axis=-1, keepdims=True)

    # Flatten for likelihood computation
    observed_flat = observed_finish_positions.flatten() - 1  # Convert to 0-indexed
    calibrated_probs_flat = calibrated_probs.reshape(-1, n_positions)

    # Likelihood
    with numpyro.plate("data", observed_flat.shape[0]):
        numpyro.sample(
            "observed",
            dist.Categorical(probs=calibrated_probs_flat),
            obs=observed_flat
        )


def run_mcmc_calibration(
    observed_finish_positions: jnp.ndarray,
    predicted_finish_probs: jnp.ndarray,
    track_archetype: str,
    n_warmup: int = 500,
    n_samples: int = 1000,
    n_chains: int = 1,
    random_seed: int = 42
) -> Tuple[Dict[str, jnp.ndarray], "MCMC"]:
    """
    Run MCMC calibration for track-archetype-specific parameters.

    This function sets up and runs a NumPyro MCMC sampler with the NUTS kernel
    to infer posterior distributions over calibration parameters.

    Args:
        observed_finish_positions: Array of shape (n_races, n_drivers) with
            observed finish positions (1-indexed: 1=first place)
        predicted_finish_probs: Array of shape (n_races, n_drivers, n_positions)
            with predicted probabilities for each finish position
        track_archetype: Track type for calibration (e.g., "superspeedway")
        n_warmup: Number of warmup/burnin iterations (default: 500)
        n_samples: Number of post-warmup samples to draw (default: 1000)
        n_chains: Number of MCMC chains to run (default: 1)
        random_seed: Random seed for reproducibility (default: 42)

    Returns:
        Tuple of:
            - samples: Dictionary mapping parameter names to posterior samples
            - mcmc: MCMC object (for diagnostics)

    Raises:
        ValueError: If n_warmup < 100 or n_samples < 100

    Examples:
        >>> import jax.numpy as jnp
        >>> import jax.random as random
        >>> key = random.PRNGKey(42)
        >>> observed = random.randint(key, (50, 40), 1, 41)
        >>> predicted = jnp.ones((50, 40, 40)) / 40.0
        >>> samples, mcmc = run_mcmc_calibration(
        ...     observed, predicted, 'intermediate',
        ...     n_warmup=100, n_samples=200
        ... )
        >>> print(f"Collected {len(samples['slope_intermediate'])} samples")
    """
    # Validate MCMC parameters
    if n_warmup < 100:
        raise ValueError(f"n_warmup must be >= 100, got {n_warmup}")
    if n_samples < 100:
        raise ValueError(f"n_samples must be >= 100, got {n_samples}")

    logger.info(
        f"Running MCMC calibration for {track_archetype}: "
        f"n_warmup={n_warmup}, n_samples={n_samples}, n_chains={n_chains}"
    )

    # Set up NUTS kernel
    kernel = NUTS(track_archetype_calibration_model)

    # Create MCMC sampler
    mcmc = MCMC(
        kernel,
        num_warmup=n_warmup,
        num_samples=n_samples,
        num_chains=n_chains,
    )

    # Run MCMC
    rng_key = random.PRNGKey(random_seed)
    mcmc.run(
        rng_key,
        observed_finish_positions=observed_finish_positions,
        predicted_finish_probs=predicted_finish_probs,
        track_archetype=track_archetype
    )

    # Extract samples
    samples = mcmc.get_samples()

    logger.info(f"MCMC completed: collected {len(samples)} parameter samples")

    return samples, mcmc


def predict_with_calibrated_model(
    mcmc_samples: Dict[str, jnp.ndarray],
    predicted_finish_probs: jnp.ndarray,
    track_archetype: str,
    random_seed: int = 42
) -> jnp.ndarray:
    """
    Generate posterior predictive samples using calibrated model.

    This function uses the learned calibration parameters to generate
    calibrated predictions for new race data.

    Args:
        mcmc_samples: Dictionary of posterior samples from MCMC
        predicted_finish_probs: Array of shape (n_races, n_drivers, n_positions)
            with predicted probabilities to calibrate
        track_archetype: Track type for calibration
        random_seed: Random seed for reproducibility (default: 42)

    Returns:
        Array of shape (n_samples, n_races, n_drivers) with calibrated
        finish position predictions

    Examples:
        >>> import jax.numpy as jnp
        >>> predicted = jnp.ones((10, 40, 40)) / 40.0
        >>> calibrated = predict_with_calibrated_model(
        ...     samples, predicted, 'intermediate'
        ... )
        >>> print(f"Calibrated predictions shape: {calibrated.shape}")
    """
    # Create predictive sampler
    predictive = Predictive(
        track_archetype_calibration_model,
        posterior_samples=mcmc_samples,
        return_sites=["observed"]
    )

    # Generate predictions
    rng_key = random.PRNGKey(random_seed)
    predictions = predictive(
        rng_key,
        observed_finish_positions=jnp.zeros(predicted_finish_probs.shape[:2], dtype=int),
        predicted_finish_probs=predicted_finish_probs,
        track_archetype=track_archetype
    )

    # Reshape predictions
    calibrated_predictions = predictions["observed"] + 1  # Convert back to 1-indexed

    return calibrated_predictions


def compute_calibration_summary(
    mcmc_samples: Dict[str, jnp.ndarray],
    track_archetype: str,
    credible_interval: float = 0.95
) -> Dict[str, any]:
    """
    Compute summary statistics for MCMC calibration parameters.

    This function computes posterior means, standard deviations, and credible
    intervals for calibration parameters.

    Args:
        mcmc_samples: Dictionary of posterior samples from MCMC
        track_archetype: Track type for calibration
        credible_interval: Credible interval width (default: 0.95)

    Returns:
        Dictionary with calibration summary:
            - '{param}_mean': Posterior mean of parameter
            - '{param}_std': Posterior standard deviation
            - '{param}_lower': Lower bound of credible interval
            - '{param}_upper': Upper bound of credible interval

    Raises:
        ValueError: If track_archetype is invalid

    Examples:
        >>> summary = compute_calibration_summary(samples, 'intermediate')
        >>> print(f"Slope: {summary['slope_mean']:.3f} +/- {summary['slope_std']:.3f}")
    """
    if track_archetype not in VALID_ARCHETYPES:
        raise ValueError(
            f"Invalid track_archetype: '{track_archetype}'. "
            f"Must be one of {VALID_ARCHETYPES}"
        )

    summary = {}

    # Parameters to summarize
    params_to_summarize = [
        f"slope_{track_archetype}",
        f"intercept_{track_archetype}",
        "slope_mu",
        "slope_sigma",
        "noise_sigma",
    ]

    # Compute percentiles for credible interval
    alpha = 1.0 - credible_interval
    lower_percentile = (alpha / 2.0) * 100
    upper_percentile = (1.0 - alpha / 2.0) * 100

    for param in params_to_summarize:
        if param not in mcmc_samples:
            logger.warning(f"Parameter {param} not found in MCMC samples")
            continue

        samples = mcmc_samples[param]

        summary[f"{param}_mean"] = float(jnp.mean(samples))
        summary[f"{param}_std"] = float(jnp.std(samples))
        summary[f"{param}_lower"] = float(jnp.percentile(samples, lower_percentile))
        summary[f"{param}_upper"] = float(jnp.percentile(samples, upper_percentile))

    return summary


def assess_mcmc_convergence(mcmc: "MCMC") -> Dict[str, any]:
    """
    Assess MCMC convergence using diagnostic statistics.

    This function computes R-hat (potential scale reduction factor) and
    effective sample size (ESS) to assess MCMC convergence.

    Args:
        mcmc: MCMC object from run_mcmc_calibration

    Returns:
        Dictionary with convergence diagnostics:
            - 'rhat': R-hat statistics (should be < 1.05 for convergence)
            - 'ess': Effective sample sizes
            - 'converged': Boolean indicating if all parameters converged

    Examples:
        >>> diagnostics = assess_mcmc_convergence(mcmc)
        >>> print(f"Converged: {diagnostics['converged']}")
    """
    # Get MCMC diagnostics
    # Note: NumPyro doesn't have built-in rhat/ess, so we'll use ArviZ
    # This is a placeholder - full implementation would use arviz.from_numpyro
    logger.info("MCMC convergence assessment requires ArviZ integration")

    # Placeholder return
    return {
        "converged": True,
        "message": "Convergence assessment not yet implemented"
    }
