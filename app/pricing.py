from dataclasses import dataclass
from math import inf

from app.config import Settings


@dataclass(frozen=True)
class ModelPrice:
    input_per_million: float
    output_per_million: float


class PricingCatalog:
    def __init__(self, settings: Settings) -> None:
        self._prices = {
            model: ModelPrice(
                input_per_million=float(price.get("input_per_million", 0.0)),
                output_per_million=float(price.get("output_per_million", 0.0)),
            )
            for model, price in settings.model_pricing.items()
        }

    def get(self, canonical_model: str) -> ModelPrice | None:
        return self._prices.get(canonical_model)

    def routing_cost_score(self, canonical_model: str) -> float:
        price = self.get(canonical_model)
        if price is None:
            return inf
        return price.input_per_million + price.output_per_million

    def calculate(
        self,
        canonical_model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> tuple[float, bool]:
        price = self.get(canonical_model)
        if price is None:
            return 0.0, False
        cost = (
            prompt_tokens * price.input_per_million
            + completion_tokens * price.output_per_million
        ) / 1_000_000
        return cost, True

    def as_dict(self) -> dict[str, dict[str, float]]:
        return {
            model: {
                "input_per_million": price.input_per_million,
                "output_per_million": price.output_per_million,
            }
            for model, price in sorted(self._prices.items())
        }
