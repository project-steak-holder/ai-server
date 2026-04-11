"""Unit tests for event middleware."""

from unittest.mock import MagicMock, patch

import pytest
from starlette.responses import Response

from src.middlewares.events import EventMiddleware, WideEvent
from tests.helpers import FakeWideEvent, make_request


def test_wide_event_add_context_and_emit_logs(monkeypatch):
    request = make_request(path="/items", method="POST")
    logged = []
    times = iter([100.0, 100.123, 100.456])

    monkeypatch.setattr("src.middlewares.events.time.time", lambda: next(times))

    mock_logger = MagicMock()
    mock_logger.info = lambda msg: logged.append(("info", msg))
    mock_logger.error = lambda msg: logged.append(("error", msg))

    with patch("logging.getLogger", return_value=mock_logger):
        event = WideEvent(request)
        event.add_context(extra="value")
        event.emit(200, "success")
        event.emit(500, "error")  # should be blocked by emitted guard

    assert event.context["method"] == "POST"
    assert event.context["path"] == "/items"
    assert event.context["extra"] == "value"
    assert event.context["status_code"] == 200
    assert event.context["outcome"] == "success"
    assert "duration_ms" in event.context
    assert len(logged) == 1
    assert logged[0][0] == "info"


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
