"""
Custom Exception
thrown if message id is invalid during history processing (e.g. summarization)

"""

from typing import Any, Optional
from .base_exceptions import AppException

class InvalidMessageIdException(AppException):
    """Exception raised when a message ID is invalid during history processing."""

    def __init__(
        self,
        message: str = "Invalid message or conversation ID",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=411,
            error="INVALID_MESSAGE_ID",
            message=message,
            details=details,
        )