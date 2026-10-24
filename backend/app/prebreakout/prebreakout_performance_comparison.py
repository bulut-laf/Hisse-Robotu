from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

import pandas as pd

from backend.app.prebreakout.prebreakout_live_performance import (
    LivePerformanceLabel,
    LiveSignalPerformance,
)

_MEASURED_LABELS = {
    LivePerformanceLabel.BASARILI,
    LivePerformanceLabel.SINIRLI_HAREKET,
    LivePerformanceLabel.BASARISIZ,
}


@dataclass(frozen=True)
class PerformanceComparisonRow:
    dimension: str
    group: str
    total_count: int
    measured_count: int
    successful_count: int
    limited_count: int
    failed_count: int
    unmeasured_count: int
    success_rate_pct: float | None
    opportunity_rate_pct: float | None
    average_close_return_20_pct: float | None
    average_max_return_20_pct: float | None
    false_positive_rate_pct: float | None


def _round_or_none(value: float | None) -> float | None:
    return None if value is None else round(float(value), 4)


def _horizon_20(record: LiveSignalPerformance):
    return next((item for item in record.horizons if item.horizon == 20), None)


def _row(dimension: str, group: str, records: Sequence[LiveSignalPerformance]) -> PerformanceComparisonRow:
    measured = [item for item in records if item.label in _MEASURED_LABELS]
    successful = sum(item.label is LivePerformanceLabel.BASARILI for item in measured)
    limited = sum(item.label is LivePerformanceLabel.SINIRLI_HAREKET for item in measured)
    failed = sum(item.label is LivePerformanceLabel.BASARISIZ for item in measured)
    close_returns: list[float] = []
    max_returns: list[float] = []
    for item in measured:
        result_20 = _horizon_20(item)
        if result_20 is None:
            continue
        if result_20.close_return_pct is not None:
            close_returns.append(float(result_20.close_return_pct))
        if result_20.max_return_pct is not None:
            max_returns.append(float(result_20.max_return_pct))
    measured_count = len(measured)
    return PerformanceComparisonRow(
        dimension=dimension,
        group=group,
        total_count=len(records),
        measured_count=measured_count,
        successful_count=successful,
        limited_count=limited,
        failed_count=failed,
        unmeasured_count=len(records) - measured_count,
        success_rate_pct=_round_or_none(successful * 100.0 / measured_count) if measured_count else None,
        opportunity_rate_pct=_round_or_none((successful + limited) * 100.0 / measured_count) if measured_count else None,
        average_close_return_20_pct=_round_or_none(sum(close_returns) / len(close_returns)) if close_returns else None,
        average_max_return_20_pct=_round_or_none(sum(max_returns) / len(max_returns)) if max_returns else None,
        false_positive_rate_pct=_round_or_none(failed * 100.0 / measured_count) if measured_count else None,
    )


def performans_karsilastirmasini_hesapla(
    records: Iterable[LiveSignalPerformance],
    *,
    sectors: Mapping[str, str] | None = None,
    market_regimes: Mapping[str, str] | None = None,
    threshold_modes: Mapping[str, str] | None = None,
) -> tuple[PerformanceComparisonRow, ...]:
    items = tuple(records)
    rows: list[PerformanceComparisonRow] = []

    for stage in ("E2", "E3", "E4"):
        group = tuple(item for item in items if item.signal_stage == stage)
        if group:
            rows.append(_row("Aşama", stage, group))

    dimensions = (
        ("Eşik politikası", threshold_modes or {}),
        ("Sektör", sectors or {}),
        ("Piyasa rejimi", market_regimes or {}),
    )
    for dimension, mapping in dimensions:
        grouped: dict[str, list[LiveSignalPerformance]] = {}
        for item in items:
            key = mapping.get(item.signal_id)
            if key:
                grouped.setdefault(str(key), []).append(item)
        for group_name in sorted(grouped):
            rows.append(_row(dimension, group_name, tuple(grouped[group_name])))
    return tuple(rows)


def performans_karsilastirmasini_tabloya_cevir(
    rows: Iterable[PerformanceComparisonRow],
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Kırılım": item.dimension,
                "Grup": item.group,
                "Toplam": item.total_count,
                "Ölçülen": item.measured_count,
                "Başarılı": item.successful_count,
                "Sınırlı": item.limited_count,
                "Başarısız": item.failed_count,
                "Ölçülemiyor": item.unmeasured_count,
                "Başarı oranı (%)": item.success_rate_pct,
                "Fırsat oranı (%)": item.opportunity_rate_pct,
                "Ort. 20G kapanış (%)": item.average_close_return_20_pct,
                "Ort. 20G en yüksek (%)": item.average_max_return_20_pct,
                "Yanlış pozitif (%)": item.false_positive_rate_pct,
            }
            for item in rows
        ]
    )
