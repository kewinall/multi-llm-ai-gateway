import json
from functools import lru_cache
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gateway_api_key: str = "dev-gateway-key"
    request_timeout_seconds: float = 60.0

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    google_api_key: str | None = None

    openai_base_url: str = "https://api.openai.com/v1"
    anthropic_base_url: str = "https://api.anthropic.com/v1"
    google_base_url: str = "https://generativelanguage.googleapis.com/v1beta"

    model_aliases_json: str = '{"default":"mock:demo"}'
    model_pools_json: str = "{}"
    fallback_models_json: str = "[]"
    model_pricing_json: str = (
        '{"mock:demo":{"input_per_million":0.0,"output_per_million":0.0}}'
    )

    routing_policy: str = "priority"
    provider_retry_attempts: int = 1
    rate_limit_requests_per_minute: int = 60
    daily_budget_usd: float | None = None
    monthly_budget_usd: float | None = None
    circuit_failure_threshold: int = 3
    circuit_recovery_seconds: float = 30.0

    @staticmethod
    def _json_object(raw: str, variable: str) -> dict[str, Any]:
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError(f"{variable} must be a JSON object")
        return value

    @property
    def model_aliases(self) -> dict[str, str]:
        value = self._json_object(self.model_aliases_json, "MODEL_ALIASES_JSON")
        return {str(key): str(model) for key, model in value.items()}

    @property
    def model_pools(self) -> dict[str, list[str]]:
        value = self._json_object(self.model_pools_json, "MODEL_POOLS_JSON")
        pools: dict[str, list[str]] = {}
        for key, models in value.items():
            if not isinstance(models, list):
                raise ValueError("Every MODEL_POOLS_JSON value must be a JSON array")
            pools[str(key)] = [str(model) for model in models]
        return pools

    @property
    def fallback_models(self) -> list[str]:
        value = json.loads(self.fallback_models_json)
        if not isinstance(value, list):
            raise ValueError("FALLBACK_MODELS_JSON must be a JSON array")
        return [str(model) for model in value]

    @property
    def model_pricing(self) -> dict[str, dict[str, float]]:
        value = self._json_object(self.model_pricing_json, "MODEL_PRICING_JSON")
        pricing: dict[str, dict[str, float]] = {}
        for model, raw_price in value.items():
            if not isinstance(raw_price, dict):
                raise ValueError("Every MODEL_PRICING_JSON value must be a JSON object")
            pricing[str(model)] = {
                "input_per_million": float(raw_price.get("input_per_million", 0.0)),
                "output_per_million": float(raw_price.get("output_per_million", 0.0)),
            }
        return pricing


@lru_cache
def get_settings() -> Settings:
    return Settings()
