from __future__ import annotations

from dataclasses import dataclass
import base64
import html as html_lib
import re
import shutil
import ssl
import subprocess
from urllib.error import URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


ERSTE_MARKET_BASE_URL = "https://www.erstemarket.hu"
ERSTE_FUND_SEARCH_URL = f"{ERSTE_MARKET_BASE_URL}/befektetesi_alapok/kereses"

_ISIN_RE = re.compile(r"\b[A-Z]{2}[A-Z0-9]{9}[0-9]\b")
_DETAIL_RE = re.compile(
    r"""(?:href=["'](?P<href>[^"']*/befektetesi_alapok/alap/(?P<isin>[A-Z]{2}[A-Z0-9]{9}[0-9])[^"']*)["'])""",
    re.IGNORECASE,
)
_SCRIPT_SRC_RE = re.compile(
    r"""<script[^>]+src=["']([^"']+)["']""",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class ErsteDiscoveryResult:
    source_url: str
    isins: tuple[str, ...]
    detail_urls: tuple[str, ...]
    script_urls: tuple[str, ...]
    html_length: int

    @property
    def fund_count(self) -> int:
        return len(self.isins)


def _unique_sorted(values: list[str]) -> tuple[str, ...]:
    return tuple(sorted(set(values)))


def discover_from_search_html(
    html: str,
    *,
    source_url: str = ERSTE_FUND_SEARCH_URL,
) -> ErsteDiscoveryResult:
    decoded = html_lib.unescape(html or "")

    detail_pairs: list[tuple[str, str]] = []
    for match in _DETAIL_RE.finditer(decoded):
        isin = match.group("isin").upper()
        href = match.group("href")
        detail_pairs.append((isin, urljoin(source_url, href)))

    detail_isins = [isin for isin, _ in detail_pairs]
    all_isins = [item.upper() for item in _ISIN_RE.findall(decoded)]
    isins = _unique_sorted(detail_isins + all_isins)

    detail_urls = _unique_sorted([url for _, url in detail_pairs])
    script_urls = _unique_sorted(
        [urljoin(source_url, src) for src in _SCRIPT_SRC_RE.findall(decoded)]
    )

    return ErsteDiscoveryResult(
        source_url=source_url,
        isins=isins,
        detail_urls=detail_urls,
        script_urls=script_urls,
        html_length=len(html or ""),
    )


def _der_to_pem(der_bytes: bytes) -> str:
    encoded = base64.b64encode(der_bytes).decode("ascii")
    lines = [encoded[i:i + 64] for i in range(0, len(encoded), 64)]
    return (
        "-----BEGIN CERTIFICATE-----\n"
        + "\n".join(lines)
        + "\n-----END CERTIFICATE-----\n"
    )


def build_verified_ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()

    enum_certificates = getattr(ssl, "enum_certificates", None)
    if enum_certificates is None:
        return context

    pem_blocks: list[str] = []
    for cert_bytes, encoding_type, _trust in enum_certificates("ROOT"):
        if encoding_type == "x509_asn":
            pem_blocks.append(_der_to_pem(cert_bytes))

    if pem_blocks:
        context.load_verify_locations(cadata="".join(pem_blocks))

    return context


def _is_certificate_chain_error(exc: BaseException) -> bool:
    text = repr(exc).casefold()
    return (
        "certificate_verify_failed" in text
        or "certificate verify failed" in text
        or "self-signed certificate in certificate chain" in text
    )


def _fetch_text_via_windows_curl(
    url: str,
    *,
    timeout_seconds: float,
    user_agent: str,
) -> str:
    curl = shutil.which("curl.exe") or shutil.which("curl")
    if not curl:
        raise RuntimeError("WINDOWS_CURL_NOT_FOUND")

    # Certificate verification remains enabled in curl fallback.
    completed = subprocess.run(
        [
            curl,
            "--fail",
            "--location",
            "--silent",
            "--show-error",
            "--max-time",
            str(max(1, int(timeout_seconds))),
            "--user-agent",
            user_agent,
            "--header",
            "Accept: text/html,application/xhtml+xml",
            url,
        ],
        capture_output=True,
        check=False,
    )

    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(
            f"CURL_FETCH_FAILED:{completed.returncode}:{stderr}"
        )

    raw = completed.stdout

    for encoding in ("utf-8", "windows-1250", "iso-8859-2"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass

    return raw.decode("utf-8", errors="replace")


def fetch_text(
    url: str,
    *,
    timeout_seconds: float = 20.0,
    user_agent: str = "Hisse-Robotu/Erste-Hungary-Discovery-v1",
) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    context = build_verified_ssl_context()

    try:
        with urlopen(
            request,
            timeout=timeout_seconds,
            context=context,
        ) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except (URLError, ssl.SSLCertVerificationError) as exc:
        if not _is_certificate_chain_error(exc):
            raise

        return _fetch_text_via_windows_curl(
            url,
            timeout_seconds=timeout_seconds,
            user_agent=user_agent,
        )


def fetch_erste_fund_search_html(
    *,
    timeout_seconds: float = 20.0,
) -> str:
    return fetch_text(
        ERSTE_FUND_SEARCH_URL,
        timeout_seconds=timeout_seconds,
    )


def discover_live_erste_market_funds(
    *,
    timeout_seconds: float = 20.0,
) -> ErsteDiscoveryResult:
    html = fetch_erste_fund_search_html(timeout_seconds=timeout_seconds)
    return discover_from_search_html(html)