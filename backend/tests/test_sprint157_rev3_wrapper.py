from pathlib import Path


WRAPPER = Path("backend/app/ui/market_context_dashboard_s157.py")


def _source() -> str:
    return WRAPPER.read_text(encoding="utf-8")


def test_wrapper_mevcut_dashboardu_import_eder():
    source = _source()
    assert "market_context_dashboard import (" in source
    assert "_render_existing_market_context_dashboard" in source


def test_wrapper_gorsel_girdiyi_ayri_bolumde_cagirir():
    source = _source()
    assert "render_market_context_image_input" in source
    assert "JPG / PNG ekran görüntüsü" in source


def test_wrapper_mevcut_dashboardu_sonra_cagirir():
    source = _source()
    image_pos = source.index("render_market_context_image_input(")
    existing_pos = source.rindex("_render_existing_market_context_dashboard(")
    assert existing_pos > image_pos


def test_wrapper_teknik_karar_motoru_cagirmaz():
    source = _source().casefold()
    for forbidden in (
        "technical_score",
        "buy_signal",
        "sell_signal",
        "risk_engine",
        "candidate_rank",
    ):
        assert forbidden not in source
