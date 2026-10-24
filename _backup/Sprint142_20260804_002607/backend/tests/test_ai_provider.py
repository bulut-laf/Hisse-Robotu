import pytest

from backend.app.market_context.ai_provider import (
    AIProviderConfig,
    AIProviderError,
    GeminiProvider,
    OpenAIProvider,
    build_provider,
)


SAFE_OUTPUT = {
    "summary": "Temkinli görünüm",
    "positive_factors": ["Dış piyasa desteği"],
    "risk_factors": ["Faiz belirsizliği"],
    "aligned_points": ["İki raporda volatilite vurgusu var"],
    "conflicting_points": [],
    "watch_items": ["Enflasyon verisi"],
}


def test_default_provider_is_gemini(monkeypatch):
    monkeypatch.delenv("HISSE_ROBOTU_AI_PROVIDER", raising=False)
    config = AIProviderConfig.from_environment()
    assert config.provider == "gemini"
    assert config.model == "gemini-2.5-flash-lite"


def test_gemini_provider_uses_structured_json_and_api_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    captured = {}

    def transport(url, headers, payload, timeout):
        captured.update(url=url, headers=headers, payload=payload, timeout=timeout)
        import json
        return {
            "candidates": [
                {"content": {"parts": [{"text": json.dumps(SAFE_OUTPUT)}]}}
            ]
        }

    provider = GeminiProvider(
        AIProviderConfig(
            provider="gemini",
            model="gemini-2.5-flash-lite",
            max_retries=0,
        ),
        transport=transport,
    )
    result = provider.evaluate("test prompt")
    assert result.output == SAFE_OUTPUT
    assert captured["headers"]["x-goog-api-key"] == "test-key"
    assert (
        captured["payload"]["generationConfig"]["responseMimeType"]
        == "application/json"
    )


def test_openai_provider_is_explicit_opt_in(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")

    def transport(url, headers, payload, timeout):
        import json
        return {
            "output": [
                {"content": [{"text": json.dumps(SAFE_OUTPUT)}]}
            ]
        }

    provider = OpenAIProvider(
        AIProviderConfig(
            provider="openai",
            model="gpt-5.6-luna",
            max_retries=0,
        ),
        transport=transport,
    )
    result = provider.evaluate("test prompt")
    assert result.provider == "openai"
    assert result.output == SAFE_OUTPUT


def test_missing_gemini_key_fails_safely(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    provider = GeminiProvider(
        AIProviderConfig(
            provider="gemini",
            model="gemini-2.5-flash-lite",
            max_retries=0,
        )
    )
    with pytest.raises(AIProviderError):
        provider.evaluate("test")


def test_no_automatic_paid_fallback():
    provider = build_provider(
        AIProviderConfig(
            provider="gemini",
            model="gemini-2.5-flash-lite",
        )
    )
    assert isinstance(provider, GeminiProvider)
