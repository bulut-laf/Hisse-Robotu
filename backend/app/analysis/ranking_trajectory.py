from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

from backend.app.analysis.ranking_memory import RankObservation


ZONE_LIMITS: tuple[tuple[str, int], ...] = (
    ("TOP30", 30),
    ("TOP50", 50),
    ("TOP100", 100),
    ("TOP200", 200),
)


@dataclass(frozen=True)
class RankTrajectory:
    symbol: str
    as_of: str
    current_rank: int
    current_universe_size: int
    rank_1s: int | None
    rank_3s: int | None
    rank_5s: int | None
    week_start_rank: int | None
    gain_1s: int | None
    gain_3s: int | None
    gain_5s: int | None
    normalized_current: float
    normalized_3s: float | None
    normalized_gain_3s: float | None
    lifecycle: str
    zone_events: tuple[str, ...]
    comparable: bool


def _position(rank: int, universe_size: int) -> float:
    if universe_size <= 0:
        raise ValueError("universe_size must be positive")
    return rank / universe_size


def _parse_observation_date(value: str) -> date:
    if value == "Kişisel liste":
        raise ValueError("Non-date observation skipped")

    for parser in (
        lambda raw: date.fromisoformat(raw),
        lambda raw: date(
            int(raw.split("/")[2]),
            int(raw.split("/")[1]),
            int(raw.split("/")[0]),
        ),
    ):
        try:
            return parser(value)
        except (ValueError, IndexError):
            continue
    raise ValueError(f"Unsupported observation date format: {value!r}")


def _session_map(items: Iterable[RankObservation]) -> list[RankObservation]:
    valid: list[tuple[date, RankObservation]] = []
    for item in items:
        try:
            parsed = _parse_observation_date(item.as_of)
        except ValueError:
            continue
        valid.append((parsed, item))
    valid.sort(key=lambda pair: pair[0])
    return [item for _, item in valid]


def _previous(items: list[RankObservation], sessions_back: int) -> RankObservation | None:
    if sessions_back <= 0:
        raise ValueError("sessions_back must be positive")
    index = len(items) - 1 - sessions_back
    return items[index] if index >= 0 else None


def _week_start(items: list[RankObservation]) -> RankObservation | None:
    if not items:
        return None
    current = _parse_observation_date(items[-1].as_of)
    same_week = [
        item
        for item in items
        if _parse_observation_date(item.as_of).isocalendar()[:2]
        == current.isocalendar()[:2]
    ]
    return same_week[0] if same_week else None


def _zone(rank: int) -> str | None:
    for name, limit in ZONE_LIMITS:
        if rank <= limit:
            return name
    return None


def _zone_events(previous: RankObservation | None, current: RankObservation) -> tuple[str, ...]:
    if previous is None:
        return ()
    events: list[str] = []
    for name, limit in ZONE_LIMITS:
        if previous.rank > limit and current.rank <= limit:
            events.append(f"YENI_{name}")
    return tuple(events)


def _comparable(a: RankObservation | None, b: RankObservation) -> bool:
    if a is None:
        return True
    if a.universe_source != b.universe_source:
        return False
    if a.profile_name != b.profile_name:
        return False
    # V1 does not invent a tolerance threshold. Universe size changes are
    # allowed for normalized comparison, but marked comparable only when
    # the same Research source/profile contract is preserved.
    return a.ranked_universe_size > 0 and b.ranked_universe_size > 0


def _lifecycle(items: list[RankObservation]) -> str:
    if len(items) < 2:
        return "RADAR_DISI"

    current = items[-1]
    prev = items[-2]

    if current.rank < prev.rank and len(items) < 4:
        return "ERKEN_IZLEME"

    if len(items) >= 4:
        last4 = items[-4:]
        ranks = [item.rank for item in last4]

        if ranks[0] > ranks[1] > ranks[2] > ranks[3]:
            if any(event.startswith("YENI_TOP") for event in _zone_events(last4[0], last4[-1])):
                return "UST_BOLGEYE_YERLESIYOR"
            return "IVMELENIYOR"

        if current.rank < last4[0].rank and current.rank > prev.rank:
            return "IVME_KAYBEDIYOR"

        best_mid = min(item.rank for item in last4[1:-1])
        if best_mid < last4[0].rank and current.rank >= last4[0].rank:
            return "SICRAMA_BASARISIZ"

        if current.rank < last4[0].rank:
            return "KAZANCINI_KORUYOR"

    if current.rank < prev.rank:
        return "SICRAMA_TESPITI"
    if current.rank > prev.rank:
        return "IVME_KAYBEDIYOR"
    return "RADAR_DISI"


def build_rank_trajectory(
    observations: Iterable[RankObservation],
    symbol: str,
) -> RankTrajectory | None:
    target = str(symbol).removesuffix(".IS").upper().strip()
    items = _session_map(item for item in observations if item.symbol == target)
    if not items:
        return None

    current = items[-1]
    p1 = _previous(items, 1)
    p3 = _previous(items, 3)
    p5 = _previous(items, 5)
    week = _week_start(items)

    comparable = all(
        _comparable(item, current)
        for item in (p1, p3, p5, week)
        if item is not None
    )

    norm_current = _position(current.rank, current.ranked_universe_size)
    norm_3s = (
        _position(p3.rank, p3.ranked_universe_size)
        if p3 is not None
        else None
    )

    return RankTrajectory(
        symbol=target,
        as_of=current.as_of,
        current_rank=current.rank,
        current_universe_size=current.ranked_universe_size,
        rank_1s=p1.rank if p1 else None,
        rank_3s=p3.rank if p3 else None,
        rank_5s=p5.rank if p5 else None,
        week_start_rank=week.rank if week else None,
        gain_1s=(p1.rank - current.rank) if p1 else None,
        gain_3s=(p3.rank - current.rank) if p3 else None,
        gain_5s=(p5.rank - current.rank) if p5 else None,
        normalized_current=norm_current,
        normalized_3s=norm_3s,
        normalized_gain_3s=(norm_3s - norm_current) if norm_3s is not None else None,
        lifecycle=_lifecycle(items),
        zone_events=_zone_events(p3 or p1, current),
        comparable=comparable,
    )


def build_rank_trajectories(
    observations: Iterable[RankObservation],
) -> tuple[RankTrajectory, ...]:
    items = tuple(observations)
    symbols = sorted({item.symbol for item in items})
    trajectories = [
        trajectory
        for symbol in symbols
        if (trajectory := build_rank_trajectory(items, symbol)) is not None
    ]
    return tuple(
        sorted(
            trajectories,
            key=lambda item: (
                item.gain_3s is None,
                -(item.gain_3s or -10**9),
                item.current_rank,
                item.symbol,
            ),
        )
    )
