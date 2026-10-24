from __future__ import annotations

from dataclasses import dataclass
from typing import Any


TREND_VERSION = "erste-hungary-rank-trend-v1"


@dataclass(frozen=True, slots=True)
class RankTrendEvidence:
    isin: str
    category_normalized: str
    rank_date_1: str
    rank_date_2: str
    rank_1: int
    rank_2: int
    rank_delta: int
    direction: str
    strength: str
    sufficient_history: bool
    trade_authority: str = "NONE"


def _strength_from_delta(delta: int) -> str:
    magnitude = abs(delta)

    if magnitude >= 20:
        return "STRONG"
    if magnitude >= 10:
        return "MODERATE"
    if magnitude >= 3:
        return "WEAK"
    return "MINIMAL"


def build_rank_trend_evidence(
    *,
    isin: str,
    category_normalized: str,
    rank_date_1: str,
    rank_date_2: str,
    rank_1: int,
    rank_2: int,
) -> RankTrendEvidence:
    delta = int(rank_1) - int(rank_2)

    if delta > 0:
        direction = "IMPROVING"
    elif delta < 0:
        direction = "WEAKENING"
    else:
        direction = "STABLE"

    return RankTrendEvidence(
        isin=isin.strip().upper(),
        category_normalized=category_normalized,
        rank_date_1=rank_date_1,
        rank_date_2=rank_date_2,
        rank_1=int(rank_1),
        rank_2=int(rank_2),
        rank_delta=delta,
        direction=direction,
        strength=_strength_from_delta(delta),
        sufficient_history=True,
        trade_authority="NONE",
    )


def evidence_from_movement_row(
    row: dict[str, Any],
    *,
    date_1: str,
    date_2: str,
) -> RankTrendEvidence:
    return build_rank_trend_evidence(
        isin=str(row["isin"]),
        category_normalized=str(row["category_normalized"]),
        rank_date_1=date_1,
        rank_date_2=date_2,
        rank_1=int(row["rank_1"]),
        rank_2=int(row["rank_2"]),
    )