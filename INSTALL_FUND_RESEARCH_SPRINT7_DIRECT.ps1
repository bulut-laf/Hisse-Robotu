$ErrorActionPreference = "Stop"
$ProjectRoot = "D:\Projects\Hisse-Robotu"
Set-Location $ProjectRoot

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupRoot = Join-Path $ProjectRoot "_backups\fund_research_sprint7_$stamp"
New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null

$moduleRelative = "backend\app\funds\erste_market.py"
$testRelative = "backend\tests\test_fund_research_sprint7.py"
$notesRelative = "PROJECT_NOTES_FUND_RESEARCH_SPRINT7.md"

$module = @'
"""Erste Market public fund-page connector.

Fetches only a user-requested Erste Market comparison URL. The connector records
retrieval metadata and extracts visible text conservatively; it never invents
missing values and does not place orders or make investment recommendations.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import quote


DEFAULT_BASE_URL = "https://www.erstemarket.hu/befektetesi_alapok/osszehasonlitas"


@dataclass(frozen=True)
class SourceFetchResult:
    ok: bool
    requested_url: str
    source_name: str
    retrieved_at: str
    http_status: int | None
    content_type: str | None
    title: str | None
    text: str
    error: str | None


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._title_depth = 0
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in ("script", "style", "noscript", "svg"):
            self._skip_depth += 1
        if tag == "title":
            self._title_depth += 1

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in ("script", "style", "noscript", "svg") and self._skip_depth:
            self._skip_depth -= 1
        if tag == "title" and self._title_depth:
            self._title_depth -= 1

    def handle_data(self, data: str) -> None:
        value = " ".join(data.split())
        if not value:
            return
        if self._title_depth:
            self.title_parts.append(value)
        if not self._skip_depth:
            self.text_parts.append(value)


def build_comparison_url(
    isin: str,
    *,
    interval_days: int = 365,
    base_url: str = DEFAULT_BASE_URL,
) -> str:
    normalized = (isin or "").strip().upper()
    if len(normalized) != 12 or not normalized.isalnum():
        raise ValueError("invalid_isin")
    if not isinstance(interval_days, int) or interval_days < 1 or interval_days > 10000:
        raise ValueError("invalid_interval_days")
    separator = "&" if "?" in base_url else "?"
    return (
        f"{base_url}{separator}funds={quote(normalized)}"
        f"&intervallum={interval_days}"
    )


def parse_visible_page(html: str) -> dict[str, Any]:
    if not isinstance(html, str):
        raise TypeError("html_must_be_text")
    parser = _VisibleTextParser()
    parser.feed(html.lstrip("\ufeff"))
    title = " ".join(parser.title_parts).strip() or None
    text = " ".join(parser.text_parts).strip()
    return {
        "title": title,
        "text": text,
        "has_visible_text": bool(text),
    }


def fetch_erste_market_page(
    isin: str,
    *,
    interval_days: int = 365,
    timeout_seconds: float = 15.0,
    opener: Callable[..., Any] | None = None,
    now: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    """Fetch the public comparison page; opener and clock are injectable for tests."""
    url = build_comparison_url(isin, interval_days=interval_days)
    clock = now or (lambda: datetime.now(timezone.utc))
    retrieved_at = clock().isoformat()
    request = Request(
        url,
        headers={
            "User-Agent": "HisseRobotu-FundResearch/1.0 (source verification)",
            "Accept": "text/html,application/xhtml+xml",
        },
        method="GET",
    )
    open_request = opener or urlopen
    try:
        response = open_request(request, timeout=timeout_seconds)
        try:
            status = getattr(response, "status", None) or response.getcode()
            headers = getattr(response, "headers", {})
            content_type = headers.get("Content-Type") if headers else None
            raw = response.read()
        finally:
            close = getattr(response, "close", None)
            if callable(close):
                close()
        charset = "utf-8"
        if content_type and "charset=" in content_type.lower():
            charset = content_type.lower().split("charset=", 1)[1].split(";", 1)[0].strip()
        try:
            html = raw.decode(charset, errors="replace")
        except LookupError:
            html = raw.decode("utf-8", errors="replace")
        parsed = parse_visible_page(html)
        ok = bool(status and 200 <= int(status) < 300 and parsed["has_visible_text"])
        return {
            "ok": ok,
            "requested_url": url,
            "source_name": "Erste Market",
            "retrieved_at": retrieved_at,
            "http_status": int(status) if status is not None else None,
            "content_type": content_type,
            "title": parsed["title"],
            "text": parsed["text"],
            "error": None if ok else "empty_or_unsuccessful_response",
            "data_status": "page_retrieved" if ok else "not_verified",
        }
    except HTTPError as exc:
        return {
            "ok": False, "requested_url": url, "source_name": "Erste Market",
            "retrieved_at": retrieved_at, "http_status": exc.code,
            "content_type": None, "title": None, "text": "",
            "error": f"http_error_{exc.code}", "data_status": "not_verified",
        }
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        return {
            "ok": False, "requested_url": url, "source_name": "Erste Market",
            "retrieved_at": retrieved_at, "http_status": None,
            "content_type": None, "title": None, "text": "",
            "error": f"fetch_failed:{type(exc).__name__}",
            "data_status": "not_verified",
        }


def evidence_record_from_fetch(
    fetch_result: dict[str, Any],
    *,
    isin: str,
    field_name: str,
    field_value: Any,
    source_date: str | None = None,
) -> dict[str, Any]:
    """Create a field-level evidence row; source date must be supplied explicitly."""
    if not fetch_result.get("ok"):
        raise ValueError("source_fetch_not_verified")
    if not source_date:
        raise ValueError("source_date_required")
    return {
        "isin": (isin or "").strip().upper(),
        "field_name": field_name,
        "field_value": field_value,
        "source_name": fetch_result["source_name"],
        "source_url": fetch_result["requested_url"],
        "source_date": source_date,
        "captured_at": fetch_result["retrieved_at"],
    }
'@

$tests = @'
import unittest
from datetime import datetime, timezone
from io import BytesIO

from backend.app.funds.erste_market import (
    build_comparison_url,
    evidence_record_from_fetch,
    fetch_erste_market_page,
    parse_visible_page,
)


class FakeResponse:
    def __init__(self, body, status=200, content_type="text/html; charset=utf-8"):
        self._body = body
        self.status = status
        self.headers = {"Content-Type": content_type}
        self.closed = False

    def read(self):
        return self._body

    def getcode(self):
        return self.status

    def close(self):
        self.closed = True


class ErsteMarketSprint7Tests(unittest.TestCase):
    def test_builds_official_url_with_isin(self):
        url = build_comparison_url("HU0000702006")
        self.assertTrue(url.startswith("https://www.erstemarket.hu/"))
        self.assertIn("funds=HU0000702006", url)
        self.assertIn("intervallum=365", url)

    def test_invalid_isin_rejected(self):
        with self.assertRaises(ValueError):
            build_comparison_url("BAD")

    def test_invalid_interval_rejected(self):
        with self.assertRaises(ValueError):
            build_comparison_url("HU0000702006", interval_days=0)

    def test_parser_extracts_title_and_visible_text(self):
        result = parse_visible_page(
            "<html><head><title>Fund page</title><script>secret()</script></head>"
            "<body><h1>ISIN</h1><p>HU0000702006</p></body></html>"
        )
        self.assertEqual(result["title"], "Fund page")
        self.assertIn("HU0000702006", result["text"])
        self.assertNotIn("secret", result["text"])

    def test_parser_handles_utf8_bom(self):
        result = parse_visible_page("\ufeff<html><body><p>Árfolyam</p></body></html>")
        self.assertIn("Árfolyam", result["text"])

    def test_successful_fetch_records_source_and_time(self):
        response = FakeResponse(b"<html><title>Erste</title><body>Fund value</body></html>")
        fixed_time = lambda: datetime(2026, 10, 28, tzinfo=timezone.utc)
        result = fetch_erste_market_page(
            "HU0000702006",
            opener=lambda request, timeout: response,
            now=fixed_time,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["source_name"], "Erste Market")
        self.assertEqual(result["retrieved_at"], "2026-10-28T00:00:00+00:00")
        self.assertTrue(response.closed)

    def test_http_error_is_not_marked_verified(self):
        from urllib.error import HTTPError
        result = fetch_erste_market_page(
            "HU0000702006",
            opener=lambda request, timeout: (_ for _ in ()).throw(
                HTTPError(request.full_url, 503, "unavailable", {}, None)
            ),
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["data_status"], "not_verified")
        self.assertEqual(result["http_status"], 503)

    def test_empty_page_is_not_marked_verified(self):
        result = fetch_erste_market_page(
            "HU0000702006",
            opener=lambda request, timeout: FakeResponse(b"<html><body></body></html>"),
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["data_status"], "not_verified")

    def test_evidence_requires_explicit_source_date(self):
        result = {
            "ok": True, "source_name": "Erste Market",
            "requested_url": "https://www.erstemarket.hu/fund",
            "retrieved_at": "2026-10-28T00:00:00+00:00",
        }
        with self.assertRaises(ValueError):
            evidence_record_from_fetch(
                result, isin="HU0000702006", field_name="currency",
                field_value="HUF",
            )

    def test_evidence_record_keeps_source_fields(self):
        result = {
            "ok": True, "source_name": "Erste Market",
            "requested_url": "https://www.erstemarket.hu/fund",
            "retrieved_at": "2026-10-28T00:00:00+00:00",
        }
        record = evidence_record_from_fetch(
            result, isin="hu0000702006", field_name="currency",
            field_value="HUF", source_date="2026-10-27",
        )
        self.assertEqual(record["isin"], "HU0000702006")
        self.assertEqual(record["source_date"], "2026-10-27")
        self.assertEqual(record["captured_at"], result["retrieved_at"])


if __name__ == "__main__":
    unittest.main()
'@

$notes = @'
# Fund Research Sprint 7 — Erste Market source connector

## Scope
- Adds a network connector for a public Erste Market fund-comparison page, with timeout and injectable opener for tests.
- Records requested URL, source name, retrieval timestamp, HTTP status, content type, title, visible text and fetch status.
- Builds an ISIN-specific comparison URL.
- Supports field-level evidence records only when a source date is explicitly supplied.
- Failed, empty or non-2xx responses remain `not_verified`.
- This connector extracts visible page text; it does not yet map every page field into normalized NAV/return/fee fields. Do not treat page retrieval as verified fund facts.
- No trades or investment recommendations are produced.

## Official source
Erste Market public fund comparison page:
https://www.erstemarket.hu/befektetesi_alapok/osszehasonlitas

## Target tests
`.\.venv\Scripts\python.exe -m pytest backend\tests\test_fund_research_sprint7.py -q`

## Full regression
`.\.venv\Scripts\python.exe -m pytest`
'@

$payloads = @{
    $moduleRelative = $module
    $testRelative = $tests
    $notesRelative = $notes
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
foreach ($relative in $payloads.Keys) {
    $destination = Join-Path $ProjectRoot $relative
    if (Test-Path $destination) {
        $backupDestination = Join-Path $backupRoot $relative
        New-Item -ItemType Directory -Force -Path (Split-Path $backupDestination -Parent) | Out-Null
        Copy-Item $destination $backupDestination -Force
    }
    New-Item -ItemType Directory -Force -Path (Split-Path $destination -Parent) | Out-Null
    [System.IO.File]::WriteAllText($destination, $payloads[$relative], $utf8NoBom)
}

Write-Host "`nSprint 7 dosyalari olusturuldu. Yedek: $backupRoot"
Write-Host "`n--- HEDEF TESTLER ---"
& .\.venv\Scripts\python.exe -m pytest $testRelative -q
if ($LASTEXITCODE -ne 0) {
    throw "Sprint 7 hedef testleri basarisiz. Tam regresyona gecmeyin."
}
Write-Host "`nHedef testler gecti. Simdi tam regresyonu calistirin:"
Write-Host ".\.venv\Scripts\python.exe -m pytest"
