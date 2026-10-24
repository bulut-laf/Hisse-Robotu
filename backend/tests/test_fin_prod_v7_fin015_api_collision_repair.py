
from datetime import date, datetime
from decimal import Decimal

from app.analysis.financial_intelligence_panel import build_financial_intelligence_panel
from app.analysis.short_term_investability import calculate_short_term_investability
from app.analysis.long_term_investability import calculate_long_term_investability
from app.models.investability_models import MarketContextInput, LongTermContextInput


def D(x):
    return Decimal(str(x))


def test_fin015_compatibility_contract():
    st = calculate_short_term_investability(
        "TUPRS",
        date(2026, 9, 4),
        financial_health_score=94,
        risk_score=0,
        financial_momentum=D(80),
        valuation_stretch=D(70),
        market=MarketContextInput(
            technical_trend=D(80),
            relative_strength=D(75),
            volume_liquidity=D(75),
            catalyst=D(70),
            entry_risk=D(65),
            earnings_surprise=D(80),
        ),
    )
    lt = calculate_long_term_investability(
        "TUPRS",
        date(2026, 9, 4),
        financial_health_score=94,
        financial_risk_score=0,
        cash_quality_score=D(90),
        capital_efficiency_score=D(85),
        valuation_score=D(70),
        margin_of_safety_score=D(65),
        context=LongTermContextInput(
            business_quality=D(90),
            growth_durability=D(80),
            governance=D(80),
            sector_risk=D(30),
        ),
    )
    p = build_financial_intelligence_panel(
        symbol="TUPRS",
        as_of=datetime(2026, 9, 4, 15, 0),
        financial_health_score=94,
        financial_health_grade="VERY_STRONG",
        financial_risk="LOW",
        short_term=st,
        long_term=lt,
        current_price=D(180),
        bear_value=D(170),
        base_value=D(210),
        bull_value=D(240),
        valuation_status="ATTRACTIVE",
        margin_of_safety_status="FAIR",
        confidence="MEDIUM",
        what_to_watch_next=("Brüt marj", "Net borç"),
    )
    assert p.read_only is True
    assert p.upside_downside_to_base == D(210) / D(180) - D(1)
    assert p.short_term_score == st.score
    assert p.long_term_score == lt.score
