from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class DailyAIPackage:
    """Günlük piyasa bağlamını AI değerlendirmesi için birleştirir.

    Karar üretmez, yalnızca analiz girdisi oluşturur.
    """

    date: str
    market_context: list[str] = field(default_factory=list)
    global_context: list[str] = field(default_factory=list)
    institution_context: list[str] = field(default_factory=list)
    fund_etf_context: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "market_context": list(self.market_context),
            "global_context": list(self.global_context),
            "institution_context": list(self.institution_context),
            "fund_etf_context": list(self.fund_etf_context),
            "risks": list(self.risks),
        }
