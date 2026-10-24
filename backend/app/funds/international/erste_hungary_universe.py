from __future__ import annotations

from dataclasses import dataclass
import html as html_lib
import math
import re
import shutil
import subprocess
import time
from urllib.parse import urlencode, urljoin

from .erste_hungary_source import (
    ERSTE_MARKET_BASE_URL,
    ERSTE_FUND_SEARCH_URL,
    fetch_erste_fund_search_html,
)


_SLIDER_RE = re.compile(
    r"""id=["']returnSlider-input["'][^>]*data-min-max=["'](?P<min>-?\d+),(?P<max>-?\d+)["']""",
    re.IGNORECASE,
)
_DETAIL_RE = re.compile(
    r"""href=["'](?P<href>[^"']*/befektetesi_alapok/alap/(?P<isin>[A-Z]{2}[A-Z0-9]{9}[0-9])[^"']*)["']""",
    re.IGNORECASE,
)
_ISIN_RE = re.compile(r"\b[A-Z]{2}[A-Z0-9]{9}[0-9]\b")

_APPVARS_PATH_PATTERNS = (
    re.compile(
        r"""appVars\s*=\s*\{.*?\bpath\s*:\s*["'](?P<path>[^"']+)["']""",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"""appVars\.path\s*=\s*["'](?P<path>[^"']+)["']""",
        re.IGNORECASE,
    ),
    re.compile(
        r"""["']path["']\s*:\s*["'](?P<path>[^"']+)["']""",
        re.IGNORECASE,
    ),
)


@dataclass(frozen=True, slots=True)
class ErsteUniverseResult:
    total_count: int
    isins: tuple[str, ...]
    detail_urls: tuple[str, ...]
    list_html_length: int
    ret_min: int
    ret_max: int
    app_base_path: str
    list_endpoint: str
    count_endpoint: str
    pages_fetched: int = 1
    page_size_observed: int = 0

    @property
    def coverage_ratio(self) -> float:
        if self.total_count <= 0:
            return 1.0
        return len(self.isins) / self.total_count


def parse_slider_bounds(search_html: str) -> tuple[int, int]:
    match = _SLIDER_RE.search(search_html or "")
    if not match:
        raise ValueError("ERSTE_RETURN_SLIDER_BOUNDS_NOT_FOUND")
    return int(match.group("min")), int(match.group("max"))


def parse_app_base_path(search_html: str) -> str:
    text = html_lib.unescape(search_html or "")

    for pattern in _APPVARS_PATH_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue

        path = match.group("path").strip().replace("\\/", "/")
        if not path:
            continue

        if not path.startswith("/"):
            path = "/" + path
        if not path.endswith("/"):
            path += "/"
        return path

    raise ValueError("ERSTE_APPVARS_PATH_NOT_FOUND")


def build_endpoints(app_base_path: str) -> tuple[str, str]:
    base = urljoin(ERSTE_MARKET_BASE_URL, app_base_path)
    if not base.endswith("/"):
        base += "/"

    list_endpoint = urljoin(
        base,
        "funds/search_results/list?layout=website",
    )
    count_endpoint = urljoin(
        base,
        "funds/search_results/count",
    )
    return list_endpoint, count_endpoint


def build_page_endpoint(
    app_base_path: str,
    *,
    page: int,
    layout: str = "website",
) -> str:
    if page < 1:
        raise ValueError("PAGE_MUST_BE_POSITIVE")

    base = urljoin(ERSTE_MARKET_BASE_URL, app_base_path)
    if not base.endswith("/"):
        base += "/"

    suffix = "funds/search_results/list"
    if page > 1:
        suffix += f"/page:{page}"

    return urljoin(base, suffix) + f"?layout={layout}"


def build_unfiltered_form(*, ret_min: int, ret_max: int) -> list[tuple[str, str]]:
    return [
        ("keyword", ""),
        ("segment", ""),
        ("ret_min", str(ret_min)),
        ("ret_max", str(ret_max)),
    ]


def extract_isins_and_detail_urls(html: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    decoded = html_lib.unescape(html or "")

    pairs: list[tuple[str, str]] = []
    for match in _DETAIL_RE.finditer(decoded):
        isin = match.group("isin").upper()
        href = match.group("href")
        pairs.append((isin, urljoin(ERSTE_MARKET_BASE_URL, href)))

    isins = sorted({isin for isin, _ in pairs})
    if not isins:
        isins = sorted({item.upper() for item in _ISIN_RE.findall(decoded)})

    detail_urls = sorted({url for _, url in pairs})
    return tuple(isins), tuple(detail_urls)


def parse_universe_list_html(
    html: str,
    *,
    total_count: int,
    ret_min: int,
    ret_max: int,
    app_base_path: str = "/",
    list_endpoint: str = "",
    count_endpoint: str = "",
) -> ErsteUniverseResult:
    isins, detail_urls = extract_isins_and_detail_urls(html)

    return ErsteUniverseResult(
        total_count=total_count,
        isins=isins,
        detail_urls=detail_urls,
        list_html_length=len(html or ""),
        ret_min=ret_min,
        ret_max=ret_max,
        app_base_path=app_base_path,
        list_endpoint=list_endpoint,
        count_endpoint=count_endpoint,
        pages_fetched=1,
        page_size_observed=len(isins),
    )


def _curl_post_text(
    url: str,
    form_fields: list[tuple[str, str]],
    *,
    timeout_seconds: float = 30.0,
) -> str:
    curl = shutil.which("curl.exe") or shutil.which("curl")
    if not curl:
        raise RuntimeError("WINDOWS_CURL_NOT_FOUND")

    command = [
        curl,
        "--fail",
        "--location",
        "--silent",
        "--show-error",
        "--max-time",
        str(max(1, int(timeout_seconds))),
        "--user-agent",
        "Hisse-Robotu/Erste-Hungary-Universe-v1",
        "--header",
        "Accept: text/html,application/xhtml+xml,*/*",
        "--header",
        "Content-Type: application/x-www-form-urlencoded; charset=UTF-8",
        "--header",
        f"Referer: {ERSTE_FUND_SEARCH_URL}",
        "--header",
        "X-Requested-With: XMLHttpRequest",
        "--data",
        urlencode(form_fields),
        url,
    ]

    completed = subprocess.run(
        command,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(
            f"CURL_POST_FAILED:{completed.returncode}:{stderr}"
        )

    raw = completed.stdout
    for encoding in ("utf-8", "windows-1250", "iso-8859-2"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="replace")


def fetch_live_universe(
    *,
    timeout_seconds: float = 30.0,
    request_delay_seconds: float = 0.08,
    max_pages: int | None = None,
) -> ErsteUniverseResult:
    search_html = fetch_erste_fund_search_html(
        timeout_seconds=timeout_seconds,
    )

    ret_min, ret_max = parse_slider_bounds(search_html)
    app_base_path = parse_app_base_path(search_html)
    first_list_endpoint, count_endpoint = build_endpoints(app_base_path)

    form = build_unfiltered_form(ret_min=ret_min, ret_max=ret_max)

    count_text = _curl_post_text(
        count_endpoint,
        form,
        timeout_seconds=timeout_seconds,
    ).strip()

    if not re.fullmatch(r"\d+", count_text):
        raise ValueError(
            "INVALID_ERSTE_COUNT_RESPONSE:"
            f"path={app_base_path}:"
            f"endpoint={count_endpoint}:"
            f"body={count_text[:200]}"
        )

    total_count = int(count_text)

    first_html = _curl_post_text(
        first_list_endpoint,
        form,
        timeout_seconds=timeout_seconds,
    )
    first_isins, first_urls = extract_isins_and_detail_urls(first_html)

    page_size = len(first_isins)
    if total_count > 0 and page_size <= 0:
        raise ValueError("ERSTE_FIRST_PAGE_EMPTY_WITH_NONZERO_TOTAL")

    expected_pages = (
        math.ceil(total_count / page_size)
        if page_size > 0
        else 1
    )
    if max_pages is not None:
        expected_pages = min(expected_pages, max_pages)

    all_isins = set(first_isins)
    all_urls = set(first_urls)
    total_html_length = len(first_html)
    pages_fetched = 1

    for page in range(2, expected_pages + 1):
        endpoint = build_page_endpoint(
            app_base_path,
            page=page,
            layout="website",
        )
        html = _curl_post_text(
            endpoint,
            form,
            timeout_seconds=timeout_seconds,
        )
        page_isins, page_urls = extract_isins_and_detail_urls(html)

        total_html_length += len(html)
        pages_fetched += 1

        if not page_isins:
            break

        all_isins.update(page_isins)
        all_urls.update(page_urls)

        if len(all_isins) >= total_count:
            break

        if request_delay_seconds > 0:
            time.sleep(request_delay_seconds)

    return ErsteUniverseResult(
        total_count=total_count,
        isins=tuple(sorted(all_isins)),
        detail_urls=tuple(sorted(all_urls)),
        list_html_length=total_html_length,
        ret_min=ret_min,
        ret_max=ret_max,
        app_base_path=app_base_path,
        list_endpoint=first_list_endpoint,
        count_endpoint=count_endpoint,
        pages_fetched=pages_fetched,
        page_size_observed=page_size,
    )