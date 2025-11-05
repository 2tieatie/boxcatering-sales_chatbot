"""HTTP request/response logging middleware."""

import time
import json
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log HTTP requests and responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Start timing
        start_time = time.time()

        # Extract request info
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        # Log request
        http_logger = logger.bind(log_type="http")
        http_logger.info(
            f"REQUEST: {request.method} {request.url.path} | "
            f"IP: {client_ip} | "
            f"User-Agent: {user_agent[:100]} | "
            f"Query: {dict(request.query_params)}"
        )

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)

            # Log response
            http_logger.info(
                f"RESPONSE: {response.status_code} | "
                f"Duration: {duration_ms}ms | "
                f"Content-Type: {response.headers.get('content-type', 'unknown')}"
            )

            return response

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            http_logger.error(f"ERROR: {str(e)} | " f"Duration: {duration_ms}ms")
            raise
