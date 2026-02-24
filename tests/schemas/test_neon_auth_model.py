"""
Unit tests for Neon Auth validation.
"""

import time
import pytest
from pydantic import ValidationError

from src.schemas.neon_auth_model import NeonAuthTokenPayload
from src.exceptions.authentication_error import AuthenticationError


def test_valid_neon_token_payload():
    """Test that a valid Neon Auth token payload is accepted."""

    valid_payload = {
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
        "iss": "https://example.neonauth.com",
        "aud": "https://example.neonauth.com",
        "sub": "user-123",
        "id": "user-123",
        "email": "user@example.com",
        "emailVerified": True,
        "name": "Test User",
        "role": "authenticated",
        "banned": False,
        "banReason": None,
        "banExpires": None,
        "createdAt": "2024-01-01T00:00:00.000Z",
        "updatedAt": "2024-01-01T00:00:00.000Z",
    }

    token = NeonAuthTokenPayload(**valid_payload)

    assert token.user_id == "user-123"
    assert token.email == "user@example.com"
    assert token.email_verified is True
    assert token.banned is False


def test_expired_token_is_rejected():
    """Test that expired tokens are rejected."""

    expired_payload = {
        "iat": int(time.time()) - 7200,
        "exp": int(time.time()) - 3600,
        "iss": "https://example.neonauth.com",
        "aud": "https://example.neonauth.com",
        "sub": "user-123",
        "id": "user-123",
        "email": "user@example.com",
        "emailVerified": True,
        "name": "Test User",
        "role": "authenticated",
        "banned": False,
        "banReason": None,
        "banExpires": None,
        "createdAt": "2024-01-01T00:00:00.000Z",
        "updatedAt": "2024-01-01T00:00:00.000Z",
    }

    with pytest.raises(AuthenticationError) as exc_info:
        NeonAuthTokenPayload(**expired_payload)

    assert "expired" in str(exc_info.value).lower()


def test_banned_user_is_rejected():
    """Test that banned users are rejected."""

    banned_payload = {
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
        "iss": "https://example.neonauth.com",
        "aud": "https://example.neonauth.com",
        "sub": "user-123",
        "id": "user-123",
        "email": "banned@example.com",
        "emailVerified": True,
        "name": "Banned User",
        "role": "authenticated",
        "banned": True,
        "banReason": "Violation of terms",
        "banExpires": None,
        "createdAt": "2024-01-01T00:00:00.000Z",
        "updatedAt": "2024-01-01T00:00:00.000Z",
    }

    with pytest.raises(AuthenticationError) as exc_info:
        NeonAuthTokenPayload(**banned_payload)

    assert "banned" in str(exc_info.value).lower()


def test_missing_required_field():
    """Test that missing required fields are rejected."""

    invalid_payload = {
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
        "iss": "https://example.neonauth.com",
        "aud": "https://example.neonauth.com",
        "sub": "user-123",
        "email": "user@example.com",
        "emailVerified": True,
        "name": "Test User",
        "role": "authenticated",
        "banned": False,
        "createdAt": "2024-01-01T00:00:00.000Z",
        "updatedAt": "2024-01-01T00:00:00.000Z",
    }

    with pytest.raises(ValidationError) as exc_info:
        NeonAuthTokenPayload(**invalid_payload)

    # Check that 'id' field is mentioned in the error
    errors = exc_info.value.errors()
    assert any(error["loc"][0] == "id" for error in errors)


def test_camelcase_fields_are_converted():
    """Test that camelCase fields from Neon are converted to snake_case."""

    payload = {
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
        "iss": "https://example.neonauth.com",
        "aud": "https://example.neonauth.com",
        "sub": "user-123",
        "id": "user-123",
        "email": "user@example.com",
        "emailVerified": True,
        "name": "Test User",
        "role": "authenticated",
        "banned": False,
        "banReason": None,
        "banExpires": None,
        "createdAt": "2024-01-01T00:00:00.000Z",
        "updatedAt": "2024-01-01T00:00:00.000Z",
    }

    token = NeonAuthTokenPayload(**payload)

    assert token.email_verified is True
    assert token.ban_reason is None
    assert token.ban_expires is None
    assert token.created_at == "2024-01-01T00:00:00.000Z"
    assert token.updated_at == "2024-01-01T00:00:00.000Z"


def test_user_id_property():
    """Test that the user_id property returns the correct value."""

    payload = {
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
        "iss": "https://example.neonauth.com",
        "aud": "https://example.neonauth.com",
        "sub": "user-123",
        "id": "user-123",
        "email": "user@example.com",
        "emailVerified": True,
        "name": "Test User",
        "role": "authenticated",
        "banned": False,
        "banReason": None,
        "banExpires": None,
        "createdAt": "2024-01-01T00:00:00.000Z",
        "updatedAt": "2024-01-01T00:00:00.000Z",
    }

    token = NeonAuthTokenPayload(**payload)

    # user_id property should match id field
    assert token.user_id == token.id
    assert token.user_id == "user-123"


def test_unverified_email_is_allowed():
    """Test that unverified emails are allowed."""

    payload = {
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
        "iss": "https://example.neonauth.com",
        "aud": "https://example.neonauth.com",
        "sub": "user-123",
        "id": "user-123",
        "email": "unverified@example.com",
        "emailVerified": False,  # Not verified, but that's OK
        "name": "Unverified User",
        "role": "authenticated",
        "banned": False,
        "banReason": None,
        "banExpires": None,
        "createdAt": "2024-01-01T00:00:00.000Z",
        "updatedAt": "2024-01-01T00:00:00.000Z",
    }

    token = NeonAuthTokenPayload(**payload)
    assert token.email_verified is False


def test_optional_fields_can_be_none():
    """Test that optional fields can be None."""

    payload = {
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
        "iss": "https://example.neonauth.com",
        "aud": "https://example.neonauth.com",
        "sub": "user-123",
        "id": "user-123",
        "email": "user@example.com",
        "emailVerified": True,
        "name": None,  # Optional
        "role": "authenticated",
        "banned": False,
        "banReason": None,  # Optional
        "banExpires": None,  # Optional
        "createdAt": "2024-01-01T00:00:00.000Z",
        "updatedAt": "2024-01-01T00:00:00.000Z",
    }

    token = NeonAuthTokenPayload(**payload)

    assert token.name is None
    assert token.ban_reason is None
    assert token.ban_expires is None
