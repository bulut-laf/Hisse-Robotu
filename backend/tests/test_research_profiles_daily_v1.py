from dataclasses import dataclass
from datetime import date

from backend.app.analysis.research_profiles import (
    CapexEvidenceStatus,
    CapexStage,
    FundamentalSnapshot,
    ProfileState,
    ResearchProfileName,
)
from backend.app.analysis.research_profiles_daily import (
    build_daily_research_profiles,
    build_daily_research_profiles_from_snapshots,
    daily_research_profile_rows,
    research_profile_contexts_from_bytes,
    snapshot_from_periods,
)
from backend.app.ui.research_profiles_dashboard import research_profiles_table_rows


AS_OF = date(2026, 8, 26)


@dataclass(frozen=True)
class Period:
    symbol: str
    period_end: date
    revenue: float
    gross_profit: float
    ebitda: float
    operating_profit: float
    operating_cash_flow: float
    cash: float
    total_debt: float


def yunsa_periods():
    return (
        Period("YUNSA.IS", date(2025, 6, 30), 1455, 193, 106, 71, -245, 400, 250),
        Period("YUNSA.IS", date(2026, 6, 30), 1871, 389, 282, 277, -155, 500, 342),
    )


def test_period_adapter_computes_same_period_yoy_and_margin_direction():
    snapshot = snapshot_from_periods("YUNSA.IS", yunsa_periods())
    assert round(snapshot.revenue_yoy_pct, 1) == 28.6
    assert snapshot.gross_margin_delta_pp > 7
    assert snapshot.ebitda_margin_delta_pp > 7
    assert snapshot.operating_profit_yoy_pct > 280


def test_missing_universe_data_stays_insufficient():
    bundle = build_daily_research_profiles(
        successful_symbols=("AAA.IS", "BBB.IS"),
        periods=(),
        contexts={},
        as_of=AS_OF,
    )
    assert bundle.successful_symbol_count == 2
    assert bundle.covered_symbol_count == 0
    assert len(bundle.results) == 6
    assert all(x.state is ProfileState.INSUFFICIENT for x in bundle.results)


def test_context_parser_accepts_verified_capex_without_inventing_fields():
    raw = b"""symbol,market_cap_try,free_float_shares,ttm_cfo,ttm_operating_profit,net_cash,capex_stage,capex_evidence_status,capex_source_date,capex_source_id,capacity_before,capacity_after
CGCAM,6500000000,42900000,100,200,300,UNDER_CONSTRUCTION,VERIFIED,2026-07-01,KAP-1,5,14
"""
    context = research_profile_contexts_from_bytes(raw, suffix=".csv")["CGCAM.IS"]
    assert context.market_cap_try == 6_500_000_000
    assert context.free_float_shares == 42_900_000
    assert context.capex is not None
    assert context.capex.stage is CapexStage.UNDER_CONSTRUCTION
    assert context.capex.evidence_status is CapexEvidenceStatus.VERIFIED
    assert context.capex.capacity_after == 14


def test_context_parser_does_not_create_capex_without_traceable_source():
    raw = b"""symbol,capex_stage,capex_evidence_status,capacity_before,capacity_after
AAA,UNDER_CONSTRUCTION,VERIFIED,5,10
"""
    context = research_profile_contexts_from_bytes(raw, suffix=".csv")["AAA.IS"]
    assert context.capex is None


def test_yunsa_like_snapshot_is_visible_in_two_research_profiles():
    snapshot = FundamentalSnapshot(
        symbol="YUNSA.IS",
        market_cap_try=4_100_000_000,
        free_float_shares=202_000_000,
        ttm_cfo=-50,
        ttm_operating_profit=400,
        latest_ebitda=282,
        latest_operating_profit=277,
        net_cash=158,
        revenue_yoy_pct=29,
        gross_margin_delta_pp=7.5,
        ebitda_margin_delta_pp=7.8,
        operating_profit_yoy_pct=288,
        cfo_direction="improving",
        leverage_direction="stable",
        capex=None,
    )
    bundle = build_daily_research_profiles_from_snapshots(
        {"YUNSA.IS": snapshot}, as_of=AS_OF
    )
    by_profile = {r.profile: r for r in bundle.results}
    assert by_profile[ResearchProfileName.EARNINGS_INFLECTION].state is ProfileState.MATCH
    assert by_profile[ResearchProfileName.BABY_QUALITY_CAPEX].state is ProfileState.INSUFFICIENT
    assert by_profile[ResearchProfileName.CAPEX_TO_EARNINGS].state is ProfileState.INSUFFICIENT


def test_rows_have_no_composite_score_or_trade_decision():
    bundle = build_daily_research_profiles(
        successful_symbols=("AAA.IS",),
        as_of=AS_OF,
    )
    rows = daily_research_profile_rows(bundle)
    assert rows
    assert all("Skor" not in row for row in rows)
    assert all("AL" not in row and "SAT" not in row for row in rows)


def test_ui_rows_translate_profile_names_only():
    bundle = build_daily_research_profiles(
        successful_symbols=("AAA.IS",),
        as_of=AS_OF,
    )
    rows = research_profiles_table_rows(bundle)
    assert {row["Profil"] for row in rows} == {
        "Baby Quality + Capex",
        "Capex → Earnings",
        "Earnings Inflection",
    }
