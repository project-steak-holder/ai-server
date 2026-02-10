import json
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from src.exceptions.base_exceptions import AppException, ErrorResponse


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler adds error context to wide event and response.
    """
    status_code = 500
    error_code = "INTERNAL_ERROR"
    error_message = "An unexpected error occurred"
    error_category = "server_error"
    error_details = None

    if isinstance(exc, AppException):
        status_code = exc.status_code
        error_code = exc.error
        error_message = exc.message
        error_details = exc.details
        error_category = _categorize_error(status_code)

    elif isinstance(exc, HTTPException):
        status_code = exc.status_code
        error_code = "HTTP_ERROR"
        error_message = str(exc.detail)
        error_category = _categorize_error(status_code)

    response = JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            error=error_code,
            message=error_message,
            details=error_details,
        ).model_dump(exclude_none=True),
    )

    wide_event = getattr(request.state, "wide_event", None)
    correlation_id = (
        getattr(wide_event, "correlation_id", None) or request.state.correlation_id
    )
    response.headers["X-Correlation-ID"] = correlation_id

    if wide_event:
        error_context = {
            "error_code": error_code,
            "error_category": error_category,
            "error_message": error_message,
        }

        if status_code >= 500:
            error_context["exception_type"] = type(exc).__name__

        if error_details:
            error_context["error_details"] = json.dumps(error_details)

        request_context = {
            "query_params": dict(request.query_params)
            if request.query_params
            else None,
            "path_params": request.path_params if request.path_params else None,
            "content_type": request.headers.get("content-type"),
            "user_agent": request.headers.get("user-agent"),
            "referer": request.headers.get("referer"),
        }

        if hasattr(request.state, "user_id"):
            request_context["user_id"] = request.state.user_id
        if hasattr(request.state, "conversation_id"):
            request_context["conversation_id"] = request.state.conversation_id

        wide_event.add_context(
            error=error_context,
            request_metadata=request_context,
        )
        wide_event.emit(status_code, "error", response)
    else:
        # TODO: Fallback log the error if wide_event is not available. This should never happen.
        print(
            f"Error occurred but no wide_event available: {error_code} - {error_message}"
        )

    return response


def _categorize_error(status_code: int) -> str:
    """Categorize errors for better analytics."""
    if status_code == 400:
        return "validation_error"
    elif status_code == 401:
        return "auth_error"
    elif status_code == 403:
        return "permission_error"
    elif status_code == 404:
        return "not_found"
    elif status_code == 429:
        return "rate_limit_error"
    elif 400 <= status_code < 500:
        return "client_error"
    else:
        return "server_error"
