
from datetime import date
import pandas as pd

from backend.scripts import run_fin_prod_v5_rev6_exact_momentum_producer as r


def test_market_symbol_uses_bist_suffix():
    assert r._market_symbol("TUPRS") == "TUPRS.IS"
    assert r._market_symbol("TUPRS.IS") == "TUPRS.IS"


def test_idx_date():
    assert r._idx_date(pd.Timestamp("2026-08-04")) == date(2026, 8, 4)


def test_runner_has_exact_existing_engine_contract():
    import inspect
    text = inspect.getsource(r)
    assert "MomentumDiscoveryEngine" in text
    assert ".analiz_et(" in text
    assert "trend_puani" not in text
    assert "goreceli_guc_puani" not in text
    assert "likidite_puani" not in text
