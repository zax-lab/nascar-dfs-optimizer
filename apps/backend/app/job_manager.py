"""
Redis-based job state persistence for long-running optimization tasks.

This module provides JobStateManager for durable job storage using Redis hashes.
Jobs survive container restarts and include automatic TTL-based cleanup.

Key features:
- Redis hash storage per job (job:{job_id})
- Automatic expiration after JOB_TTL_DAYS (default: 7 days)
- Support for job status tracking (pending, running, completed, failed)
- Query methods for running job count (for graceful shutdown monitoring)
- Connection pooling for efficient Redis access

Usage:
    pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
    manager = JobStateManager(pool)
    await manager.create_job(job_id, input_params, correlation_id)
    status = await manager.get_job(job_id)
"""
import logging
import os
import json
from typing import Optional, Dict, Any
from datetime import datetime
import redis

logger = logging.getLogger(__name__)


class JobStateManager:
    """
    Redis-based job state persistence manager.

    Stores job state in Redis hashes with automatic TTL expiration.
    Each job is stored as a hash with key pattern "job:{job_id}".

    Job hash fields:
        status: Job status (pending, running, completed, failed)
        input_params: JSON-serialized input parameters
        result: JSON-serialized optimization result (empty if not completed)
        error_message: JSON-serialized error details (empty if no error)
        created_at: ISO format timestamp
        updated_at: ISO format timestamp
        scenario_count: Number of scenarios generated
        slate_id: Slate identifier
        correlation_id: Correlation ID for tracing

    Attributes:
        redis: Redis client instance with connection pool
        ttl: Time-to-live in seconds for job records
    """

    def __init__(self, redis_pool: redis.ConnectionPool):
        """
        Initialize JobStateManager with Redis connection pool.

        Args:
            redis_pool: Redis connection pool configured with health checks

        Raises:
            ValueError: If redis_pool is None
        """
        if redis_pool is None:
            raise ValueError("redis_pool cannot be None")

        self.redis = redis.Redis(connection_pool=redis_pool)
        self.ttl = self._parse_ttl()

        logger.info(f"JobStateManager initialized with TTL={self.ttl}s ({self.ttl//86400} days)")

    def _parse_ttl(self) -> int:
        """
        Parse JOB_TTL_DAYS from environment with validation.

        Returns:
            TTL in seconds (days * 86400)

        Default:
            7 days (604800 seconds) if JOB_TTL_DAYS not set
        """
        ttl_days_str = os.getenv("JOB_TTL_DAYS", "7")

        try:
            ttl_days = int(ttl_days_str)
            if ttl_days < 1:
                logger.warning(f"JOB_TTL_DAYS={ttl_days} invalid, using default 7 days")
                ttl_days = 7
            elif ttl_days > 365:
                logger.warning(f"JOB_TTL_DAYS={ttl_days} too high, capping at 365 days")
                ttl_days = 365
        except ValueError:
            logger.warning(f"JOB_TTL_DAYS={ttl_days_str} invalid, using default 7 days")
            ttl_days = 7

        return ttl_days * 86400

    async def create_job(
        self,
        job_id: str,
        input_params: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> None:
        """
        Create a new job record in Redis.

        Initializes job with status="pending", empty result and error_message,
        and current timestamp. Sets TTL for automatic expiration.

        Args:
            job_id: Unique job identifier (UUID)
            input_params: Optimization request parameters (will be JSON serialized)
            correlation_id: Optional correlation ID for distributed tracing

        Raises:
            redis.RedisError: If Redis operation fails
        """
        now = datetime.utcnow().isoformat()

        job_data = {
            "status": "pending",
            "input_params": json.dumps(input_params),
            "result": "",
            "error_message": "",
            "created_at": now,
            "updated_at": now,
            "scenario_count": "0",
            "slate_id": input_params.get("slate_id", ""),
            "correlation_id": correlation_id or job_id
        }

        key = f"job:{job_id}"
        self.redis.hset(key, mapping=job_data)
        self.redis.expire(key, self.ttl)

        logger.info(f"Created job {job_id} with TTL {self.ttl}s")

    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve job record from Redis.

        Args:
            job_id: Job identifier to retrieve

        Returns:
            Job data dictionary with all hash fields, or None if not found

        Raises:
            redis.RedisError: If Redis operation fails
        """
        key = f"job:{job_id}"
        job_data = self.redis.hgetall(key)

        if not job_data:
            logger.debug(f"Job {job_id} not found")
            return None

        # Redis returns bytes, decode to strings
        decoded_job = {k.decode() if isinstance(k, bytes) else k:
                       v.decode() if isinstance(v, bytes) else v
                       for k, v in job_data.items()}

        logger.debug(f"Retrieved job {job_id}, status={decoded_job.get('status')}")

        return decoded_job

    async def update_job_status(
        self,
        job_id: str,
        status: str,
        result: Optional[Any] = None,
        error: Optional[Any] = None
    ) -> None:
        """
        Update job status, result, and/or error message.

        Updates the status field and always updates updated_at timestamp.
        Optionally sets result (on completion) or error_message (on failure).

        Args:
            job_id: Job identifier to update
            status: New status (pending, running, completed, failed)
            result: Optional result data (will be JSON serialized if provided)
            error: Optional error details (will be JSON serialized if provided)

        Raises:
            redis.RedisError: If Redis operation fails
            ValueError: If job_id not found
        """
        key = f"job:{job_id}"

        # Check if job exists
        if not self.redis.exists(key):
            raise ValueError(f"Job {job_id} not found")

        updates = {
            "status": status,
            "updated_at": datetime.utcnow().isoformat()
        }

        if result is not None:
            updates["result"] = json.dumps(result)

        if error is not None:
            updates["error_message"] = json.dumps(error)

        self.redis.hset(key, mapping=updates)

        logger.info(f"Updated job {job_id} to status={status}")

    async def get_running_job_count(self) -> int:
        """
        Count jobs with status="running" across all jobs.

        Useful for graceful shutdown monitoring and concurrency control.
        Uses SCAN for efficient iteration without blocking Redis.

        Returns:
            Number of jobs currently in "running" status

        Raises:
            redis.RedisError: If Redis operation fails
        """
        running_count = 0

        # Scan for all job keys
        for key in self.redis.scan_iter("job:*"):
            # Get status field only
            status_bytes = self.redis.hget(key, "status")

            if status_bytes:
                status = status_bytes.decode() if isinstance(status_bytes, bytes) else status_bytes
                if status == "running":
                    running_count += 1

        logger.debug(f"Running job count: {running_count}")

        return running_count

    def __repr__(self) -> str:
        """Return string representation of JobStateManager."""
        return f"JobStateManager(redis_pool=..., ttl={self.ttl}s)"
