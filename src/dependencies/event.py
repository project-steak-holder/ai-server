from typing import Annotated

from fastapi import Depends, Request

from src.middlewares.events import WideEvent as MiddlewareWideEvent


def get_wide_event(request: Request) -> MiddlewareWideEvent:
    """FastAPI dependency to access the WideEvent from the request state."""
    if not hasattr(request.state, "wide_event"):
        raise RuntimeError(
            "WideEvent not found in request state. "
            "Ensure EventMiddleware is properly configured."
        )
    return request.state.wide_event


WideEvent = Annotated[MiddlewareWideEvent, Depends(get_wide_event)]
