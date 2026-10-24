import json
from pathlib import Path


def test_financial_intelligence_v1_release_manifest_is_safe_and_explicit():
    root = Path(__file__).resolve().parents[2]
    p = root / "backend/data/financial_intelligence/FINANCIAL_INTELLIGENCE_V1_RELEASE_MANIFEST.json"
    assert p.exists()
    data = json.loads(p.read_text(encoding="utf-8-sig"))

    assert data["status"] == "READY_FOR_V1_RELEASE_WITH_KNOWN_LIMITATIONS"
    assert data["reference_symbol"] == "TUPRS"
    assert data["read_only_decision_support"] is True
    assert data["decision_engine_mutation"] is False
    assert data["al_sat_mutation"] is False
    assert data["scanner_mutation"] is False
    assert data["ranking_mutation"] is False
    assert data["portfolio_mutation"] is False
    assert data["fin001_to_fin016"]["roadmap_complete"] is True
    assert data["release_checks"]["long_term_coverage_value"] >= 0.95
    assert data["release_blockers"] == []
    assert "HISTORICAL_PIT_OBSERVATION_PRODUCER_MISSING" in data["known_limitations"]
    assert data["regression_baseline"]["passed"] == 3794
    assert data["regression_baseline"]["skipped"] == 1
