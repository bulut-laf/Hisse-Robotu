from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AIEvaluationInput:
    """AI değerlendirmesi için hazırlanmış günlük bağlam verisi.

    Bu sınıf analiz sonucu üretmez.
    Sadece temiz giriş verisi hazırlar.
    """

    date: str
    market_views: list[str] = field(default_factory=list)
    institution_views: list[str] = field(default_factory=list)
    global_factors: list[str] = field(default_factory=list)
    fund_flows: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "market_views": list(self.market_views),
            "institution_views": list(self.institution_views),
            "global_factors": list(self.global_factors),
            "fund_flows": list(self.fund_flows),
        }
