from typing import Any, Optional
from src.exceptions.base_exceptions import AppException


class AuthenticationError(AppException):
    """Custom exception for authentication errors."""

    def __init__(
        self,
        message: str = "Authentication required",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=401,
            error="AUTHENTICATION_REQUIRED",
            message=message,
            details=details,
        )
