from abc import ABC, abstractmethod
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
