import json
from pathlib import Path


def test_standalone_ui_entry_exists_and_tuprs_panel_is_readable():
    root = Path(__file__).resolve().parents[2]
    app = root / "backend/financial_intelligence_app.py"
    artifact = root / "backend/data/financial_intelligence/TUPRS_financial_intelligence_panel.json"

    assert app.exists()
    assert artifact.exists()

    data = json.loads(artifact.read_text(encoding="utf-8-sig"))
    assert isinstance(data, dict)
    assert data.get("status") == "PASS"

    text = app.read_text(encoding="utf-8-sig")
    assert "Finansal Zekâ Paneli" in text
    assert "st.set_page_config" in text
    assert "st.json(panel)" in text
