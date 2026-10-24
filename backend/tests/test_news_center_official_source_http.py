from io import BytesIO
from urllib.error import HTTPError, URLError

import pytest

import backend.app.news_center.official_source_http as http


class DemoError(RuntimeError):
    pass


class _Headers:
    def __init__(self, content_type="text/html; charset=utf-8"):
        self.content_type = content_type

    def get(self, key, default=""):
        if key.lower() == "content-type":
            return self.content_type
        return default


class _Response:
    def __init__(self, body=b"ok", *, url="https://example.test/x", content_type="text/html"):
        self._body = body
        self._url = url
        self.headers = _Headers(content_type)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def geturl(self):
        return self._url

    def read(self, size=-1):
        return self._body[:size] if size >= 0 else self._body


def test_ortak_sabitler_korunur():
    assert http.OFFICIAL_SOURCE_DEFAULT_TIMEOUT_SECONDS == 10
    assert http.OFFICIAL_SOURCE_MAX_RESPONSE_BYTES == 2_000_000
    assert http.OFFICIAL_SOURCE_MIN_TIMEOUT_SECONDS == 1
    assert http.OFFICIAL_SOURCE_MAX_TIMEOUT_SECONDS == 30


@pytest.mark.parametrize("value", (1, 10, 30))
def test_timeout_gecerli(value):
    assert http.validate_official_source_timeout(value) == value


@pytest.mark.parametrize("value", (0, 31, 1.5, "10"))
def test_timeout_gecersiz(value):
    with pytest.raises(ValueError, match="1-30"):
        http.validate_official_source_timeout(value)


def test_http_get_sonucu_standardize_edilir(monkeypatch):
    monkeypatch.setattr(
        http,
        "urlopen",
        lambda request, timeout: _Response(
            b"<html>ok</html>",
            url="https://example.test/final",
            content_type="text/html; charset=utf-8",
        ),
    )
    result = http.fetch_official_source_bytes(
        "https://example.test/start",
        10,
        user_agent="Test-Agent",
        error_type=DemoError,
        source_label="TEST",
    )
    assert result.body == b"<html>ok</html>"
    assert result.final_url == "https://example.test/final"
    assert "text/html" in result.content_type


def test_http_error_kaynak_etiketiyle_eslenir(monkeypatch):
    http_error = None

    def fail(request, timeout):
        nonlocal http_error
        http_error = HTTPError(request.full_url, 503, "busy", {}, None)
        raise http_error

    monkeypatch.setattr(http, "urlopen", fail)
    try:
        with pytest.raises(DemoError, match="TEST HTTP hatası: 503"):
            http.fetch_official_source_bytes(
                "https://example.test/x", 10,
                user_agent="UA", error_type=DemoError, source_label="TEST"
            )
    finally:
        if http_error is not None:
            http_error.close()

def test_url_error_kaynak_etiketiyle_eslenir(monkeypatch):
    def fail(request, timeout):
        raise URLError("offline")
    monkeypatch.setattr(http, "urlopen", fail)
    with pytest.raises(DemoError, match="TEST bağlantı hatası"):
        http.fetch_official_source_bytes(
            "https://example.test/x", 10,
            user_agent="UA", error_type=DemoError, source_label="TEST"
        )


def test_timeout_error_kaynak_etiketiyle_eslenir(monkeypatch):
    def fail(request, timeout):
        raise TimeoutError("late")
    monkeypatch.setattr(http, "urlopen", fail)
    with pytest.raises(DemoError, match="zaman aşımına uğradı"):
        http.fetch_official_source_bytes(
            "https://example.test/x", 10,
            user_agent="UA", error_type=DemoError, source_label="TEST"
        )


def test_fetch_boyut_siniri(monkeypatch):
    monkeypatch.setattr(
        http,
        "urlopen",
        lambda request, timeout: _Response(b"x" * 11),
    )
    with pytest.raises(DemoError, match="boyutu sınırını"):
        http.fetch_official_source_bytes(
            "https://example.test/x", 10,
            user_agent="UA", error_type=DemoError, source_label="TEST",
            max_response_bytes=10,
        )


def test_html_content_type_zorunlu():
    with pytest.raises(DemoError, match="HTML değil"):
        http.validate_official_source_html_payload(
            b"{}", "application/json",
            error_type=DemoError, source_label="TEST"
        )


def test_injected_fetcher_boyut_kontrolu_ortakta():
    with pytest.raises(DemoError, match="boyutu sınırını"):
        http.validate_official_source_html_payload(
            b"x" * 11, "text/html",
            error_type=DemoError, source_label="TEST", max_response_bytes=10
        )


def test_utf8_decode():
    assert http.decode_official_source_html(
        "İstanbul".encode("utf-8"),
        error_type=DemoError, source_label="TEST"
    ) == "İstanbul"


def test_iso_8859_9_fallback_decode():
    raw = "İstanbul".encode("iso-8859-9")
    assert http.decode_official_source_html(
        raw,
        error_type=DemoError, source_label="TEST"
    ) == "İstanbul"
