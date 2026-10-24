from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from statistics import mean, median
from typing import Iterable


@dataclass(frozen=True)
class HistoricalCandidateObservation:
    cut_date: date
    symbol: str
    rank: int | None
    stage: str | None
    momentum: float | None
    signal_price: float
    future_max_upside_pct: float | None
    max_adverse_excursion_pct: float | None
    resistance_distance_pct: float | None = None
    score: float | None = None

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol boş olamaz.")
        if self.rank is not None and self.rank < 1:
            raise ValueError("rank 1 veya daha büyük olmalıdır.")
        if self.signal_price <= 0:
            raise ValueError("signal_price pozitif olmalıdır.")


@dataclass(frozen=True)
class BandStatistics:
    label: str
    observations: int
    unique_symbols: int
    success_count: int
    hit_rate_pct: float | None
    avg_upside_pct: float | None
    median_upside_pct: float | None
    avg_adverse_pct: float | None
    median_adverse_pct: float | None


@dataclass(frozen=True)
class FirstAppearanceRecord:
    symbol: str
    first_cut_date: date
    first_rank: int | None
    first_stage: str | None
    first_momentum: float | None
    best_future_upside_pct: float | None


@dataclass(frozen=True)
class HistoricalValidationReport:
    total_observations: int
    unique_symbols: int
    rank_bands: tuple[BandStatistics, ...]
    stage_stats: tuple[BandStatistics, ...]
    momentum_bands: tuple[BandStatistics, ...]
    first_appearances: tuple[FirstAppearanceRecord, ...]


def _percent(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return numerator / denominator * 100.0


def _safe_mean(values: list[float]) -> float | None:
    return mean(values) if values else None


def _safe_median(values: list[float]) -> float | None:
    return median(values) if values else None


def _stats(
    label: str,
    observations: Iterable[HistoricalCandidateObservation],
    success_threshold_pct: float,
) -> BandStatistics:
    rows = list(observations)
    measurable = [x for x in rows if x.future_max_upside_pct is not None]
    successes = [
        x for x in measurable
        if float(x.future_max_upside_pct) >= success_threshold_pct
    ]
    upside = [float(x.future_max_upside_pct) for x in measurable]
    adverse = [
        float(x.max_adverse_excursion_pct)
        for x in rows
        if x.max_adverse_excursion_pct is not None
    ]
    return BandStatistics(
        label=label,
        observations=len(rows),
        unique_symbols=len({x.symbol.upper() for x in rows}),
        success_count=len(successes),
        hit_rate_pct=_percent(len(successes), len(measurable)),
        avg_upside_pct=_safe_mean(upside),
        median_upside_pct=_safe_median(upside),
        avg_adverse_pct=_safe_mean(adverse),
        median_adverse_pct=_safe_median(adverse),
    )


def rank_band_label(rank: int | None) -> str:
    if rank is None:
        return "İzleme dışı"
    if rank <= 10:
        return "1-10"
    if rank <= 20:
        return "11-20"
    if rank <= 30:
        return "21-30"
    return "31+"


def momentum_band_label(momentum: float | None) -> str:
    if momentum is None:
        return "Momentum yok"
    if momentum < 45:
        return "<45"
    if momentum < 55:
        return "45-54"
    if momentum < 65:
        return "55-64"
    if momentum < 75:
        return "65-74"
    return "75+"


def first_appearance_records(
    observations: Iterable[HistoricalCandidateObservation],
) -> tuple[FirstAppearanceRecord, ...]:
    by_symbol: dict[str, list[HistoricalCandidateObservation]] = {}
    for row in observations:
        by_symbol.setdefault(row.symbol.upper(), []).append(row)

    result: list[FirstAppearanceRecord] = []
    for symbol, rows in sorted(by_symbol.items()):
        ordered = sorted(rows, key=lambda x: x.cut_date)
        first = ordered[0]
        measurable = [
            float(x.future_max_upside_pct)
            for x in ordered
            if x.future_max_upside_pct is not None
        ]
        result.append(
            FirstAppearanceRecord(
                symbol=symbol,
                first_cut_date=first.cut_date,
                first_rank=first.rank,
                first_stage=first.stage,
                first_momentum=first.momentum,
                best_future_upside_pct=max(measurable) if measurable else None,
            )
        )
    return tuple(result)


def build_historical_validation_report(
    observations: Iterable[HistoricalCandidateObservation],
    *,
    success_threshold_pct: float = 10.0,
) -> HistoricalValidationReport:
    rows = list(observations)
    if success_threshold_pct <= 0:
        raise ValueError("success_threshold_pct sıfırdan büyük olmalıdır.")

    rank_order = ("1-10", "11-20", "21-30", "31+", "İzleme dışı")
    rank_stats = tuple(
        _stats(
            label,
            [x for x in rows if rank_band_label(x.rank) == label],
            success_threshold_pct,
        )
        for label in rank_order
    )

    stages = sorted({(x.stage or "Aşama yok") for x in rows})
    stage_stats = tuple(
        _stats(
            stage,
            [x for x in rows if (x.stage or "Aşama yok") == stage],
            success_threshold_pct,
        )
        for stage in stages
    )

    momentum_order = ("<45", "45-54", "55-64", "65-74", "75+", "Momentum yok")
    momentum_stats = tuple(
        _stats(
            label,
            [x for x in rows if momentum_band_label(x.momentum) == label],
            success_threshold_pct,
        )
        for label in momentum_order
    )

    return HistoricalValidationReport(
        total_observations=len(rows),
        unique_symbols=len({x.symbol.upper() for x in rows}),
        rank_bands=rank_stats,
        stage_stats=stage_stats,
        momentum_bands=momentum_stats,
        first_appearances=first_appearance_records(rows),
    )


def captured_move_ratio_pct(
    *,
    move_start_price: float,
    rank_entry_price: float,
    peak_price: float,
) -> float | None:
    """
    Bir sıra bandına girildiğinde toplam hareketin yüzde kaçının zaten
    gerçekleşmiş olduğunu ölçer.

    0   -> hareket daha yeni başlıyor
    100 -> tepe seviyesine kadar hareket tamamen gerçekleşmiş
    """
    if move_start_price <= 0 or rank_entry_price <= 0 or peak_price <= 0:
        raise ValueError("Fiyatlar pozitif olmalıdır.")
    total_move = peak_price - move_start_price
    if total_move <= 0:
        return None
    realised = rank_entry_price - move_start_price
    return realised / total_move * 100.0


def forward_return_pct(entry_price: float, exit_price: float) -> float:
    if entry_price <= 0 or exit_price <= 0:
        raise ValueError("Fiyatlar pozitif olmalıdır.")
    return (exit_price / entry_price - 1.0) * 100.0
