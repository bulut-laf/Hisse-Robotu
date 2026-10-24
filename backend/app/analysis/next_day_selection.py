from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Iterable


STRATEGY_ID = "NEXT_DAY_SELECTION_STRATEGY_V1"
STRATEGY_FROZEN = True
MAX_PRIMARY = 5
MAX_RESERVE = 5

EVIDENCE_FAMILIES = ("F1", "F2", "F3", "F4", "F5")
STRUCTURAL_FAMILIES = frozenset({"F1", "F2"})
TIMING_FAMILIES = frozenset({"F3", "F4"})


class NextDayRole(str, Enum):
    PRIMARY = "PRIMARY"
    RESERVE = "RESERVE"
    EXCLUDED = "EXCLUDED"


class ExtensionState(str, Enum):
    CLEAN = "CLEAN"
    MILD = "MILD"
    SEVERE = "SEVERE"


class ReboundState(str, Enum):
    NO = "NO"
    CAUTION = "CAUTION"
    TRAP = "TRAP"


@dataclass(frozen=True)
class NextDayCandidateEvidence:
    """Read-only normalized canonical evidence for one research candidate.

    This object does not calculate a new market signal. Callers map already
    existing canonical evidence into F1-F5 once, with duplicate factors
    collapsed before selection.
    """

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

    # Ordinal existing-context ranks only. Lower means better.
    readiness_rank: int = 99
    migration_rank: int = 99
    relative_strength_rank: int = 99

    explanation: str = ""
    warnings: tuple[str, ...] = ()
    next_action: str = "Tek Hisse İnceleme"


@dataclass(frozen=True)
class NextDaySelectionItem:
    canonical_date: str
    symbol: str
    role: NextDayRole
    selection_order: int
    research_rank: int
    evidence_families: tuple[str, ...]
    contradiction_state: str
    extension_state: ExtensionState
    rebound_state: ReboundState
    exclusion_reason: str | None
    explanation: str
    warnings: tuple[str, ...]
    next_action: str
    evaluation_identity: str


@dataclass(frozen=True)
class NextDaySelectionResult:
    canonical_date: str
    primary: tuple[NextDaySelectionItem, ...]
    reserve: tuple[NextDaySelectionItem, ...]
    excluded: tuple[NextDaySelectionItem, ...]
    strategy_id: str = STRATEGY_ID
    strategy_frozen: bool = STRATEGY_FROZEN


def _clean_symbol(value: object) -> str:
    return str(value or "").strip().upper().removesuffix(".IS")


def _canonical_date(value: str) -> str:
    parsed = date.fromisoformat(str(value))
    return parsed.isoformat()


def _families(values: Iterable[str]) -> tuple[str, ...]:
    """Normalize and de-duplicate family identities.

    Duplicate module appearances never increase breadth. Only F1-F5 identities
    are accepted by the frozen V1 read model.
    """

    normalized = {
        str(value or "").strip().upper()
        for value in values
        if str(value or "").strip()
    }
    unknown = normalized.difference(EVIDENCE_FAMILIES)
    if unknown:
        raise ValueError(
            "Unknown evidence family: " + ", ".join(sorted(unknown))
        )
    return tuple(family for family in EVIDENCE_FAMILIES if family in normalized)


def _normalized(candidate: NextDayCandidateEvidence) -> NextDayCandidateEvidence:
    symbol = _clean_symbol(candidate.symbol)
    if not symbol:
        raise ValueError("symbol is required")
    if int(candidate.research_rank) < 1:
        raise ValueError("research_rank must be >= 1")

    return NextDayCandidateEvidence(
        canonical_date=_canonical_date(candidate.canonical_date),
        symbol=symbol,
        research_rank=int(candidate.research_rank),
        evidence_families=_families(candidate.evidence_families),
        data_ready=bool(candidate.data_ready),
        freshness_valid=bool(candidate.freshness_valid),
        security_lock=bool(candidate.security_lock),
        universe_comparable=bool(candidate.universe_comparable),
        research_valid=bool(candidate.research_valid),
        hard_contradictions=tuple(
            str(item) for item in candidate.hard_contradictions if str(item)
        ),
        soft_contradictions=tuple(
            str(item) for item in candidate.soft_contradictions if str(item)
        ),
        extension=ExtensionState(candidate.extension),
        rebound=ReboundState(candidate.rebound),
        single_factor_domination=bool(candidate.single_factor_domination),
        readiness_rank=max(0, int(candidate.readiness_rank)),
        migration_rank=max(0, int(candidate.migration_rank)),
        relative_strength_rank=max(0, int(candidate.relative_strength_rank)),
        explanation=str(candidate.explanation or ""),
        warnings=tuple(str(item) for item in candidate.warnings if str(item)),
        next_action=str(candidate.next_action or "Tek Hisse İnceleme"),
    )


def _hard_exclusion_reason(candidate: NextDayCandidateEvidence) -> str | None:
    if not candidate.data_ready:
        return "DATA_NOT_READY"
    if not candidate.freshness_valid:
        return "STALE_DATA"
    if candidate.security_lock:
        return "SECURITY_LOCK"
    if not candidate.universe_comparable:
        return "UNIVERSE_NOT_COMPARABLE"
    if not candidate.research_valid:
        return "RESEARCH_INVALID"
    if candidate.hard_contradictions:
        return "HARD_CONTRADICTION"
    if candidate.rebound is ReboundState.TRAP:
        return "REBOUND_TRAP"
    return None


def _breadth(candidate: NextDayCandidateEvidence) -> int:
    return len(candidate.evidence_families)


def _has_structural(candidate: NextDayCandidateEvidence) -> bool:
    return bool(set(candidate.evidence_families) & STRUCTURAL_FAMILIES)


def _has_timing(candidate: NextDayCandidateEvidence) -> bool:
    return bool(set(candidate.evidence_families) & TIMING_FAMILIES)


def _primary_eligible(candidate: NextDayCandidateEvidence) -> bool:
    return (
        _hard_exclusion_reason(candidate) is None
        and _breadth(candidate) >= 3
        and _has_structural(candidate)
        and _has_timing(candidate)
        and candidate.extension is not ExtensionState.SEVERE
        and candidate.rebound is ReboundState.NO
        and not candidate.single_factor_domination
    )


def _reserve_eligible(candidate: NextDayCandidateEvidence) -> bool:
    return (
        _hard_exclusion_reason(candidate) is None
        and _breadth(candidate) >= 2
    )


def _extension_rank(candidate: NextDayCandidateEvidence) -> int:
    return {
        ExtensionState.CLEAN: 0,
        ExtensionState.MILD: 1,
        ExtensionState.SEVERE: 2,
    }[candidate.extension]


def _primary_sort_key(candidate: NextDayCandidateEvidence) -> tuple[object, ...]:
    """Frozen lexicographic order; no weighted score."""

    return (
        len(candidate.soft_contradictions),
        -_breadth(candidate),
        candidate.readiness_rank,
        _extension_rank(candidate),
        candidate.migration_rank,
        candidate.relative_strength_rank,
        candidate.research_rank,
        candidate.symbol,
    )


def _reserve_sort_key(candidate: NextDayCandidateEvidence) -> tuple[object, ...]:
    # Reserve uses the same deterministic evidence-quality order.
    return _primary_sort_key(candidate)


def _contradiction_state(candidate: NextDayCandidateEvidence) -> str:
    if candidate.hard_contradictions:
        return "HARD"
    if candidate.soft_contradictions:
        return "SOFT"
    return "NONE"


def _evaluation_identity(candidate: NextDayCandidateEvidence) -> str:
    return f"{STRATEGY_ID}|{candidate.canonical_date}|{candidate.symbol}"


def _reason(candidate: NextDayCandidateEvidence, role: NextDayRole) -> str:
    if candidate.explanation:
        return candidate.explanation

    families = ", ".join(candidate.evidence_families) or "no evidence family"
    if role is NextDayRole.PRIMARY:
        return (
            f"{families}; independent evidence breadth and T+1 readiness "
            "meet frozen V1 Primary criteria."
        )
    if role is NextDayRole.RESERVE:
        cautions: list[str] = []
        if candidate.soft_contradictions:
            cautions.append("soft contradiction")
        if candidate.extension is not ExtensionState.CLEAN:
            cautions.append(f"{candidate.extension.value.lower()} extension")
        if candidate.rebound is ReboundState.CAUTION:
            cautions.append("rebound caution")
        if candidate.single_factor_domination:
            cautions.append("single-factor domination")
        suffix = ", ".join(cautions) if cautions else "developing evidence breadth"
        return f"{families}; Reserve due to {suffix}."
    return "Excluded by frozen V1 eligibility contract."


def _item(
    candidate: NextDayCandidateEvidence,
    role: NextDayRole,
    order: int,
    exclusion_reason: str | None = None,
) -> NextDaySelectionItem:
    return NextDaySelectionItem(
        canonical_date=candidate.canonical_date,
        symbol=candidate.symbol,
        role=role,
        selection_order=order,
        research_rank=candidate.research_rank,
        evidence_families=candidate.evidence_families,
        contradiction_state=_contradiction_state(candidate),
        extension_state=candidate.extension,
        rebound_state=candidate.rebound,
        exclusion_reason=exclusion_reason,
        explanation=_reason(candidate, role),
        warnings=candidate.warnings,
        next_action=candidate.next_action,
        evaluation_identity=_evaluation_identity(candidate),
    )


def select_next_day_candidates(
    candidates: Iterable[NextDayCandidateEvidence],
    *,
    primary_limit: int = MAX_PRIMARY,
    reserve_limit: int = MAX_RESERVE,
) -> NextDaySelectionResult:
    """Build the frozen V1 read model from normalized canonical evidence.

    - no scanner
    - no persistence
    - no weighted score
    - no AL/SAT authority
    - no forced fill
    """

    if not 1 <= int(primary_limit) <= MAX_PRIMARY:
        raise ValueError(f"primary_limit must be 1..{MAX_PRIMARY}")
    if not 1 <= int(reserve_limit) <= MAX_RESERVE:
        raise ValueError(f"reserve_limit must be 1..{MAX_RESERVE}")

    materialized = tuple(_normalized(item) for item in candidates)
    if not materialized:
        raise ValueError("at least one canonical candidate is required")

    canonical_dates = {item.canonical_date for item in materialized}
    if len(canonical_dates) != 1:
        raise ValueError("all candidates must share one canonical_date")
    canonical_date = next(iter(canonical_dates))

    symbols = [item.symbol for item in materialized]
    if len(symbols) != len(set(symbols)):
        raise ValueError("duplicate candidate symbol")

    hard_excluded: list[tuple[NextDayCandidateEvidence, str]] = []
    primary_pool: list[NextDayCandidateEvidence] = []
    reserve_pool: list[NextDayCandidateEvidence] = []

    for candidate in materialized:
        hard_reason = _hard_exclusion_reason(candidate)
        if hard_reason is not None:
            hard_excluded.append((candidate, hard_reason))
            continue

        if _primary_eligible(candidate):
            primary_pool.append(candidate)
        elif _reserve_eligible(candidate):
            reserve_pool.append(candidate)
        else:
            reason = (
                "SINGLE_FACTOR_DOMINATION"
                if candidate.single_factor_domination and _breadth(candidate) < 2
                else "INSUFFICIENT_EVIDENCE_BREADTH"
            )
            hard_excluded.append((candidate, reason))

    ordered_primary_pool = sorted(primary_pool, key=_primary_sort_key)
    selected_primary = ordered_primary_pool[: int(primary_limit)]

    # Primary-like overflow remains eligible as near-Primary Reserve.
    reserve_pool.extend(ordered_primary_pool[int(primary_limit) :])
    ordered_reserve_pool = sorted(reserve_pool, key=_reserve_sort_key)
    selected_reserve = ordered_reserve_pool[: int(reserve_limit)]

    selected_symbols = {
        item.symbol for item in (*selected_primary, *selected_reserve)
    }

    capacity_excluded = [
        (candidate, "NOT_SELECTED_CAPACITY")
        for candidate in ordered_reserve_pool[int(reserve_limit) :]
        if candidate.symbol not in selected_symbols
    ]

    excluded_rows = hard_excluded + capacity_excluded
    excluded_rows.sort(key=lambda pair: (pair[0].research_rank, pair[0].symbol))

    return NextDaySelectionResult(
        canonical_date=canonical_date,
        primary=tuple(
            _item(candidate, NextDayRole.PRIMARY, order)
            for order, candidate in enumerate(selected_primary, start=1)
        ),
        reserve=tuple(
            _item(candidate, NextDayRole.RESERVE, order)
            for order, candidate in enumerate(selected_reserve, start=1)
        ),
        excluded=tuple(
            _item(candidate, NextDayRole.EXCLUDED, order, reason)
            for order, (candidate, reason) in enumerate(excluded_rows, start=1)
        ),
    )
