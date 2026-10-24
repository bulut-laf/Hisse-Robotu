from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_sprint180_prompt_patchi_tum_rapor_kapsamasini_zorunlu_kilar() -> None:
    patch_file = ROOT / "tools" / "patch_sprint180_ai_briefing.py"
    text = patch_file.read_text(encoding="utf-8")

    assert "HER raporu tek tek oku" in text
    assert "uzun bir raporun diğer kaynakları" in text
    assert "aligned_points" in text
    assert "conflicting_points" in text
    assert "Aracı kurum AL/TUT/SAT" in text
    assert "Hisse Robotu'nun kendi tavsiyesi" in text


def test_sprint180_wrapper_kaynak_kapsama_panelini_mevcut_dashboard_sonrasinda_cagirir() -> None:
    wrapper = ROOT / "backend" / "app" / "ui" / "market_context_dashboard_s157.py"
    text = wrapper.read_text(encoding="utf-8")
    ast.parse(text)

    assert "render_daily_market_briefing_panel" in text
    base_call = text.index("_render_existing_market_context_dashboard(")
    panel_call = text.index("render_daily_market_briefing_panel(", base_call)
    assert panel_call > base_call
    assert "RESET_AFTER_SAVE_KEY" in text
    assert "FILE_UPLOAD_GENERATION_KEY" in text
