from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Mapping

import pandas as pd

from backend.app.prebreakout.prebreakout_backtest import (
    HORIZONS,
    PreBreakoutPerformanceLabel,
    PreBreakoutReplayResult,
    performans_etiketi_belirle,
    tarihsel_yeniden_oynat,
)
from backend.app.prebreakout.prebreakout_models import PreBreakoutConfig


@dataclass(frozen=True)
class PreBreakoutValidationConfig:
    start_date: date
    end_date: date
    cutoff_step: int = 5
    minimum_history_bars: int = 60
    minimum_score: int = 45
    horizons: tuple[int, ...] = HORIZONS

    def __post_init__(self) -> None:
        if self.start_date > self.end_date:
            raise ValueError("Başlangıç tarihi bitiş tarihinden sonra olamaz.")
        if self.cutoff_step < 1:
            raise ValueError("Kesim adımı en az 1 işlem günü olmalıdır.")
        if self.minimum_history_bars < 60:
            raise ValueError("Minimum geçmiş bar sayısı en az 60 olmalıdır.")
        if not 0 <= self.minimum_score <= 100:
            raise ValueError("Minimum skor 0 ile 100 arasında olmalıdır.")
        if not self.horizons or any(horizon < 1 for horizon in self.horizons):
            raise ValueError("İleri performans ufukları pozitif olmalıdır.")


@dataclass(frozen=True)
class PreBreakoutValidationRecord:
    symbol: str
    cutoff_date: date
    replay: PreBreakoutReplayResult
    performance_label: str


@dataclass(frozen=True)
class PreBreakoutValidationSummary:
    total_replays: int
    score_threshold_passed: int
    accepted_candidates: int
    successful: int
    limited_move: int
    false_positive: int
    late_entry: int
    insufficient_data: int
    not_candidate: int
    success_rate_pct: float
    false_positive_rate_pct: float


def _normalize(data: pd.DataFrame) -> pd.DataFrame:
    if data.empty:
        return data.copy()
    normalized = data.copy()
    normalized.index = pd.to_datetime(normalized.index).tz_localize(None)
    normalized = normalized.sort_index()
    return normalized[~normalized.index.duplicated(keep="last")]


def uygun_kesim_tarihleri(
    data: pd.DataFrame,
    config: PreBreakoutValidationConfig,
) -> tuple[date, ...]:
    normalized = _normalize(data)
    if normalized.empty:
        return ()

    mask = (
        (normalized.index.date >= config.start_date)
        & (normalized.index.date <= config.end_date)
    )
    candidate_positions = [
        position
        for position, allowed in enumerate(mask)
        if allowed and position + 1 >= config.minimum_history_bars
    ]

    selected = candidate_positions[:: config.cutoff_step]
    return tuple(normalized.index[position].date() for position in selected)


def sembol_tarihsel_dogrulama(
    symbol: str,
    data: pd.DataFrame,
    validation_config: PreBreakoutValidationConfig,
    *,
    engine_config: PreBreakoutConfig | None = None,
    relative_strength_score: int = 5,
) -> tuple[PreBreakoutValidationRecord, ...]:
    normalized = _normalize(data)
    records: list[PreBreakoutValidationRecord] = []

    for cutoff in uygun_kesim_tarihleri(normalized, validation_config):
        replay = tarihsel_yeniden_oynat(
            symbol,
            normalized,
            cutoff,
            config=engine_config,
            relative_strength_score=relative_strength_score,
            horizons=validation_config.horizons,
        )
        if replay.analysis.score < validation_config.minimum_score:
            continue

        records.append(
            PreBreakoutValidationRecord(
                symbol=symbol,
                cutoff_date=cutoff,
                replay=replay,
                performance_label=performans_etiketi_belirle(replay),
            )
        )

    return tuple(records)


def toplu_tarihsel_dogrulama(
    data_by_symbol: Mapping[str, pd.DataFrame],
    validation_config: PreBreakoutValidationConfig,
    *,
    engine_config: PreBreakoutConfig | None = None,
    relative_strength_scores: Mapping[str, int] | None = None,
) -> tuple[PreBreakoutValidationRecord, ...]:
    records: list[PreBreakoutValidationRecord] = []

    for symbol in sorted(data_by_symbol):
        relative_strength_score = (
            relative_strength_scores.get(symbol, 5)
            if relative_strength_scores is not None
            else 5
        )
        records.extend(
            sembol_tarihsel_dogrulama(
                symbol,
                data_by_symbol[symbol],
                validation_config,
                engine_config=engine_config,
                relative_strength_score=relative_strength_score,
            )
        )

    return tuple(
        sorted(
            records,
            key=lambda record: (
                record.cutoff_date,
                record.symbol,
            ),
        )
    )


def dogrulama_ozeti(
    records: tuple[PreBreakoutValidationRecord, ...],
) -> PreBreakoutValidationSummary:
    labels = [record.performance_label for record in records]

    successful = labels.count(PreBreakoutPerformanceLabel.BASARILI)
    limited = labels.count(PreBreakoutPerformanceLabel.SINIRLI_HAREKET)
    false_positive = labels.count(
        PreBreakoutPerformanceLabel.YANLIS_POZITIF
    )
    late_entry = labels.count(PreBreakoutPerformanceLabel.GEC_GIRIS)
    insufficient = labels.count(
        PreBreakoutPerformanceLabel.YETERSIZ_VERI
    )
    not_candidate = labels.count(PreBreakoutPerformanceLabel.ADAY_DEGIL)

    accepted_candidates = sum(
        1 for record in records if record.replay.analysis.accepted
    )

    def rate(count: int, total: int) -> float:
        return (count / total * 100.0) if total else 0.0

    evaluated_candidates = successful + limited + false_positive

    return PreBreakoutValidationSummary(
        total_replays=len(records),
        score_threshold_passed=len(records),
        accepted_candidates=accepted_candidates,
        successful=successful,
        limited_move=limited,
        false_positive=false_positive,
        late_entry=late_entry,
        insufficient_data=insufficient,
        not_candidate=not_candidate,
        success_rate_pct=rate(successful, evaluated_candidates),
        false_positive_rate_pct=rate(
            false_positive,
            evaluated_candidates,
        ),
    )
