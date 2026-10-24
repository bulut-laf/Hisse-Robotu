from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

import pandas as pd

from backend.app.prebreakout.prebreakout_candidate_lifecycle import CandidateLifecycleRecord, CandidateLifecycleStatus
from backend.app.prebreakout.prebreakout_live_performance import LivePerformanceLabel, LiveSignalPerformance
from backend.app.prebreakout.prebreakout_paper_portfolio import PaperPortfolioSummary, PaperTrade, PaperTradeStatus, deneme_portfoyu_ozeti


@dataclass(frozen=True)
class StageRealResultRow:
    stage: str
    total_count: int
    measured_count: int
    successful_count: int
    limited_count: int
    failed_count: int
    success_rate_pct: float | None
    false_positive_rate_pct: float | None
    triggered_count: int
    trigger_rate_pct: float | None
    average_trigger_session: float | None


@dataclass(frozen=True)
class ThresholdModeResultRow:
    mode: str
    measured_count: int
    successful_count: int
    success_rate_pct: float | None
    average_close_return_20_pct: float | None


@dataclass(frozen=True)
class RealResultEvaluation:
    measured_count: int
    successful_count: int
    failed_count: int
    sufficient_sample: bool
    minimum_required_sample: int
    stage_rows: tuple[StageRealResultRow, ...]
    threshold_rows: tuple[ThresholdModeResultRow, ...]
    portfolio_summary: PaperPortfolioSummary
    note: str


def _round(value: float | None) -> float | None:
    return None if value is None else round(float(value), 4)


def _h20(record: LiveSignalPerformance):
    return next((item for item in record.horizons if item.horizon == 20), None)


def _threshold_mode_rows(records: Sequence[LiveSignalPerformance], threshold_modes: Mapping[str, str]) -> tuple[ThresholdModeResultRow, ...]:
    groups: dict[str, list[LiveSignalPerformance]] = {}
    for record in records:
        mode = threshold_modes.get(record.signal_id)
        if mode:
            groups.setdefault(str(mode), []).append(record)
    rows: list[ThresholdModeResultRow] = []
    for mode in sorted(groups):
        items = [x for x in groups[mode] if x.label is not LivePerformanceLabel.OLCULEMIYOR]
        successful = sum(x.label is LivePerformanceLabel.BASARILI for x in items)
        closes = []
        for item in items:
            h20 = _h20(item)
            if h20 is not None and h20.close_return_pct is not None:
                closes.append(float(h20.close_return_pct))
        rows.append(ThresholdModeResultRow(
            mode=mode,
            measured_count=len(items),
            successful_count=successful,
            success_rate_pct=_round(successful * 100.0 / len(items)) if items else None,
            average_close_return_20_pct=_round(sum(closes) / len(closes)) if closes else None,
        ))
    return tuple(rows)


def gercek_sonuclari_degerlendir(
    performance_records: Iterable[LiveSignalPerformance],
    lifecycle_records: Iterable[CandidateLifecycleRecord],
    paper_trades: Iterable[PaperTrade],
    *,
    threshold_modes: Mapping[str, str] | None = None,
    minimum_required_sample: int = 10,
    initial_capital: float = 100_000.0,
) -> RealResultEvaluation:
    if minimum_required_sample < 1:
        raise ValueError("Minimum örneklem en az 1 olmalıdır.")
    performances = tuple(performance_records)
    lifecycles = tuple(lifecycle_records)
    trades = tuple(paper_trades)
    measured = tuple(x for x in performances if x.label is not LivePerformanceLabel.OLCULEMIYOR)
    lifecycle_by_id = {x.signal_id: x for x in lifecycles}
    rows: list[StageRealResultRow] = []
    for stage in ("E2", "E3", "E4"):
        stage_all = tuple(x for x in performances if x.signal_stage == stage)
        stage_measured = tuple(x for x in stage_all if x.label is not LivePerformanceLabel.OLCULEMIYOR)
        success = sum(x.label is LivePerformanceLabel.BASARILI for x in stage_measured)
        failed = sum(x.label is LivePerformanceLabel.BASARISIZ for x in stage_measured)
        limited = sum(x.label is LivePerformanceLabel.SINIRLI_HAREKET for x in stage_measured)
        lifecycle_stage = [lifecycle_by_id[x.signal_id] for x in stage_all if x.signal_id in lifecycle_by_id]
        triggered = [x for x in lifecycle_stage if x.status is CandidateLifecycleStatus.TETIKLENDI]
        rows.append(StageRealResultRow(
            stage=stage,
            total_count=len(stage_all),
            measured_count=len(stage_measured),
            successful_count=success,
            limited_count=limited,
            failed_count=failed,
            success_rate_pct=_round(success * 100.0 / len(stage_measured)) if stage_measured else None,
            false_positive_rate_pct=_round(failed * 100.0 / len(stage_measured)) if stage_measured else None,
            triggered_count=len(triggered),
            trigger_rate_pct=_round(len(triggered) * 100.0 / len(lifecycle_stage)) if lifecycle_stage else None,
            average_trigger_session=_round(sum(x.observed_session_count for x in triggered) / len(triggered)) if triggered else None,
        ))
    sufficient = len(measured) >= minimum_required_sample
    note = (
        f"Örneklem yeterli: {len(measured)} ölçülen sonuç."
        if sufficient else
        f"Erken değerlendirme: {len(measured)}/{minimum_required_sample} ölçülen sonuç; kesin başarı hükmü verilmemeli."
    )
    return RealResultEvaluation(
        measured_count=len(measured),
        successful_count=sum(x.label is LivePerformanceLabel.BASARILI for x in measured),
        failed_count=sum(x.label is LivePerformanceLabel.BASARISIZ for x in measured),
        sufficient_sample=sufficient,
        minimum_required_sample=minimum_required_sample,
        stage_rows=tuple(rows),
        threshold_rows=_threshold_mode_rows(performances, threshold_modes or {}),
        portfolio_summary=deneme_portfoyu_ozeti(trades, initial_capital=initial_capital),
        note=note,
    )


def gercek_sonuc_asama_tablosu(result: RealResultEvaluation) -> pd.DataFrame:
    return pd.DataFrame([{
        "Aşama": x.stage, "Toplam": x.total_count, "Ölçülen": x.measured_count,
        "Başarılı": x.successful_count, "Sınırlı": x.limited_count, "Başarısız": x.failed_count,
        "Başarı oranı (%)": x.success_rate_pct, "Yanlış pozitif (%)": x.false_positive_rate_pct,
        "Tetiklendi": x.triggered_count, "Tetiklenme oranı (%)": x.trigger_rate_pct,
        "Ort. tetiklenme seansı": x.average_trigger_session,
    } for x in result.stage_rows])


def gercek_sonuc_esik_tablosu(result: RealResultEvaluation) -> pd.DataFrame:
    return pd.DataFrame([{
        "Eşik modu": x.mode, "Ölçülen": x.measured_count, "Başarılı": x.successful_count,
        "Başarı oranı (%)": x.success_rate_pct, "Ort. 20G kapanış (%)": x.average_close_return_20_pct,
    } for x in result.threshold_rows])
