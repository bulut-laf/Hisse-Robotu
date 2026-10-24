from datetime import date

import pytest

from backend.app.analysis.research_profiles import (
    ProfileState,
    ResearchProfileName,
)
from backend.app.analysis.research_profiles_daily import (
    ResearchProfileContext,
    build_daily_research_profiles,
    snapshot_from_periods,
)
from backend.app.data.fundamental_data import periods_from_records


def _periods():
    return periods_from_records(
        [
            {
                "symbol": "TEST",
                "period_end": "2026-06-30",
                "fiscal_year": 2026,
                "fiscal_quarter": 2,
                "currency": "TRY",
                "revenue": 1200,
                "gross_profit": 360,
                "operating_profit": 300,
                "ebitda": 400,
                "net_income": 220,
                "total_assets": 2600,
                "total_equity": 1000,
                "total_debt": 300,
                "cash_and_equivalents": 100,
                "current_assets": 900,
                "current_liabilities": 500,
                "operating_cash_flow": 250,
                "capital_expenditure": 80,
                "shares_outstanding": 100,
                "source": "KAP",
                "published_at": "2026-08-10",
            },
            {
                "symbol": "TEST",
                "period_end": "2025-06-30",
                "fiscal_year": 2025,
                "fiscal_quarter": 2,
                "currency": "TRY",
                "revenue": 900,
                "gross_profit": 225,
                "operating_profit": 150,
                "ebitda": 180,
                "net_income": 90,
                "total_assets": 2200,
                "total_equity": 800,
                "total_debt": 400,
                "cash_and_equivalents": 100,
                "current_assets": 700,
                "current_liabilities": 520,
                "operating_cash_flow": 100,
                "capital_expenditure": 50,
                "shares_outstanding": 100,
                "source": "KAP",
                "published_at": "2025-08-10",
            },
        ]
    )


def test_canonical_ratios_fill_only_proven_balance_fields():
    snapshot = snapshot_from_periods("TEST", _periods())

    assert snapshot.net_debt_ebitda == pytest.approx(0.5)
    assert snapshot.debt_equity == pytest.approx(0.3)
    assert snapshot.free_float_shares is None
    assert snapshot.capex is None
    assert snapshot.ttm_cfo is None
    assert snapshot.ttm_operating_profit is None


def test_explicit_context_keeps_authority_over_computed_ratios():
    snapshot = snapshot_from_periods(
        "TEST",
        _periods(),
        context=ResearchProfileContext(
            net_debt_ebitda=1.25,
            debt_equity=0.42,
        ),
    )

    assert snapshot.net_debt_ebitda == pytest.approx(1.25)
    assert snapshot.debt_equity == pytest.approx(0.42)


def test_period_data_can_activate_earnings_inflection_without_fake_inputs():
    bundle = build_daily_research_profiles(
        successful_symbols=("TEST",),
        periods=_periods(),
        as_of=date(2026, 8, 26),
    )

    assert bundle.covered_symbol_count == 1
    by_profile = {
        result.profile: result
        for result in bundle.items[0].results
    }

    assert (
        by_profile[ResearchProfileName.EARNINGS_INFLECTION].state
        is ProfileState.MATCH
    )
    assert (
        by_profile[ResearchProfileName.BABY_QUALITY_CAPEX].state
        is ProfileState.INSUFFICIENT
    )
    assert (
        by_profile[ResearchProfileName.CAPEX_TO_EARNINGS].state
        is ProfileState.INSUFFICIENT
    )
