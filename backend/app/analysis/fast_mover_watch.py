"""Fast Mover Watch V1 — pure read-only visibility policy.

Contract:
- no scanner invocation
- no persistence
- no canonical write
- no AL/SAT authority
- no composite score
- caller supplies calibrated thresholds
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Literal, Sequence


class FastMoverState(str, Enum):
    ANI_GUCLENME = "ANI_GUCLENME"
    TEKNIK_GUC_DESTEKLI = "TEKNIK_GUC_DESTEKLI"
    PERSISTENT_OVERLAP = "PERSISTENT_OVERLAP"
    DIKKAT_DAR_TEYIT = "DIKKAT_DAR_TEYIT"
    BLOCKED = "BLOCKED"


class FastMoverWarning(str, Enum):
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    EXCESSIVE_GAP = "EXCESSIVE_GAP"
    ENTRY_DISTANCE = "ENTRY_DISTANCE"
    NARROW_SUPPORT = "NARROW_SUPPORT"
    OVEREXTENDED = "OVEREXTENDED"
    SINGLE_BATCH_ANOMALY = "SINGLE_BATCH_ANOMALY"
    LOW_BASE_MATH_JUMP = "LOW_BASE_MATH_JUMP"


@dataclass(frozen=True)
class FastMoverVisibilityPolicy:
    min_rank_gain: int
    min_percentile_gain: float
    min_support_families: int
    max_contradiction_families_for_main: int

    def __post_init__(self) -> None:
        if self.min_rank_gain < 0:
            raise ValueError("min_rank_gain must be >= 0")
        if not 0.0 <= self.min_percentile_gain <= 1.0:
            raise ValueError("min_percentile_gain must be between 0 and 1")
        if self.min_support_families < 0:
            raise ValueError("min_support_families must be >= 0")
        if self.max_contradiction_families_for_main < 0:
            raise ValueError("max_contradiction_families_for_main must be >= 0")


@dataclass(frozen=True)
class FastMoverObservation:
    symbol: str
    current_rank: int | None
    previous_canonical_rank: int | None
    current_universe_size: int | None
    previous_universe_size: int | None

    data_usable: bool
    baseline_comparable: bool

    security_or_data_lock: bool = False
    proven_data_artifact: bool = False
    positive_state_transition: bool = False

    research_score_current: float | None = None
    research_score_previous: float | None = None

    support_families: tuple[str, ...] = ()
    contradiction_families: tuple[str, ...] = ()
    early_visibility_overlap: bool = False
    warnings: tuple[FastMoverWarning, ...] = ()


@dataclass(frozen=True)
class FastMoverReadModel:
    symbol: str
    visible: bool
    main_list_eligible: bool
    state: FastMoverState | None

    current_rank: int | None
    previous_canonical_rank: int | None
    rank_gain: int | None

    current_percentile_position: float | None
    previous_percentile_position: float | None
    percentile_gain: float | None

    research_score_current: float | None
    research_score_previous: float | None
    research_score_delta: float | None

    support_families: tuple[str, ...]
    contradiction_families: tuple[str, ...]
    warnings: tuple[FastMoverWarning, ...]
    reasons: tuple[str, ...]
    early_visibility_overlap: bool


def _normalize_families(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                value.strip().lower()
                for value in values
                if isinstance(value, str) and value.strip()
            }
        )
    )


def _percentile_position(rank: int | None, universe_size: int | None) -> float | None:
    if rank is None or universe_size is None:
        return None
    if rank < 1 or universe_size < 1 or rank > universe_size:
        return None
    if universe_size == 1:
        return 1.0
    return 1.0 - ((rank - 1) / (universe_size - 1))


def _delta(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None:
        return None
    return current - previous


def evaluate_fast_mover(
    observation: FastMoverObservation,
    policy: FastMoverVisibilityPolicy,
) -> FastMoverReadModel:
    support = _normalize_families(observation.support_families)
    contradictions = _normalize_families(observation.contradiction_families)
    warnings = tuple(dict.fromkeys(observation.warnings))

    current_pct = _percentile_position(
        observation.current_rank,
        observation.current_universe_size,
    )
    previous_pct = _percentile_position(
        observation.previous_canonical_rank,
        observation.previous_universe_size,
    )

    rank_gain = None
    if (
        observation.current_rank is not None
        and observation.previous_canonical_rank is not None
    ):
        rank_gain = observation.previous_canonical_rank - observation.current_rank

    percentile_gain = _delta(current_pct, previous_pct)
    score_delta = _delta(
        observation.research_score_current,
        observation.research_score_previous,
    )

    hard_blocks: list[str] = []

    if not observation.data_usable:
        hard_blocks.append("DATA_NOT_USABLE")
    if observation.current_rank is None or observation.current_universe_size is None:
        hard_blocks.append("CURRENT_OBSERVATION_MISSING")
    if (
        observation.previous_canonical_rank is None
        or observation.previous_universe_size is None
    ):
        hard_blocks.append("BASELINE_MISSING")
    if not observation.baseline_comparable:
        hard_blocks.append("BASELINE_NOT_COMPARABLE")
    if observation.security_or_data_lock:
        hard_blocks.append("SECURITY_OR_DATA_LOCK")
    if observation.proven_data_artifact:
        hard_blocks.append("PROVEN_DATA_ARTIFACT")
    if observation.current_rank is not None and current_pct is None:
        hard_blocks.append("CURRENT_UNIVERSE_POSITION_INVALID")
    if observation.previous_canonical_rank is not None and previous_pct is None:
        hard_blocks.append("PREVIOUS_UNIVERSE_POSITION_INVALID")

    if hard_blocks:
        return FastMoverReadModel(
            symbol=observation.symbol,
            visible=False,
            main_list_eligible=False,
            state=FastMoverState.BLOCKED,
            current_rank=observation.current_rank,
            previous_canonical_rank=observation.previous_canonical_rank,
            rank_gain=rank_gain,
            current_percentile_position=current_pct,
            previous_percentile_position=previous_pct,
            percentile_gain=percentile_gain,
            research_score_current=observation.research_score_current,
            research_score_previous=observation.research_score_previous,
            research_score_delta=score_delta,
            support_families=support,
            contradiction_families=contradictions,
            warnings=warnings,
            reasons=tuple(hard_blocks),
            early_visibility_overlap=observation.early_visibility_overlap,
        )

    rank_material = (
        rank_gain is not None
        and rank_gain >= policy.min_rank_gain
    )
    percentile_material = (
        percentile_gain is not None
        and percentile_gain >= policy.min_percentile_gain
    )

    material = (
        rank_material
        or percentile_material
        or observation.positive_state_transition
    )

    if not material:
        return FastMoverReadModel(
            symbol=observation.symbol,
            visible=False,
            main_list_eligible=False,
            state=None,
            current_rank=observation.current_rank,
            previous_canonical_rank=observation.previous_canonical_rank,
            rank_gain=rank_gain,
            current_percentile_position=current_pct,
            previous_percentile_position=previous_pct,
            percentile_gain=percentile_gain,
            research_score_current=observation.research_score_current,
            research_score_previous=observation.research_score_previous,
            research_score_delta=score_delta,
            support_families=support,
            contradiction_families=contradictions,
            warnings=warnings,
            reasons=("MATERIAL_SINGLE_SESSION_IMPROVEMENT_NOT_PROVEN",),
            early_visibility_overlap=observation.early_visibility_overlap,
        )

    enough_support = len(support) >= policy.min_support_families
    contradictions_ok = (
        len(contradictions)
        <= policy.max_contradiction_families_for_main
    )

    if not enough_support or not contradictions_ok:
        reasons = ["MATERIAL_MOVEMENT_PRESENT"]
        if not enough_support:
            reasons.append("QUALITY_SUPPORT_TOO_NARROW")
        if not contradictions_ok:
            reasons.append("QUALITY_CONTRADICTION")

        return FastMoverReadModel(
            symbol=observation.symbol,
            visible=True,
            main_list_eligible=False,
            state=FastMoverState.DIKKAT_DAR_TEYIT,
            current_rank=observation.current_rank,
            previous_canonical_rank=observation.previous_canonical_rank,
            rank_gain=rank_gain,
            current_percentile_position=current_pct,
            previous_percentile_position=previous_pct,
            percentile_gain=percentile_gain,
            research_score_current=observation.research_score_current,
            research_score_previous=observation.research_score_previous,
            research_score_delta=score_delta,
            support_families=support,
            contradiction_families=contradictions,
            warnings=warnings,
            reasons=tuple(reasons),
            early_visibility_overlap=observation.early_visibility_overlap,
        )

    if observation.early_visibility_overlap:
        state = FastMoverState.PERSISTENT_OVERLAP
    elif "technical_strength" in support:
        state = FastMoverState.TEKNIK_GUC_DESTEKLI
    else:
        state = FastMoverState.ANI_GUCLENME

    reasons = ["MATERIAL_MOVEMENT_PRESENT", "QUALITY_SANITY_PASS"]
    if observation.early_visibility_overlap:
        reasons.append("EARLY_VISIBILITY_OVERLAP")

    return FastMoverReadModel(
        symbol=observation.symbol,
        visible=True,
        main_list_eligible=True,
        state=state,
        current_rank=observation.current_rank,
        previous_canonical_rank=observation.previous_canonical_rank,
        rank_gain=rank_gain,
        current_percentile_position=current_pct,
        previous_percentile_position=previous_pct,
        percentile_gain=percentile_gain,
        research_score_current=observation.research_score_current,
        research_score_previous=observation.research_score_previous,
        research_score_delta=score_delta,
        support_families=support,
        contradiction_families=contradictions,
        warnings=warnings,
        reasons=tuple(reasons),
        early_visibility_overlap=observation.early_visibility_overlap,
    )


def order_fast_movers(
    rows: Sequence[FastMoverReadModel],
    *,
    by: Literal["rank_gain", "percentile_gain"] = "percentile_gain",
) -> tuple[FastMoverReadModel, ...]:
    visible = [row for row in rows if row.visible]

    def movement_value(row: FastMoverReadModel) -> float:
        raw = row.rank_gain if by == "rank_gain" else row.percentile_gain
        return float("-inf") if raw is None else float(raw)

    return tuple(
        sorted(
            visible,
            key=lambda row: (
                0 if row.main_list_eligible else 1,
                -movement_value(row),
                row.current_rank if row.current_rank is not None else 10**9,
                row.symbol,
            ),
        )
    )


__all__ = [
    "FastMoverObservation",
    "FastMoverReadModel",
    "FastMoverState",
    "FastMoverVisibilityPolicy",
    "FastMoverWarning",
    "evaluate_fast_mover",
    "order_fast_movers",
]