from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

from backend.app.compliance.vbts_models import VbtsMeasure


@dataclass(frozen=True, slots=True)
class VbtsEvaluation:
    symbol: str
    is_allowed: bool
    active_measure_types: tuple[str, ...]


class VbtsGuard:
    def __init__(self, measures: Iterable[VbtsMeasure]) -> None:
        self._measures = tuple(measures)

    def evaluate(
        self,
        symbol: str,
        control_date: date,
    ) -> VbtsEvaluation:
        normalized_symbol = self._normalize_symbol(symbol)

        active_measure_types = tuple(
            sorted(
                {
                    measure.measure_type
                    for measure in self._measures
                    if measure.symbol == normalized_symbol
                    and measure.is_active_on(control_date)
                }
            )
        )

        return VbtsEvaluation(
            symbol=normalized_symbol,
            is_allowed=not active_measure_types,
            active_measure_types=active_measure_types,
        )

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        normalized = symbol.strip().upper()

        if not normalized:
            raise ValueError("Hisse sembolü boş bırakılamaz.")

        if normalized.endswith(".IS"):
            return normalized

        return f"{normalized}.IS"