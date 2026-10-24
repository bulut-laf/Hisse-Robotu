from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SectorProfile:
    """Sektör analiz temel veri modeli.

    Sektör bağlamı tutar.
    İşlem sinyali üretmez.
    """

    name: str
    market: str = "BIST"
    symbols: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "market": self.market,
            "symbols": list(self.symbols),
            "notes": list(self.notes),
        }
