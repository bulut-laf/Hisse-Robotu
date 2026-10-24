from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from statistics import median
from typing import Iterable

from .next_day_outcome import (
    OUTCOME_CONTRACT_ID,
    NextDayCandidateOutcome,
    NextDayOutcomeResult,
)
from .next_day_selection import NextDayRole, STRATEGY_ID


WALK_FORWARD_CONTRACT_ID = "NEXT_DAY_20_SESSION_WALK_FORWARD_READINESS_V1"
REQUIRED_VALID_SESSIONS = 20


@dataclass(frozen=True)
class WalkForwardSessionIssue:
    canonical_date: str
    t1_date: str
    selection_digest: str
    reason: str


@dataclass(frozen=True)
class WalkForwardTierAggregate:
    role: NextDayRole
    observation_count: int
    hit_count: int
    miss_count: int
    hit_rate: float | None
    average_return: float | None
    median_return: float | None
    average_relative_return: float | None
    median_relative_return: float | None
    median_mfe: float | None
    median_mae: float | None


@dataclass(frozen=True)
class NextDayWalkForwardReadiness:
    contract_id: str
    strategy_id: str
    required_valid_sessions: int
    input_session_count: int
    valid_session_count: int
    invalid_session_count: int
    valid_canonical_dates: tuple[str, ...]
    issues: tuple[WalkForwardSessionIssue, ...]
    status: str  # COLLECTING / READY_FOR_REVIEW
    ready_for_review: bool
    primary: WalkForwardTierAggregate
    reserve: WalkForwardTierAggregate
    primary_reserve_median_relative_spread: float | None
    full_primary_five_session_count: int
    primary_three_of_five_hit_session_count: int
    primary_average_above_benchmark_session_count: int
    primary_average_negative_return_session_count: int
    p0_only_changes: bool
    outcome_tuning: bool
    new_score: bool
    new_store: bool
    new_scanner: bool
    al_sat_authority: bool


def _valid_digest(value: object) -> bool:
    text = str(value or "").strip().lower()
    return len(text) == 64 and all(ch in "0123456789abcdef" for ch in text)


def _finite(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if isfinite(result) else None


def _issue(session: NextDayOutcomeResult, reason: str) -> WalkForwardSessionIssue:
    return WalkForwardSessionIssue(
        canonical_date=str(getattr(session, "canonical_date", "") or ""),
        t1_date=str(getattr(session, "t1_date", "") or ""),
        selection_digest=str(getattr(session, "selection_digest", "") or ""),
        reason=reason,
    )


def _session_reason(session: NextDayOutcomeResult) -> str | None:
    if session.contract_id != OUTCOME_CONTRACT_ID:
        return "OUTCOME_CONTRACT_MISMATCH"
    if session.strategy_id != STRATEGY_ID:
        return "STRATEGY_MISMATCH"
    if not str(session.canonical_date or "").strip():
        return "CANONICAL_DATE_MISSING"
    if not str(session.t1_date or "").strip():
        return "T1_DATE_MISSING"
    if not _valid_digest(session.selection_digest):
        return "SELECTION_DIGEST_INVALID"
    if _finite(session.benchmark_return) is None:
        return "BENCHMARK_INVALID"

    rows = tuple(session.outcomes)
    expected_count = int(session.primary.candidate_count) + int(session.reserve.candidate_count)
    if len(rows) != expected_count:
        return "CANDIDATE_COUNT_MISMATCH"

    identities: set[str] = set()
    symbols: set[str] = set()
    primary_count = reserve_count = 0
    primary_hits = reserve_hits = 0
    primary_misses = reserve_misses = 0

    for row in rows:
        if row.canonical_date != session.canonical_date or row.t1_date != session.t1_date:
            return "ROW_SESSION_IDENTITY_MISMATCH"
        if row.role not in {NextDayRole.PRIMARY, NextDayRole.RESERVE}:
            return "ROW_ROLE_INVALID"
        if row.status not in {"HIT", "MISS"}:
            return "PENDING_OR_INVALID_OUTCOME"
        if (
            _finite(row.close_to_close_return) is None
            or _finite(row.relative_return) is None
            or _finite(row.mfe) is None
            or _finite(row.mae) is None
            or _finite(row.benchmark_return) is None
        ):
            return "OUTCOME_METRIC_MISSING_OR_INVALID"
        if abs(float(row.benchmark_return) - float(session.benchmark_return)) > 1e-12:
            return "BENCHMARK_MISMATCH"
        if not str(row.evaluation_identity or "").strip():
            return "EVALUATION_IDENTITY_MISSING"
        if row.evaluation_identity in identities:
            return "DUPLICATE_EVALUATION_IDENTITY"
        identities.add(row.evaluation_identity)
        symbol = str(row.symbol or "").strip().upper()
        if not symbol:
            return "SYMBOL_MISSING"
        if symbol in symbols:
            return "DUPLICATE_SYMBOL"
        symbols.add(symbol)

        if row.role is NextDayRole.PRIMARY:
            primary_count += 1
            primary_hits += row.status == "HIT"
            primary_misses += row.status == "MISS"
        else:
            reserve_count += 1
            reserve_hits += row.status == "HIT"
            reserve_misses += row.status == "MISS"

    if primary_count != int(session.primary.candidate_count):
        return "PRIMARY_COUNT_MISMATCH"
    if reserve_count != int(session.reserve.candidate_count):
        return "RESERVE_COUNT_MISMATCH"
    if int(session.primary.evaluated_count) != primary_count or int(session.primary.pending_count) != 0:
        return "PRIMARY_SUMMARY_NOT_FULLY_EVALUATED"
    if int(session.reserve.evaluated_count) != reserve_count or int(session.reserve.pending_count) != 0:
        return "RESERVE_SUMMARY_NOT_FULLY_EVALUATED"
    if int(session.primary.hit_count) != primary_hits or int(session.primary.miss_count) != primary_misses:
        return "PRIMARY_HIT_MISS_MISMATCH"
    if int(session.reserve.hit_count) != reserve_hits or int(session.reserve.miss_count) != reserve_misses:
        return "RESERVE_HIT_MISS_MISMATCH"
    return None


def _aggregate(role: NextDayRole, rows: Iterable[NextDayCandidateOutcome]) -> WalkForwardTierAggregate:
    materialized = tuple(row for row in rows if row.role is role)
    if not materialized:
        return WalkForwardTierAggregate(
            role=role,
            observation_count=0,
            hit_count=0,
            miss_count=0,
            hit_rate=None,
            average_return=None,
            median_return=None,
            average_relative_return=None,
            median_relative_return=None,
            median_mfe=None,
            median_mae=None,
        )

    returns = [float(row.close_to_close_return) for row in materialized if row.close_to_close_return is not None]
    relatives = [float(row.relative_return) for row in materialized if row.relative_return is not None]
    mfes = [float(row.mfe) for row in materialized if row.mfe is not None]
    maes = [float(row.mae) for row in materialized if row.mae is not None]
    hits = sum(row.status == "HIT" for row in materialized)
    misses = sum(row.status == "MISS" for row in materialized)

    return WalkForwardTierAggregate(
        role=role,
        observation_count=len(materialized),
        hit_count=int(hits),
        miss_count=int(misses),
        hit_rate=float(hits / len(materialized)),
        average_return=float(sum(returns) / len(returns)),
        median_return=float(median(returns)),
        average_relative_return=float(sum(relatives) / len(relatives)),
        median_relative_return=float(median(relatives)),
        median_mfe=float(median(mfes)),
        median_mae=float(median(maes)),
    )


def build_walk_forward_readiness(
    sessions: Iterable[NextDayOutcomeResult],
    *,
    required_valid_sessions: int = REQUIRED_VALID_SESSIONS,
) -> NextDayWalkForwardReadiness:
    """Aggregate frozen T+1 outcomes without tuning, scoring, persistence, or AL/SAT authority.

    A valid session may legitimately contain fewer than five Primary/Reserve candidates because
    the frozen strategy has NO FORCED FILL. Readiness is therefore based on valid session count,
    while actual observation counts are reported separately.
    """

    required = int(required_valid_sessions)
    if required < 1:
        raise ValueError("required_valid_sessions must be >= 1")

    materialized = tuple(sessions)
    by_date: dict[str, list[NextDayOutcomeResult]] = {}
    for session in materialized:
        by_date.setdefault(str(session.canonical_date or ""), []).append(session)

    issues: list[WalkForwardSessionIssue] = []
    valid: list[NextDayOutcomeResult] = []

    for canonical_date in sorted(by_date):
        group = by_date[canonical_date]
        if len(group) != 1:
            for session in group:
                issues.append(_issue(session, "DUPLICATE_CANONICAL_DATE"))
            continue
        session = group[0]
        reason = _session_reason(session)
        if reason is not None:
            issues.append(_issue(session, reason))
            continue
        valid.append(session)

    valid.sort(key=lambda x: (x.canonical_date, x.t1_date, x.selection_digest))
    all_rows = tuple(row for session in valid for row in session.outcomes)
    primary = _aggregate(NextDayRole.PRIMARY, all_rows)
    reserve = _aggregate(NextDayRole.RESERVE, all_rows)

    if (
        primary.median_relative_return is not None
        and reserve.median_relative_return is not None
    ):
        spread = primary.median_relative_return - reserve.median_relative_return
    else:
        spread = None

    full_primary_five = 0
    primary_three_of_five = 0
    primary_above_benchmark = 0
    primary_negative_return = 0

    for session in valid:
        primary_rows = tuple(row for row in session.outcomes if row.role is NextDayRole.PRIMARY)
        if len(primary_rows) == 5:
            full_primary_five += 1
            if sum(row.status == "HIT" for row in primary_rows) >= 3:
                primary_three_of_five += 1
        if primary_rows:
            avg_relative = sum(float(row.relative_return) for row in primary_rows) / len(primary_rows)
            avg_return = sum(float(row.close_to_close_return) for row in primary_rows) / len(primary_rows)
            if avg_relative > 0:
                primary_above_benchmark += 1
            if avg_return < 0:
                primary_negative_return += 1

    ready = len(valid) >= required
    return NextDayWalkForwardReadiness(
        contract_id=WALK_FORWARD_CONTRACT_ID,
        strategy_id=STRATEGY_ID,
        required_valid_sessions=required,
        input_session_count=len(materialized),
        valid_session_count=len(valid),
        invalid_session_count=len(materialized) - len(valid),
        valid_canonical_dates=tuple(session.canonical_date for session in valid),
        issues=tuple(sorted(issues, key=lambda x: (x.canonical_date, x.t1_date, x.reason, x.selection_digest))),
        status="READY_FOR_REVIEW" if ready else "COLLECTING",
        ready_for_review=ready,
        primary=primary,
        reserve=reserve,
        primary_reserve_median_relative_spread=spread,
        full_primary_five_session_count=full_primary_five,
        primary_three_of_five_hit_session_count=primary_three_of_five,
        primary_average_above_benchmark_session_count=primary_above_benchmark,
        primary_average_negative_return_session_count=primary_negative_return,
        p0_only_changes=True,
        outcome_tuning=False,
        new_score=False,
        new_store=False,
        new_scanner=False,
        al_sat_authority=False,
    )
