from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from typing import Callable, Iterable, Mapping
from urllib.parse import urljoin, urlparse

from .free_float_store import (
    FreeFloatJsonStore,
    FreeFloatRecord,
    FreeFloatStoreResult,
)
from .kap_portfolio_ingestion import (
    DEFAULT_TIMEOUT_SECONDS,
    KAP_ALLOWED_HOSTS,
    KapFundPortfolioError,
    _default_fetch,
)


KAP_BIST_COMPANIES_URL = "https://www.kap.org.tr/tr/bist-sirketler"
KAP_FREE_FLOAT_TABLE_URL = (
    "https://www.kap.org.tr/tr/tumKalemler/kpy41_acc5_fiili_dolasimdaki_pay"
)
KAP_COMPANY_SUMMARY_PATH = re.compile(
    r"^/tr/sirket-bilgileri/ozet/([^/?#]+)$",
    re.IGNORECASE,
)
KAP_COMPANY_GENERAL_PATH = re.compile(
    r"^/tr/sirket-bilgileri/genel/([^/?#]+)$",
    re.IGNORECASE,
)
MAX_COMPANY_DIRECTORY_BYTES = 8 * 1024 * 1024
MAX_COMPANY_GENERAL_BYTES = 4 * 1024 * 1024
MAX_FDO_SYMBOLS_PER_REFRESH = 100


FetchBytes = Callable[[str, int], tuple[bytes, str, str]]


class KapFreeFloatError(RuntimeError):
    """Official KAP free-float discovery / parsing error."""


@dataclass(frozen=True, slots=True)
class KapCompanyReference:
    symbol: str
    general_url: str


@dataclass(frozen=True, slots=True)
class KapFreeFloatPopulationFailure:
    symbol: str
    source_ref: str | None
    error: str


@dataclass(frozen=True, slots=True)
class KapFreeFloatPopulationSummary:
    requested: int
    discovered: int
    attempted: int
    inserted: int
    unchanged: int
    failures: tuple[KapFreeFloatPopulationFailure, ...]
    records: tuple[FreeFloatRecord, ...]


class _VisibleLinksParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text_parts: list[str] = []
        self.links: list[tuple[str, str]] = []
        self._skip_depth = 0
        self._anchor_href: str | None = None
        self._anchor_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
            return
        if lowered == "a" and self._skip_depth == 0:
            attrs_map = {str(key).lower(): str(value or "") for key, value in attrs}
            self._anchor_href = attrs_map.get("href") or None
            self._anchor_parts = []

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style", "noscript", "svg"}:
            if self._skip_depth:
                self._skip_depth -= 1
            return
        if lowered == "a" and self._anchor_href is not None:
            text = " ".join(self._anchor_parts).strip()
            self.links.append((self._anchor_href, text))
            self._anchor_href = None
            self._anchor_parts = []

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        clean = " ".join(str(data or "").split())
        if not clean:
            return
        self.text_parts.append(clean)
        if self._anchor_href is not None:
            self._anchor_parts.append(clean)


def _clean_symbol(value: object) -> str:
    symbol = str(value or "").strip().upper()
    if symbol.endswith(".IS"):
        symbol = symbol[:-3]
    if not re.fullmatch(r"[A-Z0-9]{2,12}", symbol):
        raise ValueError("FDO_SYMBOL_INVALID")
    return symbol


def _validate_kap_url(
    url: str,
    *,
    expected_path: str | re.Pattern[str],
    label: str,
) -> str:
    value = str(url or "").strip()
    parsed = urlparse(value)
    if parsed.scheme.lower() != "https":
        raise KapFreeFloatError(f"{label}_HTTPS_REQUIRED")
    if (parsed.hostname or "").lower() not in KAP_ALLOWED_HOSTS:
        raise KapFreeFloatError(f"{label}_HOST_NOT_ALLOWED")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise KapFreeFloatError(f"{label}_AUTH_OR_PORT_NOT_ALLOWED")
    path = parsed.path or ""
    if isinstance(expected_path, str):
        ok = path.rstrip("/").casefold() == expected_path.rstrip("/").casefold()
    else:
        ok = expected_path.fullmatch(path) is not None
    if not ok or parsed.query or parsed.fragment:
        raise KapFreeFloatError(f"{label}_PATH_INVALID")
    return value


def validate_kap_bist_companies_url(url: str) -> str:
    return _validate_kap_url(
        url,
        expected_path="/tr/bist-sirketler",
        label="KAP_BIST_COMPANIES",
    )


def validate_kap_company_general_url(url: str) -> str:
    return _validate_kap_url(
        url,
        expected_path=KAP_COMPANY_GENERAL_PATH,
        label="KAP_COMPANY_GENERAL",
    )


def validate_kap_free_float_table_url(url: str) -> str:
    return _validate_kap_url(
        url,
        expected_path="/tr/tumKalemler/kpy41_acc5_fiili_dolasimdaki_pay",
        label="KAP_FDO_TABLE",
    )


def _decode_html(raw: bytes, content_type: str, *, max_bytes: int, label: str) -> str:
    if len(raw) > max_bytes:
        raise KapFreeFloatError(f"{label}_RESPONSE_TOO_LARGE")
    lowered = str(content_type or "").casefold()
    if "html" not in lowered and not raw.lstrip().startswith(b"<"):
        raise KapFreeFloatError(f"{label}_NOT_HTML")
    for encoding in ("utf-8", "windows-1254", "iso-8859-9"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise KapFreeFloatError(f"{label}_ENCODING_UNSUPPORTED")


def parse_kap_bist_company_directory(
    raw_html: str,
    *,
    symbols: Iterable[str],
) -> Mapping[str, KapCompanyReference]:
    targets = {_clean_symbol(item) for item in symbols}
    if not targets:
        return {}

    parser = _VisibleLinksParser()
    parser.feed(str(raw_html or ""))
    parser.close()

    found: dict[str, KapCompanyReference] = {}
    for href, anchor_text in parser.links:
        absolute = urljoin(KAP_BIST_COMPANIES_URL, href)
        parsed = urlparse(absolute)
        match = KAP_COMPANY_SUMMARY_PATH.fullmatch(parsed.path or "")
        if (
            match is None
            or parsed.scheme.lower() != "https"
            or (parsed.hostname or "").lower() not in KAP_ALLOWED_HOSTS
        ):
            continue
        upper_text = re.sub(r"\s+", " ", anchor_text).upper()
        matches = [
            symbol
            for symbol in targets
            if re.search(rf"(?<![A-Z0-9]){re.escape(symbol)}(?![A-Z0-9])", upper_text)
        ]
        if len(matches) != 1:
            continue
        symbol = matches[0]
        general_path = f"/tr/sirket-bilgileri/genel/{match.group(1)}"
        general_url = urljoin(KAP_BIST_COMPANIES_URL, general_path)
        found[symbol] = KapCompanyReference(symbol=symbol, general_url=general_url)
    return found


def _parse_decimal_tr(value: str) -> str:
    raw = str(value).strip().replace("\u00a0", "").replace(" ", "")
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        raw = raw.replace(",", ".")
    return raw


def parse_kap_free_float_general_page(
    raw_html: str,
    *,
    source_url: str,
    expected_symbol: str,
    observed_on: date,
    ingested_at: datetime | None = None,
) -> FreeFloatRecord:
    validated_url = validate_kap_company_general_url(source_url)
    symbol = _clean_symbol(expected_symbol)

    parser = _VisibleLinksParser()
    parser.feed(str(raw_html or ""))
    parser.close()
    visible = re.sub(r"\s+", " ", " ".join(parser.text_parts)).strip()
    if not visible:
        raise KapFreeFloatError("KAP_FDO_GENERAL_PAGE_EMPTY")

    folded = visible.casefold()
    marker = "fiili dolaşımdaki paylar"
    start = folded.find(marker)
    if start < 0:
        raise KapFreeFloatError("KAP_FDO_SECTION_MISSING")
    section = visible[start:]
    end_match = re.search(
        r"Sermayeyi\s+Temsil\s+Eden\s+Paylara\s+İlişkin\s+Bilgi",
        section,
        re.IGNORECASE,
    )
    if end_match is not None:
        section = section[: end_match.start()]

    row = re.search(
        rf"(?<![A-Z0-9]){re.escape(symbol)}(?![A-Z0-9])\s+"
        r"([0-9][0-9.\s]*,[0-9]+)\s+"
        r"([0-9]+(?:[.,][0-9]+)?)",
        section,
        re.IGNORECASE,
    )
    if row is None:
        raise KapFreeFloatError(f"KAP_FDO_SYMBOL_ROW_MISSING:{symbol}")

    from decimal import Decimal, InvalidOperation
    try:
        free_float_amount = Decimal(_parse_decimal_tr(row.group(1)))
        free_float_ratio_pct = Decimal(_parse_decimal_tr(row.group(2)))
    except InvalidOperation as exc:
        raise KapFreeFloatError(f"KAP_FDO_NUMERIC_INVALID:{symbol}") from exc

    if (
        not free_float_amount.is_finite()
        or free_float_amount <= 0
        or not free_float_ratio_pct.is_finite()
        or free_float_ratio_pct <= 0
        or free_float_ratio_pct > 100
    ):
        raise KapFreeFloatError(f"KAP_FDO_NUMERIC_RANGE_INVALID:{symbol}")

    now = ingested_at or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("ingested_at timezone-aware olmalıdır.")

    # KAP's "Fiili Dolaşımdaki Pay Tutarı (TL)" is the matching nominal unit
    # for the KAP fund report's equity "Nominal Değeri". The legacy field name
    # free_float_shares is retained to preserve the existing read-model contract.
    return FreeFloatRecord(
        symbol=symbol,
        free_float_shares=free_float_amount,
        as_of=observed_on,
        source="KAP",
        source_ref=validated_url,
        ingested_at=now,
    )


def parse_kap_free_float_table(
    raw_html: str,
    *,
    symbols: Iterable[str],
    source_url: str,
    observed_on: date,
    ingested_at: datetime | None = None,
) -> tuple[FreeFloatRecord, ...]:
    validated_url = validate_kap_free_float_table_url(source_url)
    targets = tuple(sorted({_clean_symbol(item) for item in symbols}))
    if not targets:
        return ()

    parser = _VisibleLinksParser()
    parser.feed(str(raw_html or ""))
    parser.close()
    visible = re.sub(r"\s+", " ", " ".join(parser.text_parts)).strip()
    if not visible:
        raise KapFreeFloatError("KAP_FDO_TABLE_EMPTY")

    folded = visible.casefold()
    if "fiili dolaşımdaki pay" not in folded:
        raise KapFreeFloatError("KAP_FDO_TABLE_SECTION_MISSING")

    now = ingested_at or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("ingested_at timezone-aware olmalıdır.")

    from decimal import Decimal, InvalidOperation

    records: list[FreeFloatRecord] = []
    for symbol in targets:
        # Current KAP aggregate table has additional numeric columns
        # between the symbol and the canonical free-float amount/ratio.
        # Prefer that observed wide format. Fall back to the older compact
        # official format used by earlier KAP responses.
        wide_matches = list(
            re.finditer(
                rf"(?<![A-Z0-9]){re.escape(symbol)}(?![A-Z0-9])\s+"
                r"[0-9][0-9.\\s]*,[0-9]+\s+"
                r"[0-9][0-9.\\s]*,[0-9]+\s+"
                r"[0-9][0-9.\\s]*,[0-9]+\s+"
                r"[0-9][0-9.\\s]*,[0-9]+\s+"
                r"[0-9][0-9.\\s]*,[0-9]+\s+"
                r"([0-9][0-9.\\s]*,[0-9]+)\s+"
                r"([0-9]+(?:[.,][0-9]+)?)",
                visible,
                re.IGNORECASE,
            )
        )

        if wide_matches:
            matches = wide_matches
        else:
            matches = list(
                re.finditer(
                    rf"(?<![A-Z0-9]){re.escape(symbol)}(?![A-Z0-9])\s+"
                    r"([0-9][0-9.\\s]*,[0-9]+)\s+"
                    r"([0-9]+(?:[.,][0-9]+)?)",
                    visible,
                    re.IGNORECASE,
                )
            )

        if not matches:
            continue
        try:
            amounts = [Decimal(_parse_decimal_tr(item.group(1))) for item in matches]
            ratios = [Decimal(_parse_decimal_tr(item.group(2))) for item in matches]
            free_float_amount = sum(amounts, Decimal("0"))
            free_float_ratio_pct = sum(ratios, Decimal("0"))
        except InvalidOperation as exc:
            raise KapFreeFloatError(f"KAP_FDO_NUMERIC_INVALID:{symbol}") from exc

        if (
            not free_float_amount.is_finite()
            or free_float_amount <= 0
            or not free_float_ratio_pct.is_finite()
            or free_float_ratio_pct <= 0
            or free_float_ratio_pct > 100
        ):
            raise KapFreeFloatError(f"KAP_FDO_NUMERIC_RANGE_INVALID:{symbol}")

        records.append(
            FreeFloatRecord(
                symbol=symbol,
                free_float_shares=free_float_amount,
                as_of=observed_on,
                source="KAP",
                source_ref=validated_url,
                ingested_at=now,
            )
        )
    return tuple(records)


def discover_kap_company_general_urls(
    *,
    symbols: Iterable[str],
    network_enabled: bool = False,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    fetcher: FetchBytes | None = None,
    directory_url: str = KAP_BIST_COMPANIES_URL,
) -> Mapping[str, KapCompanyReference]:
    targets = tuple(sorted({_clean_symbol(item) for item in symbols}))
    if not network_enabled:
        raise KapFreeFloatError("KAP_FDO_NETWORK_DISABLED")
    if not targets:
        return {}
    if len(targets) > MAX_FDO_SYMBOLS_PER_REFRESH:
        raise KapFreeFloatError("KAP_FDO_SYMBOL_LIMIT_EXCEEDED")
    if timeout_seconds <= 0 or timeout_seconds > 30:
        raise ValueError("timeout_seconds 1-30 aralığında olmalıdır.")

    validated = validate_kap_bist_companies_url(directory_url)
    fetch = fetcher or _default_fetch
    raw, final_url, content_type = fetch(validated, timeout_seconds)
    if validate_kap_bist_companies_url(final_url) != validated:
        raise KapFreeFloatError("KAP_BIST_COMPANIES_REDIRECT_MISMATCH")
    html = _decode_html(
        raw,
        content_type,
        max_bytes=MAX_COMPANY_DIRECTORY_BYTES,
        label="KAP_BIST_COMPANIES",
    )
    return parse_kap_bist_company_directory(html, symbols=targets)


def populate_kap_free_float_for_symbols(
    *,
    store: FreeFloatJsonStore,
    symbols: Iterable[str],
    network_enabled: bool = False,
    observed_on: date | None = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    table_fetcher: FetchBytes | None = None,
    directory_fetcher: FetchBytes | None = None,
    general_fetcher: FetchBytes | None = None,
) -> KapFreeFloatPopulationSummary:
    targets = tuple(sorted({_clean_symbol(item) for item in symbols}))
    if not network_enabled:
        raise KapFreeFloatError("KAP_FDO_NETWORK_DISABLED")
    if not targets:
        return KapFreeFloatPopulationSummary(0, 0, 0, 0, 0, (), ())
    if len(targets) > MAX_FDO_SYMBOLS_PER_REFRESH:
        raise KapFreeFloatError("KAP_FDO_SYMBOL_LIMIT_EXCEEDED")
    if timeout_seconds <= 0 or timeout_seconds > 30:
        raise ValueError("timeout_seconds 1-30 aralığında olmalıdır.")

    # KAP publishes the canonical free-float dataset as one server-rendered table.
    # Fetching this single official table is both more reliable and far less bursty
    # than resolving and requesting one company page per held symbol.
    validated = validate_kap_free_float_table_url(KAP_FREE_FLOAT_TABLE_URL)
    fetch = table_fetcher or _default_fetch
    raw, final_url, content_type = fetch(validated, timeout_seconds)
    if validate_kap_free_float_table_url(final_url) != validated:
        raise KapFreeFloatError("KAP_FDO_TABLE_REDIRECT_MISMATCH")
    html = _decode_html(
        raw,
        content_type,
        max_bytes=MAX_COMPANY_DIRECTORY_BYTES,
        label="KAP_FDO_TABLE",
    )
    observed = observed_on or date.today()
    parsed_records = parse_kap_free_float_table(
        html,
        symbols=targets,
        source_url=validated,
        observed_on=observed,
    )
    by_symbol = {record.symbol: record for record in parsed_records}
    failures = tuple(
        KapFreeFloatPopulationFailure(
            symbol=symbol,
            source_ref=validated,
            error=f"KAP_FDO_SYMBOL_ROW_MISSING:{symbol}",
        )
        for symbol in targets
        if symbol not in by_symbol
    )
    records = tuple(by_symbol[symbol] for symbol in targets if symbol in by_symbol)

    if records:
        store_result: FreeFloatStoreResult = store.upsert(records)
        inserted = store_result.inserted
        unchanged = store_result.unchanged
    else:
        inserted = unchanged = 0

    return KapFreeFloatPopulationSummary(
        requested=len(targets),
        discovered=len(records),
        attempted=len(targets),
        inserted=inserted,
        unchanged=unchanged,
        failures=failures,
        records=records,
    )
