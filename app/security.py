import secrets
from typing import Annotated, Literal

from fastapi import Header, HTTPException, Request, status
from pydantic import BaseModel

Role = Literal["viewer", "operator", "admin"]


class Principal(BaseModel):
    id: str
    name: str
    role: Role
    source: str
    rate_limit_requests_per_minute: int | None = None


def _matches(provided: str | None, expected: str | None) -> bool:
    return bool(
        provided
        and expected
        and secrets.compare_digest(provided, expected)
    )


async def _authenticate(
    request: Request,
    api_key: str | None,
) -> Principal | None:
    settings = request.app.state.settings
    if _matches(api_key, settings.admin_api_key):
        return Principal(
            id="bootstrap-admin",
            name="bootstrap-admin",
            role="admin",
            source="admin_api_key",
        )

    if _matches(api_key, settings.gateway_api_key):
        return Principal(
            id="bootstrap-client",
            name="bootstrap-client",
            role="operator",
            source="gateway_api_key",
        )

    if api_key:
        record = await request.app.state.governance.authenticate_client(api_key)
        if record is not None:
            return Principal(
                id=record["id"],
                name=record["name"],
                role=record["role"],
                source="managed_client",
                rate_limit_requests_per_minute=record.get(
                    "rate_limit_requests_per_minute"
                ),
            )

    if not settings.gateway_api_key and not settings.admin_api_key and api_key is None:
        return Principal(
            id="anonymous",
            name="anonymous",
            role="admin",
            source="auth_disabled",
        )
    return None


async def require_api_key(
    request: Request,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> Principal:
    principal = await _authenticate(request, x_api_key)
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return principal


async def require_operator(
    principal: Annotated[Principal, require_api_key],
) -> Principal:
    if principal.role not in {"operator", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator role required",
        )
    return principal


async def require_admin(
    request: Request,
    x_admin_key: Annotated[str | None, Header(alias="X-Admin-Key")] = None,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> Principal:
    settings = request.app.state.settings
    if _matches(x_admin_key, settings.admin_api_key):
        return Principal(
            id="bootstrap-admin",
            name="bootstrap-admin",
            role="admin",
            source="admin_api_key",
        )

    principal = await _authenticate(request, x_api_key)
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin credential",
        )
    if principal.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return principal
