from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from backend.app.analysis.ranking_memory import RankObservation
from backend.app.analysis.ranking_trajectory import build_rank_trajectories


@dataclass(frozen=True)
class RankingMovementRow:
    symbol: str
    current_rank: int
    gain_1s: int | None
    gain_3s: int | None
    gain_5s: int | None
    acceleration: float | None
    positive_steps_5s: int
    persistence: str
    lifecycle: str
    top5_distance: int
    comparable: bool


def _valid_history(observations: Iterable[RankObservation], symbol: str) -> list[RankObservation]:
    from backend.app.analysis.ranking_trajectory import _parse_observation_date

    rows: list[tuple[object, RankObservation]] = []
    for item in observations:
        if item.symbol != symbol:
            continue
        try:
            parsed = _parse_observation_date(item.as_of)
        except ValueError:
            continue
        rows.append((parsed, item))
    rows.sort(key=lambda pair: pair[0])
    return [item for _, item in rows]


def _acceleration(history: list[RankObservation]) -> float | None:
    if len(history) < 4:
        return None
    current = history[-1].rank
    p1 = history[-2].rank
    p3 = history[-4].rank
    latest_gain = p1 - current
    prior_two_session_avg = (p3 - p1) / 2.0
    return latest_gain - prior_two_session_avg


def _positive_steps_5s(history: list[RankObservation]) -> int:
    recent = history[-6:]
    return sum(
        previous.rank > current.rank
        for previous, current in zip(recent, recent[1:])
    )


def _persistence(step_count: int, available_transitions: int) -> str:
    if available_transitions <= 0:
        return "YETERSIZ_VERI"
    ratio = step_count / available_transitions
    if available_transitions >= 3 and ratio >= 0.8:
        return "KALICI"
    if ratio >= 0.5:
        return "DESTEKLI"
    if step_count > 0:
        return "TEKIL_SICRAMA"
    return "YOK"


def build_ranking_movement_rows(
    observations: Iterable[RankObservation],
) -> tuple[RankingMovementRow, ...]:
    items = tuple(observations)
    trajectories = build_rank_trajectories(items)
    result: list[RankingMovementRow] = []

    for trajectory in trajectories:
        history = _valid_history(items, trajectory.symbol)
        transitions = max(0, min(5, len(history) - 1))
        positive_steps = _positive_steps_5s(history)
        result.append(
            RankingMovementRow(
                symbol=trajectory.symbol,
                current_rank=trajectory.current_rank,
                gain_1s=trajectory.gain_1s,
                gain_3s=trajectory.gain_3s,
                gain_5s=trajectory.gain_5s,
                acceleration=_acceleration(history),
                positive_steps_5s=positive_steps,
                persistence=_persistence(positive_steps, transitions),
                lifecycle=trajectory.lifecycle,
                top5_distance=max(0, trajectory.current_rank - 5),
                comparable=trajectory.comparable,
            )
        )

    return tuple(
        sorted(
            result,
            key=lambda row: (
                row.gain_3s is None,
                -(row.gain_3s or -10**9),
                -(row.acceleration or -10**9),
                row.current_rank,
                row.symbol,
            ),
        )
    )


def ranking_movement_reason(row: RankingMovementRow) -> str:
    """Ham hareket metriklerinden açıklanabilir görünürlük nedeni üretir."""
    if not row.comparable:
        return "Research source/profile değişti; hareket karşılaştırması bloklu."
    if row.gain_3s is None:
        return "3 seanslık karşılaştırma için yeterli tarihli snapshot yok."
    if row.gain_3s <= 0:
        return "Son 3 seansta pozitif sıra kazanımı yok."

    parts = [f"3S +{row.gain_3s} sıra"]
    if row.gain_1s is not None and row.gain_1s > 0:
        parts.append(f"1S +{row.gain_1s}")
    if row.acceleration is not None and row.acceleration > 0:
        parts.append("hareket hızlanıyor")
    if row.persistence == "KALICI":
        parts.append("5S hareket kalıcı")
    elif row.persistence == "DESTEKLI":
        parts.append("5S hareket destekli")
    elif row.persistence == "TEKIL_SICRAMA":
        parts.append("tekil sıçrama")
    if row.top5_distance <= 20:
        parts.append(f"Top-5'e {row.top5_distance} sıra")
    return " · ".join(parts)


def ranking_movement_table_rows(
    rows: Iterable[RankingMovementRow],
) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "Hisse": row.symbol,
            "Bugün": row.current_rank,
            "1S Δ": row.gain_1s if row.gain_1s is not None else "-",
            "3S Δ": row.gain_3s if row.gain_3s is not None else "-",
            "5S Δ": row.gain_5s if row.gain_5s is not None else "-",
            "Sıçrama ivmesi": round(row.acceleration, 1) if row.acceleration is not None else "-",
            "5S pozitif adım": row.positive_steps_5s,
            "Kalıcılık": row.persistence,
            "Hareket": row.lifecycle,
            "Top-5 uzaklık": row.top5_distance,
            "Sıçrama görünürlüğü": (
                "ADAY"
                if row.comparable and row.gain_3s is not None and row.gain_3s > 0
                else "DEĞİL"
            ),
            "Neden?": ranking_movement_reason(row),
            "Karşılaştırma": "Uygun" if row.comparable else "Bloklu",
        }
        for row in rows
    )
