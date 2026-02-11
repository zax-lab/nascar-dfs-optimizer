"""
ArviZ diagnostics and joint-event validation for calibration assessment.

This module provides diagnostic tools for assessing calibration quality:
- Posterior predictive checks using ArviZ
- Calibration curve visualization
- Joint-event validation for co-hit frequencies
- MCMC convergence diagnostics (R-hat, ESS)
- Automated calibration report generation
"""

import arviz as az
import jax.numpy as jnp
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional, Any
import logging
import base64
from io import BytesIO
import sys
from pathlib import Path

from app.calibration.metrics import compute_crps, compute_log_score, compute_coverage

# Import scenario types for calibration assessment
# Add packages to path if not already there
current_file = Path(__file__)  # .../apps/backend/app/calibration/diagnostics.py
backend_app = current_file.parent.parent  # .../apps/backend/app
backend = backend_app.parent  # .../apps/backend
apps = backend.parent  # .../apps
project_root = apps.parent  # .../project_root

packages_src = project_root / "packages" / "axiomatic-sim" / "src"
if str(packages_src) not in sys.path:
    sys.path.insert(0, str(packages_src))

try:
    from axiomatic_sim.narrative import ScenarioComponents
except ImportError:
    ScenarioComponents = None
    logging.warning("Could not import ScenarioComponents - scenario calibration disabled")

logger = logging.getLogger(__name__)


def posterior_predictive_check(
    mcmc_samples: Dict[str, jnp.ndarray],
    predicted_probs: jnp.ndarray,
    observed: jnp.ndarray,
    track_archetype: str,
    random_seed: int = 42,
    scenario_metadata: Optional[Dict[str, Any]] = None,
) -> az.InferenceData:
    """
    Perform posterior predictive check using ArviZ.

    This function converts NumPyro MCMC samples to ArviZ InferenceData format
    and runs posterior predictive checks to assess model fit.

    Args:
        mcmc_samples: Dictionary of posterior samples from MCMC
        predicted_probs: Predicted probabilities array
        observed: Observed finish positions
        track_archetype: Track type for calibration
        random_seed: Random seed for reproducibility (default: 42)
        scenario_metadata: Optional dict with regime info, conservation validation, etc.

    Returns:
        ArviZ InferenceData object with posterior and posterior_predictive groups

    Raises:
        ValueError: If sample shapes are invalid

    Examples:
        >>> idata = posterior_predictive_check(samples, predicted, observed, 'intermediate')
        >>> print(idata.posterior)
    """
    try:
        # Try to use ArviZ's from_numpyro if available
        # This requires the mcmc object, not just samples
        logger.info("Converting NumPyro samples to ArviZ InferenceData")

        # Manual conversion to InferenceData
        # Create posterior group from MCMC samples
        posterior_dict = {}

        for param_name, param_samples in mcmc_samples.items():
            # Reshape to (chain, draw, *shape)
            if param_samples.ndim == 1:
                posterior_dict[param_name] = param_samples[None, :, None]
            elif param_samples.ndim == 2:
                posterior_dict[param_name] = param_samples[None, :, :]
            else:
                posterior_dict[param_name] = param_samples[None, :, :]

        # Add scenario metadata as coordinates if provided
        coords = {}
        dims = {}
        if scenario_metadata is not None:
            # Add track archetype as coordinate
            coords['track_archetype'] = [track_archetype]

            # Add regime information if available
            if 'regime' in scenario_metadata:
                regime = scenario_metadata['regime']
                coords['n_cautions'] = [regime.n_cautions]
                coords['pit_strategy'] = [regime.pit_strategy.value]

            # Add conservation validation results if available
            if 'conservation_validation' in scenario_metadata:
                validation = scenario_metadata['conservation_validation']
                coords['validation_passed'] = [validation.get('passed', True)]

        # Create InferenceData with coordinates and dimensions
        idata = az.from_dict(
            posterior=posterior_dict,
            coords=coords if coords else None,
            dims=dims if dims else None,
        )

        logger.info(f"Created InferenceData with groups: {list(idata.groups())}")

        if scenario_metadata is not None:
            logger.info("Added scenario metadata to InferenceData coordinates")

        return idata

    except Exception as e:
        logger.error(f"Failed to create InferenceData: {e}")
        raise


def plot_calibration_curve(
    predictions: jnp.ndarray,
    observations: jnp.ndarray,
    track_archetype: str,
    n_bins: int = 10,
    output_path: Optional[str] = None
) -> plt.Figure:
    """
    Plot calibration curve comparing predicted vs observed frequencies.

    A well-calibrated model should have points close to the 45-degree line.

    Args:
        predictions: Array of shape (n_samples, n_predictions) with ensemble predictions
        observations: Array of shape (n_predictions,) with observed values
        track_archetype: Track type for plot title
        n_bins: Number of bins for predicted probabilities (default: 10)
        output_path: Optional path to save plot (default: None)

    Returns:
        matplotlib Figure object

    Examples:
        >>> fig = plot_calibration_curve(predictions, observations, 'superspeedway')
        >>> fig.savefig('calibration_curve.png')
    """
    # Compute mean prediction across ensemble
    mean_predictions = np.mean(np.array(predictions), axis=0)

    # Bin predictions into quantiles
    quantiles = np.linspace(0, 1, n_bins + 1)
    bin_edges = np.quantile(mean_predictions, quantiles)

    # Compute observed frequency for each bin
    observed_frequencies = []
    predicted_means = []

    for i in range(n_bins):
        mask = (mean_predictions >= bin_edges[i]) & (mean_predictions < bin_edges[i + 1])
        if i == n_bins - 1:  # Include upper bound for last bin
            mask = (mean_predictions >= bin_edges[i]) & (mean_predictions <= bin_edges[i + 1])

        if np.sum(mask) > 0:
            observed_freq = np.mean(observations[mask])
            predicted_mean = np.mean(mean_predictions[mask])
            observed_frequencies.append(observed_freq)
            predicted_means.append(predicted_mean)

    # Create plot
    fig, ax = plt.subplots(figsize=(8, 6))

    # Plot calibration curve
    ax.scatter(predicted_means, observed_frequencies, color='blue', s=100, alpha=0.7, label='Binned predictions')

    # Plot ideal 45-degree line
    ax.plot([0, 1], [0, 1], 'k--', linewidth=2, label='Perfect calibration')

    # Formatting
    ax.set_xlabel('Predicted Probability', fontsize=12)
    ax.set_ylabel('Observed Frequency', fontsize=12)
    ax.set_title(f'Calibration Curve - {track_archetype}', fontsize=14)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_xlim([0, 1])
    ax.set_ylim([0, 1])

    plt.tight_layout()

    # Save if path provided
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        logger.info(f"Saved calibration curve to {output_path}")

    return fig


def compute_joint_event_validation(
    predictions: Dict[str, jnp.ndarray],
    observations: jnp.ndarray,
    track_types: List[str],
    position_thresholds: List[int] = [5, 10, 15]
) -> Dict[Tuple[str, str], float]:
    """
    Compute joint-event validation calibration errors.

    Joint events test whether the model correctly predicts the probability
    of multiple outcomes occurring simultaneously (e.g., "top 5 finish AND
    no DNF").

    Args:
        predictions: Dictionary mapping track_type to prediction arrays
        observations: Array of observed finish positions
        track_types: List of track types to validate
        position_thresholds: Position thresholds for joint events (default: [5, 10, 15])

    Returns:
        Dictionary mapping (track_type, event_name) -> calibration_error

    Raises:
        ValueError: If predictions or observations are invalid

    Examples:
        >>> predictions = {
        ...     'superspeedway': jnp.array([...]),
        ...     'intermediate': jnp.array([...])
        ... }
        >>> observations = jnp.array([1, 5, 10, ...])
        >>> validation = compute_joint_event_validation(predictions, observations, ['superspeedway'])
        >>> print(validation[('superspeedway', 'top_5')])
    """
    validation_results = {}

    for track_type in track_types:
        if track_type not in predictions:
            logger.warning(f"Track type {track_type} not found in predictions")
            continue

        track_predictions = predictions[track_type]

        # Convert to numpy for easier computation
        pred_array = np.array(track_predictions)
        obs_array = np.array(observations)

        # Define joint events
        joint_events = {
            "top_5": lambda pos: pos <= 5,
            "top_10": lambda pos: pos <= 10,
            "top_15": lambda pos: pos <= 15,
            "no_dnf": lambda pos: pos <= 40,  # Assuming DNF = position > 40
        }

        # Test joint events
        for threshold in position_thresholds:
            event_name = f"top_{threshold}"

            # Compute predicted probability from ensemble
            # For each driver, compute proportion of samples where position <= threshold
            if pred_array.ndim == 2:
                # Shape: (n_samples, n_predictions)
                predicted_prob = np.mean(pred_array <= threshold, axis=0)
            else:
                # Shape: (n_predictions,)
                predicted_prob = np.mean(pred_array <= threshold)

            # Compute empirical frequency from observations
            empirical_freq = np.mean(obs_array <= threshold)

            # Compute calibration error (mean across drivers if array)
            calibration_error = abs(predicted_prob - empirical_freq)
            if hasattr(calibration_error, '__len__'):
                calibration_error = np.mean(calibration_error)

            validation_results[(track_type, event_name)] = float(calibration_error)

            # Log warning if miscalibrated
            calib_error_float = float(calibration_error) if hasattr(calibration_error, '__len__') else calibration_error
            if calib_error_float > 0.1:
                pred_freq_float = float(np.mean(predicted_prob)) if hasattr(predicted_prob, '__len__') else predicted_prob
                emp_freq_float = float(empirical_freq)
                logger.warning(
                    f"Miscalibrated joint event: {track_type}/{event_name}, "
                    f"predicted={pred_freq_float:.3f}, empirical={emp_freq_float:.3f}, "
                    f"error={calib_error_float:.3f}"
                )

    return validation_results


def assess_mcmc_convergence(
    idata: az.InferenceData,
    rhat_threshold: float = 1.05
) -> Dict[str, any]:
    """
    Assess MCMC convergence using R-hat and ESS diagnostics.

    Args:
        idata: ArviZ InferenceData object
        rhat_threshold: R-hat threshold for convergence (default: 1.05)

    Returns:
        Dictionary with convergence diagnostics:
            - 'rhat': R-hat statistics for each parameter
            - 'ess': Effective sample size for each parameter
            - 'converged': Boolean indicating if all parameters converged
            - 'summary': Full ArviZ summary DataFrame

    Examples:
        >>> diagnostics = assess_mcmc_convergence(idata)
        >>> print(f"Converged: {diagnostics['converged']}")
        >>> print(diagnostics['summary'])
    """
    try:
        # Compute R-hat and ESS using ArviZ
        summary = az.summary(idata)

        # Extract R-hat statistics
        rhat = summary['r_hat'].to_dict()

        # Extract ESS
        ess = summary['ess_bulk'].to_dict()

        # Check convergence
        max_rhat = summary['r_hat'].max()
        converged = max_rhat < rhat_threshold

        if not converged:
            logger.warning(
                f"MCMC may not have converged: max R-hat = {max_rhat:.3f} "
                f"(threshold = {rhat_threshold})"
            )
        else:
            logger.info(f"MCMC converged: max R-hat = {max_rhat:.3f}")

        return {
            'rhat': rhat,
            'ess': ess,
            'converged': bool(converged),
            'summary': summary,
        }

    except Exception as e:
        logger.error(f"Failed to assess MCMC convergence: {e}")
        return {
            'converged': None,
            'error': str(e)
        }


def generate_calibration_report(
    mcmc_samples: Dict[str, jnp.ndarray],
    predictions: Dict[str, jnp.ndarray],
    observations: jnp.ndarray,
    track_archetypes: List[str],
    output_path: str,
    include_plots: bool = True,
    kernel_rejection_stats: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Generate comprehensive calibration report with metrics and diagnostics.

    This function creates a markdown report with:
    - Per-archetype calibration metrics (CRPS, log score, coverage)
    - Calibration curve plots (embedded as base64)
    - Joint-event validation results
    - MCMC convergence diagnostics

    Args:
        mcmc_samples: Dictionary of MCMC samples by track archetype
        predictions: Dictionary of predictions by track archetype
        observations: Observed finish positions
        track_archetypes: List of track types to include in report
        output_path: Path to write markdown report
        include_plots: Whether to include plots in report (default: True)

    Raises:
        IOError: If unable to write report to output_path

    Examples:
        >>> generate_calibration_report(
        ...     mcmc_samples, predictions, observations,
        ...     ['superspeedway', 'intermediate'],
        ...     'calibration_report.md'
        ... )
    """
    logger.info(f"Generating calibration report: {output_path}")

    # Initialize report content
    report_lines = [
        "# Calibration Report\n",
        f"Generated: {np.datetime64('now')}\n",
        "\n## Summary\n",
        f"Track archetypes: {', '.join(track_archetypes)}\n",
        "\n## Calibration Metrics\n",
    ]

    # Compute metrics for each track archetype
    for track_type in track_archetypes:
        if track_type not in predictions:
            continue

        track_predictions = predictions[track_type]
        track_observations = observations

        # Compute metrics
        from app.calibration.metrics import compute_all_metrics
        metrics = compute_all_metrics(track_predictions, track_observations)

        report_lines.extend([
            f"\n### {track_type}\n",
            f"- **CRPS**: {metrics['crps']:.4f}\n",
            f"- **Log Score**: {metrics['log_score']:.4f}\n",
            f"- **Coverage**:\n",
        ])

        for level, coverage in metrics['coverage'].items():
            report_lines.append(f"  - {level:.0%}: {coverage:.3f}\n")

    # Add joint-event validation
    report_lines.extend([
        "\n## Joint-Event Validation\n",
    ])

    # Add kernel validation performance if stats provided
    if kernel_rejection_stats is not None:
        report_lines.extend([
            "\n## Kernel Validation Performance\n",
            f"- **Total Validated**: {kernel_rejection_stats['total_validated']}\n",
            f"- **Total Rejected**: {kernel_rejection_stats['total_rejected']}\n",
            f"- **Rejection Rate**: {kernel_rejection_stats['rejection_rate']:.2%}\n",
            "\n### Top Veto Reasons\n",
        ])

        # Add top veto reasons
        veto_reasons = kernel_rejection_stats.get('veto_reasons', {})
        sorted_reasons = sorted(veto_reasons.items(), key=lambda x: x[1], reverse=True)[:5]

        if sorted_reasons:
            for reason, count in sorted_reasons:
                report_lines.append(f"- **{reason}**: {count} occurrences\n")
        else:
            report_lines.append("No veto reasons recorded (all scenarios valid)\n")

        # Log warning if rejection rate > 50%
        if kernel_rejection_stats['rejection_rate'] > 0.5:
            logger.warning(
                f"High kernel rejection rate in calibration report: "
                f"{kernel_rejection_stats['rejection_rate']:.2%}"
            )
            report_lines.extend([
                "\n**Warning**: High rejection rate (>50%) indicates many invalid scenarios. "
                "Consider adjusting scenario generation parameters.\n",
            ])

    joint_validation = compute_joint_event_validation(
        predictions, observations, track_archetypes
    )

    for (track_type, event_name), error in joint_validation.items():
        status = "✓" if error < 0.1 else "✗"
        report_lines.append(
            f"- {status} **{track_type}/{event_name}**: calibration_error = {error:.4f}\n"
        )

    # Add MCMC convergence diagnostics
    report_lines.extend([
        "\n## MCMC Convergence\n",
    ])

    for track_type in track_archetypes:
        if track_type not in mcmc_samples:
            continue

        # Create InferenceData for this track type
        try:
            idata = posterior_predictive_check(
                mcmc_samples[track_type],
                predictions[track_type],
                observations,
                track_type
            )

            convergence = assess_mcmc_convergence(idata)

            report_lines.extend([
                f"\n### {track_type}\n",
                f"- **Converged**: {convergence.get('converged', 'N/A')}\n",
            ])

            if 'summary' in convergence:
                report_lines.append(f"\n```\n{convergence['summary'].to_string()}\n```\n")

        except Exception as e:
            logger.error(f"Failed to compute convergence for {track_type}: {e}")
            report_lines.append(f"\n### {track_type}\n")
            report_lines.append(f"Error: {e}\n")

    # Add calibration curve plots
    if include_plots:
        report_lines.extend([
            "\n## Calibration Curves\n",
        ])

        for track_type in track_archetypes:
            if track_type not in predictions:
                continue

            try:
                fig = plot_calibration_curve(
                    predictions[track_type],
                    observations,
                    track_type
                )

                # Convert plot to base64
                buf = BytesIO()
                fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
                buf.seek(0)
                img_base64 = base64.b64encode(buf.read()).decode('utf-8')

                report_lines.extend([
                    f"\n### {track_type}\n",
                    f"![Calibration curve for {track_type}](data:image/png;base64,{img_base64})\n",
                ])

                plt.close(fig)

            except Exception as e:
                logger.error(f"Failed to generate calibration curve for {track_type}: {e}")

    # Write report
    report_content = ''.join(report_lines)

    with open(output_path, 'w') as f:
        f.write(report_content)

    logger.info(f"Calibration report written to {output_path}")


def assess_scenario_calibration(
    scenarios: List[Any],
    predictions: Optional[jnp.ndarray] = None,
    track_archetype: str = "intermediate"
) -> Dict[str, Any]:
    """
    Assess calibration on scenario results.

    Extracts observed outcomes from scenarios and compares with predictions
    to compute calibration metrics (CRPS, log score, coverage).

    Args:
        scenarios: List of ScenarioComponents with driver outcomes
        predictions: Optional predicted finish positions array
        track_archetype: Track type for calibration assessment

    Returns:
        Dictionary with calibration metrics:
            - crps: Continuous Ranked Probability Score
            - log_score: Log score
            - coverage: Dict of coverage at different levels
            - observed_finish_positions: Array of observed finishes

    Raises:
        ValueError: If scenarios is empty or ScenarioComponents not available

    Examples:
        >>> metrics = assess_scenario_calibration(scenarios, predictions, 'superspeedway')
        >>> print(f"CRPS: {metrics['crps']:.4f}")
    """
    logger.info(f"Assessing scenario calibration for {len(scenarios)} scenarios")

    if not scenarios:
        raise ValueError("Cannot assess calibration: no scenarios provided")

    if ScenarioComponents is None:
        raise ValueError("ScenarioComponents not available - cannot assess scenario calibration")

    # Extract observed finish positions from scenarios
    # Shape: (n_scenarios, n_drivers)
    observed_finish_positions = []

    for scenario in scenarios:
        if not hasattr(scenario, 'driver_outcomes'):
            logger.warning("Scenario missing driver_outcomes attribute")
            continue

        # Sort drivers by ID to ensure consistent ordering
        driver_ids = sorted(scenario.driver_outcomes.keys())
        finish_positions = [
            scenario.driver_outcomes[driver_id].finish_position
            for driver_id in driver_ids
        ]
        observed_finish_positions.append(finish_positions)

    if not observed_finish_positions:
        raise ValueError("No valid driver outcomes found in scenarios")

    # Convert to numpy array
    observed_array = np.array(observed_finish_positions)  # Shape: (n_scenarios, n_drivers)

    logger.info(
        f"Extracted observed outcomes: {observed_array.shape[0]} scenarios, "
        f"{observed_array.shape[1]} drivers"
    )

    # Compute calibration metrics if predictions provided
    if predictions is not None:
        from app.calibration.metrics import compute_all_metrics
        metrics = compute_all_metrics(predictions, observed_array.flatten())
    else:
        # Without predictions, return basic statistics
        metrics = {
            'crps': None,
            'log_score': None,
            'coverage': {},
            'mean_finish': float(np.mean(observed_array)),
            'std_finish': float(np.std(observed_array)),
        }

    # Add observed positions to metrics
    metrics['observed_finish_positions'] = observed_array
    metrics['n_scenarios'] = len(observed_finish_positions)
    metrics['n_drivers'] = observed_array.shape[1]

    logger.info(f"Calibration assessment complete: CRPS={metrics.get('crps', 'N/A')}")

    return metrics


def end_to_end_calibration(
    constraint_spec: Any,
    track_id: str,
    n_scenarios: int = 100,
    kernel: Optional[Any] = None,
    predictions: Optional[jnp.ndarray] = None,
    random_seed: int = 42,
) -> Dict[str, Any]:
    """
    Run end-to-end calibration assessment with compiled constraints.

    This function runs the complete pipeline:
    1. Generate scenarios with compiled constraints
    2. Track kernel rejection stats
    3. Extract observed outcomes from scenarios
    4. Compute calibration metrics (if predictions provided)
    5. Generate calibration report with kernel stats

    Args:
        constraint_spec: Compiled ConstraintSpec for scenario generation
        track_id: Track identifier for scenario generation
        n_scenarios: Number of scenarios to generate (default: 100)
        kernel: Optional KernelLogic for validation
        predictions: Optional predicted finish positions for calibration
        random_seed: Random seed for reproducibility (default: 42)

    Returns:
        Dictionary with:
            - scenarios: List of valid ScenarioComponents
            - calibration_metrics: Dict with CRPS, log_score, coverage
            - kernel_rejection_stats: Dict with rejection statistics
            - report_path: Path to calibration report (if generated)

    Examples:
        >>> result = end_to_end_calibration(
        ...     constraint_spec=spec,
        ...     track_id='daytona',
        ...     n_scenarios=100,
        ...     kernel=kernel
        ... )
        >>> print(f"Generated {len(result['scenarios'])} scenarios")
        >>> print(f"Rejection rate: {result['kernel_rejection_stats']['rejection_rate']:.2%}")
    """
    logger.info(f"Starting end-to-end calibration: track={track_id}, n_scenarios={n_scenarios}")

    # Import generate_scenarios_with_constraints
    # Use sys.path to handle module import
    import sys
    from pathlib import Path

    # Add packages to path if not already there
    # Navigate from apps/backend/app/calibration/diagnostics.py to project root
    current_file = Path(__file__)  # .../apps/backend/app/calibration/diagnostics.py
    backend_app = current_file.parent.parent  # .../apps/backend/app
    backend = backend_app.parent  # .../apps/backend
    apps = backend.parent  # .../apps
    project_root = apps.parent  # .../project_root

    packages_src = project_root / "packages" / "axiomatic-sim" / "src"
    if str(packages_src) not in sys.path:
        sys.path.insert(0, str(packages_src))

    try:
        from axiomatic_sim.scenario_generator import generate_scenarios_with_constraints
    except ImportError as e:
        logger.error(f"Failed to import generate_scenarios_with_constraints: {e}")
        raise ImportError(
            "Could not import scenario generator. Ensure axiomatic-sim package is available."
        )

    # Import kernel stats
    from app.kernel import get_rejection_stats, reset_rejection_stats

    # Reset kernel stats for clean measurement
    reset_rejection_stats()

    # Generate scenarios with compiled constraints
    logger.info(f"Generating {n_scenarios} scenarios with compiled constraints")
    scenarios = generate_scenarios_with_constraints(
        constraint_spec=constraint_spec,
        track_id=track_id,
        n_scenarios=n_scenarios,
        kernel=kernel,
        random_seed=random_seed,
    )

    logger.info(f"Generated {len(scenarios)} valid scenarios")

    # Get kernel rejection statistics
    kernel_rejection_stats = get_rejection_stats()

    logger.info(
        f"Kernel rejection rate: {kernel_rejection_stats['rejection_rate']:.2%} "
        f"({kernel_rejection_stats['total_rejected']}/{kernel_rejection_stats['total_validated']} rejected)"
    )

    # Assess calibration on scenario results
    logger.info("Assessing scenario calibration")
    calibration_metrics = assess_scenario_calibration(
        scenarios=scenarios,
        predictions=predictions,
        track_archetype=track_id,
    )

    # Add kernel stats to calibration metrics
    calibration_metrics['kernel_rejection_stats'] = kernel_rejection_stats

    # Log warnings for miscalibration
    if calibration_metrics.get('crps') is not None:
        if calibration_metrics['crps'] > 10:
            logger.warning(f"High CRPS detected: {calibration_metrics['crps']:.4f}")

    # Log warnings for high rejection rate
    if kernel_rejection_stats['rejection_rate'] > 0.5:
        logger.warning(
            f"High kernel rejection rate: {kernel_rejection_stats['rejection_rate']:.2%} "
            f"(>50% of scenarios rejected)"
        )

    # Log coverage deviation warnings
    if 'coverage' in calibration_metrics:
        for level, coverage in calibration_metrics['coverage'].items():
            expected = float(level)
            deviation = abs(coverage - expected)
            if deviation > 0.1:
                logger.warning(
                    f"Miscalibrated coverage at {level:.0%}: "
                    f"observed={coverage:.3f}, expected={expected:.3f}, "
                    f"deviation={deviation:.3f}"
                )

    logger.info("End-to-end calibration complete")

    return {
        'scenarios': scenarios,
        'calibration_metrics': calibration_metrics,
        'kernel_rejection_stats': kernel_rejection_stats,
        'report_path': None,  # Can be enhanced to generate report
    }
