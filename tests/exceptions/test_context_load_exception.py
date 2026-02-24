"""Unit tests for ContextLoadException."""

from src.exceptions.context_load_exception import ContextLoadException


def test_context_load_exception_defaults():
    exc = ContextLoadException()

    assert exc.status_code == 501
    assert exc.error == "CONTEXT_LOAD_ERROR"
