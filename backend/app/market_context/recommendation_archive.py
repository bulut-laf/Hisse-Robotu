from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RecommendationArchiveData:
    """Kurum önerilerini market context içinde ayrı veri olarak taşır."""

    report_type: str
    buy: list[str] = field(default_factory=list)
    sell: list[str] = field(default_factory=list)
    watch: list[str] = field(default_factory=list)
    target_prices: dict[str, str] = field(default_factory=dict)
    time_horizon: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_type": self.report_type,
            "recommendations": {
                "buy": list(self.buy),
                "sell": list(self.sell),
                "watch": list(self.watch),
            },
            "target_prices": dict(self.target_prices),
            "time_horizon": self.time_horizon,
        }
