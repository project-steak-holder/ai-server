"""
Unit tests for user authentication dependency.
"""

import time
import pytest
from unittest.mock import patch

from src.dependencies.user import get_current_user, AuthenticatedUser
from src.exceptions.authentication_error import AuthenticationError


@pytest.mark.anyio
async def test_get_current_user_success():
    """Test successful authentication with valid token."""
    mock_user_data = {
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

    # Mock validate_neon_token to return our test data
    with patch("src.dependencies.user.validate_neon_token") as mock_validate:
        mock_validate.return_value = mock_user_data

        # Call get_current_user with a Bearer token
        result = await get_current_user(authorization="Bearer test-token-123")

        # Assertions
        assert isinstance(result, AuthenticatedUser)
        assert result.user_id == "user-123"

        # Verify validate_neon_token was called with correct token
        mock_validate.assert_called_once_with("test-token-123")


@pytest.mark.anyio
async def test_get_current_user_no_header():
    """Test that missing Authorization header is rejected."""
    with pytest.raises(AuthenticationError) as exc_info:
        await get_current_user(authorization=None)

    assert "No authorization token" in str(exc_info.value)


@pytest.mark.anyio
async def test_get_current_user_invalid_header_format():
    """Test that malformed Authorization headers are rejected."""
    with pytest.raises(AuthenticationError) as exc_info:
        await get_current_user(authorization="just-a-token")

    assert "No authorization token" in str(exc_info.value)


@pytest.mark.anyio
async def test_get_current_user_expired_token():
    """Test that expired tokens are rejected."""

    expired_data = {
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

    with patch("src.dependencies.user.validate_neon_token") as mock_validate:
        mock_validate.return_value = expired_data

        with pytest.raises(AuthenticationError) as exc_info:
            await get_current_user(authorization="Bearer expired-token")

        assert "expired" in str(exc_info.value).lower()


@pytest.mark.anyio
async def test_get_current_user_banned_user():
    """Test that banned users are rejected."""

    banned_data = {
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
        "banReason": "Violation",
        "banExpires": None,
        "createdAt": "2024-01-01T00:00:00.000Z",
        "updatedAt": "2024-01-01T00:00:00.000Z",
    }

    with patch("src.dependencies.user.validate_neon_token") as mock_validate:
        mock_validate.return_value = banned_data

        with pytest.raises(AuthenticationError) as exc_info:
            await get_current_user(authorization="Bearer banned-token")

        assert "banned" in str(exc_info.value).lower()


@pytest.mark.anyio
async def test_get_current_user_invalid_token_payload():
    """Test that invalid token payloads are rejected."""

    invalid_data = {
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
        "iss": "https://example.neonauth.com",
        "aud": "https://example.neonauth.com",
        "sub": "user-123",
        # Missing "id" field
        "email": "user@example.com",
        "emailVerified": True,
        "name": "Test User",
        "role": "authenticated",
        "banned": False,
        "createdAt": "2024-01-01T00:00:00.000Z",
        "updatedAt": "2024-01-01T00:00:00.000Z",
    }

    with patch("src.dependencies.user.validate_neon_token") as mock_validate:
        mock_validate.return_value = invalid_data

        with pytest.raises(AuthenticationError) as exc_info:
            await get_current_user(authorization="Bearer invalid-token")

        assert "Invalid token payload" in str(exc_info.value)


@pytest.mark.anyio
async def test_get_current_user_uses_id_field():
    """Test that user_id is extracted from 'id' field."""

    user_data = {
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
        "iss": "https://example.neonauth.com",
        "aud": "https://example.neonauth.com",
        "sub": "abc-123",
        "id": "abc-123",
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

    with patch("src.dependencies.user.validate_neon_token") as mock_validate:
        mock_validate.return_value = user_data

        result = await get_current_user(authorization="Bearer token")

        # user_id should match the 'id' field
        assert result.user_id == "abc-123"


@pytest.mark.anyio
async def test_get_current_user_token_extraction():
    """Test that Bearer token is correctly extracted."""

    user_data = {
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

    with patch("src.dependencies.user.validate_neon_token") as mock_validate:
        mock_validate.return_value = user_data

        await get_current_user(authorization="Bearer my-secret-token-xyz")

        # Verify we extracted just the token part (after "Bearer ")
        mock_validate.assert_called_once_with("my-secret-token-xyz")
