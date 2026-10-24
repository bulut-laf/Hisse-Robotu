import json
from pathlib import Path


def test_release_manifest_v9_sync():
    root = Path(__file__).resolve().parents[2]
    p = root / "backend/data/financial_intelligence/FINANCIAL_INTELLIGENCE_V1_RELEASE_MANIFEST.json"
    assert p.exists()

    data = json.loads(p.read_text(encoding="utf-8-sig"))

    status = data.get("STATUS") or data.get("status")
    assert status == "READY_FOR_V1_RELEASE_WITH_KNOWN_LIMITATIONS"

    assert data["FIN016_PRODUCTION_STATUS"] == "CLOSED_WITH_EXPLICIT_BLOCKER"
    assert data["FIN016_PRODUCTION_CALIBRATION_READY"] is False
    assert data["FIN016_PRODUCTION_OBSERVATION_COUNT"] == 0
    assert data["FIN016_EXACT_BLOCKER"] == "OBSERVATION_DATE_MARKET_PRICE_MISSING:TUPRS"
    assert (
        "HISTORICAL_PIT_OBSERVATION_PRODUCER_MARKET_HISTORY_GAP"
        in data["KNOWN_LIMITATIONS"]
    )
    assert "HISTORICAL_PIT_OBSERVATION_PRODUCER_MISSING" not in data["KNOWN_LIMITATIONS"]
    assert data["RELEASE_BLOCKERS"] == []
