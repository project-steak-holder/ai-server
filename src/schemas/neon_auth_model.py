"""
Pydantic models for Neon Auth token validation.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class NeonAuthTokenPayload(BaseModel):
    """Validates the JWT payload from Neon Auth."""

    # JWT standard claims
    iat: int = Field(..., description="Issued at timestamp")
    exp: int = Field(..., description="Expiration timestamp")
    iss: str = Field(..., description="Issuer")
    aud: str = Field(..., description="Audience")
    sub: str = Field(..., description="Subject (user ID)")

    # Neon Auth user fields
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    email_verified: bool = Field(
        ..., alias="emailVerified", description="Email verification status"
    )
    name: Optional[str] = Field(None, description="User's full name")
    role: str = Field(..., description="User role (e.g., 'authenticated')")
    banned: bool = Field(False, description="Whether user is banned")
    ban_reason: Optional[str] = Field(None, alias="banReason")
    ban_expires: Optional[str] = Field(None, alias="banExpires")
    created_at: str = Field(..., alias="createdAt", description="Account creation date")
    updated_at: str = Field(..., alias="updatedAt", description="Last update date")

    model_config = {"populate_by_name": True}

    @field_validator("exp")
    @classmethod
    def validate_not_expired(cls, exp: int) -> int:
        """Validate token has not expired."""
        import time

        current_time = int(time.time())
        if current_time >= exp:
            from src.exceptions.authentication_error import AuthenticationError

            raise AuthenticationError("Token has expired")
        return exp

    @field_validator("banned")
    @classmethod
    def validate_not_banned(cls, banned: bool) -> bool:
        """Validate user is not banned."""
        if banned:
            from src.exceptions.authentication_error import AuthenticationError

            raise AuthenticationError("User account is banned")
        return banned

    @property
    def user_id(self) -> str:
        """Get the user ID (same as 'id' and 'sub')."""
        return self.id
