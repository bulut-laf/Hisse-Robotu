import importlib.util
import json
from pathlib import Path


def _load():
    root = Path(__file__).resolve().parents[2]
    p = root / "backend/scripts/run_fin_prod_v9_historical_pit_producer_and_calibration.py"
    spec = importlib.util.spec_from_file_location("finprodv9v4", p)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_real_tuprs_canonical_health_score_is_94():
    mod = _load()
    root = Path(__file__).resolve().parents[2]
    fi = root / "backend/data/financial_intelligence"

    score, source = mod._score_from_canonical_sources(fi, "TUPRS")
    assert score == 94.0
    assert source is not None


def test_v9_output_remains_fail_closed():
    root = Path(__file__).resolve().parents[2]
    p = root / "backend/data/financial_intelligence/FIN_PROD_V9_HISTORICAL_PIT_PRODUCTION_OBSERVATIONS.json"
    assert p.exists()

    data = json.loads(p.read_text(encoding="utf-8-sig"))
    assert "NO_SYNTHETIC_PRODUCTION_CALIBRATION" in data["rules"]
    assert "NO_WEIGHT_OPTIMIZATION" in data["rules"]
    assert "NO_THRESHOLD_OPTIMIZATION" in data["rules"]

    for row in data["observations"]:
        assert row["publication_date"] <= row["observation_date"]
        assert row["score"] is not None
        assert row["forward_return"] is not None
