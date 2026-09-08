import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.config import Settings
from app.errors import ProviderNotConfiguredError, ProviderRequestError
from app.models import ChatCompletionRequest
from app.providers.base import BaseProvider


class OpenAIProvider(BaseProvider):
    name = "openai"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def configured(self) -> bool:
        return bool(self.settings.openai_api_key)

    async def chat(self, model: str, request: ChatCompletionRequest) -> dict[str, Any]:
        if not self.configured():
            raise ProviderNotConfiguredError("OpenAI provider is not configured")

        payload = request.provider_payload()
        payload["model"] = model
        payload["stream"] = False

        try:
            async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
                response = await client.post(
                    f"{self.settings.openai_base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
                    json=payload,
                )
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderRequestError(f"OpenAI request failed: {type(exc).__name__}") from exc

    async def stream(
        self,
        model: str,
        request: ChatCompletionRequest,
    ) -> AsyncIterator[dict[str, Any]]:
        if not self.configured():
            raise ProviderNotConfiguredError("OpenAI provider is not configured")

        payload = request.provider_payload()
        payload["model"] = model
        payload["stream"] = True
        payload["stream_options"] = {"include_usage": True}

        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "POST",
                    f"{self.settings.openai_base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if not data or data == "[DONE]":
                            continue
                        yield json.loads(data)
        except (httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
            raise ProviderRequestError(
                f"OpenAI stream failed: {type(exc).__name__}"
            ) from exc
