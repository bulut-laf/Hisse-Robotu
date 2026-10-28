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