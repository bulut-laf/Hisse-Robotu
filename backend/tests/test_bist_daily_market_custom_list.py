from __future__ import annotations

from backend.app.analysis.bist_daily_market import ozel_liste_girdilerini_ayir, sembol_eslesmeleri


def test_custom_input_split() -> None:
    assert ozel_liste_girdilerini_ayir("thy, tupr\nASEL; kchol") == ["THY", "TUPR", "ASEL", "KCHOL"]


def test_symbol_match_exact_prefix_contains() -> None:
    universe = ["THYAO.IS", "TUPRS.IS", "ASELS.IS", "KCHOL.IS", "KCAER.IS"]
    assert sembol_eslesmeleri("THYAO", universe) == ["THYAO"]
    assert sembol_eslesmeleri("thy", universe) == ["THYAO"]
    assert sembol_eslesmeleri("kc", universe) == ["KCAER", "KCHOL"]
    assert sembol_eslesmeleri("prs", universe) == ["TUPRS"]


def test_ui_contains_custom_list_contract() -> None:
    from pathlib import Path
    text = Path("backend/app/ui/bist_daily_market_dashboard.py").read_text(encoding="utf-8")
    assert '"Özel Liste": None' in text
    assert '"Özel Liste Değerlerini Getir"' in text
    assert "sembol_eslesmeleri" in text
