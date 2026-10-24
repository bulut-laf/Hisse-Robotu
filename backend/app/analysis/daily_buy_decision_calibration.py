from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable


MIN_SAMPLE = 10


@dataclass(frozen=True)
class CalibrationSlice:
    dimension: str
    segment: str
    horizon: str
    sample_size: int
    positive_count: int
    hit_rate: float | None
    average_return: float | None
    status: str


def _band_score(value: int) -> str:
    if value >= 80:
        return "80+"
    if value >= 70:
        return "70-79"
    return "<70"


def _band_ratio(value: float, *, high: float, mid: float) -> str:
    if value >= high:
        return f">={high:g}"
    if value >= mid:
        return f"{mid:g}-{high:g}"
    return f"<{mid:g}"


def _band_rank(value: int | None) -> str:
    if value is None:
        return "YOK"
    if value >= 30:
        return "+30 ve üzeri"
    if value > 0:
        return "+1..+29"
    if value == 0:
        return "0"
    return "Negatif"


def _segments(record: object) -> tuple[tuple[str, str], ...]:
    return (
        ("Faz", str(getattr(record, "phase", "-")).upper()),
        ("Öncelik", f"#{int(getattr(record, 'priority', 0))}"),
        ("Teknik skor", _band_score(int(getattr(record, "technical_score", 0)))),
        (
            "Hacim",
            _band_ratio(float(getattr(record, "volume_ratio", 0.0)), high=1.3, mid=1.0),
        ),
        (
            "Risk/Getiri",
            _band_ratio(float(getattr(record, "risk_reward", 0.0)), high=2.0, mid=1.5),
        ),
        ("Sıra değişimi", _band_rank(getattr(record, "rank_change", None))),
        ("Araştırma önceliği", str(getattr(record, "research_priority", "-")).upper()),
        ("Erken görünürlük", str(getattr(record, "visibility_state", "-") or "-").upper()),
    )


def _status(sample_size: int, hit_rate: float | None, average_return: float | None) -> str:
    if sample_size < MIN_SAMPLE:
        return "YETERSİZ VERİ"
    if hit_rate is None or average_return is None:
        return "YETERSİZ VERİ"
    if hit_rate >= 60.0 and average_return > 0:
        return "DESTEKLEYİCİ"
    if hit_rate < 45.0 or average_return < 0:
        return "GÖZDEN GEÇİR"
    return "İZLE"


def build_buy_decision_calibration(
    records: Iterable[object],
) -> tuple[CalibrationSlice, ...]:
    buckets: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    horizon_attrs = (("1S", "return_1s"), ("3S", "return_3s"), ("5S", "return_5s"))

    for record in records:
        for horizon, attr in horizon_attrs:
            value = getattr(record, attr, None)
            if value is None:
                continue
            value = float(value)
            for dimension, segment in _segments(record):
                buckets[(dimension, segment, horizon)].append(value)

    result: list[CalibrationSlice] = []
    for (dimension, segment, horizon), values in sorted(buckets.items()):
        positive = sum(value > 0 for value in values)
        hit_rate = (positive / len(values)) * 100.0 if values else None
        average_return = sum(values) / len(values) if values else None
        result.append(
            CalibrationSlice(
                dimension=dimension,
                segment=segment,
                horizon=horizon,
                sample_size=len(values),
                positive_count=positive,
                hit_rate=hit_rate,
                average_return=average_return,
                status=_status(len(values), hit_rate, average_return),
            )
        )
    return tuple(result)


def buy_decision_calibration_rows(
    slices: Iterable[CalibrationSlice],
) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "Boyut": item.dimension,
            "Segment": item.segment,
            "Ufuk": item.horizon,
            "Örnek": item.sample_size,
            "Pozitif": item.positive_count,
            "İsabet (%)": round(item.hit_rate, 1) if item.hit_rate is not None else "-",
            "Ort. getiri (%)": round(item.average_return, 2) if item.average_return is not None else "-",
            "Durum": item.status,
        }
        for item in slices
    )
