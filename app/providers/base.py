from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from app.models import ChatCompletionRequest


class BaseProvider(ABC):
    name: str

    @abstractmethod
    def configured(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def chat(self, model: str, request: ChatCompletionRequest) -> dict[str, Any]:
        raise NotImplementedError

    async def stream(
        self,
        model: str,
        request: ChatCompletionRequest,
    ) -> AsyncIterator[dict[str, Any]]:
        buffered = request.model_copy(update={"stream": False})
        result = await self.chat(model, buffered)
        choice = result.get("choices", [{}])[0]
        text = str(choice.get("message", {}).get("content", ""))
        words = text.split(" ")
        for index, word in enumerate(words):
            suffix = " " if index < len(words) - 1 else ""
            yield {
                "id": result.get("id"),
                "object": "chat.completion.chunk",
                "created": result.get("created"),
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
            "id": result.get("id"),
            "object": "chat.completion.chunk",
            "created": result.get("created"),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": choice.get("finish_reason", "stop"),
                }
            ],
            "usage": result.get("usage", {}),
        }
