from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from backend.app.analysis.ranking_trajectory import RankTrajectory


DEFAULT_EARLY_RANK_MIN = 22
DEFAULT_EARLY_RANK_MAX = 80
DEFAULT_EARLY_LIMIT = 5


@dataclass(frozen=True)
class DailyEarlyTrajectoryCandidate:
    symbol: str
    current_rank: int
    rank_1s: int
    rank_3s: int
    rank_5s: int
    gain_1s: int
    gain_3s: int
    gain_5s: int
    movement: str = "SAĞLIKLI İVMELENME"

    @property
    def rank_path(self) -> str:
        return (
            f"{self.rank_5s} → {self.rank_3s} → "
            f"{self.rank_1s} → {self.current_rank}"
        )


def _healthy_rank_path(item: RankTrajectory) -> bool:
    values = (
        item.rank_5s,
        item.rank_3s,
        item.rank_1s,
        item.current_rank,
        item.gain_1s,
        item.gain_3s,
        item.gain_5s,
    )
    if any(value is None for value in values):
        return False

    return bool(
        item.rank_5s > item.rank_3s > item.rank_1s > item.current_rank
        and item.gain_1s > 0
        and item.gain_3s > 0
        and item.gain_5s > 0
    )


def build_daily_early_trajectory_candidates(
    trajectories: Iterable[RankTrajectory],
    *,
    primary_symbols: Iterable[str] = (),
    limit: int = DEFAULT_EARLY_LIMIT,
    rank_min: int = DEFAULT_EARLY_RANK_MIN,
    rank_max: int = DEFAULT_EARLY_RANK_MAX,
) -> tuple[DailyEarlyTrajectoryCandidate, ...]:
    """
    Read-only early-research selection.

    This is not a score and has no AL/SAT authority. It selects only
    comparable Research trajectories whose 5S -> 3S -> 1S -> today path
    improves monotonically inside the configured research rank band.

    Ordering is deterministic:
    1) 3S rank gain descending (primary early-visibility horizon)
    2) 5S rank gain descending (persistence context)
    3) 1S rank gain descending (latest continuation)
    4) current Research rank ascending
    5) symbol ascending
    """
    if limit < 1:
        raise ValueError("limit 1 veya daha büyük olmalıdır")
    if rank_min < 1 or rank_max < rank_min:
        raise ValueError("rank bandı geçersiz")

    excluded = {
        str(symbol).removesuffix(".IS").upper().strip()
        for symbol in primary_symbols
    }

    candidates: list[DailyEarlyTrajectoryCandidate] = []
    for item in trajectories:
        symbol = str(item.symbol).removesuffix(".IS").upper().strip()
        if symbol in excluded:
            continue
        if not item.comparable:
            continue
        if item.current_rank < rank_min or item.current_rank > rank_max:
            continue
        if not _healthy_rank_path(item):
            continue

        candidates.append(
            DailyEarlyTrajectoryCandidate(
                symbol=symbol,
                current_rank=int(item.current_rank),
                rank_1s=int(item.rank_1s),
                rank_3s=int(item.rank_3s),
                rank_5s=int(item.rank_5s),
                gain_1s=int(item.gain_1s),
                gain_3s=int(item.gain_3s),
                gain_5s=int(item.gain_5s),
            )
        )

    candidates.sort(
        key=lambda item: (
            -item.gain_3s,
            -item.gain_5s,
            -item.gain_1s,
            item.current_rank,
            item.symbol,
        )
    )
    return tuple(candidates[:limit])


def daily_early_trajectory_rows(
    candidates: Iterable[DailyEarlyTrajectoryCandidate],
    *,
    start_priority: int = 6,
) -> tuple[dict[str, object], ...]:
    if start_priority < 1:
        raise ValueError("start_priority 1 veya daha büyük olmalıdır")

    rows = []
    for offset, item in enumerate(candidates):
        rows.append(
            {
                "Öncelik": start_priority + offset,
                "Hisse": item.symbol,
                "Sıra yolu": item.rank_path,
                "1S Δ": f"+{item.gain_1s}",
                "3S Δ": f"+{item.gain_3s}",
                "5S Δ": f"+{item.gain_5s}",
                "Bugün": f"#{item.current_rank}",
                "Hareket": item.movement,
            }
        )
    return tuple(rows)