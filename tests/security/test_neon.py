"""Unit tests for Neon security helpers."""

from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest

from src.security import neon


def test_get_signing_key_success_and_errors(monkeypatch):
    """Test Neon signing-key selection and error branches."""
    monkeypatch.setattr(neon.jwt, "get_unverified_header", lambda _token: {"kid": "k1"})
    sentinel_key = object()
    monkeypatch.setattr(
        neon.Ed25519PublicKey,
        "from_public_bytes",
        lambda public_key_bytes: sentinel_key,
    )

    x_value = "AQIDBA"  # base64url; function applies padding
    assert (
        neon.get_signing_key("token", {"keys": [{"kid": "k1", "x": x_value}]})
        is sentinel_key
    )

    monkeypatch.setattr(neon.jwt, "get_unverified_header", lambda _token: {})
    with pytest.raises(Exception, match="missing 'kid'"):
        neon.get_signing_key("token", {"keys": []})

    monkeypatch.setattr(neon.jwt, "get_unverified_header", lambda _token: {"kid": "k1"})
    with pytest.raises(Exception, match="JWK missing 'kid'"):
        neon.get_signing_key("token", {"keys": [{}]})

    with pytest.raises(Exception, match="missing 'x'"):
        neon.get_signing_key("token", {"keys": [{"kid": "k1"}]})

    with pytest.raises(Exception, match="Matching JWK not found"):
        neon.get_signing_key("token", {"keys": [{"kid": "other", "x": x_value}]})


@pytest.mark.anyio
async def test_get_jwks_and_validate_token(monkeypatch):
    """Test JWKS retrieval and token validation error/success paths."""
    fake_response = MagicMock()
    fake_response.json.return_value = {"keys": ["ok"]}
    fake_client = MagicMock()
    fake_client.get = AsyncMock(return_value=fake_response)

    class FakeClientCM:
        async def __aenter__(self):
            return fake_client

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(neon, "AsyncClient", lambda: FakeClientCM())
    assert await neon.get_jwks() == {"keys": ["ok"]}
    fake_client.get.assert_awaited_once()
    fake_response.raise_for_status.assert_called_once()

    monkeypatch.setattr(neon, "get_jwks", AsyncMock(return_value={"keys": []}))
    monkeypatch.setattr(neon, "get_signing_key", lambda token, jwks: "signing-key")
    monkeypatch.setattr(neon.jwt, "decode", lambda *args, **kwargs: {"sub": "user-1"})
    assert await neon.validate_neon_token("token") == {"sub": "user-1"}

    monkeypatch.setattr(
        neon.jwt,
        "decode",
        lambda *args, **kwargs: (_ for _ in ()).throw(jwt.PyJWTError("bad token")),
    )
    with pytest.raises(Exception, match="Token validation error"):
        await neon.validate_neon_token("token")
