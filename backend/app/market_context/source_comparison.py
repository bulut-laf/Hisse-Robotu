from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SourceComparison:
    """Farklı kaynak görüşlerini karşılaştırma hazırlığı.

    Karar üretmez, yalnızca kaynak farklılıklarını saklar.
    """

    topic: str
    positive_views: list[str] = field(default_factory=list)
    negative_views: list[str] = field(default_factory=list)
    risk_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "positive_views": list(self.positive_views),
            "negative_views": list(self.negative_views),
            "risk_notes": list(self.risk_notes),
        }
