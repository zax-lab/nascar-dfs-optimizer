"""JobManager for concurrent optimization job execution.

Manages background jobs using ThreadPoolExecutor for true parallelism,
with SQLite persistence for job history and crash recovery.
Supports GPU offload to remote Windows GPU workers.
"""

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable

from PySide6.QtCore import QObject, Signal

from ..persistence.database import DatabaseManager
from ..persistence.models import Job, JobStatus
from ..optimization.mcmc_optimizer import MCMCLineupOptimizer
from .gpu_client import GPUWorkerClient, GPUWorkerError

logger = logging.getLogger(__name__)


class JobManager(QObject):
    """Manages concurrent optimization jobs with thread pool execution.

    Provides:
    - ThreadPoolExecutor for concurrent job execution (CPU-bound JAX work)
    - SQLite persistence for job history and crash recovery
    - Qt signals for job lifecycle events
    - Job queue management (submit, cancel, query)

    Signals:
        job_started: Emitted when a job starts running (job_id)
        job_progress: Emitted on progress updates (job_id, percent, message)
        job_completed: Emitted when job completes successfully (job_id, results)
        job_failed: Emitted when job fails (job_id, error_message)
        job_cancelled: Emitted when job is cancelled (job_id)
        job_status_changed: Emitted on any status change (job_id, new_status)

    Example:
        job_manager = JobManager(max_workers=4)
        job_id = job_manager.submit_job({
            "race_id": 1,
            "drivers": [...],
            "num_lineups": 20,
            "iterations": 1000
        })
        # Job runs in background, signals emitted on progress/completion
    """

    # Qt signals for job lifecycle events
    job_started = Signal(str)  # job_id
    job_progress = Signal(str, int, str)  # job_id, percent, message
    job_completed = Signal(str, list)  # job_id, lineups
    job_failed = Signal(str, str)  # job_id, error_message
    job_cancelled = Signal(str)  # job_id
    job_status_changed = Signal(str, str)  # job_id, status

    def __init__(
        self,
        database_manager: DatabaseManager,
        max_workers: Optional[int] = None,
        gpu_client: Optional[GPUWorkerClient] = None,
        parent: Optional[QObject] = None,
    ):
        """Initialize JobManager.

        Args:
            database_manager: DatabaseManager for job persistence
            max_workers: Maximum concurrent jobs (default: CPU count)
            gpu_client: Optional GPUWorkerClient for GPU offload
            parent: Optional parent QObject
        """
        super().__init__(parent)

        self.database_manager = database_manager
        self.max_workers = max_workers or os.cpu_count() or 2
        self.gpu_client = gpu_client

        # Thread pool for concurrent execution
        self.executor = ThreadPoolExecutor(
            max_workers=self.max_workers, thread_name_prefix="optimization_worker_"
        )

        # Track active futures
        self._active_futures: Dict[str, Future] = {}

        # Cancellation flags for running jobs
        self._cancel_flags: Dict[str, bool] = {}

        # Optimizer instance (will be created per thread as needed)
        self._optimizer: Optional[MCMCLineupOptimizer] = None

        logger.info(f"JobManager initialized with {self.max_workers} workers")
        if gpu_client:
            logger.info(f"GPU client configured: {gpu_client.base_url}")

    @property
    def is_gpu_available(self) -> bool:
        """Check if GPU worker is available.

        Returns:
            True if GPU client is configured and connected, False otherwise
        """
        if self.gpu_client is None:
            return False
        return self.gpu_client.is_available()

    def submit_job(
        self,
        config: Dict[str, Any],
        job_name: Optional[str] = None,
    ) -> str:
        """Submit a new optimization job to the queue.

        Args:
            config: Optimization configuration dict with:
                - race_id: int
                - drivers: List[Dict] with name, salary, projected_points, team
                - num_lineups: int (default: 20)
                - iterations: int (default: 1000)
                - constraints: Dict with min_stack, max_stack, exclude_drivers
                - gpu_offload: bool (optional, default False) - use GPU worker
            job_name: Optional human-readable name (default: "Optimization {race}")

        Returns:
            str: Job ID (UUID)

        Raises:
            ValueError: If config is missing required fields
        """
        # Validate config
        if "race_id" not in config:
            raise ValueError("config must contain 'race_id'")
        if "drivers" not in config or not config["drivers"]:
            raise ValueError("config must contain non-empty 'drivers' list")

        # Generate job name if not provided
        if job_name is None:
            race_id = config.get("race_id", "unknown")
            job_name = f"Optimization Race {race_id}"

        # Check if GPU offload is requested
        gpu_offload = config.get("gpu_offload", False)
        execution_mode = "local"  # Default

        if gpu_offload and self.gpu_client:
            # Test connection before routing to GPU
            if self.gpu_client.test_connection():
                execution_mode = "gpu"
                logger.info(f"Job will use GPU offload via {self.gpu_client.base_url}")
            else:
                logger.warning(
                    "GPU offload requested but worker unavailable, falling back to local CPU"
                )

        # Add execution mode to metadata
        config["execution_mode"] = execution_mode

        # Create job record
        job = Job.create(name=job_name, config=config)

        # Save to database
        job_dict = job.to_dict()
        self.database_manager.insert_job(job_dict)

        # Submit to appropriate executor
        if execution_mode == "gpu":
            future = self.executor.submit(self._execute_job_gpu, job.id, config)
        else:
            future = self.executor.submit(self._execute_job, job.id, config)

        self._active_futures[job.id] = future

        logger.info(f"Submitted job {job.id}: {job_name} (mode: {execution_mode})")

        return job.id

    def cancel_job(self, job_id: str) -> bool:
        """Attempt to cancel a job.

        Args:
            job_id: ID of job to cancel

        Returns:
            bool: True if cancellation was requested, False if job not found
                   or already terminal
        """
        # Check if job exists and is active
        job_dict = self.database_manager.get_job(job_id)
        if not job_dict:
            logger.warning(f"Cannot cancel: job {job_id} not found")
            return False

        status = job_dict.get("status")
        if status not in ("queued", "running"):
            logger.info(f"Cannot cancel job {job_id}: already {status}")
            return False

        # Set cancellation flag
        self._cancel_flags[job_id] = True

        # Cancel the future if it's still pending
        future = self._active_futures.get(job_id)
        if future and not future.done():
            future.cancel()

        # Update status if queued (can cancel immediately)
        if status == "queued":
            self._update_job_status(job_id, JobStatus.CANCELLED)
            self.job_cancelled.emit(job_id)
            self.job_status_changed.emit(job_id, "cancelled")

        logger.info(f"Cancellation requested for job {job_id}")
        return True

    def get_job_status(self, job_id: str) -> Optional[JobStatus]:
        """Get the current status of a job.

        Args:
            job_id: ID of job to query

        Returns:
            JobStatus enum value, or None if job not found
        """
        job_dict = self.database_manager.get_job(job_id)
        if not job_dict:
            return None

        return JobStatus(job_dict.get("status", "queued"))

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get full job details.

        Args:
            job_id: ID of job to retrieve

        Returns:
            Job dictionary with all fields, or None if not found
        """
        return self.database_manager.get_job(job_id)

    def get_running_jobs(self) -> List[Dict[str, Any]]:
        """Get all currently running jobs.

        Returns:
            List of job dictionaries with status='running'
        """
        return self.database_manager.list_jobs(status="running")

    def get_queued_jobs(self) -> List[Dict[str, Any]]:
        """Get all queued jobs.

        Returns:
            List of job dictionaries with status='queued'
        """
        return self.database_manager.list_jobs(status="queued")

    def get_recent_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent jobs regardless of status.

        Args:
            limit: Maximum number of jobs to return

        Returns:
            List of job dictionaries, most recent first
        """
        return self.database_manager.list_jobs(limit=limit)

    def get_running_jobs_count(self) -> int:
        """Get count of currently running jobs.

        Returns:
            int: Number of jobs with status='running'
        """
        return len(self.get_running_jobs())

    def get_queued_jobs_count(self) -> int:
        """Get count of queued jobs.

        Returns:
            int: Number of jobs with status='queued'
        """
        return len(self.get_queued_jobs())

    def get_active_jobs_count(self) -> int:
        """Get count of active jobs (queued + running).

        Returns:
            int: Total number of active jobs
        """
        return self.get_running_jobs_count() + self.get_queued_jobs_count()

    def shutdown(self, wait: bool = True, timeout: Optional[float] = None) -> None:
        """Shutdown the job manager and executor.

        Args:
            wait: If True, wait for running jobs to complete
            timeout: Maximum time to wait (seconds), None for indefinite
        """
        logger.info(f"Shutting down JobManager (wait={wait}, timeout={timeout})")

        # Cancel all queued jobs
        queued = self.get_queued_jobs()
        for job in queued:
            job_id = job.get("id")
            if job_id:
                self._update_job_status(job_id, JobStatus.CANCELLED)

        # Set cancellation flags for running jobs
        running = self.get_running_jobs()
        for job in running:
            job_id = job.get("id")
            if job_id:
                self._cancel_flags[job_id] = True

        # Shutdown executor
        self.executor.shutdown(wait=wait)

        logger.info("JobManager shutdown complete")

    def _execute_job(self, job_id: str, config: Dict[str, Any]) -> None:
        """Internal method to execute a job in the thread pool.

        This method runs in a worker thread and performs the actual
        optimization work.

        Args:
            job_id: Job ID for tracking
            config: Optimization configuration
        """
        try:
            # Check if already cancelled
            if self._cancel_flags.get(job_id, False):
                logger.info(f"Job {job_id} was cancelled before starting")
                return

            # Update status to running
            self._update_job_status(job_id, JobStatus.RUNNING)
            self.job_started.emit(job_id)
            self.job_status_changed.emit(job_id, "running")

            # Extract config
            drivers = config.get("drivers", [])
            num_lineups = config.get("num_lineups", 20)
            iterations = config.get("iterations", 1000)
            constraints = config.get("constraints", {})

            # Create optimizer (per thread)
            optimizer = MCMCLineupOptimizer(default_iterations=iterations)

            # Progress callback
            def progress_callback(current: int, total: int, best_score: float) -> None:
                if self._cancel_flags.get(job_id, False):
                    return  # Will be caught by optimizer's cancellation check

                percent = int((current / total) * 100)
                message = f"Iteration {current}/{total} (best: {best_score:.2f})"

                # Update progress in database (throttle to every 10% or 5 seconds)
                if percent % 10 == 0:
                    self.database_manager.update_job(
                        job_id, {"progress_percent": percent}
                    )

                # Emit signal
                self.job_progress.emit(job_id, percent, message)

            # Run optimization
            logger.info(f"Starting optimization for job {job_id}")
            lineups = optimizer.optimize(
                drivers=drivers,
                num_lineups=num_lineups,
                constraints=constraints,
                progress_callback=progress_callback,
                cancellation_check=lambda: self._cancel_flags.get(job_id, False),
            )

            # Check if cancelled during execution
            if self._cancel_flags.get(job_id, False):
                logger.info(f"Job {job_id} was cancelled during execution")
                self._update_job_status(job_id, JobStatus.CANCELLED)
                self.job_cancelled.emit(job_id)
                self.job_status_changed.emit(job_id, "cancelled")
                return

            # Save results
            result_data = {
                "lineups": lineups,
                "lineup_count": len(lineups),
                "completed_at": datetime.now().isoformat(),
            }

            self.database_manager.update_job(
                job_id,
                {
                    "status": "completed",
                    "result_json": result_data,
                    "completed_at": datetime.now().isoformat(),
                    "progress_percent": 100,
                },
            )

            logger.info(
                f"Job {job_id} completed successfully with {len(lineups)} lineups"
            )

            # Emit signals
            self.job_completed.emit(job_id, lineups)
            self.job_status_changed.emit(job_id, "completed")

        except Exception as e:
            logger.exception(f"Job {job_id} failed: {e}")

            # Update status to failed
            self.database_manager.update_job(
                job_id,
                {
                    "status": "failed",
                    "error_message": str(e),
                    "completed_at": datetime.now().isoformat(),
                },
            )

            # Emit signals
            self.job_failed.emit(job_id, str(e))
            self.job_status_changed.emit(job_id, "failed")

        finally:
            # Clean up
            if job_id in self._active_futures:
                del self._active_futures[job_id]
            if job_id in self._cancel_flags:
                del self._cancel_flags[job_id]

    def _execute_job_gpu(self, job_id: str, config: Dict[str, Any]) -> None:
        """Execute a job on the remote GPU worker.

        This method runs in a worker thread and submits the job to the
        GPU worker via HTTP, then polls for completion.

        Args:
            job_id: Job ID for tracking
            config: Optimization configuration with gpu_offload=True
        """
        try:
            # Check if already cancelled
            if self._cancel_flags.get(job_id, False):
                logger.info(f"Job {job_id} was cancelled before starting")
                return

            # Update status to running
            self._update_job_status(job_id, JobStatus.RUNNING)
            self.job_started.emit(job_id)
            self.job_status_changed.emit(job_id, "running")

            logger.info(f"Starting GPU execution for job {job_id}")

            # Submit to GPU worker
            response = self.gpu_client.submit_job(job_id, config)

            # Handle synchronous completion (immediate result)
            if response.get("status") == "completed":
                result_data = response.get("result", {})
                lineups = result_data.get("lineups", [])

                # Save results
                self.database_manager.update_job(
                    job_id,
                    {
                        "status": "completed",
                        "result_json": result_data,
                        "completed_at": datetime.now().isoformat(),
                        "progress_percent": 100,
                    },
                )

                logger.info(
                    f"Job {job_id} completed on GPU with {len(lineups)} lineups"
                )

                # Emit signals
                self.job_completed.emit(job_id, lineups)
                self.job_status_changed.emit(job_id, "completed")
                return

            # Handle asynchronous (poll for completion)
            if response.get("status") == "accepted":
                # Poll for completion
                max_poll_time = config.get("gpu_timeout", 300)  # 5 min default
                poll_interval = 2  # seconds
                start_time = time.time()
                last_progress = 0

                while time.time() - start_time < max_poll_time:
                    # Check for cancellation
                    if self._cancel_flags.get(job_id, False):
                        logger.info(f"Job {job_id} was cancelled during GPU execution")
                        try:
                            self.gpu_client.cancel_job(job_id)
                        except Exception:
                            pass  # Best effort
                        self._update_job_status(job_id, JobStatus.CANCELLED)
                        self.job_cancelled.emit(job_id)
                        self.job_status_changed.emit(job_id, "cancelled")
                        return

                    # Check status
                    try:
                        status_response = self.gpu_client.get_job_status(job_id)
                        status = status_response.get("status")
                        progress = status_response.get("progress", 0)

                        # Emit progress updates
                        if progress > last_progress:
                            message = f"GPU processing: {progress}%"
                            self.job_progress.emit(job_id, progress, message)
                            if progress % 10 == 0:
                                self.database_manager.update_job(
                                    job_id, {"progress_percent": progress}
                                )
                            last_progress = progress

                        # Check completion
                        if status == "completed":
                            result_data = status_response.get("result", {})
                            lineups = result_data.get("lineups", [])

                            self.database_manager.update_job(
                                job_id,
                                {
                                    "status": "completed",
                                    "result_json": result_data,
                                    "completed_at": datetime.now().isoformat(),
                                    "progress_percent": 100,
                                },
                            )

                            logger.info(
                                f"Job {job_id} completed on GPU with {len(lineups)} lineups"
                            )

                            self.job_completed.emit(job_id, lineups)
                            self.job_status_changed.emit(job_id, "completed")
                            return

                        if status == "failed":
                            error_msg = status_response.get(
                                "error", "GPU worker failed"
                            )
                            raise Exception(f"GPU worker error: {error_msg}")

                    except GPUWorkerError as e:
                        # Connection lost during polling
                        logger.error(f"Lost connection to GPU worker: {e}")
                        raise Exception(f"GPU connection lost: {e}")

                    time.sleep(poll_interval)

                # Timeout
                raise Exception(f"GPU job timed out after {max_poll_time}s")

            # Unknown status
            raise Exception(f"Unexpected GPU response: {response.get('status')}")

        except Exception as e:
            logger.exception(f"Job {job_id} failed on GPU: {e}")

            # Try to cancel on GPU if still running
            try:
                self.gpu_client.cancel_job(job_id)
            except Exception:
                pass  # Best effort

            # Check if we should fallback to local
            if config.get("gpu_fallback_on_error", True):
                logger.info(f"Falling back to local CPU for job {job_id}")
                self.fallback_job_to_local(job_id, config)
            else:
                # Mark as failed
                self.database_manager.update_job(
                    job_id,
                    {
                        "status": "failed",
                        "error_message": str(e),
                        "completed_at": datetime.now().isoformat(),
                    },
                )

                self.job_failed.emit(job_id, str(e))
                self.job_status_changed.emit(job_id, "failed")

        finally:
            # Clean up
            if job_id in self._active_futures:
                del self._active_futures[job_id]
            if job_id in self._cancel_flags:
                del self._cancel_flags[job_id]

    def fallback_job_to_local(self, job_id: str, config: Dict[str, Any]) -> None:
        """Fallback a job to local CPU execution after GPU failure.

        Updates the job status and re-queues it for local execution.

        Args:
            job_id: ID of job to fallback
            config: Optimization configuration (will remove gpu_offload flag)
        """
        logger.info(f"Falling back job {job_id} to local CPU execution")

        # Remove GPU offload flag to prevent infinite loop
        local_config = config.copy()
        local_config["gpu_offload"] = False
        local_config["execution_mode"] = "local"
        local_config["gpu_fallback"] = True  # Mark as fallback

        # Update job config in database
        self.database_manager.update_job(
            job_id,
            {
                "config_json": local_config,
                "error_message": "Falling back to local CPU after GPU failure",
            },
        )

        # Re-queue for local execution
        future = self.executor.submit(self._execute_job, job_id, local_config)
        self._active_futures[job_id] = future

        logger.info(f"Job {job_id} re-queued for local execution")

    def _update_job_status(self, job_id: str, status: JobStatus) -> None:
        """Update job status in database.

        Args:
            job_id: Job ID to update
            status: New status value
        """
        updates = {"status": status.value}

        if status == JobStatus.RUNNING:
            updates["started_at"] = datetime.now().isoformat()
        elif status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            updates["completed_at"] = datetime.now().isoformat()

        self.database_manager.update_job(job_id, updates)

    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.shutdown(wait=False)
        except Exception:
            pass
