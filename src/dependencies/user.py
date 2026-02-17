"""
FastAPI dependencies for authentication
"""

from dataclasses import dataclass
from typing import Annotated
from fastapi import Depends, Header
from pydantic import ValidationError

from src.exceptions.authentication_error import AuthenticationError
from src.security.neon import validate_neon_token
from src.schemas.neon_auth_model import NeonAuthTokenPayload


@dataclass
class AuthenticatedUser:
    """Represents an authenticated user in the system."""

    user_id: str


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> AuthenticatedUser:
    """FastAPI dependency to validate authorization token and retrieve authenticated user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("No authorization token provided")

    token = authorization.split(" ")[1]

    user_data = await validate_neon_token(token)

    try:
        token_payload = NeonAuthTokenPayload(**user_data)
    except ValidationError as e:
        raise AuthenticationError(f"Invalid token payload: {e.errors()[0]['msg']}")

    return AuthenticatedUser(user_id=token_payload.user_id)


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
