"""Unit tests for MissingRequiredFieldException."""

from src.exceptions.missing_required_field import MissingRequiredFieldException


def test_missing_required_field_exception_defaults():
    exc = MissingRequiredFieldException()

    assert exc.status_code == 400
    assert exc.error == "MISSING_REQUIRED_FIELD"
