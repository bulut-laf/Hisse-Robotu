from datetime import date, datetime
from decimal import Decimal

from app.analysis.short_term_investability import calculate_short_term_investability
from app.analysis.long_term_investability import calculate_long_term_investability
from app.analysis.financial_intelligence_panel import build_financial_intelligence_panel
from app.analysis.financial_intelligence_validation import validate_point_in_time, calibrate_score_separation
from app.models.investability_models import MarketContextInput, LongTermContextInput, PointInTimeObservation


def D(x):
    return Decimal(str(x))


def test_fin013_short_term_requires_market_context():
    r = calculate_short_term_investability("TUPRS", date(2026, 9, 4), financial_health_score=94, risk_score=0, financial_momentum=D(90), valuation_stretch=D(70), market=MarketContextInput())
    assert r.locked is True
    assert r.score is None
    assert r.label == "DATA_INSUFFICIENT"


def test_fin013_short_term_scores_complete_evidence():
    r = calculate_short_term_investability("TUPRS", date(2026, 9, 4), financial_health_score=94, risk_score=5, financial_momentum=D(88), valuation_stretch=D(70), market=MarketContextInput(technical_trend=D(85), relative_strength=D(80), volume_liquidity=D(75), catalyst=D(70), entry_risk=D(65), earnings_surprise=D(90)))
    assert r.locked is False
    assert r.score is not None and r.score >= 70
    assert r.label in {"STRONG_CANDIDATE", "POSITIVE"}


def test_fin014_long_term_separates_quality_and_valuation():
    r = calculate_long_term_investability("TUPRS", date(2026, 9, 4), financial_health_score=94, financial_risk_score=5, cash_quality_score=D(92), capital_efficiency_score=D(85), valuation_score=D(45), margin_of_safety_score=D(40), context=LongTermContextInput(business_quality=D(90), growth_durability=D(82), governance=D(80), sector_risk=D(35)))
    assert r.score is not None
    assert "FINANCIAL_HEALTH" in r.strengths
    assert "MARGIN_OF_SAFETY" in r.risks
    assert r.label in {"ATTRACTIVE", "WATCH_PRICE_WAIT"}


def test_fin015_panel_is_read_only_and_computes_upside():
    st = calculate_short_term_investability("TUPRS", date(2026, 9, 4), financial_health_score=94, risk_score=0, financial_momentum=D(80), valuation_stretch=D(70), market=MarketContextInput(technical_trend=D(80), relative_strength=D(75), volume_liquidity=D(75), catalyst=D(70), entry_risk=D(65), earnings_surprise=D(80)))
    lt = calculate_long_term_investability("TUPRS", date(2026, 9, 4), financial_health_score=94, financial_risk_score=0, cash_quality_score=D(90), capital_efficiency_score=D(85), valuation_score=D(70), margin_of_safety_score=D(65), context=LongTermContextInput(business_quality=D(90), growth_durability=D(80), governance=D(80), sector_risk=D(30)))
    p = build_financial_intelligence_panel(symbol="TUPRS", as_of=datetime(2026, 9, 4, 15, 0), financial_health_score=94, financial_health_grade="VERY_STRONG", financial_risk="LOW", short_term=st, long_term=lt, current_price=D(180), bear_value=D(170), base_value=D(210), bull_value=D(240), valuation_status="ATTRACTIVE", margin_of_safety_status="FAIR", confidence="MEDIUM", what_to_watch_next=("Brüt marj", "Net borç"))
    assert p.read_only is True
    assert p.upside_downside_to_base == D(210) / D(180) - D(1)
    assert p.short_term_score == st.score
    assert p.long_term_score == lt.score


def test_fin016_point_in_time_blocks_future_publication():
    o = PointInTimeObservation(date(2026, 8, 1), date(2026, 8, 4), 80, D("0.10"))
    assert validate_point_in_time(o) is False


def test_fin016_point_in_time_accepts_public_information():
    o = PointInTimeObservation(date(2026, 8, 5), date(2026, 8, 4), 80, D("0.10"))
    assert validate_point_in_time(o) is True


def test_fin016_calibration_insufficient_sample_is_not_overfit():
    obs = tuple(PointInTimeObservation(date(2026, 8, 5), date(2026, 8, 4), 80 if i % 2 == 0 else 40, D("0.03") if i % 2 == 0 else D("-0.01")) for i in range(10))
    c = calibrate_score_separation(obs)
    assert c.status == "INSUFFICIENT_SAMPLE"
    assert c.separation == D("0.04")


def test_fin016_calibration_detects_positive_separation():
    obs = tuple(PointInTimeObservation(date(2026, 8, 5), date(2026, 8, 4), 80 if i % 2 == 0 else 40, D("0.05") if i % 2 == 0 else D("-0.01")) for i in range(20))
    c = calibrate_score_separation(obs)
    assert c.status == "POSITIVE_SEPARATION"
    assert c.usable_size == 20
    assert c.separation == D("0.06")
