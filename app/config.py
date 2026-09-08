import json
from functools import lru_cache

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
    fallback_models_json: str = "[]"

    @property
    def model_aliases(self) -> dict[str, str]:
        value = json.loads(self.model_aliases_json)
        if not isinstance(value, dict):
            raise ValueError("MODEL_ALIASES_JSON must be a JSON object")
        return {str(key): str(model) for key, model in value.items()}

    @property
    def fallback_models(self) -> list[str]:
        value = json.loads(self.fallback_models_json)
        if not isinstance(value, list):
            raise ValueError("FALLBACK_MODELS_JSON must be a JSON array")
        return [str(model) for model in value]


@lru_cache
def get_settings() -> Settings:
    return Settings()
