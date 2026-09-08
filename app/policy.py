from dataclasses import dataclass
from fnmatch import fnmatch
from typing import Any

from app.models import ChatCompletionRequest


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    policy: str
    reason: str


class PolicyEngine:
    @staticmethod
    def _matches(
        rule: dict[str, Any],
        *,
        principal_id: str,
        role: str,
        model: str,
    ) -> bool:
        roles = rule.get("roles")
        if roles and role not in roles:
            return False
        clients = rule.get("clients")
        if clients and principal_id not in clients:
            return False
        models = rule.get("models")
        if models and not any(fnmatch(model, pattern) for pattern in models):
            return False
        return True

    def evaluate(
        self,
        policies: dict[str, dict[str, Any]],
        *,
        principal_id: str,
        role: str,
        request: ChatCompletionRequest,
    ) -> PolicyDecision:
        ordered = sorted(
            (
                (name, rule)
                for name, rule in policies.items()
                if rule.get("enabled", True)
            ),
            key=lambda item: int(item[1].get("priority", 100)),
        )

        for name, rule in ordered:
            if not self._matches(
                rule,
                principal_id=principal_id,
                role=role,
                model=request.model,
            ):
                continue

            max_tokens = rule.get("max_tokens")
            if max_tokens is not None and (request.max_tokens or 0) > int(max_tokens):
                return PolicyDecision(False, name, "max_tokens_exceeded")

            if request.stream and rule.get("allow_stream") is False:
                return PolicyDecision(False, name, "streaming_denied")

            effect = str(rule.get("effect", "allow")).lower()
            if effect == "deny":
                return PolicyDecision(False, name, "explicit_deny")
            if effect == "allow":
                return PolicyDecision(True, name, "explicit_allow")

        return PolicyDecision(True, "default", "default_allow")
