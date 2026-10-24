import json
from pathlib import Path

def test_v1_2_release_status_manifest_contract():
    root = Path(__file__).resolve().parents[2]
    path = root / "backend" / "data" / "financial_intelligence" / "FINANCIAL_INTELLIGENCE_V1_2_RELEASE_STATUS_MANIFEST.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    assert data["release"] == "V1.2"
    assert data["status"] == "CLOSED_PASS"
    assert data["full_regression"] == {"passed": 3915, "skipped": 1, "failed": 0, "status": "PASS"}
    assert data["target_regression"] == {"passed": 80, "failed": 0, "status": "PASS"}
    assert data["production_ready_models"] == ["INDUSTRIAL"]
    assert data["infrastructure_ready_but_not_production_ready"] == {
        "BANK": "NO_REAL_BANK_SOURCE",
        "INSURANCE": "NO_REAL_INSURANCE_SOURCE",
        "REIT": "NO_REAL_REIT_SOURCE",
        "HOLDING": "NO_REAL_HOLDING_SOURCE",
    }
    assert data["missing_to_zero"] is False
    assert data["future_publication_allowed"] is False
    assert data["production_evidence_synthesized"] is False
    assert data["tefas_history_verified_period"] == 1
    assert data["tefas_unverified_period_rejected_before_network"] is True
    assert data["al_sat_authority"] == "NONE"
    assert data["scanner_mutation"] is False
    assert data["ranking_mutation"] is False
    assert data["portfolio_mutation"] is False
