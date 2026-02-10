from typing import Any, Optional
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standard Error Response Model"""

    error: str
    message: str
    details: Optional[dict[str, Any]] = None


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        status_code: int = 500,
        error: str = "INTERNAL_ERROR",
        message: str = "An unexpected error occurred",
        details: Optional[dict[str, Any]] = None,
    ):
        self.status_code = status_code
        self.error = error
        self.message = message
        self.details = details
        super().__init__(message)
