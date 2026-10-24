
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.analysis.financial_intelligence_panel_read_model import build_financial_intelligence_panel


def _write(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_panel_preserves_missing_as_null(tmp_path):
    root = tmp_path
    panel = build_financial_intelligence_panel(root, "ABC", period_key="2026_2")
    assert panel["status"] == "PARTIAL"
    assert panel["sections"]["financial_health"]["score"] is None
    assert panel["sections"]["valuation"]["base"] is None
    assert panel["read_only"] is True


def test_panel_reads_canonical_short_long_and_v4(tmp_path):
    root = tmp_path
    backend = root / "backend"
    fi = backend / "data" / "financial_intelligence"

    _write(backend / "data" / "financial_intelligence_acceptance_TUPRS_2026_2.json", {
        "financial_health": {"total_score": 94, "components": [{"code": "CAPITAL_EFFICIENCY", "score": 15}]},
        "earnings_cash_quality": {"total_score": 100},
        "financial_risk": {"status": "LOW"},
    })
    _write(fi / "TUPRS_market_ownership_acceptance.json", {"status": "PASS"})
    _write(fi / "TUPRS_fair_value_acceptance.json", {
        "base": 239.6, "bear": 168.5, "bull": 340.9,
        "current_price": 385, "attractive_entry_price": 179.7,
        "status": "VERY_EXPENSIVE",
    })
    _write(fi / "TUPRS_investability_production_closure.json", {"status": "PASS"})
    _write(fi / "TUPRS_short_term_canonical_context.json", {
        "status": "PASS", "as_of_date": "2026-08-04",
        "technical_trend": "15", "relative_strength": "20",
        "volume_liquidity": "10", "data_quality": "READY", "blockers": [],
    })
    _write(fi / "TUPRS_long_term_canonical_coverage.json", {
        "status": "PASS", "as_of_date": "2026-08-04",
        "business_quality": {"status": "PASS", "value": "45"},
        "governance": {"status": "PASS", "value": "45"},
        "growth_context": {"status": "PASS", "growth_durability": "70"},
        "capital_efficiency": {"status": "PASS", "value": "15"},
        "coverage": {"value": "0.95"}, "data_quality": {"status": "PASS"}, "blockers": [],
    })
    _write(fi / "FIN_PROD_V4_CANONICAL_COVERAGE.json", {
        "symbols": [{
            "symbol": "TUPRS",
            "canonical_coverage_v4": {
                "short_term": {"status": "PASS"},
                "long_term": {"status": "PASS"},
                "unresolved_blockers": [],
                "coverage_status": "READY_FULL_CANONICAL_COVERAGE",
            },
            "decision_support_status_v4": "READY_FULL_DECISION_SUPPORT",
        }]
    })

    panel = build_financial_intelligence_panel(root, "TUPRS")
    assert panel["status"] == "PASS"
    assert panel["sections"]["financial_health"]["score"] == 94
    assert panel["sections"]["financial_health"]["cash_quality_score"] == 100
    assert panel["sections"]["long_term_context"]["business_quality"] == "45"
    assert panel["sections"]["long_term_context"]["governance"] == "45"
    assert panel["sections"]["long_term_context"]["growth_durability"] == "70"
    assert panel["sections"]["coverage_readiness"]["coverage_status"] == "READY_FULL_CANONICAL_COVERAGE"
    assert panel["sections"]["coverage_readiness"]["decision_support_status"] == "READY_FULL_DECISION_SUPPORT"
