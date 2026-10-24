import importlib.util
from pathlib import Path


def _load():
    root = Path(__file__).resolve().parents[2]
    p = root / "backend/scripts/run_fin_prod_v9_historical_pit_producer_and_calibration.py"
    spec = importlib.util.spec_from_file_location("finprodv9v5", p)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_exact_financial_health_scalar_and_object_contract():
    mod = _load()
    assert mod._financial_health_score({"financial_health": 94}) == 94.0
    assert mod._financial_health_score({"financial_health": {"score": 94}}) == 94.0
    assert mod._financial_health_score({"financial_health": {"overall_score": 94}}) == 94.0
    assert mod._financial_health_score({"health_score": 94}) == 94.0


def test_unrelated_scores_are_not_accepted():
    mod = _load()
    assert mod._financial_health_score({"score": 94}) is None
    assert mod._financial_health_score({"momentum_score": 94}) is None
