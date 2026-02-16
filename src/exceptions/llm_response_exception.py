"""
Custom Exception
thrown if required fields are missing
"""

from .base_exceptions import AppException


class LlmResponseException(AppException):
    """Exception raised when llm response is invalid or missing required fields."""

    def __init__(
        self,
        message: str = "LLM response is invalid or missing required fields",
        details: dict = {},
    ):
        super().__init__(
            status_code=500,
            error="LLM_RESPONSE_ERROR",
            message=message,
            details=details,
        )
