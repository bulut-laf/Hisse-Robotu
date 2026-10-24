import pytest

from backend.app.market_context.image_input import (
    GeminiMarketContextImageExtractor,
    MarketContextImageExtractionError,
    validate_market_context_image,
)


PNG = b"\x89PNG\r\n\x1a\n" + b"retry-sample"


def _image():
    return validate_market_context_image(
        filename="retry.png",
        mime_type="image/png",
        data=PNG,
    )


def _transient(status_code: int) -> MarketContextImageExtractionError:
    return MarketContextImageExtractionError(
        f"Gemini görsel okuma HTTP hatası: {status_code}. temporary",
        status_code=status_code,
        retryable=status_code in {429, 503},
    )


def test_503_sonrasi_basarili_yanit_yeniden_denenir(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    calls = {"count": 0}
    sleeps = []

    def transport(url, headers, payload, timeout):
        calls["count"] += 1
        if calls["count"] == 1:
            raise _transient(503)
        return {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}

    result = GeminiMarketContextImageExtractor(
        transport=transport,
        retry_delays_seconds=(2.0, 4.0, 8.0),
        sleep_fn=sleeps.append,
        jitter_fn=lambda: 0.0,
    ).extract(_image())

    assert result.text == "ok"
    assert calls["count"] == 2
    assert sleeps == [2.0]


def test_503_icin_2_4_8_saniye_backoff_uygulanir(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    calls = {"count": 0}
    sleeps = []

    def transport(url, headers, payload, timeout):
        calls["count"] += 1
        if calls["count"] < 4:
            raise _transient(503)
        return {"candidates": [{"content": {"parts": [{"text": "sonunda ok"}]}}]}

    result = GeminiMarketContextImageExtractor(
        transport=transport,
        retry_delays_seconds=(2.0, 4.0, 8.0),
        sleep_fn=sleeps.append,
        jitter_fn=lambda: 0.0,
    ).extract(_image())

    assert result.text == "sonunda ok"
    assert calls["count"] == 4
    assert sleeps == [2.0, 4.0, 8.0]


def test_429_da_gecici_hata_olarak_yeniden_denenir(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    calls = {"count": 0}

    def transport(url, headers, payload, timeout):
        calls["count"] += 1
        if calls["count"] == 1:
            raise _transient(429)
        return {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}

    result = GeminiMarketContextImageExtractor(
        transport=transport,
        retry_delays_seconds=(0.0,),
        sleep_fn=lambda value: None,
        jitter_fn=lambda: 0.0,
    ).extract(_image())

    assert result.text == "ok"
    assert calls["count"] == 2


def test_400_gibi_kalici_hata_yeniden_denenmez(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    calls = {"count": 0}

    def transport(url, headers, payload, timeout):
        calls["count"] += 1
        raise MarketContextImageExtractionError(
            "Gemini görsel okuma HTTP hatası: 400. invalid",
            status_code=400,
            retryable=False,
        )

    with pytest.raises(MarketContextImageExtractionError, match="400"):
        GeminiMarketContextImageExtractor(
            transport=transport,
            retry_delays_seconds=(0.0, 0.0, 0.0),
            sleep_fn=lambda value: None,
            jitter_fn=lambda: 0.0,
        ).extract(_image())

    assert calls["count"] == 1


def test_tum_503_deneme_haklari_biterse_temiz_manuel_mesaj_verir(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    calls = {"count": 0}

    def transport(url, headers, payload, timeout):
        calls["count"] += 1
        raise _transient(503)

    with pytest.raises(
        MarketContextImageExtractionError,
        match="4 deneme başarısız",
    ) as exc_info:
        GeminiMarketContextImageExtractor(
            transport=transport,
            retry_delays_seconds=(0.0, 0.0, 0.0),
            sleep_fn=lambda value: None,
            jitter_fn=lambda: 0.0,
        ).extract(_image())

    assert calls["count"] == 4
    assert exc_info.value.status_code == 503
    assert exc_info.value.retryable is True
    assert "Görsel arşivde korunuyor" in str(exc_info.value)


def test_jitter_350_milisaniye_ile_sinirlanir(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    calls = {"count": 0}
    sleeps = []

    def transport(url, headers, payload, timeout):
        calls["count"] += 1
        if calls["count"] == 1:
            raise _transient(503)
        return {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}

    GeminiMarketContextImageExtractor(
        transport=transport,
        retry_delays_seconds=(2.0,),
        sleep_fn=sleeps.append,
        jitter_fn=lambda: 99.0,
    ).extract(_image())

    assert sleeps == [2.35]


def test_negatif_retry_gecikmesi_reddedilir():
    with pytest.raises(ValueError, match="negatif"):
        GeminiMarketContextImageExtractor(
            retry_delays_seconds=(-1.0,),
        )
