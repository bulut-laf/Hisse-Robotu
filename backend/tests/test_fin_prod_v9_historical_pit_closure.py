import json
from pathlib import Path

def test_fin_prod_v9_historical_pit_closure():
    root = Path(__file__).resolve().parents[2]

    path = (
        root
        / "backend"
        / "data"
        / "financial_intelligence"
        / "FIN_PROD_V9_HISTORICAL_PIT_CLOSURE.json"
    )

    assert path.exists()

    data = json.loads(
        path.read_text(encoding="utf-8-sig")
    )

    assert data["status"] == "PASS_CLOSED_WITH_EXPLICIT_BLOCKER"

    assert (
        data["closed_with_blocker"]
        == "OBSERVATION_DATE_MARKET_PRICE_MISSING:TUPRS"
    )

    assert data["observation_count"] == 0

    assert (
        data["remaining_limitation"]
        == "HISTORICAL_PIT_OBSERVATION_PRODUCER_MARKET_HISTORY_GAP"
    )

    assert "NO_SYNTHETIC_PRODUCTION_CALIBRATION" in data["rules"]
    assert "NO_FUZZY_MARKET_DATE_MAPPING" in data["rules"]
