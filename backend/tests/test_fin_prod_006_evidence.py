from decimal import Decimal
from app.analysis.canonical_investability_evidence import (
    valuation_score_from_fair_value,
    margin_of_safety_score_from_result,
    build_canonical_evidence,
)

def test_valuation_score_deterministic():
    assert valuation_score_from_fair_value(current_price=Decimal("100"), base_fair_value=Decimal("100")) == Decimal("50")
    assert valuation_score_from_fair_value(current_price=Decimal("50"), base_fair_value=Decimal("100")) == Decimal("100")
    assert valuation_score_from_fair_value(current_price=Decimal("150"), base_fair_value=Decimal("100")) == Decimal("0")

def test_mos_score_deterministic():
    assert margin_of_safety_score_from_result(current_margin_of_safety=Decimal("0")) == Decimal("50")
    assert margin_of_safety_score_from_result(current_margin_of_safety=Decimal("0.5")) == Decimal("100")
    assert margin_of_safety_score_from_result(current_margin_of_safety=Decimal("-0.5")) == Decimal("0")

def test_no_technical_context_is_invented():
    r = build_canonical_evidence(
        financial_acceptance={},
        fair_value_acceptance={
            "current_price":"385",
            "composite_fair_value":{"base_value":"239.6152784240735753418742541"},
            "margin_of_safety":{"current_margin_of_safety":"-0.606742285100130612308512974"}
        },
        market_ownership_acceptance=None,
    )
    assert all(v is None for v in r["market_context"].values())
    assert r["valuation_score"] is not None
    assert r["margin_of_safety_score"] == Decimal("0")
