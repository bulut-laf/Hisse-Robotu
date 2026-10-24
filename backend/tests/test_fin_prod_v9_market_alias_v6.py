import importlib.util
from pathlib import Path


def _load():
    root = Path(__file__).resolve().parents[2]
    p = root / "backend/scripts/run_fin_prod_v9_historical_pit_producer_and_calibration.py"
    spec = importlib.util.spec_from_file_location("finprodv9v6", p)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_bist_alias_is_exact_and_deterministic():
    mod = _load()
    assert mod._market_symbol_aliases("TUPRS") == {"TUPRS", "TUPRS.IS"}
    assert mod._market_symbol_aliases("KRDMD") == {"KRDMD", "KRDMD.IS"}
