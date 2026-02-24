"""Unit tests for global error handler middleware utilities."""

import json

import pytest
from fastapi import HTTPException

from src.middlewares.error_handler import _categorize_error, global_exception_handler
from tests.helpers import FakeWideEvent, make_request


@pytest.mark.parametrize(
    ("status_code", "category"),
    [
        (400, "validation_error"),
        (401, "auth_error"),
        (403, "permission_error"),
        (404, "not_found"),
        (429, "rate_limit_error"),
        (418, "client_error"),
        (500, "server_error"),
    ],
)
def test_error_handler_categorize_error(status_code, category):
    assert _categorize_error(status_code) == category


@pytest.mark.anyio
async def test_global_exception_handler_app_exception_with_wide_event():
    from src.exceptions.authentication_error import AuthenticationError

    request = make_request(
        path="/api/v1/generate",
        headers={
            "content-type": "application/json",
            "user-agent": "pytest",
            "referer": "http://example.test",
        },
        query_string=b"a=1",
        path_params={"id": "123"},
    )
    wide_event = FakeWideEvent()
    wide_event.correlation_id = "corr-1"
    request.state.wide_event = wide_event
    request.state.user_id = "user-1"
    request.state.conversation_id = "conv-1"

    exc = AuthenticationError("bad token", details={"reason": "expired"})
    response = await global_exception_handler(request, exc)

    assert response.status_code == 401
    assert response.headers["X-Correlation-ID"] == "corr-1"
    payload = json.loads(response.body)
    assert payload["error"] == "AUTHENTICATION_REQUIRED"
    assert wide_event.added
    assert wide_event.emitted


@pytest.mark.anyio
async def test_global_exception_handler_http_exception_and_fallback_print(monkeypatch):
    request = make_request()
    request.state.wide_event = FakeWideEvent()

    response = await global_exception_handler(
        request, HTTPException(status_code=404, detail="nope")
    )
    assert response.status_code == 404
    payload = json.loads(response.body)
    assert payload["error"] == "HTTP_ERROR"

    request2 = make_request()
    printed = []
    monkeypatch.setattr("builtins.print", lambda msg: printed.append(msg))

    response2 = await global_exception_handler(request2, RuntimeError("boom"))
    assert response2.status_code == 500
    assert printed and "no wide_event" in printed[0]


@pytest.mark.anyio
async def test_global_exception_handler_generic_exception_with_wide_event():
    request = make_request()
    wide_event = FakeWideEvent()
    request.state.wide_event = wide_event

    response = await global_exception_handler(request, RuntimeError("boom"))

    assert response.status_code == 500
    error_context = wide_event.added[0]["error"]
    assert error_context["exception_type"] == "RuntimeError"
