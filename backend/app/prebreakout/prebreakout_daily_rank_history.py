from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable


@dataclass(frozen=True)
class DailyRankObservation:
    cut_date: date
    symbol: str
    rank: int | None
    score: float | None
    momentum: float | None
    stage: str | None
    signal_price: float | None = None
    future_peak_price: float | None = None
    future_peak_date: date | None = None

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol boş olamaz.")
        if self.rank is not None and self.rank < 1:
            raise ValueError("rank 1 veya daha büyük olmalıdır.")
        if self.score is not None and not 0 <= self.score <= 100:
            raise ValueError("score 0-100 arasında olmalıdır.")
        if self.signal_price is not None and self.signal_price <= 0:
            raise ValueError("signal_price pozitif olmalıdır.")
        if self.future_peak_price is not None and self.future_peak_price <= 0:
            raise ValueError("future_peak_price pozitif olmalıdır.")


@dataclass(frozen=True)
class DailyRankPoint:
    cut_date: date
    rank: int | None
    score: float | None
    momentum: float | None
    stage: str | None
    rank_velocity: float | None
    score_velocity: float | None
    momentum_velocity: float | None


@dataclass(frozen=True)
class SymbolJourney:
    symbol: str
    points: tuple[DailyRankPoint, ...]
    first_seen_date: date | None
    first_top30_date: date | None
    first_top20_date: date | None
    first_top10_date: date | None
    first_top5_date: date | None
    first_early_radar_date: date | None
    first_early_radar_rank: int | None
    sessions_radar_to_top5: int | None
    move_captured_before_top5_pct: float | None


def _velocity(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    return values[-1] - values[-2]


def _rank_velocity(values: list[int]) -> float | None:
    if len(values) < 2:
        return None
    return float(values[-2] - values[-1])


def _first_rank_date(rows: tuple[DailyRankObservation, ...], max_rank: int) -> date | None:
    for row in rows:
        if row.rank is not None and row.rank <= max_rank:
            return row.cut_date
    return None


def _session_distance(rows: tuple[DailyRankObservation, ...], start: date, end: date) -> int | None:
    dates = [row.cut_date for row in rows]
    try:
        i = dates.index(start)
        j = dates.index(end)
    except ValueError:
        return None
    return j - i


def _is_early_radar_point(
    point: DailyRankPoint,
    *,
    min_rank: int = 11,
    max_rank: int = 30,
) -> bool:
    if point.rank is None or not (min_rank <= point.rank <= max_rank):
        return False
    stage = (point.stage or "").upper()
    early_stage = stage in {"E0", "E1", "E2"}
    rank_up = point.rank_velocity is not None and point.rank_velocity > 0
    score_up = point.score_velocity is not None and point.score_velocity > 0
    momentum_up = point.momentum_velocity is not None and point.momentum_velocity > 0
    return early_stage and rank_up and (score_up or momentum_up)


def build_symbol_journey(
    observations: Iterable[DailyRankObservation],
) -> SymbolJourney:
    rows = tuple(sorted(observations, key=lambda x: x.cut_date))
    if not rows:
        raise ValueError("En az bir gözlem gereklidir.")

    symbols = {row.symbol.upper() for row in rows}
    if len(symbols) != 1:
        raise ValueError("build_symbol_journey tek hisse için kullanılmalıdır.")

    rank_hist: list[int] = []
    score_hist: list[float] = []
    momentum_hist: list[float] = []
    points: list[DailyRankPoint] = []

    for row in rows:
        if row.rank is not None:
            rank_hist.append(row.rank)
        if row.score is not None:
            score_hist.append(float(row.score))
        if row.momentum is not None:
            momentum_hist.append(float(row.momentum))

        points.append(
            DailyRankPoint(
                cut_date=row.cut_date,
                rank=row.rank,
                score=row.score,
                momentum=row.momentum,
                stage=row.stage,
                rank_velocity=_rank_velocity(rank_hist),
                score_velocity=_velocity(score_hist),
                momentum_velocity=_velocity(momentum_hist),
            )
        )

    first_radar = next((point for point in points if _is_early_radar_point(point)), None)
    first_top5 = _first_rank_date(rows, 5)

    move_captured = None
    if first_top5 is not None:
        top5_row = next(row for row in rows if row.cut_date == first_top5)
        start_row = rows[0]
        peak_row = next((row for row in rows if row.future_peak_price is not None), None)
        if (
            start_row.signal_price is not None
            and top5_row.signal_price is not None
            and peak_row is not None
            and peak_row.future_peak_price is not None
        ):
            total = peak_row.future_peak_price - start_row.signal_price
            realized = top5_row.signal_price - start_row.signal_price
            if total > 0:
                move_captured = realized / total * 100.0

    return SymbolJourney(
        symbol=rows[0].symbol.upper(),
        points=tuple(points),
        first_seen_date=rows[0].cut_date,
        first_top30_date=_first_rank_date(rows, 30),
        first_top20_date=_first_rank_date(rows, 20),
        first_top10_date=_first_rank_date(rows, 10),
        first_top5_date=first_top5,
        first_early_radar_date=None if first_radar is None else first_radar.cut_date,
        first_early_radar_rank=None if first_radar is None else first_radar.rank,
        sessions_radar_to_top5=(
            None
            if first_radar is None or first_top5 is None
            else _session_distance(rows, first_radar.cut_date, first_top5)
        ),
        move_captured_before_top5_pct=move_captured,
    )


def build_all_journeys(
    observations: Iterable[DailyRankObservation],
) -> tuple[SymbolJourney, ...]:
    grouped: dict[str, list[DailyRankObservation]] = {}
    for row in observations:
        grouped.setdefault(row.symbol.upper(), []).append(row)

    return tuple(
        build_symbol_journey(grouped[symbol])
        for symbol in sorted(grouped)
    )


@dataclass(frozen=True)
class EarlyRadarValidationSummary:
    symbols: int
    radar_triggered: int
    reached_top5: int
    radar_before_top5: int
    avg_sessions_radar_to_top5: float | None
    avg_move_captured_before_top5_pct: float | None


def summarize_journeys(
    journeys: Iterable[SymbolJourney],
) -> EarlyRadarValidationSummary:
    rows = list(journeys)
    radar = [x for x in rows if x.first_early_radar_date is not None]
    top5 = [x for x in rows if x.first_top5_date is not None]
    radar_before_top5 = [
        x for x in rows
        if x.first_early_radar_date is not None
        and x.first_top5_date is not None
        and x.first_early_radar_date <= x.first_top5_date
    ]

    distances = [
        float(x.sessions_radar_to_top5)
        for x in radar_before_top5
        if x.sessions_radar_to_top5 is not None
    ]
    captured = [
        float(x.move_captured_before_top5_pct)
        for x in rows
        if x.move_captured_before_top5_pct is not None
    ]

    return EarlyRadarValidationSummary(
        symbols=len(rows),
        radar_triggered=len(radar),
        reached_top5=len(top5),
        radar_before_top5=len(radar_before_top5),
        avg_sessions_radar_to_top5=(
            sum(distances) / len(distances) if distances else None
        ),
        avg_move_captured_before_top5_pct=(
            sum(captured) / len(captured) if captured else None
        ),
    )
