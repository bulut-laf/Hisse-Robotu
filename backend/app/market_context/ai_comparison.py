from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AIComparisonResult:
    """İki AI değerlendirmesini karşılaştırma hazırlığı.

    Karar üretmez.
    Sadece değişimleri yapılandırır.
    """

    previous_date: str
    current_date: str
    changed_items: list[str] = field(default_factory=list)
    increased_risks: list[str] = field(default_factory=list)
    reduced_risks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "previous_date": self.previous_date,
            "current_date": self.current_date,
            "changed_items": list(self.changed_items),
            "increased_risks": list(self.increased_risks),
            "reduced_risks": list(self.reduced_risks),
        }
