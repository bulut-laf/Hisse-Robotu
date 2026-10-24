from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AIEvaluationReport:
    """AI değerlendirme çıktısı için standart sözleşme.

    Bu yapı karar üretmez.
    Sadece gelecekteki değerlendirme çıktısını düzenler.
    """

    summary: str | None = None
    positive_factors: list[str] = field(default_factory=list)
    risk_factors: list[str] = field(default_factory=list)
    stock_specific_risks: list[str] = field(default_factory=list)
    aligned_points: list[str] = field(default_factory=list)
    conflicting_points: list[str] = field(default_factory=list)
    watch_items: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "positive_factors": list(self.positive_factors),
            "risk_factors": list(self.risk_factors),
            "stock_specific_risks": list(self.stock_specific_risks),
            "aligned_points": list(self.aligned_points),
            "conflicting_points": list(self.conflicting_points),
            "watch_items": list(self.watch_items),
        }
