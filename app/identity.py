import time
from typing import Any

import httpx
import jwt
from jwt import PyJWKSet

from app.config import Settings


class OIDCAuthenticator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._jwks: PyJWKSet | None = None
        self._jwks_loaded_at = 0.0

    @property
    def enabled(self) -> bool:
        return bool(
            self.settings.oidc_issuer
            and self.settings.oidc_audience
            and self.settings.oidc_jwks_url
        )

    async def _load_jwks(self) -> PyJWKSet:
        now = time.monotonic()
        if (
            self._jwks is not None
            and now - self._jwks_loaded_at < self.settings.oidc_jwks_cache_seconds
        ):
            return self._jwks

        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
            response = await client.get(str(self.settings.oidc_jwks_url))
            response.raise_for_status()
            self._jwks = PyJWKSet.from_dict(response.json())
            self._jwks_loaded_at = now
            return self._jwks

    async def authenticate(self, token: str) -> dict[str, Any]:
        if not self.enabled:
            raise ValueError("OIDC authentication is not configured")

        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if not kid:
            raise ValueError("JWT kid header is required")

        jwks = await self._load_jwks()
        key = next((item.key for item in jwks.keys if item.key_id == kid), None)
        if key is None:
            self._jwks = None
            jwks = await self._load_jwks()
            key = next((item.key for item in jwks.keys if item.key_id == kid), None)
        if key is None:
            raise ValueError("JWT signing key was not found")

        claims = jwt.decode(
            token,
            key=key,
            algorithms=self.settings.oidc_algorithms,
            audience=self.settings.oidc_audience,
            issuer=self.settings.oidc_issuer,
            options={"require": ["exp", "iat", "sub"]},
        )
        return dict(claims)

    def role_from_claims(self, claims: dict[str, Any]) -> str:
        raw = claims.get(self.settings.oidc_role_claim, self.settings.oidc_default_role)
        roles = raw if isinstance(raw, list) else [raw]
        allowed = {"viewer", "operator", "admin"}
        normalized = {str(role).lower() for role in roles}
        for role in ("admin", "operator", "viewer"):
            if role in normalized and role in allowed:
                return role
        return self.settings.oidc_default_role
