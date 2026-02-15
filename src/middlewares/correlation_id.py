import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add a correlation ID to each response for tracing purposes."""

    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        wide_event = getattr(request.state, "wide_event", None)
        if wide_event is not None:
            wide_event.correlation_id = correlation_id

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
