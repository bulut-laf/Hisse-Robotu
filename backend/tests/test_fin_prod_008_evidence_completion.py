from decimal import Decimal
from app.analysis.long_term_evidence_completion import (
    growth_evidence_score,
    financial_momentum_score,
    complete_evidence,
)

def _financial(vals):
    return {
        "earnings_cash_quality": {
            "metrics": [
                {"code": "REVENUE_GROWTH_YOY", "value": str(vals[0])},
                {"code": "OPERATING_PROFIT_GROWTH_YOY", "value": str(vals[1])},
                {"code": "NET_INCOME_GROWTH_YOY", "value": str(vals[2])},
                {"code": "OCF_GROWTH_YOY", "value": str(vals[3])},
            ]
        }
    }

def test_all_positive_growth_is_capped_not_called_100_durable():
    score, flags = growth_evidence_score(_financial((10, 20, 30, 40)))
    assert score == Decimal("70")
    assert "NOT_MULTI_YEAR_DURABILITY_PROOF" in flags

def test_financial_momentum_uses_canonical_metrics():
    assert financial_momentum_score(_financial((10, 20, 30, 40))) == Decimal("100")

def test_completion_does_not_fake_unlock():
    r = complete_evidence(
        financial_acceptance=_financial((10, 20, 30, 40)),
        existing_evidence={
            "financial_momentum": None,
            "valuation_score": "0",
            "margin_of_safety_score": "0",
            "governance_score": "45",
            "market_context": {},
            "long_term_context": {"governance": "45"},
            "flags": ["GROWTH_DURABILITY_NOT_SYNTHESIZED"],
        },
    )
    assert r["long_term_context"]["growth_durability"] == "70"
    assert r["coverage_assessment"]["after_expected"] == "0.68"
    assert r["coverage_assessment"]["expected_locked"] is True
