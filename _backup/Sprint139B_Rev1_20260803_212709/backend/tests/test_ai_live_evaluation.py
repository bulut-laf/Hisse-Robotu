from backend.app.market_context.ai_live_evaluation import (
    build_live_evaluation_prompt,
    evaluate_daily_package_with_ai,
)
from backend.app.market_context.ai_provider import AIProviderResult


SAFE_OUTPUT = {
    "summary": "Temkinli görünüm",
    "positive_factors": ["Dış piyasa desteği"],
    "risk_factors": ["Faiz belirsizliği"],
    "aligned_points": [],
    "conflicting_points": [],
    "watch_items": ["Enflasyon verisi"],
}


class FakeProvider:
    def evaluate(self, prompt):
        return AIProviderResult(
            provider="gemini",
            model="fake-model",
            output=SAFE_OUTPUT,
            elapsed_seconds=0.01,
        )


class UnsafeProvider:
    def evaluate(self, prompt):
        output = dict(SAFE_OUTPUT)
        output["summary"] = "AL fırsatı"
        return AIProviderResult(
            provider="gemini",
            model="fake-model",
            output=output,
            elapsed_seconds=0.01,
        )


def test_live_prompt_supports_foreign_language_input():
    prompt = build_live_evaluation_prompt(
        {
            "source": "Foreign broker",
            "text": "We remain overweight on the banking sector.",
        }
    )
    assert "Yabancı dildeki finansal metinleri" in prompt
    assert "overweight" in prompt


def test_live_evaluation_accepts_safe_provider_output():
    result = evaluate_daily_package_with_ai(
        {"reports": [{"text": "Market context"}]},
        provider=FakeProvider(),
    )
    assert result["ok"] is True
    assert result["status"] == "accepted"
    assert result["provider"] == "gemini"
    assert result["output"] == SAFE_OUTPUT


def test_live_evaluation_rejects_trade_language():
    result = evaluate_daily_package_with_ai(
        {"reports": [{"text": "Market context"}]},
        provider=UnsafeProvider(),
    )
    assert result["ok"] is False
    assert result["status"] == "rejected"
    assert result["output"] == {}


def test_live_evaluation_rejects_empty_input_without_provider_call():
    result = evaluate_daily_package_with_ai(
        {},
        provider=FakeProvider(),
    )
    assert result["ok"] is False
    assert result["status"] == "invalid_input"
