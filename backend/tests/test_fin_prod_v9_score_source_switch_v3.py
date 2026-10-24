import json
from pathlib import Path


def test_fin_prod_v9_score_resolution_is_closed_and_market_gap_is_exact():
    root = Path(__file__).resolve().parents[2]
    p = root / "backend/data/financial_intelligence/FIN_PROD_V9_HISTORICAL_PIT_PRODUCTION_OBSERVATIONS.json"
    assert p.exists()

    data = json.loads(p.read_text(encoding="utf-8-sig"))
    assert "SCORE_MISSING:TUPRS" not in data["blockers"]
    assert "OBSERVATION_DATE_MARKET_PRICE_MISSING:TUPRS" in data["blockers"]
    assert "NO_SYNTHETIC_PRODUCTION_CALIBRATION" in data["rules"]
