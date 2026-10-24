from __future__ import annotations

import ast
from pathlib import Path


def _stock_analyzer_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "app"
        / "analysis"
        / "stock_analyzer.py"
    )


def test_stock_analyzer_atr_fallback_minimum_2r_sozlesmesini_saglar():
    source = _stock_analyzer_path().read_text(encoding="utf-8")
    tree = ast.parse(source)

    calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id == "risk_plani_olustur":
            kwargs = {
                kw.arg: kw.value
                for kw in node.keywords
                if kw.arg is not None
            }
            if {
                "stop_atr_katsayisi",
                "hedef_atr_katsayisi",
                "minimum_risk_odul",
            } <= set(kwargs):
                calls.append(kwargs)

    assert len(calls) == 1
    kwargs = calls[0]

    stop = ast.literal_eval(kwargs["stop_atr_katsayisi"])
    target = ast.literal_eval(kwargs["hedef_atr_katsayisi"])
    minimum_rr = ast.literal_eval(kwargs["minimum_risk_odul"])

    assert stop == 1.50
    assert minimum_rr == 2.00
    assert target == 3.00
    assert target / stop >= minimum_rr


def test_atr_fallback_tam_2r_uretir():
    from backend.app.risk.risk_engine import risk_plani_olustur

    plan = risk_plani_olustur(
        giris_fiyati=100.0,
        atr=2.0,
        stop_atr_katsayisi=1.50,
        hedef_atr_katsayisi=3.00,
        minimum_risk_odul=2.00,
    )

    assert abs(plan.risk_odul_orani - 2.0) < 1e-9
    assert plan.filtreyi_gecti is True
