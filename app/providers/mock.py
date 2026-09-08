import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

from app.models import ChatCompletionRequest
from app.providers.base import BaseProvider


class MockProvider(BaseProvider):
    name = "mock"

    def configured(self) -> bool:
        return True

    @staticmethod
    def _response_text(request: ChatCompletionRequest) -> str:
        latest = next(
            (message.content for message in reversed(request.messages) if message.role == "user"),
            "",
        )
        return f"mock response: {latest}"

    @staticmethod
    def _usage(request: ChatCompletionRequest, text: str) -> dict[str, int]:
        prompt_tokens = sum(len(message.content.split()) for message in request.messages)
        completion_tokens = len(text.split())
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }

    async def chat(self, model: str, request: ChatCompletionRequest) -> dict[str, Any]:
        text = self._response_text(request)
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
            "usage": self._usage(request, text),
        }

    async def stream(
        self,
        model: str,
        request: ChatCompletionRequest,
    ) -> AsyncIterator[dict[str, Any]]:
        text = self._response_text(request)
        completion_id = f"chatcmpl-{uuid.uuid4().hex}"
        created = int(time.time())

        yield {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {"role": "assistant"},
                    "finish_reason": None,
                }
            ],
        }

        words = text.split(" ")
        for index, word in enumerate(words):
            suffix = " " if index < len(words) - 1 else ""
            yield {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": word + suffix},
                        "finish_reason": None,
                    }
                ],
            }

        yield {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop",
                }
            ],
            "usage": self._usage(request, text),
        }
