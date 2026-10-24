from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AIDashboardCard:
    title: str = "AI Piyasa Değerlendirmesi"
    summary: str | None = None
    positive_items: list[str] = field(default_factory=list)
    risk_items: list[str] = field(default_factory=list)
    change_items: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "positive_items": list(self.positive_items),
            "risk_items": list(self.risk_items),
            "change_items": list(self.change_items),
        }
