"""QThread worker for running optimization with progress signals."""

import logging
from typing import List, Dict, Any, Optional, Callable

from PySide6.QtCore import QThread, Signal, QObject

from .mcmc_optimizer import MCMCLineupOptimizer, CancellationError

logger = logging.getLogger(__name__)


class OptimizationWorker(QThread):
    """QThread worker for running MCMC optimization without blocking the UI.

    This worker runs the optimization in a background thread, emitting signals
    for progress updates, completion, errors, and cancellation. This allows
    the main GUI to remain responsive during the 30-60 second MCMC sampling
    process.

    Signals:
        progress(current, total, best_score): Emitted during optimization
        finished(lineups): Emitted when optimization completes successfully
        error(message): Emitted when an error occurs
        cancelled(): Emitted when optimization is cancelled by user

    Example:
        worker = OptimizationWorker(optimizer, drivers, num_lineups=20)
        worker.progress.connect(update_progress_bar)
        worker.finished.connect(handle_results)
        worker.error.connect(show_error_dialog)
        worker.start()
    """

    # Signal emitted during optimization: (current_iteration, total_iterations, best_score)
    progress = Signal(int, int, float)

    # Signal emitted on completion: (list_of_lineups)
    finished = Signal(list)

    # Signal emitted on error: (error_message)
    error = Signal(str)

    # Signal emitted on cancellation
    cancelled = Signal()

    def __init__(
        self,
        optimizer: MCMCLineupOptimizer,
        drivers: List[Dict[str, Any]],
        num_lineups: int = 20,
        constraints: Optional[Dict[str, Any]] = None,
        iterations: Optional[int] = None,
        parent: Optional[QObject] = None,
    ):
        """Initialize optimization worker.

        Args:
            optimizer: MCMCLineupOptimizer instance to use
            drivers: List of driver dictionaries
            num_lineups: Number of lineups to generate (default 20)
            constraints: Optional constraints dict
                - min_stack: int - minimum drivers from same team
                - max_stack: int - maximum drivers from same team
                - exclude_drivers: List[str] - driver IDs to exclude
            iterations: Optional override for MCMC iterations
            parent: Optional parent QObject
        """
        super().__init__(parent)

        self.optimizer = optimizer
        self.drivers = drivers
        self.num_lineups = num_lineups
        self.constraints = constraints or {}
        self.iterations = iterations

        # Cancellation flag
        self._cancelled = False

        logger.info(
            f"OptimizationWorker initialized: {num_lineups} lineups, "
            f"{len(drivers)} drivers"
        )

    def run(self) -> None:
        """Run the optimization in background thread.

        This method is called when the thread starts. It wraps the
        optimizer.optimize() call with error handling and signal emission.
        """
        try:
            logger.info("Starting optimization worker")

            # Reset cancellation flag
            self._cancelled = False

            # Run optimization with progress callback
            lineups = self.optimizer.optimize(
                drivers=self.drivers,
                num_lineups=self.num_lineups,
                iterations=self.iterations,
                constraints=self.constraints,
                progress_callback=self._on_progress,
                cancellation_check=self._is_cancelled,
            )

            # Check if cancelled during optimization
            if self._cancelled:
                logger.info("Optimization was cancelled")
                self.cancelled.emit()
                return

            logger.info(f"Optimization complete: {len(lineups)} lineups generated")
            self.finished.emit(lineups)

        except CancellationError:
            logger.info("Optimization cancelled by user")
            self.cancelled.emit()

        except Exception as e:
            logger.error(f"Optimization error: {e}", exc_info=True)
            self.error.emit(str(e))

    def cancel(self) -> None:
        """Request cancellation of the optimization.

        Sets the internal cancellation flag. The optimizer will check
        this flag between iterations and stop gracefully.
        """
        logger.info("Cancellation requested")
        self._cancelled = True

    def _on_progress(self, current: int, total: int, best_score: float) -> None:
        """Handle progress updates from optimizer.

        Args:
            current: Current iteration
            total: Total iterations
            best_score: Current best lineup score
        """
        # Thread-safe signal emission
        self.progress.emit(current, total, best_score)

    def _is_cancelled(self) -> bool:
        """Check if cancellation has been requested.

        Returns:
            True if cancellation was requested, False otherwise
        """
        return self._cancelled


class OptimizationWorkerPool(QObject):
    """Pool for managing multiple optimization workers.

    Manages a collection of optimization workers, ensuring proper
    cleanup and preventing memory leaks from abandoned threads.

    Example:
        pool = OptimizationWorkerPool()
        worker = pool.create_worker(optimizer, drivers, num_lineups=20)
        worker.start()
    """

    def __init__(self, parent: Optional[QObject] = None):
        """Initialize worker pool.

        Args:
            parent: Optional parent QObject
        """
        super().__init__(parent)
        self._workers: List[OptimizationWorker] = []

    def create_worker(
        self,
        optimizer: MCMCLineupOptimizer,
        drivers: List[Dict[str, Any]],
        num_lineups: int = 20,
        constraints: Optional[Dict[str, Any]] = None,
        iterations: Optional[int] = None,
    ) -> OptimizationWorker:
        """Create a new optimization worker and track it.

        Args:
            optimizer: MCMCLineupOptimizer instance
            drivers: List of driver dictionaries
            num_lineups: Number of lineups to generate
            constraints: Optional constraints dict
            iterations: Optional iterations override

        Returns:
            New OptimizationWorker instance
        """
        worker = OptimizationWorker(
            optimizer=optimizer,
            drivers=drivers,
            num_lineups=num_lineups,
            constraints=constraints,
            iterations=iterations,
            parent=self,
        )

        # Track worker
        self._workers.append(worker)

        # Connect finished signal to cleanup
        worker.finished.connect(lambda: self._cleanup_worker(worker))
        worker.cancelled.connect(lambda: self._cleanup_worker(worker))
        worker.error.connect(lambda _: self._cleanup_worker(worker))

        return worker

    def cancel_all(self) -> None:
        """Cancel all active workers."""
        for worker in self._workers:
            if worker.isRunning():
                worker.cancel()

    def _cleanup_worker(self, worker: OptimizationWorker) -> None:
        """Remove worker from tracking list.

        Args:
            worker: Worker to clean up
        """
        if worker in self._workers:
            self._workers.remove(worker)
            logger.debug(f"Cleaned up worker, {len(self._workers)} remaining")

    def active_count(self) -> int:
        """Get number of active workers.

        Returns:
            Number of running workers
        """
        return sum(1 for w in self._workers if w.isRunning())
