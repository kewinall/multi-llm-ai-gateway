from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.security import Principal, require_admin

router = APIRouter(prefix="/admin", tags=["admin"])


class AliasUpdate(BaseModel):
    target: str


class PoolUpdate(BaseModel):
    models: list[str] = Field(min_length=1)


class PriceUpdate(BaseModel):
    input_per_million: float = Field(ge=0)
    output_per_million: float = Field(ge=0)


class RoutingPolicyUpdate(BaseModel):
    routing_policy: Literal["priority", "round_robin", "random", "cost"]


class ClientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    role: Literal["viewer", "operator", "admin"] = "operator"
    rate_limit_requests_per_minute: int | None = Field(default=None, ge=1)


class ClientUpdate(BaseModel):
    role: Literal["viewer", "operator", "admin"] | None = None
    enabled: bool | None = None
    rate_limit_requests_per_minute: int | None = Field(default=None, ge=1)
    clear_rate_limit_override: bool = False


def _store(request: Request):
    return request.app.state.governance


@router.get("/api/summary")
async def summary(
    request: Request,
    principal: Annotated[Principal, Depends(require_admin)],
) -> dict[str, object]:
    store = _store(request)
    return {
        "version": request.app.version,
        "actor": principal.model_dump(),
        "governance": await store.snapshot(),
        "clients": await store.list_clients(),
        "audit": await store.audit_events(50),
    }


@router.put("/api/aliases/{name}")
async def set_alias(
    name: str,
    body: AliasUpdate,
    request: Request,
    principal: Annotated[Principal, Depends(require_admin)],
) -> dict[str, str]:
    try:
        await _store(request).set_alias(name, body.target, principal.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"name": name, "target": body.target}


@router.delete("/api/aliases/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alias(
    name: str,
    request: Request,
    principal: Annotated[Principal, Depends(require_admin)],
) -> None:
    await _store(request).delete_alias(name, principal.id)


@router.put("/api/pools/{name}")
async def set_pool(
    name: str,
    body: PoolUpdate,
    request: Request,
    principal: Annotated[Principal, Depends(require_admin)],
) -> dict[str, object]:
    try:
        await _store(request).set_pool(name, body.models, principal.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"name": name, "models": body.models}


@router.delete("/api/pools/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pool(
    name: str,
    request: Request,
    principal: Annotated[Principal, Depends(require_admin)],
) -> None:
    await _store(request).delete_pool(name, principal.id)


@router.put("/api/pricing/{model:path}")
async def set_price(
    model: str,
    body: PriceUpdate,
    request: Request,
    principal: Annotated[Principal, Depends(require_admin)],
) -> dict[str, object]:
    try:
        await _store(request).set_price(
            model,
            body.input_per_million,
            body.output_per_million,
            principal.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"model": model, **body.model_dump()}


@router.delete("/api/pricing/{model:path}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_price(
    model: str,
    request: Request,
    principal: Annotated[Principal, Depends(require_admin)],
) -> None:
    await _store(request).delete_price(model, principal.id)


@router.put("/api/settings/routing-policy")
async def set_routing_policy(
    body: RoutingPolicyUpdate,
    request: Request,
    principal: Annotated[Principal, Depends(require_admin)],
) -> dict[str, str]:
    await _store(request).set_routing_policy(body.routing_policy, principal.id)
    return body.model_dump()


@router.get("/api/clients")
async def clients(
    request: Request,
    _principal: Annotated[Principal, Depends(require_admin)],
) -> dict[str, object]:
    return {"clients": await _store(request).list_clients()}


@router.post("/api/clients", status_code=status.HTTP_201_CREATED)
async def create_client(
    body: ClientCreate,
    request: Request,
    principal: Annotated[Principal, Depends(require_admin)],
) -> dict[str, object]:
    return await _store(request).create_client(
        name=body.name,
        role=body.role,
        actor=principal.id,
        rate_limit_requests_per_minute=body.rate_limit_requests_per_minute,
    )


@router.patch("/api/clients/{client_id}")
async def update_client(
    client_id: str,
    body: ClientUpdate,
    request: Request,
    principal: Annotated[Principal, Depends(require_admin)],
) -> dict[str, object]:
    try:
        return await _store(request).update_client(
            client_id,
            actor=principal.id,
            role=body.role,
            enabled=body.enabled,
            rate_limit_requests_per_minute=body.rate_limit_requests_per_minute,
            update_rate_limit=(
                body.rate_limit_requests_per_minute is not None
                or body.clear_rate_limit_override
            ),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Client not found") from exc


@router.delete("/api/clients/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: str,
    request: Request,
    principal: Annotated[Principal, Depends(require_admin)],
) -> None:
    try:
        await _store(request).delete_client(client_id, principal.id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Client not found") from exc


@router.get("/api/audit")
async def audit(
    request: Request,
    _principal: Annotated[Principal, Depends(require_admin)],
    limit: int = 100,
) -> dict[str, object]:
    return {"events": await _store(request).audit_events(limit)}
