import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt import PyJWKSet
from jwt.algorithms import RSAAlgorithm

from app.config import Settings
from app.identity import OIDCAuthenticator


@pytest.mark.asyncio
async def test_oidc_authenticator_validates_signed_jwt_and_maps_role() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    jwk["kid"] = "test-key"

    settings = Settings(
        gateway_api_key="",
        admin_api_key="",
        oidc_issuer="https://issuer.example",
        oidc_audience="ai-gateway",
        oidc_jwks_url="https://issuer.example/.well-known/jwks.json",
        oidc_role_claim="roles",
        oidc_default_role="viewer",
    )
    authenticator = OIDCAuthenticator(settings)
    authenticator._jwks = PyJWKSet.from_dict({"keys": [jwk]})
    authenticator._jwks_loaded_at = time.monotonic()

    now = int(time.time())
    token = jwt.encode(
        {
            "sub": "user-123",
            "preferred_username": "platform-user",
            "roles": ["operator"],
            "iss": settings.oidc_issuer,
            "aud": settings.oidc_audience,
            "iat": now,
            "exp": now + 300,
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )

    claims = await authenticator.authenticate(token)
    assert claims["sub"] == "user-123"
    assert authenticator.role_from_claims(claims) == "operator"


@pytest.mark.asyncio
async def test_oidc_rejects_wrong_audience() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    jwk["kid"] = "test-key"

    settings = Settings(
        gateway_api_key="",
        admin_api_key="",
        oidc_issuer="https://issuer.example",
        oidc_audience="ai-gateway",
        oidc_jwks_url="https://issuer.example/jwks",
    )
    authenticator = OIDCAuthenticator(settings)
    authenticator._jwks = PyJWKSet.from_dict({"keys": [jwk]})
    authenticator._jwks_loaded_at = time.monotonic()

    now = int(time.time())
    token = jwt.encode(
        {
            "sub": "user-123",
            "iss": settings.oidc_issuer,
            "aud": "wrong-audience",
            "iat": now,
            "exp": now + 300,
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )

    with pytest.raises(jwt.InvalidAudienceError):
        await authenticator.authenticate(token)
