import hashlib
import json
import secrets
import uuid
from datetime import UTC, datetime
from threading import Lock
from typing import Any

from app.config import Settings
from app.state import RedisStateBackend, StateBackend


class GovernanceStore:
    def __init__(self, settings: Settings, backend: StateBackend) -> None:
        self.settings = settings
        self.backend = backend
        self._lock = Lock()
        self._memory: dict[str, dict[str, str]] = {
            "aliases": {},
            "pools": {},
            "pricing": {},
            "settings": {},
            "clients": {},
        }
        self._audit_events: list[dict[str, Any]] = []

    @property
    def distributed(self) -> bool:
        return isinstance(self.backend, RedisStateBackend)

    def _redis_key(self, section: str) -> str:
        assert isinstance(self.backend, RedisStateBackend)
        return self.backend._key("governance", section)

    async def _hgetall(self, section: str) -> dict[str, str]:
        if isinstance(self.backend, RedisStateBackend):
            return await self.backend.redis.hgetall(self._redis_key(section))
        with self._lock:
            return dict(self._memory[section])

    async def _hget(self, section: str, field: str) -> str | None:
        if isinstance(self.backend, RedisStateBackend):
            return await self.backend.redis.hget(self._redis_key(section), field)
        with self._lock:
            return self._memory[section].get(field)

    async def _hset(self, section: str, field: str, value: str) -> None:
        if isinstance(self.backend, RedisStateBackend):
            await self.backend.redis.hset(self._redis_key(section), field, value)
            return
        with self._lock:
            self._memory[section][field] = value

    async def _hdel(self, section: str, field: str) -> None:
        if isinstance(self.backend, RedisStateBackend):
            await self.backend.redis.hdel(self._redis_key(section), field)
            return
        with self._lock:
            self._memory[section].pop(field, None)

    async def reset(self) -> None:
        if isinstance(self.backend, RedisStateBackend):
            keys = [
                self._redis_key("aliases"),
                self._redis_key("pools"),
                self._redis_key("pricing"),
                self._redis_key("settings"),
                self._redis_key("clients"),
                self._redis_key("audit"),
            ]
            await self.backend.redis.delete(*keys)
            return
        with self._lock:
            for section in self._memory.values():
                section.clear()
            self._audit_events.clear()

    async def audit(
        self,
        *,
        actor: str,
        action: str,
        resource: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        event = {
            "timestamp": datetime.now(UTC).isoformat(),
            "actor": actor,
            "action": action,
            "resource": resource,
            "details": details or {},
        }
        if isinstance(self.backend, RedisStateBackend):
            key = self._redis_key("audit")
            await self.backend.redis.lpush(key, json.dumps(event, separators=(",", ":")))
            await self.backend.redis.ltrim(key, 0, 199)
            return
        with self._lock:
            self._audit_events.append(event)
            del self._audit_events[:-200]

    async def audit_events(self, limit: int = 100) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 200))
        if isinstance(self.backend, RedisStateBackend):
            raw = await self.backend.redis.lrange(self._redis_key("audit"), 0, limit - 1)
            return [json.loads(item) for item in raw]
        with self._lock:
            return list(reversed(self._audit_events[-limit:]))

    async def snapshot(self) -> dict[str, Any]:
        dynamic_aliases = await self._hgetall("aliases")
        dynamic_pools = await self._hgetall("pools")
        dynamic_pricing = await self._hgetall("pricing")
        dynamic_settings = await self._hgetall("settings")

        aliases = dict(self.settings.model_aliases)
        aliases.update(dynamic_aliases)

        pools = dict(self.settings.model_pools)
        pools.update({key: json.loads(value) for key, value in dynamic_pools.items()})

        pricing = dict(self.settings.model_pricing)
        pricing.update({key: json.loads(value) for key, value in dynamic_pricing.items()})

        return {
            "aliases": aliases,
            "pools": pools,
            "pricing": pricing,
            "routing_policy": dynamic_settings.get(
                "routing_policy",
                self.settings.routing_policy,
            ),
            "state_backend": self.backend.name,
            "governance_distributed": self.distributed,
        }

    async def set_alias(self, name: str, target: str, actor: str) -> None:
        if ":" not in target:
            raise ValueError("Alias target must use provider:model format")
        await self._hset("aliases", name, target)
        await self.audit(
            actor=actor,
            action="upsert",
            resource=f"alias:{name}",
            details={"target": target},
        )

    async def delete_alias(self, name: str, actor: str) -> None:
        await self._hdel("aliases", name)
        await self.audit(actor=actor, action="delete", resource=f"alias:{name}")

    async def set_pool(self, name: str, models: list[str], actor: str) -> None:
        if not models:
            raise ValueError("Model pool must contain at least one model")
        if any(":" not in model for model in models):
            raise ValueError("Every pool model must use provider:model format")
        await self._hset("pools", name, json.dumps(models, separators=(",", ":")))
        await self.audit(
            actor=actor,
            action="upsert",
            resource=f"pool:{name}",
            details={"models": models},
        )

    async def delete_pool(self, name: str, actor: str) -> None:
        await self._hdel("pools", name)
        await self.audit(actor=actor, action="delete", resource=f"pool:{name}")

    async def set_price(
        self,
        model: str,
        input_per_million: float,
        output_per_million: float,
        actor: str,
    ) -> None:
        if ":" not in model:
            raise ValueError("Pricing model must use provider:model format")
        value = {
            "input_per_million": float(input_per_million),
            "output_per_million": float(output_per_million),
        }
        await self._hset("pricing", model, json.dumps(value, separators=(",", ":")))
        await self.audit(
            actor=actor,
            action="upsert",
            resource=f"pricing:{model}",
            details=value,
        )

    async def delete_price(self, model: str, actor: str) -> None:
        await self._hdel("pricing", model)
        await self.audit(actor=actor, action="delete", resource=f"pricing:{model}")

    async def set_routing_policy(self, policy: str, actor: str) -> None:
        if policy not in {"priority", "round_robin", "random", "cost"}:
            raise ValueError(f"Unsupported routing policy '{policy}'")
        await self._hset("settings", "routing_policy", policy)
        await self.audit(
            actor=actor,
            action="update",
            resource="settings:routing_policy",
            details={"routing_policy": policy},
        )

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        return hashlib.sha256(api_key.encode("utf-8")).hexdigest()

    async def create_client(
        self,
        *,
        name: str,
        role: str,
        actor: str,
        rate_limit_requests_per_minute: int | None = None,
    ) -> dict[str, Any]:
        if role not in {"viewer", "operator", "admin"}:
            raise ValueError("role must be viewer, operator, or admin")
        api_key = f"llmgw_{secrets.token_urlsafe(24)}"
        digest = self.hash_api_key(api_key)
        record = {
            "id": str(uuid.uuid4()),
            "name": name,
            "role": role,
            "enabled": True,
            "rate_limit_requests_per_minute": rate_limit_requests_per_minute,
            "created_at": datetime.now(UTC).isoformat(),
        }
        await self._hset("clients", digest, json.dumps(record, separators=(",", ":")))
        await self.audit(
            actor=actor,
            action="create",
            resource=f"client:{record['id']}",
            details={"name": name, "role": role},
        )
        return {**record, "api_key": api_key}

    async def authenticate_client(self, api_key: str) -> dict[str, Any] | None:
        raw = await self._hget("clients", self.hash_api_key(api_key))
        if raw is None:
            return None
        record = json.loads(raw)
        if not record.get("enabled", False):
            return None
        return record

    async def list_clients(self) -> list[dict[str, Any]]:
        raw = await self._hgetall("clients")
        records = [json.loads(value) for value in raw.values()]
        return sorted(records, key=lambda item: (item["name"], item["id"]))

    async def _client_entry_by_id(self, client_id: str) -> tuple[str, dict[str, Any]] | None:
        raw = await self._hgetall("clients")
        for digest, value in raw.items():
            record = json.loads(value)
            if record.get("id") == client_id:
                return digest, record
        return None

    async def update_client(
        self,
        client_id: str,
        *,
        actor: str,
        role: str | None = None,
        enabled: bool | None = None,
        rate_limit_requests_per_minute: int | None = None,
        update_rate_limit: bool = False,
    ) -> dict[str, Any]:
        entry = await self._client_entry_by_id(client_id)
        if entry is None:
            raise KeyError(client_id)
        digest, record = entry
        if role is not None:
            if role not in {"viewer", "operator", "admin"}:
                raise ValueError("role must be viewer, operator, or admin")
            record["role"] = role
        if enabled is not None:
            record["enabled"] = enabled
        if update_rate_limit:
            record["rate_limit_requests_per_minute"] = rate_limit_requests_per_minute
        await self._hset("clients", digest, json.dumps(record, separators=(",", ":")))
        await self.audit(
            actor=actor,
            action="update",
            resource=f"client:{client_id}",
            details={
                "role": record["role"],
                "enabled": record["enabled"],
                "rate_limit_requests_per_minute": record.get(
                    "rate_limit_requests_per_minute"
                ),
            },
        )
        return record

    async def delete_client(self, client_id: str, actor: str) -> None:
        entry = await self._client_entry_by_id(client_id)
        if entry is None:
            raise KeyError(client_id)
        digest, record = entry
        await self._hdel("clients", digest)
        await self.audit(
            actor=actor,
            action="delete",
            resource=f"client:{client_id}",
            details={"name": record["name"]},
        )
