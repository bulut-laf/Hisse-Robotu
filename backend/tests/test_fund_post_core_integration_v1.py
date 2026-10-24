from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from backend.app.funds.analysis_engine import (
    FundAnalysisClass,
    FundAnalysisResult,
)
from backend.app.funds.outcome import (
    FundPricePoint,
    OutcomeHorizon,
    evaluate_forward_outcomes,
)
from backend.app.funds.weekly_snapshot import (
    build_weekly_snapshot,
)


def analysis_result():
    return FundAnalysisResult(
        canonical_fund_id="fund:tefas:AAA",
        category_id="test-category",
        classification=FundAnalysisClass.C,
        class_label="ZLEME",
        positive_families=("F2",),
        neutral_families=(),
        caution_families=(),
        unavailable_families=("F1", "F3", "F4", "F5"),
        eligibility_reason="TEST",
        explanation="integration evidence",
    )


def test_forward_outcome_keeps_zero_tuning_authority():
    result = analysis_result()

    selection = date(2025, 1, 1)

    prices = tuple(
        FundPricePoint(
            canonical_fund_id=result.canonical_fund_id,
            observation_date=selection + timedelta(days=i),
            unit_price=Decimal("100") + Decimal(i),
        )
        for i in range(1, 601)
    )

    outcomes = evaluate_forward_outcomes(
        result,
        selection_date=selection,
        start_price=Decimal("100"),
        prices=prices,
        as_of=date(2026, 8, 24),
    )

    assert outcomes
    assert len(outcomes) == len(tuple(OutcomeHorizon))

    assert all(
        item.canonical_fund_id
        == result.canonical_fund_id
        for item in outcomes
    )

    assert all(
        item.tuning_authority == "NONE"
        for item in outcomes
    )


def test_weekly_snapshot_preserves_analysis_and_no_scheduler_authority():
    result = analysis_result()

    snapshot = build_weekly_snapshot(
        date(2026, 8, 28),
        (result,),
        observed_at=datetime(
            2026,
            8,
            28,
            18,
            0,
            tzinfo=timezone.utc,
        ),
    )

    assert snapshot.week_ending == date(
        2026,
        8,
        28,
    )

    assert snapshot.results == (
        result,
    )

    assert snapshot.scheduler_authority == "NONE"


def test_analysis_result_still_has_no_trade_authority():
    result = analysis_result()

    assert result.automatic_trade_authority == "NONE"
    assert result.forced_fill is False
