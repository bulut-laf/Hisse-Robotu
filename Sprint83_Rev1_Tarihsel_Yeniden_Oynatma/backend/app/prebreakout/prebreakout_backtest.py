from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

import pandas as pd

from backend.app.prebreakout.prebreakout_engine import (
    on_yukselis_hazirligini_analiz_et,
)
from backend.app.prebreakout.prebreakout_models import (
    PreBreakoutConfig,
    PreBreakoutResult,
)


HORIZONS = (1, 3, 5, 10, 20)


@dataclass(frozen=True)
class PreBreakoutForwardPerformance:
    horizon: int
    close_return_pct: float | None
    max_return_pct: float | None
    min_return_pct: float | None
    available: bool


@dataclass(frozen=True)
class PreBreakoutReplayResult:
    symbol: str
    cutoff_date: date
    analysis: PreBreakoutResult
    entry_close: float | None
    forward: tuple[PreBreakoutForwardPerformance, ...]


@dataclass(frozen=True)
class PreBreakoutReplaySummary:
    total_replays: int
    accepted_candidates: int
    late_entry_count: int
    rejected_count: int
    positive_5d_count: int
    positive_5d_rate_pct: float
    five_day_at_least_5_pct_count: int
    five_day_at_least_5_pct_rate_pct: float
    ten_day_at_least_5_pct_count: int
    ten_day_at_least_5_pct_rate_pct: float
    twenty_day_at_least_10_pct_count: int
    twenty_day_at_least_10_pct_rate_pct: float


class PreBreakoutReplayError(ValueError):
    pass


def _normalize_index(data: pd.DataFrame) -> pd.DataFrame:
    if data.empty:
        raise PreBreakoutReplayError("Tarihsel yeniden oynatma için veri boş.")

    normalized = data.copy()
    normalized.index = pd.to_datetime(normalized.index).tz_localize(None)
    normalized = normalized.sort_index()
    normalized = normalized[~normalized.index.duplicated(keep="last")]
    return normalized


def _pct_change(current: float, base: float) -> float:
    if base == 0.0:
        return 0.0
    return ((current / base) - 1.0) * 100.0


def _forward_metrics(
    future: pd.DataFrame,
    *,
    entry_close: float,
    horizon: int,
) -> PreBreakoutForwardPerformance:
    if len(future) < horizon:
        return PreBreakoutForwardPerformance(
            horizon=horizon,
            close_return_pct=None,
            max_return_pct=None,
            min_return_pct=None,
            available=False,
        )

    window = future.iloc[:horizon]
    close_return = _pct_change(float(window["Close"].iloc[-1]), entry_close)
    max_return = _pct_change(float(window["High"].max()), entry_close)
    min_return = _pct_change(float(window["Low"].min()), entry_close)

    return PreBreakoutForwardPerformance(
        horizon=horizon,
        close_return_pct=close_return,
        max_return_pct=max_return,
        min_return_pct=min_return,
        available=True,
    )


def tarihsel_yeniden_oynat(
    symbol: str,
    data: pd.DataFrame,
    cutoff_date: date,
    *,
    config: PreBreakoutConfig | None = None,
    relative_strength_score: int = 5,
    horizons: Iterable[int] = HORIZONS,
) -> PreBreakoutReplayResult:
    normalized = _normalize_index(data)
    cutoff_timestamp = pd.Timestamp(cutoff_date)

    historical = normalized.loc[normalized.index <= cutoff_timestamp]
    future = normalized.loc[normalized.index > cutoff_timestamp]

    if historical.empty:
        raise PreBreakoutReplayError(
            "Kesim tarihinde veya öncesinde fiyat verisi bulunamadı."
        )

    analysis = on_yukselis_hazirligini_analiz_et(
        symbol,
        historical,
        config=config,
        relative_strength_score=relative_strength_score,
    )

    entry_close: float | None = None
    if "Close" in historical.columns:
        entry_close = float(historical["Close"].iloc[-1])

    forward: list[PreBreakoutForwardPerformance] = []
    if entry_close is not None:
        for horizon in tuple(horizons):
            if horizon < 1:
                raise PreBreakoutReplayError(
                    "İleri performans ufku en az 1 işlem günü olmalıdır."
                )
            forward.append(
                _forward_metrics(
                    future,
                    entry_close=entry_close,
                    horizon=horizon,
                )
            )

    return PreBreakoutReplayResult(
        symbol=symbol,
        cutoff_date=cutoff_date,
        analysis=analysis,
        entry_close=entry_close,
        forward=tuple(forward),
    )


def replay_ozeti(
    results: Iterable[PreBreakoutReplayResult],
) -> PreBreakoutReplaySummary:
    result_list = list(results)
    accepted = [result for result in result_list if result.analysis.accepted]
    late_entry = [result for result in result_list if result.analysis.late_entry]
    rejected = [
        result
        for result in result_list
        if not result.analysis.accepted and not result.analysis.late_entry
    ]

    def metric(result: PreBreakoutReplayResult, horizon: int):
        return next(
            (
                item
                for item in result.forward
                if item.horizon == horizon and item.available
            ),
            None,
        )

    five_day = [
        value
        for result in accepted
        if (value := metric(result, 5)) is not None
    ]
    ten_day = [
        value
        for result in accepted
        if (value := metric(result, 10)) is not None
    ]
    twenty_day = [
        value
        for result in accepted
        if (value := metric(result, 20)) is not None
    ]

    positive_5d = sum(
        1
        for value in five_day
        if value.close_return_pct is not None and value.close_return_pct > 0
    )
    five_at_least_5 = sum(
        1
        for value in five_day
        if value.max_return_pct is not None and value.max_return_pct >= 5.0
    )
    ten_at_least_5 = sum(
        1
        for value in ten_day
        if value.max_return_pct is not None and value.max_return_pct >= 5.0
    )
    twenty_at_least_10 = sum(
        1
        for value in twenty_day
        if value.max_return_pct is not None and value.max_return_pct >= 10.0
    )

    def rate(count: int, total: int) -> float:
        return (count / total * 100.0) if total else 0.0

    return PreBreakoutReplaySummary(
        total_replays=len(result_list),
        accepted_candidates=len(accepted),
        late_entry_count=len(late_entry),
        rejected_count=len(rejected),
        positive_5d_count=positive_5d,
        positive_5d_rate_pct=rate(positive_5d, len(five_day)),
        five_day_at_least_5_pct_count=five_at_least_5,
        five_day_at_least_5_pct_rate_pct=rate(
            five_at_least_5,
            len(five_day),
        ),
        ten_day_at_least_5_pct_count=ten_at_least_5,
        ten_day_at_least_5_pct_rate_pct=rate(
            ten_at_least_5,
            len(ten_day),
        ),
        twenty_day_at_least_10_pct_count=twenty_at_least_10,
        twenty_day_at_least_10_pct_rate_pct=rate(
            twenty_at_least_10,
            len(twenty_day),
        ),
    )
