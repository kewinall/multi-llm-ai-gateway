import time
import uuid
from typing import Any

from app.models import ChatCompletionRequest
from app.providers.base import BaseProvider


class MockProvider(BaseProvider):
    name = "mock"

    def configured(self) -> bool:
        return True

    async def chat(self, model: str, request: ChatCompletionRequest) -> dict[str, Any]:
        latest = next(
            (message.content for message in reversed(request.messages) if message.role == "user"),
            "",
        )
        text = f"mock response: {latest}"
        prompt_tokens = sum(len(message.content.split()) for message in request.messages)
        completion_tokens = len(text.split())

        return {
            "id": f"chatcmpl-{uuid.uuid4().hex}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        }
