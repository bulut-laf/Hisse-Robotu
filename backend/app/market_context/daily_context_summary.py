from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class DailyContextSummary:
    """Aynı güne ait farklı bağlamsal raporları birleştirir.

    Bu sınıf yalnızca bilgi toplama amaçlıdır.
    Teknik skor veya işlem kararı üretmez.
    """

    date: str
    documents: list[dict[str, Any]] = field(default_factory=list)

    def add_document(self, document: dict[str, Any]) -> None:
        self.documents.append(document)

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "document_count": len(self.documents),
            "documents": list(self.documents),
        }
