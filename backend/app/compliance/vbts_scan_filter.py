from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from types import MappingProxyType
from typing import Iterable, Mapping

from backend.app.compliance.vbts_dataset import VbtsDataset
from backend.app.compliance.vbts_guard import VbtsGuard


class VbtsDatasetNotUsableError(RuntimeError):
    """VBTS veri paketi güvenli kullanıma uygun olmadığında oluşur."""


@dataclass(frozen=True, slots=True)
class VbtsScanFilterResult:
    allowed_symbols: tuple[str, ...]
    blocked_symbols: tuple[str, ...]
    block_reasons: Mapping[str, tuple[str, ...]]


class VbtsScanFilter:
    def __init__(
        self,
        dataset: VbtsDataset,
        maximum_age: timedelta,
    ) -> None:
        if maximum_age < timedelta(0):
            raise ValueError("Azami veri yaşı negatif olamaz.")

        self._dataset = dataset
        self._maximum_age = maximum_age
        self._guard = VbtsGuard(dataset.measures)

    def apply(
        self,
        symbols: Iterable[str],
        control_date: date,
        control_time: datetime,
    ) -> VbtsScanFilterResult:
        if not self._dataset.is_usable_at(
            control_time=control_time,
            maximum_age=self._maximum_age,
        ):
            raise VbtsDatasetNotUsableError(
                "VBTS veri paketi güncel ve doğrulanmış değil; tarama durduruldu."
            )

        return self.apply_known_measures(
            symbols=symbols,
            control_date=control_date,
        )

    def apply_known_measures(
        self,
        symbols: Iterable[str],
        control_date: date,
    ) -> VbtsScanFilterResult:
        """Tazelik garantisi vermeden dosyada bilinen aktif tedbirleri değerlendirir."""

        allowed_symbols: list[str] = []
        blocked_symbols: list[str] = []
        block_reasons: dict[str, tuple[str, ...]] = {}

        for symbol in symbols:
            evaluation = self._guard.evaluate(
                symbol=symbol,
                control_date=control_date,
            )

            if evaluation.is_allowed:
                allowed_symbols.append(evaluation.symbol)
                continue

            blocked_symbols.append(evaluation.symbol)
            block_reasons[evaluation.symbol] = (
                evaluation.active_measure_types
            )

        return VbtsScanFilterResult(
            allowed_symbols=tuple(allowed_symbols),
            blocked_symbols=tuple(blocked_symbols),
            block_reasons=MappingProxyType(block_reasons),
        )
