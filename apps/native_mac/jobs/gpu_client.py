"""GPU Worker Client for HTTP communication with remote Windows GPU worker.

Provides HTTP client for submitting optimization jobs to a remote Windows
machine with CUDA GPU acceleration. Uses standard library urllib for
zero-dependency HTTP communication.
"""

import json
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class GPUWorkerError(Exception):
    """Exception raised for GPU worker communication errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class GPUWorkerClient:
    """Client for communicating with Windows GPU worker via HTTP.

    Provides methods for:
    - Testing connection to GPU worker
    - Submitting optimization jobs
    - Checking job status
    - Cancelling jobs

    Uses urllib.request from Python standard library to avoid external
    dependencies. Supports configurable timeout and API key authentication.

    Example:
        client = GPUWorkerClient('http://192.168.1.100:8000', api_key='secret')
        if client.test_connection():
            client.submit_job('job-123', config)
    """

    def __init__(
        self, base_url: str, api_key: Optional[str] = None, timeout: float = 30.0
    ):
        """Initialize GPU worker client.

        Args:
            base_url: Base URL of GPU worker (e.g., 'http://192.168.1.100:8000')
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds (default: 30.0)
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

        logger.info(f"GPUWorkerClient initialized for {base_url}")

    def _make_request(
        self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to GPU worker.

        Args:
            method: HTTP method ('GET', 'POST', etc.)
            endpoint: API endpoint (e.g., '/health', '/optimize')
            data: Optional JSON data to send in request body

        Returns:
            Dictionary with response data

        Raises:
            GPUWorkerError: If request fails
        """
        url = f"{self.base_url}{endpoint}"

        # Build request
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            if data is not None:
                body = json.dumps(data).encode("utf-8")
                req = urllib.request.Request(
                    url, data=body, headers=headers, method=method
                )
            else:
                req = urllib.request.Request(url, headers=headers, method=method)

            # Make request with timeout
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                response_body = response.read().decode("utf-8")

                if response_body:
                    return json.loads(response_body)
                return {"status": "success"}

        except urllib.error.HTTPError as e:
            error_msg = f"HTTP {e.code}: {e.reason}"
            try:
                error_body = e.read().decode("utf-8")
                error_data = json.loads(error_body)
                if "error" in error_data:
                    error_msg = f"{error_msg} - {error_data['error']}"
            except Exception:
                pass

            logger.error(f"GPU worker HTTP error: {error_msg}")
            raise GPUWorkerError(error_msg, status_code=e.code)

        except urllib.error.URLError as e:
            error_msg = f"Connection failed: {e.reason}"
            logger.error(f"GPU worker connection error: {error_msg}")
            raise GPUWorkerError(error_msg)

        except TimeoutError:
            error_msg = f"Request timeout after {self.timeout}s"
            logger.error(f"GPU worker timeout: {error_msg}")
            raise GPUWorkerError(error_msg)

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON response: {e}"
            logger.error(f"GPU worker response error: {error_msg}")
            raise GPUWorkerError(error_msg)

    def test_connection(self) -> bool:
        """Test connection to GPU worker.

        Returns:
            True if worker is reachable and healthy, False otherwise
        """
        try:
            # Try /health endpoint first
            try:
                response = self._make_request("GET", "/health")
                logger.info(f"GPU worker health check: {response}")
                return True
            except GPUWorkerError:
                # Fall back to /ping or root
                pass

            # Try /ping endpoint
            try:
                response = self._make_request("GET", "/ping")
                logger.info(f"GPU worker ping: {response}")
                return True
            except GPUWorkerError:
                pass

            # Try root endpoint
            try:
                response = self._make_request("GET", "/")
                logger.info(f"GPU worker root: {response}")
                return True
            except GPUWorkerError:
                pass

            return False

        except Exception as e:
            logger.warning(f"GPU worker connection test failed: {e}")
            return False

    def submit_job(self, job_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Submit optimization job to GPU worker.

        Args:
            job_id: Unique job identifier
            config: Optimization configuration dictionary

        Returns:
            Dictionary with response from worker containing:
            - status: 'accepted', 'completed', or 'failed'
            - job_id: The job ID
            - result: Optimization results (if completed synchronously)
            - message: Status message

        Raises:
            GPUWorkerError: If submission fails
        """
        payload = {
            "job_id": job_id,
            "config": config,
            "submitted_at": datetime.now().isoformat(),
        }

        logger.info(f"Submitting job {job_id} to GPU worker")

        try:
            response = self._make_request("POST", "/optimize", payload)
            logger.info(
                f"Job {job_id} submitted successfully: {response.get('status')}"
            )
            return response

        except GPUWorkerError as e:
            logger.error(f"Failed to submit job {job_id}: {e}")
            raise

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of a submitted job.

        Args:
            job_id: Job ID to query

        Returns:
            Dictionary with job status:
            - status: 'queued', 'running', 'completed', 'failed'
            - progress: Progress percentage (0-100)
            - result: Results if completed
            - error: Error message if failed

        Raises:
            GPUWorkerError: If status check fails
        """
        try:
            response = self._make_request("GET", f"/jobs/{job_id}/status")
            logger.debug(f"Job {job_id} status: {response.get('status')}")
            return response

        except GPUWorkerError as e:
            logger.error(f"Failed to get status for job {job_id}: {e}")
            raise

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running or queued job.

        Args:
            job_id: Job ID to cancel

        Returns:
            True if cancellation was successful, False otherwise
        """
        try:
            response = self._make_request("POST", f"/jobs/{job_id}/cancel")
            success = response.get("status") in ("cancelled", "cancelling")
            logger.info(f"Job {job_id} cancellation: {success}")
            return success

        except GPUWorkerError as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            return False

    def is_available(self) -> bool:
        """Check if GPU worker is available.

        Convenience method that wraps test_connection().

        Returns:
            True if worker is available, False otherwise
        """
        return self.test_connection()

    def get_worker_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the GPU worker.

        Returns:
            Dictionary with worker info (version, GPU info, etc.)
            or None if not available
        """
        try:
            return self._make_request("GET", "/info")
        except GPUWorkerError:
            return None
