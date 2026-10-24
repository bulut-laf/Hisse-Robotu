from datetime import date
from dataclasses import replace

from backend.app.analysis.research_profiles import (
    CapexEvidence, CapexEvidenceStatus, CapexStage, FundamentalDirection,
    FundamentalSnapshot, ProfileState, ResearchProfileName,
    evaluate_baby_quality_capex, evaluate_capex_to_earnings,
    evaluate_earnings_inflection, evaluate_fundamental_direction,
    evaluate_research_profiles,
)

AS_OF = date(2026, 8, 26)

def capex(**kw):
    x = dict(source_type="KAP", source_date=date(2026,7,6), source_id="KAP-TEST",
             investment_type="capacity", stage=CapexStage.UNDER_CONSTRUCTION,
             evidence_status=CapexEvidenceStatus.VERIFIED,
             expected_completion_date=date(2027,5,1),
             capacity_before=100.0, capacity_after=140.0)
    x.update(kw); return CapexEvidence(**x)

def yunsa():
    return FundamentalSnapshot(
        symbol="YUNSA", market_cap_try=4.1e9, free_float_shares=202e6,
        ttm_cfo=-50e6, ttm_operating_profit=400e6,
        latest_ebitda=282e6, latest_operating_profit=277e6, net_cash=158e6,
        revenue_yoy_pct=29, gross_margin_delta_pp=7.5, ebitda_margin_delta_pp=7.8,
        operating_profit_yoy_pct=288, cfo_direction="improving",
        leverage_direction="stable", capex=capex())

def cgcam():
    return FundamentalSnapshot(
        symbol="CGCAM", market_cap_try=6.5e9, free_float_shares=42.9e6,
        ttm_cfo=82e6, ttm_operating_profit=41e6,
        latest_ebitda=114e6, latest_operating_profit=41e6, net_cash=176.7e6,
        revenue_yoy_pct=-14, gross_margin_delta_pp=-10.5, ebitda_margin_delta_pp=-8.8,
        operating_profit_yoy_pct=-80, cfo_direction="deteriorating",
        leverage_direction="deteriorating",
        capex=capex(expected_completion_date=date(2026,12,1), expected_revenue_impact=22e6))

def test_yunsa_direction_positive():
    assert evaluate_fundamental_direction(yunsa()).direction is FundamentalDirection.POSITIVE

def test_cgcam_direction_negative():
    assert evaluate_fundamental_direction(cgcam()).direction is FundamentalDirection.NEGATIVE

def test_yunsa_earnings_inflection_match_with_cfo_watch():
    r=evaluate_earnings_inflection(yunsa(),as_of=AS_OF)
    assert r.state is ProfileState.MATCH and "WATCH_CFO_NEGATIVE" in r.warnings

def test_yunsa_not_baby_due_float():
    r=evaluate_baby_quality_capex(yunsa(),as_of=AS_OF)
    assert r.state is ProfileState.BLOCKED and "BLOCK_FREE_FLOAT_ABOVE_LIMIT" in r.reasons

def test_yunsa_capex_match():
    assert evaluate_capex_to_earnings(yunsa(),as_of=AS_OF).state is ProfileState.MATCH

def test_cgcam_baby_blocked_by_direction():
    r=evaluate_baby_quality_capex(cgcam(),as_of=AS_OF)
    assert r.state is ProfileState.BLOCKED and "BLOCK_DIRECTION_NEGATIVE" in r.reasons

def test_cgcam_capex_blocked_by_direction():
    r=evaluate_capex_to_earnings(cgcam(),as_of=AS_OF)
    assert r.state is ProfileState.BLOCKED and "BLOCK_DIRECTION_NEGATIVE" in r.reasons

def test_missing_capex_is_insufficient():
    s=replace(yunsa(),free_float_shares=10e6,capex=None)
    assert evaluate_baby_quality_capex(s,as_of=AS_OF).state is ProfileState.INSUFFICIENT

def test_stale_capex_blocks():
    s=replace(yunsa(),capex=capex(evidence_status=CapexEvidenceStatus.STALE))
    assert evaluate_capex_to_earnings(s,as_of=AS_OF).state is ProfileState.BLOCKED

def test_high_leverage_blocks_baby():
    s=replace(yunsa(),symbol="TARKM",free_float_shares=5e6,net_cash=-1.2e9,
              net_debt_ebitda=4.2,debt_equity=1.5,leverage_direction="deteriorating")
    r=evaluate_baby_quality_capex(s,as_of=AS_OF)
    assert r.state is ProfileState.BLOCKED and "BLOCK_HIGH_LEVERAGE" in r.reasons

def test_secondary_baby_classification():
    s=FundamentalSnapshot(
        symbol="BFREN",market_cap_try=16e9,free_float_shares=18.9e6,
        ttm_cfo=300e6,ttm_operating_profit=200e6,latest_ebitda=250e6,
        latest_operating_profit=200e6,net_cash=95e6,revenue_yoy_pct=5,
        gross_margin_delta_pp=1.5,ebitda_margin_delta_pp=1.5,
        cfo_direction="stable",leverage_direction="stable",
        capex=capex(expected_completion_date=date(2027,8,1)))
    r=evaluate_baby_quality_capex(s,as_of=AS_OF)
    assert r.state is ProfileState.MATCH and r.size_classification=="SECONDARY"

def test_capex_requires_economic_effect():
    c=capex(capacity_before=None,capacity_after=None)
    s=replace(yunsa(),capex=c)
    r=evaluate_capex_to_earnings(s,as_of=AS_OF)
    assert r.state is ProfileState.INSUFFICIENT and "MISSING_CAPEX_ECONOMIC_EFFECT" in r.reasons

def test_inflection_requires_positive_operating_profit():
    s=replace(yunsa(),latest_operating_profit=-1)
    assert evaluate_earnings_inflection(s,as_of=AS_OF).state is ProfileState.BLOCKED

def test_all_three_profiles_without_score():
    rs=evaluate_research_profiles(yunsa(),as_of=AS_OF)
    assert [x.profile for x in rs]==[
        ResearchProfileName.BABY_QUALITY_CAPEX,
        ResearchProfileName.CAPEX_TO_EARNINGS,
        ResearchProfileName.EARNINGS_INFLECTION]
    assert all(not hasattr(x,"score") for x in rs)

def test_deterministic():
    s=yunsa()
    assert evaluate_research_profiles(s,as_of=AS_OF)==evaluate_research_profiles(s,as_of=AS_OF)
