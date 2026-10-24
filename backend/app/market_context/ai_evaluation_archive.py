from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AIEvaluationArchiveRecord:
    """AI değerlendirme geçmiş kaydı.

    Sadece karar destek geçmişi tutar.
    İşlem sinyali veya teknik skor üretmez.
    """

    date: str
    summary: str
    risk_factors: list[str] = field(default_factory=list)
    positive_factors: list[str] = field(default_factory=list)
    conflicting_points: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "summary": self.summary,
            "risk_factors": list(self.risk_factors),
            "positive_factors": list(self.positive_factors),
            "conflicting_points": list(self.conflicting_points),
        }
