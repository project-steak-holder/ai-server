"""
Custom Exception
thrown if persona, project details, or conversation history
fail to load into agent context
"""

from .base_exceptions import AppException


class ContextLoadException(AppException):
    """Exception raised when loading persona, project or message history context fails."""

    def __init__(self, message: str = "Failure loading context", details: dict = {}):
        super().__init__(
            status_code=501,
            error="CONTEXT_LOAD_ERROR",
            message=message,
            details=details,
        )
