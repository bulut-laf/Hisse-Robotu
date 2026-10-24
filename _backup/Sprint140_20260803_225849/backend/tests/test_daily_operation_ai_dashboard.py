from __future__ import annotations

import ast
from pathlib import Path

DASHBOARD = Path("backend/dashboard.py")


def source() -> str:
    return DASHBOARD.read_text(encoding="utf-8-sig")


def test_daily_operation_dashboard_has_ai_decision_support_section():
    text = source()
    assert "load_daily_ai_operation_context" in text
    assert "_gunluk_ai_karar_destegi_goster()" in text
    assert "Günlük AI karar desteği" in text
    assert "Önceki AI değerlendirmesine göre değişim" in text


def test_daily_operation_ai_section_does_not_make_live_ai_call():
    text = source()
    start = text.index("def _gunluk_ai_karar_destegi_goster()")
    end = text.index("def golge_portfoy_formu()", start)
    section = text[start:end]
    assert "evaluate_daily_package_with_ai" not in section
    assert "GEMINI_API_KEY" not in section


def test_daily_operation_ai_section_keeps_trade_decisions_isolated():
    text = source()
    start = text.index("def _gunluk_ai_karar_destegi_goster()")
    end = text.index("def golge_portfoy_formu()", start)
    section = text[start:end]
    assert "Teknik skorları" in section
    assert "AL/SAT kararlarını değiştirmez" in section


def test_dashboard_syntax_is_valid_after_sprint140_patch():
    ast.parse(source())
