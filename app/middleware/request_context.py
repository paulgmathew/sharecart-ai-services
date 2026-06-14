from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import structlog


logger = structlog.get_logger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        request.state.started_at = time.perf_counter()

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            client_host=(request.client.host if request.client else None),
        )

        try:
            response: Response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - request.state.started_at) * 1000
            logger.exception(
                "request_unhandled_exception",
                method=request.method,
                path=request.url.path,
                processing_time_ms=round(elapsed_ms, 2),
            )
            raise

        elapsed_ms = (time.perf_counter() - request.state.started_at) * 1000
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            processing_time_ms=round(elapsed_ms, 2),
        )
        response.headers["X-Request-ID"] = request_id
        return response
