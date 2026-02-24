"""Unit tests for event middleware."""

from unittest.mock import MagicMock

import pytest
from starlette.responses import Response

from src.middlewares.events import EventMiddleware, WideEvent
from tests.helpers import FakeWideEvent, make_request


def test_wide_event_add_context_and_emit_prints(monkeypatch):
    request = make_request(path="/items", method="POST")
    outputs = []
    times = iter([100.0, 100.123, 100.456])

    monkeypatch.setattr("src.middlewares.events.time.time", lambda: next(times))
    monkeypatch.setattr("builtins.print", lambda payload: outputs.append(payload))

    event = WideEvent(request)
    event.add_context(extra="value")
    event.emit(200, "success")
    event.emit(500, "error")

    assert event.context["method"] == "POST"
    assert event.context["path"] == "/items"
    assert event.context["extra"] == "value"
    assert event.context["status_code"] == 500
    assert event.context["outcome"] == "error"
    assert "duration_ms" in event.context
    assert len(outputs) == 2


@pytest.mark.anyio
async def test_event_middleware_dispatch_success(monkeypatch):
    created = []

    class TrackingWideEvent(FakeWideEvent):
        def __init__(self, request):
            super().__init__(request)
            created.append(self)

    monkeypatch.setattr("src.middlewares.events.WideEvent", TrackingWideEvent)
    middleware = EventMiddleware(app=MagicMock())
    request = make_request(path="/ok")

    async def call_next(req):
        assert hasattr(req.state, "wide_event")
        return Response(status_code=201)

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 201
    assert len(created) == 1
    assert created[0].emitted == [(201, "success", None)]


@pytest.mark.anyio
async def test_event_middleware_dispatch_exception(monkeypatch):
    created = []

    class TrackingWideEvent(FakeWideEvent):
        def __init__(self, request):
            super().__init__(request)
            created.append(self)

    monkeypatch.setattr("src.middlewares.events.WideEvent", TrackingWideEvent)
    middleware = EventMiddleware(app=MagicMock())
    request = make_request(path="/boom")

    async def call_next(_req):
        raise ValueError("failure")

    with pytest.raises(ValueError, match="failure"):
        await middleware.dispatch(request, call_next)

    assert len(created) == 1
    assert created[0].emitted == []
