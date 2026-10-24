from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Mapping

from backend.app.analysis.next_day_selection import (
    ExtensionState,
    NextDayCandidateEvidence,
    ReboundState,
)

CONTRACT_ID = "WEEKLY_OPPORTUNITY_ANALYSIS_V1"


class WeeklyOpportunityStage(str, Enum):
    W0 = "W0_NO_SETUP"
    W1 = "W1_EARLY_FORMATION"
    W2 = "W2_DEVELOPING_OPPORTUNITY"
    W3 = "W3_ACTIVATION_WATCH"
    W4 = "W4_HIGH_CONVICTION_ACTIVATION_WATCH"


class WeeklyOpportunityState(str, Enum):
    CLEAN = "CLEAN"
    SOFT_CAUTION = "SOFT_CAUTION"
    BLOCKED = "BLOCKED"
    EXTENDED = "EXTENDED"


@dataclass(frozen=True)
class WeeklyPricePlan:
    current_price: float | None = None
    entry_zone_low: float | None = None
    entry_zone_high: float | None = None
    ideal_entry: float | None = None
    stop_loss: float | None = None
    target_1: float | None = None
    target_2: float | None = None
    risk_reward: float | None = None
    late_entry_above: float | None = None
    source: str = "EXISTING_CONTRACT_ONLY"

    @property
    def available(self) -> bool:
        return any(
            value is not None
            for value in (
                self.entry_zone_low,
                self.entry_zone_high,
                self.ideal_entry,
                self.stop_loss,
                self.target_1,
                self.target_2,
                self.risk_reward,
                self.late_entry_above,
            )
        )


@dataclass(frozen=True)
class WeeklyOpportunityEvidence:
    canonical_date: str
    symbol: str
    research_rank: int
    evidence_families: tuple[str, ...]
    data_ready: bool = True
    freshness_valid: bool = True
    security_lock: bool = False
    universe_comparable: bool = True
    research_valid: bool = True
    hard_contradictions: tuple[str, ...] = ()
    soft_contradictions: tuple[str, ...] = ()
    extension: ExtensionState = ExtensionState.CLEAN
    rebound: ReboundState = ReboundState.NO
    single_factor_domination: bool = False
    readiness_rank: int = 10**9
    migration_rank: int = 10**9
    relative_strength_rank: int = 10**9
    explanation: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class WeeklyOpportunityCandidate:
    canonical_date: str
    symbol: str
    stage: WeeklyOpportunityStage
    state: WeeklyOpportunityState
    research_rank: int
    evidence_families: tuple[str, ...]
    soft_contradictions: tuple[str, ...]
    extension: ExtensionState
    rebound: ReboundState
    readiness_rank: int
    migration_rank: int
    relative_strength_rank: int
    next_day_status: str
    why_visible_now: str
    what_must_happen_next: str
    what_invalidates_setup: str
    pilot_research_status: str
    price_plan: WeeklyPricePlan


@dataclass(frozen=True)
class WeeklyOpportunityResult:
    contract_id: str
    canonical_date: str
    candidates: tuple[WeeklyOpportunityCandidate, ...]
    excluded_count: int

    @property
    def w4(self) -> tuple[WeeklyOpportunityCandidate, ...]:
        return tuple(x for x in self.candidates if x.stage is WeeklyOpportunityStage.W4)

    @property
    def w3(self) -> tuple[WeeklyOpportunityCandidate, ...]:
        return tuple(x for x in self.candidates if x.stage is WeeklyOpportunityStage.W3)

    @property
    def w2(self) -> tuple[WeeklyOpportunityCandidate, ...]:
        return tuple(x for x in self.candidates if x.stage is WeeklyOpportunityStage.W2)

    @property
    def w1(self) -> tuple[WeeklyOpportunityCandidate, ...]:
        return tuple(x for x in self.candidates if x.stage is WeeklyOpportunityStage.W1)


_ALLOWED = {"F1", "F2", "F3", "F4", "F5"}
_STAGE_ORDER = {
    WeeklyOpportunityStage.W4: 0,
    WeeklyOpportunityStage.W3: 1,
    WeeklyOpportunityStage.W2: 2,
    WeeklyOpportunityStage.W1: 3,
    WeeklyOpportunityStage.W0: 4,
}


def weekly_evidence_from_next_day(
    item: NextDayCandidateEvidence,
) -> WeeklyOpportunityEvidence:
    return WeeklyOpportunityEvidence(
        canonical_date=item.canonical_date,
        symbol=item.symbol,
        research_rank=item.research_rank,
        evidence_families=tuple(item.evidence_families),
        data_ready=item.data_ready,
        freshness_valid=item.freshness_valid,
        security_lock=item.security_lock,
        universe_comparable=item.universe_comparable,
        research_valid=item.research_valid,
        hard_contradictions=tuple(item.hard_contradictions),
        soft_contradictions=tuple(item.soft_contradictions),
        extension=item.extension,
        rebound=item.rebound,
        single_factor_domination=item.single_factor_domination,
        readiness_rank=item.readiness_rank,
        migration_rank=item.migration_rank,
        relative_strength_rank=item.relative_strength_rank,
        explanation=tuple(item.explanation),
        warnings=tuple(item.warnings),
    )


def _families(item: WeeklyOpportunityEvidence) -> tuple[str, ...]:
    return tuple(sorted({str(x).upper() for x in item.evidence_families if str(x).upper() in _ALLOWED}))


def _blocked(item: WeeklyOpportunityEvidence) -> bool:
    return (
        not item.data_ready
        or not item.freshness_valid
        or item.security_lock
        or not item.universe_comparable
        or not item.research_valid
        or bool(item.hard_contradictions)
        or item.rebound is ReboundState.TRAP
    )


def _stage(item: WeeklyOpportunityEvidence) -> tuple[WeeklyOpportunityStage, WeeklyOpportunityState]:
    fam = set(_families(item))
    if _blocked(item):
        return WeeklyOpportunityStage.W0, WeeklyOpportunityState.BLOCKED
    if item.single_factor_domination or len(fam) < 2:
        return WeeklyOpportunityStage.W0, WeeklyOpportunityState.CLEAN

    state = WeeklyOpportunityState.CLEAN
    if item.extension is ExtensionState.SEVERE:
        state = WeeklyOpportunityState.EXTENDED
    elif (
        item.soft_contradictions
        or item.extension is ExtensionState.MILD
        or item.rebound is ReboundState.CAUTION
    ):
        state = WeeklyOpportunityState.SOFT_CAUTION

    stage = WeeklyOpportunityStage.W0

    if {"F1", "F2"}.issubset(fam):
        stage = WeeklyOpportunityStage.W1

    if {"F1", "F2"}.issubset(fam) and ({"F3", "F5"} & fam):
        stage = WeeklyOpportunityStage.W2

    if len(fam) >= 3 and ({"F1", "F2"} & fam) and {"F3", "F4"}.issubset(fam):
        stage = WeeklyOpportunityStage.W3

    if (
        {"F1", "F2", "F3", "F4"}.issubset(fam)
        and not item.single_factor_domination
        and not item.soft_contradictions
        and item.extension is ExtensionState.CLEAN
        and item.rebound is ReboundState.NO
    ):
        stage = WeeklyOpportunityStage.W4

    # Severe extension is still research-visible but never activation-ready.
    if item.extension is ExtensionState.SEVERE and _STAGE_ORDER[stage] < _STAGE_ORDER[WeeklyOpportunityStage.W2]:
        stage = WeeklyOpportunityStage.W2

    return stage, state


def _why(item: WeeklyOpportunityEvidence, stage: WeeklyOpportunityStage) -> str:
    names = {
        "F1": "Research migration / Early Visibility",
        "F2": "trend / structural quality",
        "F3": "momentum / relative strength",
        "F4": "activation readiness",
        "F5": "volume / participation",
    }
    parts = [names[x] for x in _families(item)]
    return f"{stage.value}: " + ", ".join(parts) + "."


def _next(item: WeeklyOpportunityEvidence, stage: WeeklyOpportunityStage) -> str:
    fam = set(_families(item))
    missing = [x for x in ("F1", "F2", "F3", "F4", "F5") if x not in fam]
    if stage is WeeklyOpportunityStage.W4:
        return "Mevcut evidence korunmalı; giriş/risk kontratı geçerli kalmalı."
    if "F4" in missing:
        return "Existing F4 activation/readiness teyidi güçlenmeli."
    if "F3" in missing:
        return "Existing momentum/relative-strength teyidi oluşmalı."
    if "F5" in missing:
        return "Katılım/hacim desteği güçlenirse kalite artar."
    return "Mevcut yapı bozulmadan evidence breadth korunmalı."


def _invalidate(item: WeeklyOpportunityEvidence) -> str:
    return (
        "Freshness/security lock, hard contradiction, rebound trap, "
        "structure breakdown veya severe extension."
    )


def _pilot(stage: WeeklyOpportunityStage, state: WeeklyOpportunityState) -> str:
    if state in (WeeklyOpportunityState.BLOCKED, WeeklyOpportunityState.EXTENDED):
        return "PASS"
    if stage is WeeklyOpportunityStage.W4:
        return "PILOT_SHORTLIST"
    if stage is WeeklyOpportunityStage.W3:
        return "REVIEW"
    if stage in (WeeklyOpportunityStage.W2, WeeklyOpportunityStage.W1):
        return "WATCH"
    return "PASS"


def _sort_key(item: WeeklyOpportunityCandidate) -> tuple[object, ...]:
    return (
        _STAGE_ORDER[item.stage],
        len(item.soft_contradictions),
        -len(item.evidence_families),
        item.readiness_rank,
        item.migration_rank,
        item.relative_strength_rank,
        item.research_rank,
        item.symbol,
    )


def classify_weekly_opportunities(
    evidence: Iterable[WeeklyOpportunityEvidence | NextDayCandidateEvidence],
    *,
    price_plans: Mapping[str, WeeklyPricePlan] | None = None,
    next_day_roles: Mapping[str, str] | None = None,
) -> WeeklyOpportunityResult:
    materialized = tuple(evidence)
    if not materialized:
        raise ValueError("Weekly opportunity input cannot be empty.")

    converted = tuple(
        weekly_evidence_from_next_day(x) if isinstance(x, NextDayCandidateEvidence) else x
        for x in materialized
    )
    dates = {x.canonical_date for x in converted}
    if len(dates) != 1:
        raise ValueError("Weekly opportunity evidence must share one canonical date.")

    plans = {str(k).upper(): v for k, v in (price_plans or {}).items()}
    roles = {str(k).upper(): str(v).upper() for k, v in (next_day_roles or {}).items()}

    rows: list[WeeklyOpportunityCandidate] = []
    excluded = 0
    for item in converted:
        stage, state = _stage(item)
        if stage is WeeklyOpportunityStage.W0:
            excluded += 1
            continue
        fam = _families(item)
        rows.append(
            WeeklyOpportunityCandidate(
                canonical_date=item.canonical_date,
                symbol=item.symbol,
                stage=stage,
                state=state,
                research_rank=item.research_rank,
                evidence_families=fam,
                soft_contradictions=tuple(item.soft_contradictions),
                extension=item.extension,
                rebound=item.rebound,
                readiness_rank=item.readiness_rank,
                migration_rank=item.migration_rank,
                relative_strength_rank=item.relative_strength_rank,
                next_day_status=roles.get(item.symbol.upper(), "NONE"),
                why_visible_now=_why(item, stage),
                what_must_happen_next=_next(item, stage),
                what_invalidates_setup=_invalidate(item),
                pilot_research_status=_pilot(stage, state),
                price_plan=plans.get(item.symbol.upper(), WeeklyPricePlan()),
            )
        )

    ordered = tuple(sorted(rows, key=_sort_key))
    return WeeklyOpportunityResult(
        contract_id=CONTRACT_ID,
        canonical_date=next(iter(dates)),
        candidates=ordered,
        excluded_count=excluded,
    )
