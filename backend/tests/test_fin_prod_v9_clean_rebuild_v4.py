import json
from pathlib import Path


def test_fin_prod_v9_current_fail_closed_contract():
    root = Path(__file__).resolve().parents[2]
    p = root / "backend/data/financial_intelligence/FIN_PROD_V9_HISTORICAL_PIT_PRODUCTION_OBSERVATIONS.json"
    assert p.exists()

    data = json.loads(p.read_text(encoding="utf-8-sig"))
    assert data["status"] == "NO_PRODUCTION_OBSERVATIONS"
    assert data["observation_count"] == 0
    assert "OBSERVATION_DATE_MARKET_PRICE_MISSING:TUPRS" in data["blockers"]
    assert "SCORE_MISSING:TUPRS" not in data["blockers"]
