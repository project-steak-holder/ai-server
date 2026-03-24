from contextvars import ContextVar
from datetime import datetime, timezone
import functools
import inspect
import json
import time
from typing import Any, Dict
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

_current_wide_event: ContextVar["WideEvent | None"] = ContextVar(
    "wide_event", default=None
)


def set_wide_event(event: "WideEvent") -> None:
    _current_wide_event.set(event)


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
        set_wide_event(wide_event)
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


def wide_event(name: str):

    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                _record_trace(name, start, "success")
                return result
            except Exception:
                _record_trace(name, start, "error")
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                _record_trace(name, start, "success")
                return result
            except Exception:
                _record_trace(name, start, "error")
                raise

        return async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper

    return decorator


def _record_trace(name: str, start: float, status: str) -> None:
    event = _current_wide_event.get()
    if event is not None:
        event.add_context(
            **{
                f"{name}_duration_ms": int((time.time() - start) * 1000),
                f"{name}_status": status,
            }
        )
