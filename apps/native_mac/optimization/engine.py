"""OptimizationEngine facade for coordinating optimizer, worker, and persistence."""

import json
import logging
from typing import List, Dict, Any, Optional, Callable

from PySide6.QtCore import QObject

from ..persistence.database import DatabaseManager
from .mcmc_optimizer import MCMCLineupOptimizer
from .progress_worker import OptimizationWorker

logger = logging.getLogger(__name__)


class OptimizationEngine(QObject):
    """High-level facade for lineup optimization with database integration.

    This class provides a simple API for the GUI to:
    - Start optimization in background threads
    - Save/load optimization results to/from database
    - Manage optimization configuration

    The engine handles the coordination between:
    - MCMCLineupOptimizer: JAX-based MCMC optimization
    - OptimizationWorker: QThread for non-blocking execution
    - DatabaseManager: SQLite persistence of results

    Example:
        engine = OptimizationEngine(database_manager)
        worker = engine.start_optimization(
            race_id=1,
            drivers=driver_list,
            progress_callback=update_progress_bar,
            finished_callback=display_results
        )
    """

    def __init__(
        self,
        database_manager: DatabaseManager,
        default_iterations: int = 1000,
        default_num_lineups: int = 20,
        parent: Optional[QObject] = None,
    ):
        """Initialize optimization engine.

        Args:
            database_manager: DatabaseManager instance for persistence
            default_iterations: Default MCMC iterations
            default_num_lineups: Default number of lineups to generate
            parent: Optional parent QObject
        """
        super().__init__(parent)

        self.database_manager = database_manager
        self.default_iterations = default_iterations
        self.default_num_lineups = default_num_lineups

        # Create optimizer instance
        self.optimizer = MCMCLineupOptimizer(
            default_iterations=default_iterations,
        )

        # Track active worker
        self._active_worker: Optional[OptimizationWorker] = None

        logger.info(
            f"OptimizationEngine initialized: "
            f"default_iterations={default_iterations}, "
            f"default_num_lineups={default_num_lineups}"
        )

    def start_optimization(
        self,
        race_id: int,
        drivers: List[Dict[str, Any]],
        constraints: Optional[Dict[str, Any]] = None,
        num_lineups: Optional[int] = None,
        iterations: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int, float], None]] = None,
        finished_callback: Optional[Callable[[List[Dict[str, Any]]], None]] = None,
        error_callback: Optional[Callable[[str], None]] = None,
        cancelled_callback: Optional[Callable[[], None]] = None,
    ) -> OptimizationWorker:
        """Start optimization in background thread.

        Args:
            race_id: Race ID for saving results
            drivers: List of driver dictionaries
            constraints: Optional constraints dict
                - min_stack: int - minimum drivers from same team
                - max_stack: int - maximum drivers from same team
                - exclude_drivers: List[str] - driver IDs to exclude
            num_lineups: Number of lineups to generate (default: self.default_num_lineups)
            iterations: MCMC iterations (default: self.default_iterations)
            progress_callback: Called with (current, total, best_score) during optimization
            finished_callback: Called with list of lineups when complete
            error_callback: Called with error message if optimization fails
            cancelled_callback: Called if optimization is cancelled

        Returns:
            OptimizationWorker instance for monitoring/cancellation

        Raises:
            RuntimeError: If optimization already in progress
        """
        # Check if already running
        if self._active_worker and self._active_worker.isRunning():
            raise RuntimeError("Optimization already in progress")

        # Use defaults if not specified
        num_lineups = num_lineups or self.default_num_lineups
        iterations = iterations or self.default_iterations

        logger.info(
            f"Starting optimization for race {race_id}: "
            f"{num_lineups} lineups, {len(drivers)} drivers"
        )

        # Create worker
        worker = OptimizationWorker(
            optimizer=self.optimizer,
            drivers=drivers,
            num_lineups=num_lineups,
            constraints=constraints,
            iterations=iterations,
            parent=self,
        )

        # Connect signals to callbacks
        if progress_callback:
            worker.progress.connect(progress_callback)

        if finished_callback:
            # Wrap finished callback to save results
            def on_finished(lineups: List[Dict[str, Any]]) -> None:
                try:
                    self.save_results(race_id, lineups)
                    finished_callback(lineups)
                except Exception as e:
                    logger.error(f"Error saving results: {e}")
                    if error_callback:
                        error_callback(f"Failed to save results: {e}")

            worker.finished.connect(on_finished)

        if error_callback:
            worker.error.connect(error_callback)

        if cancelled_callback:
            worker.cancelled.connect(cancelled_callback)

        # Track active worker
        self._active_worker = worker

        # Clean up when done
        worker.finished.connect(self._on_worker_finished)
        worker.cancelled.connect(self._on_worker_finished)
        worker.error.connect(self._on_worker_finished)

        # Start worker
        worker.start()

        return worker

    def cancel_optimization(self) -> None:
        """Cancel the currently running optimization."""
        if self._active_worker and self._active_worker.isRunning():
            logger.info("Cancelling active optimization")
            self._active_worker.cancel()

    def is_running(self) -> bool:
        """Check if optimization is currently running.

        Returns:
            True if optimization is in progress, False otherwise
        """
        return self._active_worker is not None and self._active_worker.isRunning()

    def save_results(
        self,
        race_id: int,
        lineups: List[Dict[str, Any]],
    ) -> List[int]:
        """Save generated lineups to database.

        Args:
            race_id: Race ID to associate with lineups
            lineups: List of lineup dictionaries

        Returns:
            List of lineup IDs from database

        Raises:
            ValueError: If lineup format is invalid
        """
        lineup_ids = []

        for lineup in lineups:
            # Validate lineup format
            self._validate_lineup(lineup)

            # Prepare lineup data for storage
            lineup_data = {
                "drivers": [
                    {
                        "driver_id": d.get("driver_id"),
                        "name": d.get("name"),
                        "team": d.get("team"),
                        "salary": d.get("salary"),
                        "projected_points": d.get("projected_points"),
                    }
                    for d in lineup["drivers"]
                ],
                "total_projected_points": lineup.get("total_projected_points", 0),
                "total_salary": lineup.get("total_salary", 0),
                "total_value": lineup.get("total_value", 0),
                "risk_score": lineup.get("risk_score", 0),
                "lineup_score": lineup.get("lineup_score", 0),
            }

            # Save to database
            lineup_id = self.database_manager.save_lineup(race_id, lineup_data)
            lineup_ids.append(lineup_id)

        logger.info(f"Saved {len(lineup_ids)} lineups for race {race_id}")
        return lineup_ids

    def load_results(self, race_id: int) -> List[Dict[str, Any]]:
        """Load previously generated lineups for a race.

        Args:
            race_id: Race ID to load lineups for

        Returns:
            List of lineup dictionaries
        """
        records = self.database_manager.load_lineups(race_id)

        lineups = []
        for record in records:
            lineup_data = record.get("lineup_data", {})

            # Convert to standard format
            lineup = {
                "id": record.get("id"),
                "race_id": record.get("race_id"),
                "drivers": lineup_data.get("drivers", []),
                "total_projected_points": lineup_data.get("total_projected_points", 0),
                "total_salary": lineup_data.get("total_salary", 0),
                "total_value": lineup_data.get("total_value", 0),
                "risk_score": lineup_data.get("risk_score", 0),
                "lineup_score": lineup_data.get("lineup_score", 0),
                "created_at": record.get("created_at"),
            }

            lineups.append(lineup)

        logger.info(f"Loaded {len(lineups)} lineups for race {race_id}")
        return lineups

    def delete_lineup(self, lineup_id: int) -> bool:
        """Delete a lineup by ID.

        Args:
            lineup_id: ID of lineup to delete

        Returns:
            True if deleted, False if not found
        """
        return self.database_manager.delete_lineup(lineup_id)

    def load_config(self) -> Dict[str, Any]:
        """Load optimization configuration from app_state.

        Returns:
            Configuration dictionary with defaults
        """
        config_record = self.database_manager.load_config("optimization_defaults")

        if config_record:
            config = config_record.get("config_data", {})
        else:
            config = {}

        # Apply defaults
        return {
            "iterations": config.get("iterations", self.default_iterations),
            "num_lineups": config.get("num_lineups", self.default_num_lineups),
            "temperature": config.get("temperature", 1.0),
            "salary_cap": config.get("salary_cap", 50000),
            "min_stack": config.get("min_stack", 0),
            "max_stack": config.get("max_stack", 6),
        }

    def save_config(self, config: Dict[str, Any]) -> int:
        """Save optimization configuration to app_state.

        Args:
            config: Configuration dictionary

        Returns:
            Configuration ID
        """
        return self.database_manager.save_config("optimization_defaults", config)

    def _validate_lineup(self, lineup: Dict[str, Any]) -> None:
        """Validate lineup format before saving.

        Args:
            lineup: Lineup dictionary to validate

        Raises:
            ValueError: If lineup is invalid
        """
        # Check required fields
        if "drivers" not in lineup:
            raise ValueError("Lineup missing 'drivers' field")

        drivers = lineup["drivers"]

        # Check lineup size
        if len(drivers) != 6:
            raise ValueError(f"Lineup must have 6 drivers, got {len(drivers)}")

        # Check salary cap
        total_salary = sum(d.get("salary", 0) for d in drivers)
        if total_salary > 50000:
            raise ValueError(f"Lineup exceeds salary cap: ${total_salary} > $50000")

        # Check each driver has required fields
        for driver in drivers:
            if "name" not in driver:
                raise ValueError("Driver missing 'name' field")
            if "salary" not in driver:
                raise ValueError("Driver missing 'salary' field")

    def _on_worker_finished(self) -> None:
        """Handle worker completion/cancellation/error."""
        logger.debug("Worker finished, clearing active worker")
        self._active_worker = None

    def get_default_constraints(self) -> Dict[str, Any]:
        """Get default optimization constraints.

        Returns:
            Default constraints dictionary
        """
        return {
            "min_stack": 0,
            "max_stack": 6,
            "exclude_drivers": [],
        }

    def calculate_driver_stats(
        self,
        drivers: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Calculate statistics for driver pool.

        Args:
            drivers: List of driver dictionaries

        Returns:
            Statistics dictionary
        """
        if not drivers:
            return {
                "count": 0,
                "avg_salary": 0,
                "avg_projected_points": 0,
                "salary_range": (0, 0),
            }

        salaries = [d.get("salary", 0) for d in drivers]
        points = [d.get("projected_points", 0) for d in drivers]

        return {
            "count": len(drivers),
            "avg_salary": sum(salaries) / len(salaries),
            "avg_projected_points": sum(points) / len(points) if points else 0,
            "salary_range": (min(salaries), max(salaries)),
            "total_combinations": self._estimate_combinations(drivers),
        }

    def _estimate_combinations(self, drivers: List[Dict[str, Any]]) -> int:
        """Estimate number of valid lineup combinations.

        Args:
            drivers: List of driver dictionaries

        Returns:
            Estimated number of valid combinations
        """
        n = len(drivers)
        if n < 6:
            return 0

        # Rough estimate: C(n, 6) filtered by salary cap
        # Actual number will be much less due to salary constraints
        from math import comb

        total = comb(n, 6)

        # Assume ~10% of combinations satisfy salary cap
        return total // 10
