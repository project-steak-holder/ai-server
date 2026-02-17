"""
Custom Exception
thrown if required fields are missing
"""

from typing import Any, Optional
from .base_exceptions import AppException


class MissingRequiredFieldException(AppException):
    """Exception raised when required fields are missing."""

    def __init__(
        self,
        message: str = "Missing required field",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=400,
            error="MISSING_REQUIRED_FIELD",
            message=message,
            details=details,
        )
