import time
import uuid
from typing import Any

import httpx

from app.config import Settings
from app.errors import ProviderNotConfiguredError, ProviderRequestError
from app.models import ChatCompletionRequest
from app.providers.base import BaseProvider


class GoogleProvider(BaseProvider):
    name = "google"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def configured(self) -> bool:
        return bool(self.settings.google_api_key)

    async def chat(self, model: str, request: ChatCompletionRequest) -> dict[str, Any]:
        if not self.configured():
            raise ProviderNotConfiguredError("Google provider is not configured")

        system_parts = [m.content for m in request.messages if m.role == "system"]
        contents = [
            {
                "role": "model" if m.role == "assistant" else "user",
                "parts": [{"text": m.content}],
            }
            for m in request.messages
            if m.role != "system"
        ]
        payload: dict[str, Any] = {"contents": contents}
        if system_parts:
            payload["systemInstruction"] = {"parts": [{"text": "\n".join(system_parts)}]}

        generation_config: dict[str, Any] = {}
        if request.temperature is not None:
            generation_config["temperature"] = request.temperature
        if request.max_tokens is not None:
            generation_config["maxOutputTokens"] = request.max_tokens
        if generation_config:
            payload["generationConfig"] = generation_config

        url = (
            f"{self.settings.google_base_url.rstrip('/')}/models/{model}:generateContent"
        )

        try:
            async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
                response = await client.post(
                    url,
                    params={"key": self.settings.google_api_key},
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderRequestError(f"Google request failed: {type(exc).__name__}") from exc

        candidates = data.get("candidates", [])
        parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
        text = "".join(part.get("text", "") for part in parts)
        finish_reason = (
            candidates[0].get("finishReason", "STOP").lower() if candidates else "stop"
        )
        usage = data.get("usageMetadata", {})
        prompt_tokens = int(usage.get("promptTokenCount", 0))
        completion_tokens = int(usage.get("candidatesTokenCount", 0))

        return {
            "id": f"chatcmpl-{uuid.uuid4().hex}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": finish_reason,
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": int(
                    usage.get("totalTokenCount", prompt_tokens + completion_tokens)
                ),
            },
        }
