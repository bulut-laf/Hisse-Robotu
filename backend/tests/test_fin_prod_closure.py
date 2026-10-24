from pathlib import Path
import json

from app.analysis.investability_production_closure import (
    discover_exact_canonical_candidates,
    run_closure,
)

def test_exact_discovery_only(tmp_path):
    p = tmp_path / "TUPRS_demo.json"
    p.write_text(json.dumps({
        "symbol": "TUPRS",
        "technical_trend": 80,
        "some_random_trend_score": 99,
        "business_quality": 72,
    }), encoding="utf-8")

    r = discover_exact_canonical_candidates(tmp_path, "TUPRS")
    keys = {x["key"] for x in r}
    assert "technical_trend" in keys
    assert "business_quality" in keys
    assert "some_random_trend_score" not in keys

def test_no_fake_unlock_without_extra_data(tmp_path, monkeypatch):
    class R:
        def __init__(self, locked=True):
            self.symbol="TUPRS"; self.as_of_date=None; self.score=None
            self.label="DATA_INSUFFICIENT"; self.locked=locked; self.components=()
            self.strengths=(); self.risks=(); self.explanation=""; self.confidence="LOW"
            self.engine_version="x"

    monkeypatch.setattr(
        "app.analysis.investability_production_closure.calculate_short_term_investability",
        lambda *a, **k: R(True)
    )
    monkeypatch.setattr(
        "app.analysis.investability_production_closure.calculate_long_term_investability",
        lambda *a, **k: R(True)
    )
    monkeypatch.setattr(
        "app.analysis.investability_production_closure.build_financial_intelligence_panel",
        lambda **k: {"read_only": True}
    )

    base = {
        "symbol": "TUPRS",
        "as_of_date": "2026-08-04",
        "short_term": {},
        "long_term": {"components":[{"code":"CASH_QUALITY","score":"100"}]},
        "panel": {
            "as_of":"2026-08-04T18:24:32",
            "financial_health_score":94,
            "financial_health_grade":"VERY_STRONG",
            "financial_risk":"LOW",
        },
    }
    evidence = {
        "financial_momentum":"100",
        "valuation_score":"0",
        "margin_of_safety_score":"0",
        "market_context":{},
        "long_term_context":{"growth_durability":"70","governance":"45"},
    }
    out = run_closure(base_acceptance=base, completed_evidence=evidence, data_root=tmp_path)
    assert out["status"] == "PASS_CLOSED_WITH_EXPLICIT_BLOCKERS"
    assert out["long_term_coverage"] == "0.68"
