import base64

import pytest

from backend.app.market_context.image_input import (
    GeminiMarketContextImageExtractor,
    MarketContextImageExtractionError,
    validate_market_context_image,
)


PNG = b"\x89PNG\r\n\x1a\n" + b"sample"


def _image():
    return validate_market_context_image(
        filename="screen.png",
        mime_type="image/png",
        data=PNG,
    )


def test_gemini_inline_data_payload_kullanir(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    captured = {}

    def transport(url, headers, payload, timeout):
        captured.update(url=url, headers=headers, payload=payload, timeout=timeout)
        return {
            "candidates": [
                {"content": {"parts": [{"text": "BIST 100 destek 13.000"}]}}
            ]
        }

    result = GeminiMarketContextImageExtractor(
        model="gemini-test",
        timeout_seconds=3,
        transport=transport,
    ).extract(_image())

    part = captured["payload"]["contents"][0]["parts"][0]["inline_data"]
    assert part["mime_type"] == "image/png"
    assert base64.b64decode(part["data"]) == PNG
    assert captured["headers"]["x-goog-api-key"] == "test-key"
    assert result.text == "BIST 100 destek 13.000"
    assert result.provider == "gemini"


def test_prompt_yorum_ve_uydurma_yasagi_icerir(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    captured = {}

    def transport(url, headers, payload, timeout):
        captured["payload"] = payload
        return {"candidates": [{"content": {"parts": [{"text": "metin"}]}}]}

    GeminiMarketContextImageExtractor(transport=transport).extract(_image())
    prompt = captured["payload"]["contents"][0]["parts"][1]["text"]
    assert "Yorum" in prompt
    assert "görselde olmayan" in prompt
    assert "Sadece çıkarılan metni" in prompt


def test_api_key_yoksa_manuel_giris_mesaji_verir(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(MarketContextImageExtractionError, match="manuel"):
        GeminiMarketContextImageExtractor().extract(_image())


def test_bos_gemini_yaniti_reddedilir(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    def transport(url, headers, payload, timeout):
        return {"candidates": [{"content": {"parts": []}}]}

    with pytest.raises(MarketContextImageExtractionError, match="çıkaramadı"):
        GeminiMarketContextImageExtractor(transport=transport).extract(_image())


def test_kod_blogunun_dis_citi_temizlenir(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    def transport(url, headers, payload, timeout):
        return {
            "candidates": [
                {"content": {"parts": [{"text": "```text\nSatır 1\nSatır 2\n```"}]}}
            ]
        }

    result = GeminiMarketContextImageExtractor(transport=transport).extract(_image())
    assert result.text == "Satır 1\nSatır 2"
