from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class VbtsMeasure:
    symbol: str
    measure_type: str
    start_date: date
    end_date: date
    source: str
    source_reference: str

    def __post_init__(self) -> None:
        normalized_symbol = self._normalize_symbol(self.symbol)
        normalized_measure_type = self.measure_type.strip().upper()
        normalized_source = self.source.strip().upper()
        normalized_reference = self.source_reference.strip()

        if not normalized_measure_type:
            raise ValueError("Tedbir türü boş bırakılamaz.")

        if self.end_date is None:
            raise ValueError("VBTS tedbirinin bitiş tarihi bilinmelidir.")

        if self.end_date < self.start_date:
            raise ValueError(
                "VBTS tedbirinin bitiş tarihi başlangıç tarihinden önce olamaz."
            )

        if not normalized_source:
            raise ValueError("Tedbir kaynağı boş bırakılamaz.")

        if not normalized_reference:
            raise ValueError("Kaynak referansı boş bırakılamaz.")

        object.__setattr__(self, "symbol", normalized_symbol)
        object.__setattr__(self, "measure_type", normalized_measure_type)
        object.__setattr__(self, "source", normalized_source)
        object.__setattr__(self, "source_reference", normalized_reference)

    def is_active_on(self, control_date: date) -> bool:
        return self.start_date <= control_date <= self.end_date

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        normalized = symbol.strip().upper()

        if not normalized:
            raise ValueError("Hisse sembolü boş bırakılamaz.")

        if normalized.endswith(".IS"):
            return normalized

        return f"{normalized}.IS"