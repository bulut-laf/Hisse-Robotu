import json
from pathlib import Path


def test_fin016_closure_is_fail_closed_and_never_claims_fake_production_calibration():
    root = Path(__file__).resolve().parents[2]
    p = root / "backend/data/financial_intelligence/FIN_PROD_V8_FIN016_PRODUCTION_CLOSURE.json"
    assert p.exists()
    data = json.loads(p.read_text(encoding="utf-8-sig"))

    assert data["read_only"] is True
    assert data["status"] in {"PASS_CLOSED_WITH_EXPLICIT_BLOCKERS", "BLOCKED"}
    assert data["core_contract"]["production_evidence"] is False
    assert data["historical_pit_producer"]["status"] == "NO_EXACT_PRODUCTION_OBSERVATION_PRODUCER"
    assert "HISTORICAL_PIT_OBSERVATION_PRODUCER_MISSING" in data["unresolved_blockers"]
    assert "NO_SYNTHETIC_DATA_AS_PRODUCTION_CALIBRATION" in data["rules"]
