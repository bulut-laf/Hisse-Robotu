from pathlib import Path


def test_dashboard_contains_ai_history_trend_section():
    source = Path("backend/dashboard.py").read_text(encoding="utf-8-sig")

    assert "AI Geçmişi ve Eğilim" in source
    assert "load_ai_evaluation_history" in source
    assert "analyze_ai_history_trend" in source
    assert "_ai_gecmis_egilim_goster()" in source


def test_dashboard_history_section_has_no_live_ai_call():
    source = Path("backend/dashboard.py").read_text(encoding="utf-8-sig")

    start = source.index("def _ai_gecmis_egilim_goster()")
    end = source.index("def golge_portfoy_formu()", start)
    section = source[start:end]

    assert "evaluate_daily_package_with_ai" not in section
    assert "GEMINI_API_KEY" not in section
