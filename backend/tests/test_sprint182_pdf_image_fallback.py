from __future__ import annotations

import base64

import pytest

from backend.app.market_context.pdf_image_fallback import (
    MAX_PDF_BYTES,
    PdfImageFallbackError,
    PdfImageFallbackProviderError,
    extract_scanned_pdf_text,
)


def _pdf(payload: bytes = b"scan") -> bytes:
    return b"%PDF-1.7\n" + payload


def _success(text: str = "BIST 100 destek 13.700") -> dict:
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


def test_empty_pdf_is_rejected():
    with pytest.raises(PdfImageFallbackError, match="boş"):
        extract_scanned_pdf_text(b"", api_key="x")


def test_non_pdf_signature_is_rejected():
    with pytest.raises(PdfImageFallbackError, match="PDF imzası"):
        extract_scanned_pdf_text(b"not-a-pdf", api_key="x")


def test_oversized_pdf_is_rejected():
    with pytest.raises(PdfImageFallbackError, match="en fazla"):
        extract_scanned_pdf_text(b"%PDF-" + b"x" * MAX_PDF_BYTES, api_key="x")


def test_api_key_is_required(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(PdfImageFallbackError, match="GEMINI_API_KEY"):
        extract_scanned_pdf_text(_pdf())


def test_pdf_is_sent_inline_with_application_pdf_and_safe_prompt():
    captured = {}

    def transport(url, headers, payload, timeout):
        captured.update(url=url, headers=headers, payload=payload, timeout=timeout)
        return _success()

    result = extract_scanned_pdf_text(
        _pdf(b"abc"),
        filename="bulten.pdf",
        api_key="test-key",
        transport=transport,
        jitter_func=lambda _a, _b: 0.0,
    )

    assert result.ok is True
    assert result.text == "BIST 100 destek 13.700"
    parts = captured["payload"]["contents"][0]["parts"]
    assert parts[1]["inlineData"]["mimeType"] == "application/pdf"
    assert base64.b64decode(parts[1]["inlineData"]["data"]).startswith(b"%PDF-")
    prompt = parts[0]["text"]
    assert "uydurma" in prompt.casefold()
    assert "AL/SAT" in prompt
    assert "özetleme" in prompt
    assert captured["headers"]["x-goog-api-key"] == "test-key"


def test_429_is_retried_and_then_succeeds():
    calls = []
    sleeps = []

    def transport(_url, _headers, _payload, _timeout):
        calls.append(1)
        if len(calls) == 1:
            raise PdfImageFallbackProviderError("rate", status_code=429, retriable=True)
        return _success("ok")

    result = extract_scanned_pdf_text(
        _pdf(),
        api_key="x",
        transport=transport,
        sleep_func=sleeps.append,
        jitter_func=lambda _a, _b: 0.0,
    )
    assert result.ok is True
    assert len(calls) == 2
    assert sleeps == [2.0]


def test_400_is_not_retried():
    calls = []
    sleeps = []

    def transport(_url, _headers, _payload, _timeout):
        calls.append(1)
        raise PdfImageFallbackProviderError("bad request", status_code=400, retriable=False)

    result = extract_scanned_pdf_text(
        _pdf(),
        api_key="x",
        transport=transport,
        sleep_func=sleeps.append,
        jitter_func=lambda _a, _b: 0.0,
    )
    assert result.ok is False
    assert len(calls) == 1
    assert sleeps == []
    assert "bad request" in result.error


def test_empty_model_text_returns_safe_error_result():
    result = extract_scanned_pdf_text(
        _pdf(),
        api_key="x",
        transport=lambda *_args: _success("   "),
        sleep_func=lambda _seconds: None,
        jitter_func=lambda _a, _b: 0.0,
    )
    assert result.ok is False
    assert result.status == "provider_error"
    assert result.text == ""
    assert "boş metin" in result.error
