"""Background job management for NASCAR DFS Optimizer.

Provides concurrent optimization job queue with thread pool execution,
SQLite persistence, and Qt signal integration.
"""

from .job_manager import JobManager, JobStatus
from .gpu_client import GPUWorkerClient, GPUWorkerError

__all__ = ["JobManager", "JobStatus", "GPUWorkerClient", "GPUWorkerError"]
