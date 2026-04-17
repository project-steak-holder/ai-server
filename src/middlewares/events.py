import functools
import inspect
import logging
import os
import subprocess
import time
from asyncio import CancelledError
from contextvars import ContextVar
from datetime import datetime, timezone
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Any, Dict, AsyncGenerator

_current_wide_event: ContextVar["WideEvent | None"] = ContextVar(
    "wide_event", default=None
)


def add_event_context(**kwargs) -> None:
    event = _current_wide_event.get()
    if event is not None:
        event.add_context(**kwargs)


def set_wide_event(event: "WideEvent") -> None:
    _current_wide_event.set(event)


def _load_env_context() -> dict:
    commit_hash = os.environ.get("COMMIT_HASH")
    if not commit_hash:
        try:
            commit_hash = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"], text=True
            ).strip()
        except Exception:
            commit_hash = "unknown"
    return {
        "service": "ai-server",
        "service_version": os.environ.get("SERVICE_VERSION", "unknown"),
        "environment": os.environ.get("ENVIRONMENT", "development"),
        "commit_hash": commit_hash,
    }


_env_context = _load_env_context()


class WideEvent:
    """
    WideEvent captures detailed information about each request
    """

    def __init__(self, request: Request):
        self.deferred = False
        self.emitted = False
        self.correlation_id: str | None = None
        self.context: Dict[str, Any] = {
            **_env_context,
            "method": request.method,
            "path": request.url.path,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.start_time = time.time()

    def mark_deferred(self):
        self.deferred = True

    def add_context(self, **kwargs):
        """
        Add context to the event
        """
        self.context.update(kwargs)

    def emit(self, status_code: int, outcome: str, error: Exception | None = None):
        """
        Emit the event with final context
        """
        if self.emitted:
            return

        self.context.update(
            {
                "status_code": status_code,
                "outcome": outcome,
                "duration_ms": int((time.time() - self.start_time) * 1000),
            }
        )

        logger = logging.getLogger("wide_event")
        if status_code >= 500:
            logger.error(self.context)
        else:
            logger.info(self.context)

        self.emitted = True


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
            if error is None and not wide_event.deferred and not wide_event.emitted:
                wide_event.emit(status_code, outcome, error)


async def tracked_stream(
    generator: AsyncGenerator, wide_event: WideEvent
) -> AsyncGenerator:
    wide_event.mark_deferred()
    start = time.time()
    first_chunk_time = None
    chunk_count = 0
    outcome = "success"
    error = None

    try:
        async for chunk in generator:
            if first_chunk_time is None:
                first_chunk_time = time.time()
                wide_event.add_context(
                    first_chunk_latency_ms=int((first_chunk_time - start) * 1000)
                )
            chunk_count += 1
            yield chunk
    except (GeneratorExit, CancelledError):
        outcome = "client_disconnect"
    except Exception as e:
        outcome = "error"
        error = e
        raise
    finally:
        now = time.time()
        wide_event.add_context(
            stream_duration_ms=int((now - start) * 1000),
            chunk_count=chunk_count,
            stream_outcome=outcome,
        )
        status = {"success": 200, "client_disconnect": 499}.get(outcome, 500)
        wide_event.emit(status, outcome, error)


def wide_event(name: str):

    def decorator(func):
        @functools.wraps(func)
        async def asyncgen_wrapper(*args, **kwargs) -> AsyncGenerator:
            start = time.time()
            try:
                async for item in func(*args, **kwargs):
                    yield item
                _record_trace(name, start, "success")
            except GeneratorExit:
                _record_trace(name, start, "cancelled")
            except Exception:
                _record_trace(name, start, "error")
                raise

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

        if inspect.isasyncgenfunction(func):
            return asyncgen_wrapper
        elif inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

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
