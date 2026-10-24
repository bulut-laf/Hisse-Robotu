
from pathlib import Path
import importlib.util
import json


def _load_module():
    root = Path(__file__).resolve().parents[2]
    p = root / "backend/scripts/run_fin_prod_v9_historical_pit_producer_and_calibration.py"
    spec = importlib.util.spec_from_file_location("finprodv9", p)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_exact_financial_health_component_score():
    mod = _load_module()
    assert mod._financial_health_component_score(
        {"components": [{"component": "FINANCIAL_HEALTH", "score": 94}]}
    ) == 94.0
    assert mod._financial_health_component_score(
        {"FINANCIAL_HEALTH": {"value": 94}}
    ) == 94.0


def test_real_tuprs_investability_closure_exposes_financial_health_score():
    mod = _load_module()
    root = Path(__file__).resolve().parents[2]
    p = root / "backend/data/financial_intelligence/TUPRS_investability_production_closure.json"
    assert p.exists()
    data = json.loads(p.read_text(encoding="utf-8-sig"))
    assert mod._financial_health_component_score(data) == 94.0
