from backend.app.analysis.ranking_memory import RankObservation
from backend.app.analysis.ranking_validation import (
    build_validation_outcomes,
    evaluate_entry_outcomes,
    summarize_outcomes,
)


def obs(day, rank, symbol="AAA", size=500, source="BIST", profile="default"):
    return RankObservation(
        as_of=day,
        symbol=symbol,
        rank=rank,
        ranked_universe_size=size,
        universe_source=source,
        profile_name=profile,
    )


def history():
    ranks = [400, 300, 220, 150, 110, 80, 70, 60, 55, 48, 42]
    days = [f"2026-08-{day:02d}" for day in range(1, 12)]
    return tuple(obs(day, rank) for day, rank in zip(days, ranks))


def test_outcomes_cover_1_3_5_10_sessions():
    outcomes = evaluate_entry_outcomes(
        history(),
        symbol="AAA",
        entry_as_of="2026-08-01",
    )
    assert [item.horizon_sessions for item in outcomes] == [1, 3, 5, 10]
    assert [item.outcome_rank for item in outcomes] == [300, 150, 80, 42]


def test_top_zone_conversion_is_measured_not_used_as_signal():
    outcomes = evaluate_entry_outcomes(
        history(),
        symbol="AAA",
        entry_as_of="2026-08-01",
    )
    by_horizon = {item.horizon_sessions: item for item in outcomes}
    assert by_horizon[5].reached_top100 is True
    assert by_horizon[10].reached_top50 is True
    assert not hasattr(by_horizon[10], "decision")
    assert not hasattr(by_horizon[10], "signal")


def test_normalized_gain_handles_universe_size_change():
    items = (
        obs("2026-08-01", 400, size=600),
        obs("2026-08-02", 200, size=500),
    )
    result = evaluate_entry_outcomes(
        items,
        symbol="AAA",
        entry_as_of="2026-08-01",
    )[0]
    assert result.available is True
    assert result.rank_gain == 200
    assert result.normalized_gain is not None
    assert result.normalized_gain > 0


def test_source_change_marks_outcome_unavailable():
    items = (
        obs("2026-08-01", 400, source="OLD"),
        obs("2026-08-02", 100, source="BIST"),
    )
    result = evaluate_entry_outcomes(
        items,
        symbol="AAA",
        entry_as_of="2026-08-01",
    )[0]
    assert result.available is False
    assert result.rank_gain is None


def test_summary_reports_conversion_retention_and_unavailable_rate():
    all_outcomes = build_validation_outcomes(
        history(),
        entries=(("AAA", "2026-08-01"),),
    )
    summary = summarize_outcomes(all_outcomes, horizon_sessions=5)
    assert summary.total_entries == 1
    assert summary.evaluated_outcomes == 1
    assert summary.top100_conversion_rate == 1.0
    assert summary.positive_rank_gain_rate == 1.0
    assert summary.retention_rate == 1.0
    assert summary.unavailable_rate == 0.0


def test_future_horizon_stays_pending_without_fake_result():
    outcomes = evaluate_entry_outcomes(
        history()[:4],
        symbol="AAA",
        entry_as_of="2026-08-01",
    )
    ten = next(item for item in outcomes if item.horizon_sessions == 10)
    assert ten.available is False
    assert ten.outcome_rank is None
    assert ten.rank_gain is None
