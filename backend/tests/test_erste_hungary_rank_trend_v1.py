from backend.app.funds.international.erste_hungary_rank_trend import (
    build_rank_trend_evidence,
)


def test_improving_rank_is_positive_delta():
    evidence = build_rank_trend_evidence(
        isin="LU0000000001",
        category_normalized="EQUITY",
        rank_date_1="2026-09-24",
        rank_date_2="2026-09-25",
        rank_1=50,
        rank_2=30,
    )

    assert evidence.rank_delta == 20
    assert evidence.direction == "IMPROVING"
    assert evidence.strength == "STRONG"
    assert evidence.trade_authority == "NONE"


def test_weakening_rank_is_negative_delta():
    evidence = build_rank_trend_evidence(
        isin="LU0000000002",
        category_normalized="EQUITY",
        rank_date_1="2026-09-24",
        rank_date_2="2026-09-25",
        rank_1=20,
        rank_2=35,
    )

    assert evidence.rank_delta == -15
    assert evidence.direction == "WEAKENING"
    assert evidence.strength == "MODERATE"


def test_unchanged_rank_is_stable():
    evidence = build_rank_trend_evidence(
        isin="LU0000000003",
        category_normalized="BOND",
        rank_date_1="2026-09-24",
        rank_date_2="2026-09-25",
        rank_1=12,
        rank_2=12,
    )

    assert evidence.rank_delta == 0
    assert evidence.direction == "STABLE"
    assert evidence.strength == "MINIMAL"


def test_small_move_is_weak_not_trade_authority():
    evidence = build_rank_trend_evidence(
        isin="LU0000000004",
        category_normalized="MIXED",
        rank_date_1="2026-09-24",
        rank_date_2="2026-09-25",
        rank_1=14,
        rank_2=10,
    )

    assert evidence.rank_delta == 4
    assert evidence.strength == "WEAK"
    assert evidence.trade_authority == "NONE"