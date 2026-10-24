from pathlib import Path


DASHBOARD = Path("backend/dashboard.py")

OLD_IMPORT = (
    "from backend.app.ui.market_context_dashboard "
    "import render_market_context_dashboard"
)
ALIAS_IMPORT = (
    "from backend.app.ui.market_context_dashboard_s157 "
    "import render_market_context_dashboard as render_market_context_dashboard_s157"
)
ASSIGNMENT = (
    "render_market_context_dashboard = "
    "render_market_context_dashboard_s157"
)


def _source() -> str:
    return DASHBOARD.read_text(encoding="utf-8-sig")


def test_legacy_sprint137e2_import_satiri_korunur():
    source = _source()
    assert OLD_IMPORT in source
    assert source.count(OLD_IMPORT) == 1


def test_sprint157_wrapper_alias_import_edilir():
    source = _source()
    assert ALIAS_IMPORT in source


def test_mevcut_route_adi_wrappera_yonlendirilir():
    source = _source()
    assert ASSIGNMENT in source


def test_route_kodunu_degistirmeye_gerek_yoktur():
    source = _source()
    assert 'render_market_context_dashboard(' in source
