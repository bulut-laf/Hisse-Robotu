from __future__ import annotations

from dataclasses import replace

import pytest

from app.analysis.next_day_outcome import (
    OUTCOME_CONTRACT_ID,
    T1Bar,
    evaluate_next_day_selection,
    selection_digest,
)
from app.analysis.next_day_selection import (
    NextDayCandidateEvidence,
    select_next_day_candidates,
)


def c(
    symbol: str,
    families: tuple[str, ...],
    *,
    rank: int,
) -> NextDayCandidateEvidence:
    return NextDayCandidateEvidence(
        canonical_date="2026-08-28",
        symbol=symbol,
        research_rank=rank,
        evidence_families=families,
        readiness_rank=rank,
        migration_rank=rank,
        relative_strength_rank=rank,
    )


def selection():
    return select_next_day_candidates(
        (
            c("AAA", ("F1", "F3", "F4"), rank=1),
            c("BBB", ("F1", "F2", "F3", "F4"), rank=2),
            c("CCC", ("F2", "F4"), rank=3),
            c("DDD", ("F1", "F5"), rank=4),
        )
    )


def universe():
    t_close = {
        "AAA": 100,
        "BBB": 100,
        "CCC": 100,
        "DDD": 100,
        "EEE": 100,
    }
    t1 = {
        "AAA": T1Bar(101, 106, 99, 104),   # +4
        "BBB": T1Bar(100, 102, 97, 99),    # -1
        "CCC": T1Bar(100, 105, 98, 103),   # +3
        "DDD": T1Bar(100, 101, 95, 98),    # -2
        "EEE": T1Bar(100, 103, 99, 101),   # +1
    }
    return t_close, t1


def test_selection_digest_is_stable():
    s = selection()
    assert selection_digest(s) == selection_digest(s)
    assert len(selection_digest(s)) == 64


def test_digest_detects_later_selection_mutation():
    s = selection()
    digest = selection_digest(s)
    changed = replace(s, primary=tuple(reversed(s.primary)))
    assert selection_digest(changed) != digest


def test_main_benchmark_is_canonical_universe_median():
    s = selection()
    t_close, t1 = universe()
    result = evaluate_next_day_selection(
        s,
        t1_date="2026-08-31",
        t_close_by_symbol=t_close,
        t1_bars_by_symbol=t1,
        universe_t_close_by_symbol=t_close,
        universe_t1_bars_by_symbol=t1,
    )
    assert result.contract_id == OUTCOME_CONTRACT_ID
    assert result.benchmark_return == pytest.approx(0.01)


def test_candidate_hit_is_strictly_above_benchmark():
    s = selection()
    t_close, t1 = universe()
    result = evaluate_next_day_selection(
        s,
        t1_date="2026-08-31",
        t_close_by_symbol=t_close,
        t1_bars_by_symbol=t1,
        universe_t_close_by_symbol=t_close,
        universe_t1_bars_by_symbol=t1,
    )
    by_symbol = {row.symbol: row for row in result.outcomes}
    assert by_symbol["AAA"].status == "HIT"
    assert by_symbol["BBB"].status == "MISS"
    assert by_symbol["CCC"].status == "HIT"
    assert by_symbol["DDD"].status == "MISS"


def test_mfe_mae_are_measured_from_t_close_not_trade_entry():
    s = selection()
    t_close, t1 = universe()
    result = evaluate_next_day_selection(
        s,
        t1_date="2026-08-31",
        t_close_by_symbol=t_close,
        t1_bars_by_symbol=t1,
        universe_t_close_by_symbol=t_close,
        universe_t1_bars_by_symbol=t1,
    )
    aaa = next(row for row in result.outcomes if row.symbol == "AAA")
    assert aaa.close_to_close_return == pytest.approx(0.04)
    assert aaa.relative_return == pytest.approx(0.03)
    assert aaa.mfe == pytest.approx(0.06)
    assert aaa.mae == pytest.approx(-0.01)


def test_primary_and_reserve_are_measured_separately():
    s = selection()
    t_close, t1 = universe()
    result = evaluate_next_day_selection(
        s,
        t1_date="2026-08-31",
        t_close_by_symbol=t_close,
        t1_bars_by_symbol=t1,
        universe_t_close_by_symbol=t_close,
        universe_t1_bars_by_symbol=t1,
    )
    assert result.primary.candidate_count == 2
    assert result.reserve.candidate_count == 2
    assert result.primary.evaluated_count == 2
    assert result.reserve.evaluated_count == 2
    assert result.primary.hit_count == 1
    assert result.reserve.hit_count == 1
    assert result.primary_reserve_relative_spread is not None


def test_missing_candidate_bar_is_pending_not_fabricated():
    s = selection()
    t_close, t1 = universe()
    candidate_bars = dict(t1)
    candidate_bars.pop("AAA")

    result = evaluate_next_day_selection(
        s,
        t1_date="2026-08-31",
        t_close_by_symbol=t_close,
        t1_bars_by_symbol=candidate_bars,
        universe_t_close_by_symbol=t_close,
        universe_t1_bars_by_symbol=t1,
    )
    aaa = next(row for row in result.outcomes if row.symbol == "AAA")
    assert aaa.status == "PENDING"
    assert aaa.close_to_close_return is None
    assert aaa.missing_reason == "T1_BAR_MISSING_OR_INVALID"


def test_invalid_ohlc_is_pending():
    s = selection()
    t_close, t1 = universe()
    candidate_bars = dict(t1)
    candidate_bars["AAA"] = {"open": 100, "high": 99, "low": 98, "close": 101}

    result = evaluate_next_day_selection(
        s,
        t1_date="2026-08-31",
        t_close_by_symbol=t_close,
        t1_bars_by_symbol=candidate_bars,
        universe_t_close_by_symbol=t_close,
        universe_t1_bars_by_symbol=t1,
    )
    aaa = next(row for row in result.outcomes if row.symbol == "AAA")
    assert aaa.status == "PENDING"


def test_digest_guard_rejects_changed_historical_selection():
    s = selection()
    t_close, t1 = universe()
    with pytest.raises(ValueError, match="digest mismatch"):
        evaluate_next_day_selection(
            s,
            t1_date="2026-08-31",
            t_close_by_symbol=t_close,
            t1_bars_by_symbol=t1,
            universe_t_close_by_symbol=t_close,
            universe_t1_bars_by_symbol=t1,
            expected_selection_digest="0" * 64,
        )


def test_no_benchmark_data_fails_closed():
    s = selection()
    t_close, t1 = universe()
    with pytest.raises(ValueError, match="benchmark"):
        evaluate_next_day_selection(
            s,
            t1_date="2026-08-31",
            t_close_by_symbol=t_close,
            t1_bars_by_symbol=t1,
            universe_t_close_by_symbol={},
            universe_t1_bars_by_symbol={},
        )


def test_no_trade_authority_fields_are_created():
    s = selection()
    t_close, t1 = universe()
    result = evaluate_next_day_selection(
        s,
        t1_date="2026-08-31",
        t_close_by_symbol=t_close,
        t1_bars_by_symbol=t1,
        universe_t_close_by_symbol=t_close,
        universe_t1_bars_by_symbol=t1,
    )
    assert not hasattr(result, "buy")
    assert not hasattr(result, "sell")
    assert not hasattr(result, "position_size")
