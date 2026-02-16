import base64
import os
from urllib.parse import urlparse
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from httpx import AsyncClient

import jwt
from jwt import PyJWTError

from src.exceptions.authentication_error import AuthenticationError

NEON_AUTH_BASE_URL = os.environ.get("AUTH_URL", "")
NEON_JWKS_URL = f"{NEON_AUTH_BASE_URL}/.well-known/jwks.json"
parsed = urlparse(NEON_AUTH_BASE_URL)
ORIGIN = f"{parsed.scheme}://{parsed.netloc}"


async def get_jwks():
    """Fetch JWKS from Neon Auth service."""
    async with AsyncClient() as client:
        response = await client.get(NEON_JWKS_URL)
        response.raise_for_status()
        return response.json()


def get_signing_key(token, jwks):
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header["kid"]
    for jwk in jwks["keys"]:
        if jwk["kid"] == kid:
            x = jwk["x"]
            public_key_bytes = base64.urlsafe_b64decode(x + "==")
            return Ed25519PublicKey.from_public_bytes(public_key_bytes)
    raise ValueError("Matching JWK not found")


async def validate_neon_token(token: str):
    try:
        jwks = await get_jwks()
        signing_key = get_signing_key(token, jwks)
        payload = jwt.decode(
            token, key=signing_key, algorithms=["EdDSA"], issuer=ORIGIN, audience=ORIGIN
        )
        return payload
    except PyJWTError as error:
        raise AuthenticationError(
            message="Token validation error",
            details={"error": str(error)},
        )
    except Exception as error:
        raise AuthenticationError(
            message="Unexpected error during token validation",
            details={"error": str(error)},
        )
