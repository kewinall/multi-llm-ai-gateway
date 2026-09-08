import time
import uuid
from typing import Any

import httpx

from app.config import Settings
from app.errors import ProviderNotConfiguredError, ProviderRequestError
from app.models import ChatCompletionRequest
from app.providers.base import BaseProvider


class AnthropicProvider(BaseProvider):
    name = "anthropic"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def configured(self) -> bool:
        return bool(self.settings.anthropic_api_key)

    async def chat(self, model: str, request: ChatCompletionRequest) -> dict[str, Any]:
        if not self.configured():
            raise ProviderNotConfiguredError("Anthropic provider is not configured")

        system_parts = [m.content for m in request.messages if m.role == "system"]
        messages = [
            {
                "role": "assistant" if m.role == "assistant" else "user",
                "content": m.content,
            }
            for m in request.messages
            if m.role != "system"
        ]
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": request.max_tokens or 1024,
        }
        if system_parts:
            payload["system"] = "\n".join(system_parts)
        if request.temperature is not None:
            payload["temperature"] = request.temperature

        try:
            async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
                response = await client.post(
                    f"{self.settings.anthropic_base_url.rstrip('/')}/messages",
                    headers={
                        "x-api-key": str(self.settings.anthropic_api_key),
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderRequestError(f"Anthropic request failed: {type(exc).__name__}") from exc

        text = "".join(
            block.get("text", "")
            for block in data.get("content", [])
            if block.get("type") == "text"
        )
        usage = data.get("usage", {})
        prompt_tokens = int(usage.get("input_tokens", 0))
        completion_tokens = int(usage.get("output_tokens", 0))
        return {
            "id": data.get("id", f"chatcmpl-{uuid.uuid4().hex}"),
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": data.get("stop_reason") or "stop",
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        }
