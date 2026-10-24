from __future__ import annotations

from dataclasses import dataclass
import re
from urllib.parse import urljoin

from .erste_hungary_source import ERSTE_MARKET_BASE_URL, fetch_text


ERSTE_FUNDS_BUNDLE_URL = (
    ERSTE_MARKET_BASE_URL
    + "/min-js?f=js/modules/funds.js&v=1.104"
)

_QUOTED_RE = re.compile(
    r"""(?P<quote>["'])(?P<value>.*?)(?P=quote)""",
    re.DOTALL,
)

_INTERESTING_TOKEN_RE = re.compile(
    r"(fund|alap|befektet|keres|search|ajax|api|instrument|product|portfolio|price|hozam)",
    re.IGNORECASE,
)

_HTTP_CALL_RE = re.compile(
    r"""(?P<call>
        \$\.ajax\s*\(
        |\$\.get(?:JSON)?\s*\(
        |\$\.post\s*\(
        |fetch\s*\(
        |axios\.(?:get|post)\s*\(
    )""",
    re.IGNORECASE | re.VERBOSE,
)


@dataclass(frozen=True, slots=True)
class EndpointDiscovery:
    source_url: str
    bundle_length: int
    string_candidates: tuple[str, ...]
    absolute_url_candidates: tuple[str, ...]
    call_snippets: tuple[str, ...]


def _clean_candidate(value: str) -> str:
    return (
        value.replace("\\/", "/")
        .replace("\\u002F", "/")
        .replace("\\u002f", "/")
        .strip()
    )


def _is_candidate(value: str) -> bool:
    if len(value) < 2 or len(value) > 500:
        return False
    if not _INTERESTING_TOKEN_RE.search(value):
        return False

    return (
        value.startswith("/")
        or value.startswith("http://")
        or value.startswith("https://")
        or "ajax" in value.casefold()
        or "api" in value.casefold()
        or "fund" in value.casefold()
        or "alap" in value.casefold()
    )


def discover_endpoint_candidates(
    javascript: str,
    *,
    source_url: str = ERSTE_FUNDS_BUNDLE_URL,
) -> EndpointDiscovery:
    candidates: set[str] = set()

    for match in _QUOTED_RE.finditer(javascript or ""):
        value = _clean_candidate(match.group("value"))
        if _is_candidate(value):
            candidates.add(value)

    absolute_urls: set[str] = set()
    for value in candidates:
        if value.startswith("http://") or value.startswith("https://"):
            absolute_urls.add(value)
        elif value.startswith("/"):
            absolute_urls.add(urljoin(ERSTE_MARKET_BASE_URL, value))

    snippets: set[str] = set()
    for match in _HTTP_CALL_RE.finditer(javascript or ""):
        start = max(0, match.start() - 220)
        end = min(len(javascript), match.start() + 700)
        snippet = " ".join((javascript[start:end]).split())
        if _INTERESTING_TOKEN_RE.search(snippet):
            snippets.add(snippet)

    return EndpointDiscovery(
        source_url=source_url,
        bundle_length=len(javascript or ""),
        string_candidates=tuple(sorted(candidates)),
        absolute_url_candidates=tuple(sorted(absolute_urls)),
        call_snippets=tuple(sorted(snippets)),
    )


def fetch_funds_bundle(*, timeout_seconds: float = 30.0) -> str:
    return fetch_text(
        ERSTE_FUNDS_BUNDLE_URL,
        timeout_seconds=timeout_seconds,
        user_agent="Hisse-Robotu/Erste-Hungary-Endpoint-Discovery-v1",
    )


def discover_live_funds_endpoints(
    *,
    timeout_seconds: float = 30.0,
) -> EndpointDiscovery:
    javascript = fetch_funds_bundle(timeout_seconds=timeout_seconds)
    return discover_endpoint_candidates(javascript)