from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

RoutingPolicy = Literal["priority", "round_robin", "random", "cost"]


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str = "default"
    messages: list[ChatMessage] = Field(min_length=1)
    temperature: float | None = Field(default=None, ge=0)
    max_tokens: int | None = Field(default=None, gt=0)
    stream: bool = False
    routing_policy: RoutingPolicy | None = None

    def provider_payload(self) -> dict[str, Any]:
        payload = self.model_dump(exclude_none=True)
        payload.pop("model", None)
        payload.pop("routing_policy", None)
        return payload
