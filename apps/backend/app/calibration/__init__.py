"""
Calibration harness for track-archetype uncertainty quantification.

This package provides probabilistic calibration metrics and diagnostics for
assessing how well CBN-sampled scenarios match observed outcomes by track type.

Modules:
    metrics: CRPS, log score, and coverage calculations
    models: NumPyro calibration models with NUTS sampling
    diagnostics: ArviZ posterior predictive checks and calibration plots
"""

from app.calibration.metrics import compute_crps, compute_log_score, compute_coverage, compute_all_metrics
from app.calibration.models import track_archetype_calibration_model, run_mcmc_calibration, compute_calibration_summary
from app.calibration.diagnostics import (
    posterior_predictive_check,
    plot_calibration_curve,
    compute_joint_event_validation,
    assess_mcmc_convergence,
    generate_calibration_report,
)

__all__ = [
    # Metrics
    "compute_crps",
    "compute_log_score",
    "compute_coverage",
    "compute_all_metrics",
    # Models
    "track_archetype_calibration_model",
    "run_mcmc_calibration",
    "compute_calibration_summary",
    # Diagnostics
    "posterior_predictive_check",
    "plot_calibration_curve",
    "compute_joint_event_validation",
    "assess_mcmc_convergence",
    "generate_calibration_report",
]
