
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Iterable

from .ranking_memory import RankObservationJsonlStore, ResearchProfileObservation
from .ranking_trajectory import RankTrajectory, build_rank_trajectories
from .research_profiles import ProfileState
from .research_profiles_daily import DailyResearchProfileBundle

RESEARCH_PROFILE_MEMORY_ACTIVATION_DATE = date(2026, 8, 26)
CANONICAL_PROFILE_MEMORY_UNIVERSE = "BIST Tüm"


@dataclass(frozen=True)
class ResearchProfileMemoryWriteResult:
    status: str
    attempted: int
    appended: int
    as_of: str
    reason: str = ""


@dataclass(frozen=True)
class ProfileLifecycleContext:
    symbol: str
    research_profile: str
    current_state: str
    first_match: str | None
    last_match: str | None
    consecutive_match_sessions: int
    profile_age_sessions: int
    event: str | None
    block_reason: str | None
    observed_sessions: int


@dataclass(frozen=True)
class RankMovementContext:
    symbol: str
    current_rank: int | None
    rank_1s: int | None
    rank_3s: int | None
    rank_5s: int | None
    gain_1s: int | None
    gain_3s: int | None
    gain_5s: int | None
    lifecycle: str | None
    comparable: bool
    warming_up: bool

    @property
    def rank_path(self) -> str:
        if self.current_rank is None:
            return "Ana Research sıralamasında değil"
        if self.warming_up:
            return "WARMING UP"
        return f"{self.rank_5s} → {self.rank_3s} → {self.rank_1s} → {self.current_rank}"


def _clean_symbol(value: object) -> str:
    raw = str(value or "").strip().upper()
    return raw.removesuffix(".IS")


def _iso(value: str) -> str:
    return date.fromisoformat(str(value)[:10]).isoformat()


def profile_observations_from_bundle(
    bundle: DailyResearchProfileBundle,
    *,
    recorded_at: str | None = None,
    universe_name: str = CANONICAL_PROFILE_MEMORY_UNIVERSE,
) -> tuple[ResearchProfileObservation, ...]:
    stamp = recorded_at or datetime.now(timezone.utc).isoformat()
    output = []
    for item in bundle.items:
        for result in item.results:
            output.append(
                ResearchProfileObservation(
                    as_of=bundle.as_of.isoformat(),
                    symbol=_clean_symbol(item.symbol),
                    research_profile=result.profile.value,
                    state=result.state.value,
                    direction=result.direction.value,
                    reasons=tuple(result.reasons),
                    warnings=tuple(result.warnings),
                    universe_name=universe_name,
                    successful_universe_size=bundle.successful_symbol_count,
                    recorded_at=stamp,
                )
            )
    return tuple(output)


def persist_research_profile_bundle(
    bundle: DailyResearchProfileBundle,
    *,
    universe_name: str,
    store: RankObservationJsonlStore | None = None,
    activation_date: date = RESEARCH_PROFILE_MEMORY_ACTIVATION_DATE,
) -> ResearchProfileMemoryWriteResult:
    if universe_name != CANONICAL_PROFILE_MEMORY_UNIVERSE:
        return ResearchProfileMemoryWriteResult(
            "SKIPPED_NON_CANONICAL_UNIVERSE", 0, 0, bundle.as_of.isoformat(),
            f"Canonical universe is {CANONICAL_PROFILE_MEMORY_UNIVERSE}.",
        )

    if bundle.as_of < activation_date:
        return ResearchProfileMemoryWriteResult(
            "WARMING_UP", 0, 0, bundle.as_of.isoformat(),
            "Forward-only activation not reached; profile backfill is forbidden.",
        )

    observations = profile_observations_from_bundle(
        bundle, universe_name=universe_name
    )
    target = store or RankObservationJsonlStore()
    appended = target.append_profile_snapshot(
        observations, activation_date=activation_date
    )
    return ResearchProfileMemoryWriteResult(
        "WRITTEN" if appended else "UNCHANGED",
        len(observations),
        appended,
        bundle.as_of.isoformat(),
    )


def _latest_revision_by_session(
    observations: Iterable[ResearchProfileObservation],
    *,
    symbol: str,
    research_profile: str,
) -> tuple[ResearchProfileObservation, ...]:
    revisions = [
        item for item in observations
        if _clean_symbol(item.symbol) == _clean_symbol(symbol)
        and item.research_profile == research_profile
    ]
    latest = {}
    for item in sorted(revisions, key=lambda x: (_iso(x.as_of), x.recorded_at)):
        latest[_iso(item.as_of)] = item
    return tuple(latest[key] for key in sorted(latest))


def build_profile_lifecycle(
    observations: Iterable[ResearchProfileObservation],
    *,
    symbol: str,
    research_profile: str,
) -> ProfileLifecycleContext | None:
    sessions = _latest_revision_by_session(
        observations, symbol=symbol, research_profile=research_profile
    )
    if not sessions:
        return None

    current = sessions[-1]
    previous = sessions[-2] if len(sessions) >= 2 else None
    matches = [x for x in sessions if x.state == ProfileState.MATCH.value]
    first_match = matches[0].as_of if matches else None
    last_match = matches[-1].as_of if matches else None

    streak = 0
    for item in reversed(sessions):
        if item.state != ProfileState.MATCH.value:
            break
        streak += 1

    age = 0
    if first_match:
        first = _iso(first_match)
        age = sum(_iso(item.as_of) >= first for item in sessions)

    event = None
    if current.state == ProfileState.MATCH.value and (
        previous is None or previous.state != ProfileState.MATCH.value
    ):
        event = "ENTRY"
    elif (
        current.state != ProfileState.MATCH.value
        and previous is not None
        and previous.state == ProfileState.MATCH.value
    ):
        event = "EXIT"

    block_reason = next(
        (x for x in current.reasons if str(x).startswith("BLOCK_")), None
    )

    return ProfileLifecycleContext(
        symbol=_clean_symbol(symbol),
        research_profile=research_profile,
        current_state=current.state,
        first_match=first_match,
        last_match=last_match,
        consecutive_match_sessions=streak,
        profile_age_sessions=age,
        event=event,
        block_reason=block_reason,
        observed_sessions=len(sessions),
    )


def build_profile_lifecycle_map(bundle, observations):
    history = tuple(observations)
    output = {}
    for item in bundle.items:
        symbol = _clean_symbol(item.symbol)
        for result in item.results:
            ctx = build_profile_lifecycle(
                history,
                symbol=symbol,
                research_profile=result.profile.value,
            )
            if ctx:
                output[(symbol, result.profile.value)] = ctx
    return output


def _rank_context(trajectory: RankTrajectory) -> RankMovementContext:
    warming = (
        not trajectory.comparable
        or trajectory.rank_1s is None
        or trajectory.rank_3s is None
        or trajectory.rank_5s is None
    )
    return RankMovementContext(
        symbol=_clean_symbol(trajectory.symbol),
        current_rank=trajectory.current_rank,
        rank_1s=trajectory.rank_1s,
        rank_3s=trajectory.rank_3s,
        rank_5s=trajectory.rank_5s,
        gain_1s=trajectory.gain_1s,
        gain_3s=trajectory.gain_3s,
        gain_5s=trajectory.gain_5s,
        lifecycle=trajectory.lifecycle,
        comparable=trajectory.comparable,
        warming_up=warming,
    )


def build_rank_movement_map(store=None):
    target = store or RankObservationJsonlStore()
    return {
        _clean_symbol(item.symbol): _rank_context(item)
        for item in build_rank_trajectories(target.list())
    }


def load_profile_memory_context(bundle, *, store=None):
    target = store or RankObservationJsonlStore()
    return (
        build_profile_lifecycle_map(
            bundle, target.list_profile_observations()
        ),
        build_rank_movement_map(target),
    )
