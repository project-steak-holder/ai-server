"""Unit tests for event dependency."""

import pytest

from src.dependencies.event import get_wide_event
from tests.helpers import make_request


def test_dependencies_event_success_and_missing():
    request = make_request()
    fake_event = object()
    request.state.wide_event = fake_event
    assert get_wide_event(request) is fake_event

    request2 = make_request()
    with pytest.raises(RuntimeError, match="WideEvent not found"):
        get_wide_event(request2)
