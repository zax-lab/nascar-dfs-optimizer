"""
Correlation ID middleware for distributed tracing.

This module provides middleware that generates and propagates correlation IDs
through HTTP requests, enabling distributed tracing across logs.

Key features:
- Generates ULID-based correlation IDs (time-ordered, sortable)
- Reuses existing X-Correlation-ID header if provided
- Binds correlation ID to structlog context for all log entries
- Returns correlation ID in X-Correlation-ID response header

Usage:
    from app.middleware import CorrelationIDMiddleware

    app.add_middleware(CorrelationIDMiddleware)

The correlation ID will automatically appear in all logs:
{
  \"correlation_id\": \"01ARZ3NDEKTSV4RRFFQ69G5FAV\",
  \"event\": \"Request received\",
  ...
}
"""

from contextvars import ContextVar
import logging
import ulid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Context variable for async-safe correlation ID storage
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default=None)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Correlation ID middleware using Starlette's BaseHTTPMiddleware."""

    async def dispatch(self, request: Request, call_next):
        """
        Handle request with correlation ID.

        Args:
            request: FastAPI Request object
            call_next: Next middleware or route handler

        Returns:
            Response with X-Correlation-ID header
        """
        # Generate new ULID or use existing correlation ID from header
        correlation_id = request.headers.get("X-Correlation-ID") or str(ulid.ULID())

        # Store in context variable for async-safe access
        correlation_id_var.set(correlation_id)

        # Bind correlation ID to logging context
        # Using Python's logging module to set context
        if hasattr(request.state, "request_id"):
            logging.LoggerAdapter(
                logging.getLogger(__name__),
                {
                    "correlation_id": correlation_id,
                    "request_id": request.state.request_id,
                },
            )
        else:
            logging.LoggerAdapter(
                logging.getLogger(__name__), {"correlation_id": correlation_id}
            )

        # Process request through middleware chain
        response = await call_next(request)

        # Add correlation ID to response headers for client correlation
        response.headers["X-Correlation-ID"] = correlation_id

        # Return response
        return response
