from datetime import datetime, timezone
import json
import time
from typing import Any, Dict
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class WideEvent:
    """
    WideEvent captures detailed information about each request
    """

    def __init__(self, request: Request):
        self.context: Dict[str, Any] = {
            "method": request.method,
            "path": request.url.path,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.start_time = time.time()

    def add_context(self, **kwargs):
        """
        Add context to the event
        """
        self.context.update(kwargs)

    def emit(self, status_code: int, outcome: str, error: Exception | None = None):
        """
        Emit the event with final context
        """
        self.context.update(
            {
                "status_code": status_code,
                "outcome": outcome,
                "duration_ms": int((time.time() - self.start_time) * 1000),
            }
        )

        # TODO: Replace print with actual logging or event emission to a monitoring system
        if status_code >= 500:
            print(json.dumps(self.context, indent=2))
        else:
            print(json.dumps(self.context, indent=2))


class EventMiddleware(BaseHTTPMiddleware):
    """
    Middleware to capture detailed events for each request, including context and errors.
    """

    async def dispatch(self, request: Request, call_next):
        wide_event = WideEvent(request)
        request.state.wide_event = wide_event
        status_code = 500
        outcome = "error"
        error = None

        try:
            response = await call_next(request)
            status_code = response.status_code
            outcome = "success" if status_code < 400 else "client_error"
            return response
        except Exception as e:
            error = e
            outcome = "error"
            raise
        finally:
            if error is None:
                wide_event.emit(status_code, outcome, error)
