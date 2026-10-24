from __future__ import annotations

from dataclasses import replace

import pytest

from app.analysis.next_day_outcome import (
    NextDayCandidateOutcome,
    NextDayOutcomeResult,
    NextDayTierOutcomeSummary,
    OUTCOME_CONTRACT_ID,
)
from app.analysis.next_day_selection import NextDayRole, STRATEGY_ID
from app.analysis.next_day_walk_forward import (
    REQUIRED_VALID_SESSIONS,
    WALK_FORWARD_CONTRACT_ID,
    build_walk_forward_readiness,
)


def tier(role: NextDayRole, rows: tuple[NextDayCandidateOutcome, ...]) -> NextDayTierOutcomeSummary:
    selected = tuple(row for row in rows if row.role is role)
    hits = sum(row.status == "HIT" for row in selected)
    misses = sum(row.status == "MISS" for row in selected)
    relatives = [float(row.relative_return) for row in selected if row.relative_return is not None]
    mfes = [float(row.mfe) for row in selected if row.mfe is not None]
    maes = [float(row.mae) for row in selected if row.mae is not None]
    return NextDayTierOutcomeSummary(
        role=role,
        candidate_count=len(selected),
        evaluated_count=len(selected),
        pending_count=0,
        hit_count=hits,
        miss_count=misses,
        hit_rate=(hits / len(selected)) if selected else None,
        median_relative_return=(sorted(relatives)[len(relatives)//2] if relatives else None),
        average_relative_return=(sum(relatives) / len(relatives)) if relatives else None,
        median_mfe=(sorted(mfes)[len(mfes)//2] if mfes else None),
        median_mae=(sorted(maes)[len(maes)//2] if maes else None),
        basket_success=None,
    )


def row(date: str, symbol: str, role: NextDayRole, order: int, ret: float, benchmark: float = 0.01):
    relative = ret - benchmark
    return NextDayCandidateOutcome(
        evaluation_identity=f"{STRATEGY_ID}|{date}|{symbol}",
        canonical_date=date,
        t1_date="2026-09-01",
        symbol=symbol,
        role=role,
        selection_order=order,
        t_close=100.0,
        t1_open=100.0,
        t1_high=106.0,
        t1_low=97.0,
        t1_close=100.0 * (1.0 + ret),
        close_to_close_return=ret,
        relative_return=relative,
        mfe=0.06,
        mae=-0.03,
        benchmark_return=benchmark,
        status="HIT" if ret > benchmark else "MISS",
    )


def session(index: int, *, primary_count: int = 2, reserve_count: int = 2) -> NextDayOutcomeResult:
    date = f"2026-09-{index + 1:02d}"
    rows = []
    for i in range(primary_count):
        ret = 0.04 if i % 2 == 0 else -0.01
        rows.append(row(date, f"P{index:02d}{i}", NextDayRole.PRIMARY, i + 1, ret))
    for i in range(reserve_count):
        ret = 0.03 if i % 2 == 0 else -0.02
        rows.append(row(date, f"R{index:02d}{i}", NextDayRole.RESERVE, i + 1, ret))
    rows_t = tuple(rows)
    p = tier(NextDayRole.PRIMARY, rows_t)
    r = tier(NextDayRole.RESERVE, rows_t)
    spread = None
    if p.median_relative_return is not None and r.median_relative_return is not None:
        spread = p.median_relative_return - r.median_relative_return
    return NextDayOutcomeResult(
        contract_id=OUTCOME_CONTRACT_ID,
        strategy_id=STRATEGY_ID,
        canonical_date=date,
        t1_date="2026-09-01",
        selection_digest=(f"{index + 1:064x}")[-64:],
        benchmark_return=0.01,
        outcomes=rows_t,
        primary=p,
        reserve=r,
        primary_reserve_relative_spread=spread,
    )


def test_collecting_below_20_valid_sessions():
    result = build_walk_forward_readiness(session(i) for i in range(19))
    assert result.contract_id == WALK_FORWARD_CONTRACT_ID
    assert result.required_valid_sessions == REQUIRED_VALID_SESSIONS
    assert result.valid_session_count == 19
    assert result.status == "COLLECTING"
    assert result.ready_for_review is False


def test_ready_at_20_valid_sessions():
    result = build_walk_forward_readiness(session(i) for i in range(20))
    assert result.valid_session_count == 20
    assert result.status == "READY_FOR_REVIEW"
    assert result.ready_for_review is True


def test_no_forced_fill_sparse_or_empty_session_can_still_be_valid():
    sparse = session(0, primary_count=1, reserve_count=0)
    empty = session(1, primary_count=0, reserve_count=0)
    result = build_walk_forward_readiness((sparse, empty), required_valid_sessions=2)
    assert result.ready_for_review is True
    assert result.valid_session_count == 2
    assert result.primary.observation_count == 1
    assert result.reserve.observation_count == 0


def test_pending_outcome_excludes_session_fail_closed():
    s = session(0)
    first = replace(s.outcomes[0], status="PENDING", close_to_close_return=None, relative_return=None, mfe=None, mae=None)
    rows = (first,) + s.outcomes[1:]
    s = replace(s, outcomes=rows)
    result = build_walk_forward_readiness((s,))
    assert result.valid_session_count == 0
    assert result.invalid_session_count == 1
    assert result.issues[0].reason == "PENDING_OR_INVALID_OUTCOME"


def test_duplicate_canonical_date_is_not_double_counted():
    s = session(0)
    duplicate = replace(s, selection_digest="f" * 64)
    result = build_walk_forward_readiness((s, duplicate), required_valid_sessions=1)
    assert result.valid_session_count == 0
    assert result.invalid_session_count == 2
    assert {issue.reason for issue in result.issues} == {"DUPLICATE_CANONICAL_DATE"}


def test_invalid_digest_excludes_session():
    s = replace(session(0), selection_digest="bad")
    result = build_walk_forward_readiness((s,))
    assert result.issues[0].reason == "SELECTION_DIGEST_INVALID"


def test_contract_or_strategy_mismatch_excludes_session():
    a = replace(session(0), contract_id="OTHER")
    b = replace(session(1), strategy_id="OTHER")
    result = build_walk_forward_readiness((a, b))
    assert {issue.reason for issue in result.issues} == {"OUTCOME_CONTRACT_MISMATCH", "STRATEGY_MISMATCH"}


def test_aggregate_metrics_keep_primary_and_reserve_separate():
    result = build_walk_forward_readiness((session(0),))
    assert result.primary.observation_count == 2
    assert result.reserve.observation_count == 2
    assert result.primary.hit_rate == pytest.approx(0.5)
    assert result.reserve.hit_rate == pytest.approx(0.5)
    assert result.primary.average_return == pytest.approx(0.015)
    assert result.reserve.average_return == pytest.approx(0.005)
    assert result.primary.average_relative_return == pytest.approx(0.005)
    assert result.reserve.average_relative_return == pytest.approx(-0.005)
    assert result.primary_reserve_median_relative_spread is not None


def test_three_of_five_counter_only_uses_full_primary_five_sessions():
    full = session(0, primary_count=5, reserve_count=0)
    sparse = session(1, primary_count=3, reserve_count=0)
    result = build_walk_forward_readiness((full, sparse))
    assert result.full_primary_five_session_count == 1
    assert result.primary_three_of_five_hit_session_count == 1


def test_primary_daily_distribution_counters_are_explicit():
    result = build_walk_forward_readiness((session(0),))
    assert result.primary_average_above_benchmark_session_count == 1
    assert result.primary_average_negative_return_session_count == 0


def test_order_is_deterministic_by_canonical_date():
    sessions = [session(2), session(0), session(1)]
    result = build_walk_forward_readiness(sessions)
    assert result.valid_canonical_dates == ("2026-09-01", "2026-09-02", "2026-09-03")


def test_no_tuning_or_authority_is_created():
    result = build_walk_forward_readiness((session(0),))
    assert result.p0_only_changes is True
    assert result.outcome_tuning is False
    assert result.new_score is False
    assert result.new_store is False
    assert result.new_scanner is False
    assert result.al_sat_authority is False
    assert not hasattr(result, "threshold_adjustment")
    assert not hasattr(result, "buy")
    assert not hasattr(result, "sell")
