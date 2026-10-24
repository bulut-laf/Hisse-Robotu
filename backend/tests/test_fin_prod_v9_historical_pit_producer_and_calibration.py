import json
from pathlib import Path


def test_fin_prod_v9_historical_pit_producer_contract():
    root = Path(__file__).resolve().parents[2]
    p = root / "backend/data/financial_intelligence/FIN_PROD_V9_HISTORICAL_PIT_PRODUCTION_OBSERVATIONS.json"
    assert p.exists()
    data = json.loads(p.read_text(encoding="utf-8-sig"))

    assert data["mode"] == "READ_ONLY_PRODUCTION_PIT_OBSERVATION_PRODUCER"
    assert "NO_SYNTHETIC_PRODUCTION_CALIBRATION" in data["rules"]
    assert "NO_WEIGHT_OPTIMIZATION" in data["rules"]
    assert "NO_THRESHOLD_OPTIMIZATION" in data["rules"]
    assert "NO_AL_SAT_SCANNER_RANKING_PORTFOLIO_MUTATION" in data["rules"]

    for row in data["observations"]:
        assert row["publication_date"] <= row["observation_date"]
        assert row["score"] is not None
        assert row["forward_return"] is not None

    if data["observation_count"] < 20:
        assert data["status"] in {"INSUFFICIENT_SAMPLE", "NO_PRODUCTION_OBSERVATIONS"}
