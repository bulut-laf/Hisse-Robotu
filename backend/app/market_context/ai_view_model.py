from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AIViewModel:
    """AI değerlendirmesinin kullanıcı görünümü için veri modeli.

    Görselleştirme hazırlığıdır.
    Karar üretmez.
    """

    summary: str | None = None
    positive_factors: list[str] = field(default_factory=list)
    risk_factors: list[str] = field(default_factory=list)
    changed_items: list[str] = field(default_factory=list)
    watch_items: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "positive_factors": list(self.positive_factors),
            "risk_factors": list(self.risk_factors),
            "changed_items": list(self.changed_items),
            "watch_items": list(self.watch_items),
        }
