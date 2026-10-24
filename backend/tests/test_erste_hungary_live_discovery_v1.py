from __future__ import annotations

from backend.app.funds.international.erste_hungary_source import (
    ERSTE_FUND_SEARCH_URL,
    discover_from_search_html,
)


def test_discovery_extracts_detail_links_isins_and_scripts():
    html = """
    <html>
      <head><script src="/assets/funds.js"></script></head>
      <body>
        <a href="/befektetesi_alapok/alap/HU0000704200">
          Erste Stock Hungary
        </a>
        <a href="https://www.erstemarket.hu/befektetesi_alapok/alap/HU0000706007">
          Erste Euro Bazis
        </a>
        <script>
          window.seed = {"isin":"HU0000723572"};
        </script>
      </body>
    </html>
    """

    result = discover_from_search_html(html)

    assert result.source_url == ERSTE_FUND_SEARCH_URL
    assert result.isins == (
        "HU0000704200",
        "HU0000706007",
        "HU0000723572",
    )
    assert result.detail_urls == (
        "https://www.erstemarket.hu/befektetesi_alapok/alap/HU0000704200",
        "https://www.erstemarket.hu/befektetesi_alapok/alap/HU0000706007",
    )
    assert result.script_urls == (
        "https://www.erstemarket.hu/assets/funds.js",
    )


def test_discovery_is_deterministic_and_deduplicates():
    html = """
    HU0000704200
    HU0000704200
    <a href="/befektetesi_alapok/alap/HU0000704200">x</a>
    """
    result = discover_from_search_html(html)
    assert result.isins == ("HU0000704200",)
    assert result.fund_count == 1

def test_verified_ssl_context_keeps_verification_enabled():
    import ssl

    from backend.app.funds.international.erste_hungary_source import (
        build_verified_ssl_context,
    )

    context = build_verified_ssl_context()

    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True

def test_certificate_error_detector():
    from backend.app.funds.international.erste_hungary_source import (
        _is_certificate_chain_error,
    )

    assert _is_certificate_chain_error(
        RuntimeError(
            "SSL: CERTIFICATE_VERIFY_FAILED self-signed certificate in certificate chain"
        )
    )
    assert not _is_certificate_chain_error(
        RuntimeError("HTTP 404")
    )


def test_curl_fallback_command_does_not_disable_tls_verification(monkeypatch):
    import backend.app.funds.international.erste_hungary_source as source

    captured = {}

    class Result:
        returncode = 0
        stdout = b"<html></html>"
        stderr = b""

    def fake_run(command, **kwargs):
        captured["command"] = list(command)
        return Result()

    monkeypatch.setattr(source.shutil, "which", lambda _name: "curl.exe")
    monkeypatch.setattr(source.subprocess, "run", fake_run)

    result = source._fetch_text_via_windows_curl(
        "https://example.invalid",
        timeout_seconds=5,
        user_agent="test-agent",
    )

    assert result == "<html></html>"
    assert "--insecure" not in captured["command"]
    assert "-k" not in captured["command"]