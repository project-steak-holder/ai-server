"""Unit tests for correlation ID middleware."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from starlette.responses import Response

from src.middlewares.correlation_id import CorrelationIDMiddleware
from tests.helpers import make_request


@pytest.mark.anyio
async def test_correlation_id_middleware_uses_header_and_default(monkeypatch):
    middleware = CorrelationIDMiddleware(app=MagicMock())

    request_with_header = make_request(headers={"X-Correlation-ID": "abc-123"})
    request_with_header.state.wide_event = SimpleNamespace(correlation_id=None)

    async def call_next_header(_req):
        return Response(status_code=200)

    response = await middleware.dispatch(request_with_header, call_next_header)
    assert response.headers["X-Correlation-ID"] == "abc-123"
    assert request_with_header.state.wide_event.correlation_id == "abc-123"

    request_without_header = make_request()
    request_without_header.state.wide_event = SimpleNamespace(correlation_id=None)
    monkeypatch.setattr(
        "src.middlewares.correlation_id.uuid.uuid4", lambda: "generated"
    )

    async def call_next_default(_req):
        return Response(status_code=200)

    response2 = await middleware.dispatch(request_without_header, call_next_default)
    assert response2.headers["X-Correlation-ID"] == "generated"
    assert request_without_header.state.wide_event.correlation_id == "generated"
