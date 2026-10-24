import pytest

from backend.app.market_context.ai_output_validator import validate_ai_output


def _safe_output():
    return {
        "summary": "Temkinli pozitif",
        "positive_factors": ["Global destek"],
        "risk_factors": ["Faiz riski"],
        "aligned_points": [],
        "conflicting_points": [],
        "watch_items": ["Enflasyon verisi izlenmeli"],
    }


def test_ai_output_validator_accepts_safe_output():
    assert validate_ai_output(_safe_output())


@pytest.mark.parametrize(
    "unsafe_text",
    [
        "AL fırsatı",
        "SAT fırsatı",
        "Bu hisse alınabilir",
        "Bu hisse satılabilir",
        "Pozisyon açılmalı",
        "Pozisyon kapatılmalı",
        "Hedef fiyat 120 TL",
        "Stop 95 TL",
        "BUY",
        "SELL",
        "AL fД±rsatД±",
    ],
)
def test_ai_output_validator_rejects_trade_language(unsafe_text):
    data = _safe_output()
    data["summary"] = unsafe_text
    assert not validate_ai_output(data)


def test_ai_output_validator_rejects_technical_score():
    data = _safe_output()
    data["technical_score"] = 78
    assert not validate_ai_output(data)


def test_ai_output_validator_rejects_missing_required_field():
    data = _safe_output()
    del data["summary"]
    assert not validate_ai_output(data)
