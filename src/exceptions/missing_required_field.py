"""
Custom Exception
thrown if required fields are missing
"""

from .base_exceptions import AppException


class MissingRequiredFieldException(AppException):
    """Exception raised when required fields are missing."""

    def __init__(self, message: str = "Missing required field", details: dict = {}):
        super().__init__(
            status_code=400,
            error="MISSING_REQUIRED_FIELD",
            message=message,
            details=details,
        )
