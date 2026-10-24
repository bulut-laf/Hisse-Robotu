from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from backend.app.prebreakout.prebreakout_candidate_lifecycle import (
    CandidateLifecycleRecord,
    CandidateLifecycleStatus,
)
from backend.app.prebreakout.prebreakout_live_performance import (
    LivePerformanceLabel,
    LiveSignalPerformance,
)


@dataclass(frozen=True)
class CandidateQualityStageRow:
    stage: str
    total_signal_count: int
    measured_count: int
    triggered_count: int
    early_triggered_count: int
    successful_count: int
    limited_count: int
    failed_count: int
    trigger_rate_pct: float | None
    early_trigger_rate_pct: float | None
    success_rate_pct: float | None
    false_positive_rate_pct: float | None
    average_trigger_session: float | None
    average_close_return_20_pct: float | None
    average_max_return_20_pct: float | None


@dataclass(frozen=True)
class CandidateQualityReport:
    total_signal_count: int
    measured_count: int
    triggered_count: int
    early_triggered_count: int
    successful_count: int
    false_positive_count: int
    success_rate_pct: float | None
    false_positive_rate_pct: float | None
    trigger_rate_pct: float | None
    early_trigger_rate_pct: float | None
    average_trigger_session: float | None
    sufficient_sample: bool
    minimum_required_sample: int
    early_trigger_session_limit: int
    stage_rows: tuple[CandidateQualityStageRow, ...]
    note: str


def _round(value: float | None) -> float | None:
    return None if value is None else round(float(value), 4)


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return _round(numerator * 100.0 / denominator)


def _h20(record: LiveSignalPerformance):
    return next((item for item in record.horizons if item.horizon == 20), None)


def _stage_row(
    stage: str,
    performances: tuple[LiveSignalPerformance, ...],
    lifecycles: dict[str, CandidateLifecycleRecord],
    *,
    early_trigger_session_limit: int,
) -> CandidateQualityStageRow:
    all_stage = tuple(item for item in performances if item.signal_stage == stage)
    measured = tuple(
        item for item in all_stage if item.label is not LivePerformanceLabel.OLCULEMIYOR
    )
    lifecycle_rows = tuple(
        lifecycles[item.signal_id]
        for item in all_stage
        if item.signal_id in lifecycles
    )
    triggered = tuple(
        item for item in lifecycle_rows if item.status is CandidateLifecycleStatus.TETIKLENDI
    )
    early_triggered = tuple(
        item
        for item in triggered
        if item.observed_session_count <= early_trigger_session_limit
    )

    successful = sum(item.label is LivePerformanceLabel.BASARILI for item in measured)
    limited = sum(item.label is LivePerformanceLabel.SINIRLI_HAREKET for item in measured)
    failed = sum(item.label is LivePerformanceLabel.BASARISIZ for item in measured)

    closes: list[float] = []
    maximums: list[float] = []
    for item in measured:
        horizon = _h20(item)
        if horizon is None:
            continue
        if horizon.close_return_pct is not None:
            closes.append(float(horizon.close_return_pct))
        if horizon.max_return_pct is not None:
            maximums.append(float(horizon.max_return_pct))

    return CandidateQualityStageRow(
        stage=stage,
        total_signal_count=len(all_stage),
        measured_count=len(measured),
        triggered_count=len(triggered),
        early_triggered_count=len(early_triggered),
        successful_count=successful,
        limited_count=limited,
        failed_count=failed,
        trigger_rate_pct=_rate(len(triggered), len(lifecycle_rows)),
        early_trigger_rate_pct=_rate(len(early_triggered), len(lifecycle_rows)),
        success_rate_pct=_rate(successful, len(measured)),
        false_positive_rate_pct=_rate(failed, len(measured)),
        average_trigger_session=(
            _round(sum(item.observed_session_count for item in triggered) / len(triggered))
            if triggered
            else None
        ),
        average_close_return_20_pct=(
            _round(sum(closes) / len(closes)) if closes else None
        ),
        average_max_return_20_pct=(
            _round(sum(maximums) / len(maximums)) if maximums else None
        ),
    )


def aday_kalitesini_degerlendir(
    performance_records: Iterable[LiveSignalPerformance],
    lifecycle_records: Iterable[CandidateLifecycleRecord],
    *,
    minimum_required_sample: int = 20,
    early_trigger_session_limit: int = 3,
) -> CandidateQualityReport:
    """E2-E4 canlı adaylarının gerçek erken-yakalama kalitesini ölçer.

    Bu katman aday üretmez ve eşik değiştirmez. Yalnızca daha önce dondurulmuş
    canlı sinyal, yaşam döngüsü ve 20 işlem günlük performans kayıtlarını
    değerlendirir; bu nedenle geleceğe bakış sızıntısı üretmez.
    """
    if minimum_required_sample < 1:
        raise ValueError("Minimum örneklem en az 1 olmalıdır.")
    if early_trigger_session_limit < 1:
        raise ValueError("Erken tetiklenme seans sınırı en az 1 olmalıdır.")

    performances = tuple(
        item for item in performance_records if item.signal_stage in {"E2", "E3", "E4"}
    )
    lifecycle_by_id = {item.signal_id: item for item in lifecycle_records}
    measured = tuple(
        item for item in performances if item.label is not LivePerformanceLabel.OLCULEMIYOR
    )
    lifecycle_rows = tuple(
        lifecycle_by_id[item.signal_id]
        for item in performances
        if item.signal_id in lifecycle_by_id
    )
    triggered = tuple(
        item for item in lifecycle_rows if item.status is CandidateLifecycleStatus.TETIKLENDI
    )
    early_triggered = tuple(
        item
        for item in triggered
        if item.observed_session_count <= early_trigger_session_limit
    )
    successful = sum(item.label is LivePerformanceLabel.BASARILI for item in measured)
    false_positives = sum(item.label is LivePerformanceLabel.BASARISIZ for item in measured)

    rows = tuple(
        _stage_row(
            stage,
            performances,
            lifecycle_by_id,
            early_trigger_session_limit=early_trigger_session_limit,
        )
        for stage in ("E2", "E3", "E4")
    )
    sufficient = len(measured) >= minimum_required_sample
    note = (
        f"Örneklem yeterli: {len(measured)} ölçülen E2-E4 sonucu; erken yakalama kalitesi değerlendirilebilir."
        if sufficient
        else f"Erken değerlendirme: {len(measured)}/{minimum_required_sample} ölçülen E2-E4 sonucu; kesin kalite hükmü verilmemeli."
    )

    return CandidateQualityReport(
        total_signal_count=len(performances),
        measured_count=len(measured),
        triggered_count=len(triggered),
        early_triggered_count=len(early_triggered),
        successful_count=successful,
        false_positive_count=false_positives,
        success_rate_pct=_rate(successful, len(measured)),
        false_positive_rate_pct=_rate(false_positives, len(measured)),
        trigger_rate_pct=_rate(len(triggered), len(lifecycle_rows)),
        early_trigger_rate_pct=_rate(len(early_triggered), len(lifecycle_rows)),
        average_trigger_session=(
            _round(sum(item.observed_session_count for item in triggered) / len(triggered))
            if triggered
            else None
        ),
        sufficient_sample=sufficient,
        minimum_required_sample=minimum_required_sample,
        early_trigger_session_limit=early_trigger_session_limit,
        stage_rows=rows,
        note=note,
    )


def aday_kalitesi_tablosu(report: CandidateQualityReport) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Aşama": row.stage,
                "Toplam aday": row.total_signal_count,
                "Ölçülen": row.measured_count,
                "Tetiklenen": row.triggered_count,
                "Erken tetiklenen": row.early_triggered_count,
                "Tetiklenme (%)": row.trigger_rate_pct,
                "Erken tetiklenme (%)": row.early_trigger_rate_pct,
                "Ort. tetiklenme seansı": row.average_trigger_session,
                "Başarılı": row.successful_count,
                "Sınırlı": row.limited_count,
                "Başarısız": row.failed_count,
                "Başarı (%)": row.success_rate_pct,
                "Yanlış pozitif (%)": row.false_positive_rate_pct,
                "Ort. 20G kapanış (%)": row.average_close_return_20_pct,
                "Ort. 20G en yüksek (%)": row.average_max_return_20_pct,
            }
            for row in report.stage_rows
        ]
    )
