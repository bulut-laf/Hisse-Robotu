from types import SimpleNamespace
from app.analysis.investability_runtime_wiring import run_runtime_wiring

class R:
    locked = True
    score = None
    label = "DATA_INSUFFICIENT"
    strengths = ()
    risks = ()
    confidence = "LOW"

def test_fin_prod_007_wires_only_proven_evidence(monkeypatch):
    seen = {}

    def fake_short(*a, **k):
        seen["short"] = k
        return R()

    def fake_long(*a, **k):
        seen["long"] = k
        return R()

    monkeypatch.setattr(
        "app.analysis.investability_runtime_wiring.calculate_short_term_investability",
        fake_short,
    )
    monkeypatch.setattr(
        "app.analysis.investability_runtime_wiring.calculate_long_term_investability",
        fake_long,
    )
    monkeypatch.setattr(
        "app.analysis.investability_runtime_wiring.build_financial_intelligence_panel",
        lambda **k: {"read_only": True},
    )

    base = {
        "symbol": "TUPRS",
        "as_of_date": "2026-08-04",
        "financial_health_score": 94,
        "short_term": {"risk_score": 0, "valuation_stretch": None},
        "long_term": {"financial_risk_score": 0, "cash_quality_score": 100},
        "valuation": {"current_price": "385"},
    }
    evidence = {
        "financial_momentum": None,
        "valuation_score": "0",
        "margin_of_safety_score": "0",
        "governance_score": "45",
        "market_context": {},
        "long_term_context": {"governance": "45"},
    }

    r = run_runtime_wiring(base_input=base, canonical_evidence=evidence)

    assert r["status"] == "PASS"
    assert seen["short"]["valuation_stretch"] is None
    assert seen["long"]["valuation_score"] == 0
    assert seen["long"]["margin_of_safety_score"] == 0
    assert seen["long"]["context"].governance == 45
