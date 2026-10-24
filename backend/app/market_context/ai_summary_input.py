from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AIPreparedSummary:
    """Günlük piyasa bağlamını AI değerlendirmesine hazırlayan veri yapısı.

    Bu sınıf karar üretmez.
    Sadece özetleme için yapılandırılmış giriş sağlar.
    """

    date: str
    market_points: list[str] = field(default_factory=list)
    positive_factors: list[str] = field(default_factory=list)
    risk_factors: list[str] = field(default_factory=list)
    institution_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "market_points": list(self.market_points),
            "positive_factors": list(self.positive_factors),
            "risk_factors": list(self.risk_factors),
            "institution_notes": list(self.institution_notes),
        }
