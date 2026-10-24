
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[2]
DASHBOARD = ROOT / "backend" / "dashboard.py"
UI = ROOT / "backend" / "app" / "ui" / "financial_intelligence_dashboard.py"


def test_financial_intelligence_ui_module_exists_and_is_read_only():
    source = UI.read_text(encoding="utf-8-sig")
    tree = ast.parse(source)
    assert "render_financial_intelligence_dashboard" in source
    assert "AL/SAT" in source
    assert "read-only" in source.lower()
    assert "write_text(" not in source
    assert "save_" not in source


def test_dashboard_wires_financial_intelligence_panel():
    source = DASHBOARD.read_text(encoding="utf-8-sig")
    ast.parse(source)
    assert "FIN_PROD_V7_FINANCIAL_INTELLIGENCE_UI_WIRING_V1" in source
    assert '"Finansal Zekâ Paneli"' in source
    assert "backend.app.ui.financial_intelligence_dashboard" in source
    assert "render_financial_intelligence_dashboard(" in source
    assert 'elif analiz_modu == "Temel Analiz":' in source
    assert 'elif analiz_modu == "Finansal Zekâ Paneli":' in source


def test_panel_is_inserted_after_temas_analiz_deterministically():
    source = DASHBOARD.read_text(encoding="utf-8-sig")
    assert '_fin_prod_v7_moduller.index("Temel Analiz") + 1' in source
