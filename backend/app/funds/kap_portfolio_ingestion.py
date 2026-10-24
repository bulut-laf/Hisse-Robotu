from __future__ import annotations

import calendar
import io
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from .contracts import DataQualityState
from .normalization import normalize_fund_code, parse_decimal_tr
from .portfolio_tracking import (
    FundPortfolioPosition,
    FundPortfolioSnapshot,
    FundPortfolioSnapshotJsonStore,
    PortfolioSnapshotStoreResult,
)


ISTANBUL = ZoneInfo("Europe/Istanbul")
KAP_ALLOWED_HOSTS = frozenset({"kap.org.tr", "www.kap.org.tr"})
KAP_DETAIL_PATH = re.compile(r"^/tr/Bildirim/(\d+)/?$", re.IGNORECASE)
KAP_ATTACHMENT_PATH = re.compile(
    r"^/tr/api/file/download/([A-Za-z0-9_-]+)$",
    re.IGNORECASE,
)
MAX_KAP_DETAIL_BYTES = 4 * 1024 * 1024
MAX_KAP_PORTFOLIO_PDF_BYTES = 12 * 1024 * 1024
MAX_KAP_PORTFOLIO_PDF_PAGES = 150
DEFAULT_TIMEOUT_SECONDS = 10


class KapFundPortfolioError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class KapPortfolioReportReference:
    notification_id: str
    detail_url: str
    attachment_url: str
    attachment_name: str
    publication_at: datetime
    report_year: int
    report_month: int

    @property
    def portfolio_date(self) -> date:
        last_day = calendar.monthrange(self.report_year, self.report_month)[1]
        return date(self.report_year, self.report_month, last_day)


@dataclass(frozen=True, slots=True)
class KapPortfolioIngestionResult:
    reference: KapPortfolioReportReference
    snapshot: FundPortfolioSnapshot
    store_result: PortfolioSnapshotStoreResult


FetchBytes = Callable[[str, int], tuple[bytes, str, str]]
PdfTextExtractor = Callable[[bytes], str]


class _KapDetailHtmlParser(HTMLParser):
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


def _validate_https_kap_url(url: str, *, path_pattern: re.Pattern[str], label: str) -> tuple[str, str]:
    value = str(url or "").strip()
    parsed = urlparse(value)
    if parsed.scheme.lower() != "https":
        raise KapFundPortfolioError(f"{label}_HTTPS_REQUIRED")
    if (parsed.hostname or "").lower() not in KAP_ALLOWED_HOSTS:
        raise KapFundPortfolioError(f"{label}_HOST_NOT_ALLOWED")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise KapFundPortfolioError(f"{label}_AUTH_OR_PORT_NOT_ALLOWED")
    match = path_pattern.fullmatch(parsed.path or "")
    if match is None or parsed.query or parsed.fragment:
        raise KapFundPortfolioError(f"{label}_PATH_INVALID")
    return value, match.group(1)


def validate_kap_portfolio_detail_url(url: str) -> tuple[str, str]:
    return _validate_https_kap_url(url, path_pattern=KAP_DETAIL_PATH, label="KAP_DETAIL")


def validate_kap_attachment_url(url: str) -> tuple[str, str]:
    return _validate_https_kap_url(url, path_pattern=KAP_ATTACHMENT_PATH, label="KAP_ATTACHMENT")


def _default_fetch(url: str, timeout_seconds: int) -> tuple[bytes, str, str]:
    request = Request(
        url,
        headers={
            "User-Agent": "Hisse-Robotu/Fund-Portfolio-V1",
            "Accept": "text/html,application/pdf,application/octet-stream;q=0.9,*/*;q=0.1",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body = response.read(MAX_KAP_PORTFOLIO_PDF_BYTES + 1)
            final_url = response.geturl()
            content_type = str(response.headers.get("Content-Type", ""))
    except HTTPError as exc:
        raise KapFundPortfolioError(f"KAP_HTTP_ERROR:{exc.code}") from exc
    except URLError as exc:
        raise KapFundPortfolioError(f"KAP_CONNECTION_ERROR:{exc.reason}") from exc
    except TimeoutError as exc:
        raise KapFundPortfolioError("KAP_TIMEOUT") from exc
    return body, final_url, content_type


def _decode_html(raw: bytes, content_type: str) -> str:
    lowered = content_type.casefold()
    if "html" not in lowered and not raw.lstrip().startswith(b"<"):
        raise KapFundPortfolioError("KAP_DETAIL_NOT_HTML")
    if len(raw) > MAX_KAP_DETAIL_BYTES:
        raise KapFundPortfolioError("KAP_DETAIL_TOO_LARGE")
    for encoding in ("utf-8", "windows-1254", "iso-8859-9"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise KapFundPortfolioError("KAP_DETAIL_ENCODING_UNSUPPORTED")


def parse_kap_portfolio_report_reference(
    raw_html: str,
    *,
    detail_url: str,
) -> KapPortfolioReportReference:
    validated_detail, notification_id = validate_kap_portfolio_detail_url(detail_url)
    parser = _KapDetailHtmlParser()
    parser.feed(str(raw_html or ""))
    parser.close()
    visible = re.sub(r"\s+", " ", " ".join(parser.text_parts)).strip()
    if not visible:
        raise KapFundPortfolioError("KAP_DETAIL_EMPTY")
    if "portföy dağılım raporu" not in visible.casefold() and "portfoy dagilim raporu" not in visible.casefold():
        raise KapFundPortfolioError("KAP_NOT_PORTFOLIO_ALLOCATION_REPORT")

    published = re.search(
        r"Gönderim\s+Tarihi\s+(\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}:\d{2})",
        visible,
        re.IGNORECASE,
    )
    year_match = re.search(r"\bYıl\s+(\d{4})\b", visible, re.IGNORECASE)
    period_match = re.search(r"\bPeriyot\s+(\d{1,2})\.\s*Aylık\b", visible, re.IGNORECASE)
    if published is None or year_match is None or period_match is None:
        raise KapFundPortfolioError("KAP_REPORT_METADATA_MISSING")

    try:
        publication_at = datetime.strptime(published.group(1), "%d.%m.%Y %H:%M:%S").replace(tzinfo=ISTANBUL)
    except ValueError as exc:
        raise KapFundPortfolioError("KAP_PUBLICATION_DATE_INVALID") from exc
    report_year = int(year_match.group(1))
    report_month = int(period_match.group(1))
    if not 1 <= report_month <= 12:
        raise KapFundPortfolioError("KAP_REPORT_MONTH_INVALID")

    candidates: list[tuple[str, str]] = []
    for href, anchor_text in parser.links:
        absolute = urljoin(validated_detail, href)
        try:
            validated_attachment, _ = validate_kap_attachment_url(absolute)
        except KapFundPortfolioError:
            continue
        if anchor_text.casefold().endswith(".pdf") or ".pdf" in anchor_text.casefold():
            candidates.append((validated_attachment, anchor_text.strip()))

    unique = {(url, name) for url, name in candidates}
    if not unique:
        raise KapFundPortfolioError("KAP_PORTFOLIO_PDF_ATTACHMENT_MISSING")
    if len(unique) != 1:
        raise KapFundPortfolioError("KAP_PORTFOLIO_PDF_ATTACHMENT_AMBIGUOUS")
    attachment_url, attachment_name = next(iter(unique))
    return KapPortfolioReportReference(
        notification_id=notification_id,
        detail_url=validated_detail,
        attachment_url=attachment_url,
        attachment_name=attachment_name,
        publication_at=publication_at,
        report_year=report_year,
        report_month=report_month,
    )


def extract_kap_portfolio_pdf_payload(raw_payload: bytes) -> bytes:
    """Return the embedded PDF bytes from a bounded KAP/mirror payload.

    Some browser/mirror downloads wrap the original PDF with transport bytes.
    Native PDFs are returned unchanged; wrapped payloads are sliced from the
    first PDF header through the last EOF marker when available.
    """
    if not isinstance(raw_payload, (bytes, bytearray)) or not raw_payload:
        raise KapFundPortfolioError("KAP_PORTFOLIO_ATTACHMENT_EMPTY")
    raw = bytes(raw_payload)
    if len(raw) > MAX_KAP_PORTFOLIO_PDF_BYTES:
        raise KapFundPortfolioError("KAP_PORTFOLIO_PDF_TOO_LARGE")

    start = raw.find(b"%PDF-")
    if start < 0:
        raise KapFundPortfolioError("KAP_PORTFOLIO_ATTACHMENT_NOT_PDF")
    if start == 0:
        return raw

    end = raw.rfind(b"%%EOF")
    if end >= start:
        end += len(b"%%EOF")
        payload = raw[start:end]
    else:
        payload = raw[start:]

    if not payload.startswith(b"%PDF-"):
        raise KapFundPortfolioError("KAP_PORTFOLIO_ATTACHMENT_NOT_PDF")
    if len(payload) > MAX_KAP_PORTFOLIO_PDF_BYTES:
        raise KapFundPortfolioError("KAP_PORTFOLIO_PDF_TOO_LARGE")
    return payload


def extract_kap_portfolio_pdf_text(raw_pdf: bytes) -> str:
    raw_pdf = extract_kap_portfolio_pdf_payload(raw_pdf)
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency contract.
        raise KapFundPortfolioError("PYPDF_DEPENDENCY_MISSING") from exc
    try:
        reader = PdfReader(io.BytesIO(raw_pdf))
        if reader.is_encrypted:
            raise KapFundPortfolioError("KAP_PORTFOLIO_PDF_ENCRYPTED")
        if len(reader.pages) > MAX_KAP_PORTFOLIO_PDF_PAGES:
            raise KapFundPortfolioError("KAP_PORTFOLIO_PDF_PAGE_LIMIT")
        parts = [str(page.extract_text() or "") for page in reader.pages]
    except KapFundPortfolioError:
        raise
    except Exception as exc:
        raise KapFundPortfolioError("KAP_PORTFOLIO_PDF_PARSE_FAILED") from exc
    text = "\n".join(parts).strip()
    if not text:
        raise KapFundPortfolioError("KAP_PORTFOLIO_PDF_TEXT_EMPTY")
    return text


_INVALID_FUND_CODE_TOKENS = frozenset({
    "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII",
    "TLII", "SERBEST",
})


def _valid_fund_code_candidate(value: object) -> str:
    code = normalize_fund_code(value)
    if not code or code.isdigit() or code in _INVALID_FUND_CODE_TOKENS:
        return ""
    if not re.fullmatch(r"[A-Z0-9]{2,8}", code):
        return ""
    return code


def _extract_kap_fund_code(report_text: str, *, reference: KapPortfolioReportReference) -> str:
    text = str(report_text or "").replace("\u00a0", " ")
    for pattern in (
        r"A[.)-]?\s*FONUN\s+ADI\s*:?\s*\(([A-Z0-9]{2,8})\)",
        r"A[.)-]?\s*FONUN\s+ADI\s*:?\s*([A-Z0-9]{2,8})\s*[-–—]",
    ):
        match = re.search(pattern, text, re.IGNORECASE)
        if match is not None:
            code = _valid_fund_code_candidate(match.group(1))
            if code:
                return code

    attachment_name = Path(str(reference.attachment_name or "")).name
    attachment_match = re.match(r"^\s*([A-Z0-9]{2,8})(?=[\s_.-])", attachment_name, re.IGNORECASE)
    if attachment_match is not None:
        code = _valid_fund_code_candidate(attachment_match.group(1))
        if code:
            return code

    header = "\n".join(text.splitlines()[:120])
    for pattern in (
        r"(?m)^\s*\(?([A-Z0-9]{2,8})\)?\s*[-–—]\s*.+?\bFON\b",
        r"(?m)^\s*([A-Z0-9]{2,8})\s+FON\b",
    ):
        match = re.search(pattern, header, re.IGNORECASE)
        if match is not None:
            code = _valid_fund_code_candidate(match.group(1))
            if code:
                return code
    raise KapFundPortfolioError("KAP_FUND_CODE_MISSING")


def _portfolio_value_section(report_text: str) -> str:
    text = str(report_text or "").replace("\u00a0", " ")
    match = re.search(
        r"III\s*[-.)]?\s*FON\s+PORTF[ÖO]Y\s+(?:DE[GĞ]ER[İI]|DEGERI|cE[GĞ]ER[İI])\s+TABLOSU"
        r"(.*?)"
        r"(?=IV\s*[-.)]?\s*FON\s+TOPLAM\s+DE[GĞ]ER[İI]\s+TABLOSU|\Z)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if match is None:
        # Compatibility path for the canonical AP5/KAP report shape already
        # supported by V1 tests: those reports expose A) HİSSE SENETLERİ
        # directly without an explicit III...IV wrapper.
        return text
    return match.group(1)


def _equity_section(report_text: str) -> str:
    portfolio = _portfolio_value_section(report_text)
    for pattern in (
        r":?\s*A\)\s*H[İI]SSE\s+SENETLER[İI]",
        r"(?m)^\s*H[İI]SSE\s+SENETLER[İI]\s*$",
        r"(?m)^\s*Hisse\s+T[üu]rk\s*$",
    ):
        match = re.search(pattern, portfolio, re.IGNORECASE)
        if match is not None:
            tail = portfolio[match.end():]
            stop = re.search(
                r"(?m)^\s*(?:"
                r":?\s*[B-ZÇĞİÖŞÜ]\)\s*[A-ZÇĞİÖŞÜ]|"
                r":?\s*(?:O|Ş|U|AC|AF)\)\s*|"
                r"B\)\s*VARANTLAR|VARANTLAR|BOR[ÇC]LANMA|T[ÜU]REV|V[İI]OP|YATIRIM\s+FONU|TAKASBANK"
                r")",
                tail,
                re.IGNORECASE,
            )
            return tail[:stop.start()] if stop is not None else tail
    raise KapFundPortfolioError("KAP_EQUITY_SECTION_MISSING")


def _parse_mixed_decimal(raw: str) -> Decimal:
    value = str(raw or "").strip().replace(" ", "")
    if not value:
        raise KapFundPortfolioError("KAP_EQUITY_ROW_NUMERIC_MISSING")
    if "," in value and "." in value:
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    elif "," in value:
        value = value.replace(".", "").replace(",", ".")
    return Decimal(value)


def _merge_equity(aggregated, *, symbol: str, asset_name: str, shares: Decimal, market_value: Decimal, weight: Decimal) -> None:
    symbol = re.sub(r"\s+", "", str(symbol or "").upper())
    if not re.fullmatch(r"[A-Z0-9]{3,6}", symbol):
        raise KapFundPortfolioError(f"KAP_EQUITY_SYMBOL_INVALID:{symbol}")
    # Signed KAP correction fragments are allowed here.
    # Final aggregate validation happens in _parse_equity_rows.
    prior = aggregated.get(symbol)
    if prior is None:
        aggregated[symbol] = (asset_name, shares, market_value, weight)
    else:
        aggregated[symbol] = (prior[0] or asset_name, prior[1] + shares, prior[2] + market_value, prior[3] + weight)


def _parse_equity_rows(section: str):
    aggregated = {}
    lines = [str(line or "").strip() for line in str(section or "").splitlines()]

    classic = re.compile(
        r"^(?P<name>.+?)\s+"
        r"(?P<shares>-?\d[\d.,]*)\s+"
        r"(?P<market>-?\d[\d.,]*)\s+"
        r"(?P<weight>\d[\d.,]*)"
        r"(?P<tail>TR[A-Z0-9 ]{12,32})$",
        re.IGNORECASE,
    )
    for line in lines:
        match = classic.match(line)
        if match is None:
            continue
        tail = re.sub(r"\s+", "", match.group("tail").upper())
        if len(tail) <= 12:
            continue
        _merge_equity(
            aggregated,
            symbol=tail[12:],
            asset_name=re.sub(r"\s+", " ", match.group("name")).strip(),
            shares=_parse_mixed_decimal(match.group("shares")),
            market_value=_parse_mixed_decimal(match.group("market")),
            weight=_parse_mixed_decimal(match.group("weight")) / Decimal("100"),
        )

    # Legacy canonical AP5/KAP format preserved from V1:
    # SAHOL SABANCI HOLDİNG A.Ş. 4.800,00 441.600,00 %45,66
    legacy = re.compile(
        r"^(?P<symbol>[A-Z0-9]{3,12})\s+"
        r"(?P<name>.+?)\s+"
        r"(?P<shares>-?\d[\d.]*,\d+)\s+"
        r"(?P<market>-?\d[\d.]*,\d+)\s+"
        r"(?P<weight>-?%\s*\d[\d.,]*)$",
        re.IGNORECASE,
    )
    for line in lines:
        match = legacy.match(line)
        if match is None:
            continue
        shares = parse_decimal_tr(match.group("shares"))
        market_value = parse_decimal_tr(match.group("market"))
        weight = parse_decimal_tr(match.group("weight"), percent=True)
        if shares is None or market_value is None or weight is None:
            raise KapFundPortfolioError(
                f"KAP_EQUITY_ROW_NUMERIC_MISSING:{match.group('symbol').upper()}"
            )
        _merge_equity(
            aggregated,
            symbol=match.group("symbol").upper(),
            asset_name=re.sub(r"\s+", " ", match.group("name")).strip(),
            shares=shares,
            market_value=market_value,
            weight=weight,
        )

    split_numeric = re.compile(
        r"^(?P<shares>-?\d[\d.,]*)\s+"
        r"-?\d[\d.,]*\s+"
        r"\d{2}/\d{2}/\d{2,4}\s+"
        r"-?\d[\d.,]*\s+"
        r"(?P<market>-?\d[\d.,]*)\s+"
        r"-?\d[\d.,]*\s+"
        r"(?P<weight>-?\d[\d.,]*)TL\b",
        re.IGNORECASE,
    )
    current_symbol = ""
    current_name_parts = []
    for line in lines:
        if not line:
            continue
        header = re.match(r"^([A-Z0-9]{3,6})\s+(.+)$", line)
        if header is not None and not current_symbol and not re.match(r"^\d", line):
            candidate = header.group(1).upper()
            if candidate in {
                "ISIN", "ORANI", "SATIN", "ALIS", "ALIŞ", "TARIHI", "TARİHİ",
                "BIRIM", "BİRİM", "FIYATI", "FİYATI", "NOMINAL", "NOMİNAL",
                "VADE", "DOVIZ", "DÖVİZ", "BORSA", "TOPLAM", "GRUP", "REPO",
            }:
                continue
            if candidate == "ORANI":
                continue
            header_upper = line.upper()
            if candidate == "REPO" and ("TEMİNAT" in header_upper or "TEMINAT" in header_upper):
                continue
            header_upper = line.upper()
            if (
                " - " in line
                or "FONU" in header_upper
                or "PORTFÖY" in header_upper
                or "PORTFOY" in header_upper
                or "TOPLAM" in header_upper
                or "(FPD" in header_upper
                or "(FTD" in header_upper
            ):
                continue
            if candidate not in {"TOPLAM", "HISSE", "HİSSE", "GRUP"}:
                current_symbol = candidate
                current_name_parts = [header.group(2).strip()]
                continue
        numeric = split_numeric.match(line)
        if numeric is not None and current_symbol:
            _merge_equity(
                aggregated,
                symbol=current_symbol,
                asset_name=re.sub(r"\s+", " ", " ".join(current_name_parts)).strip(),
                shares=_parse_mixed_decimal(numeric.group("shares")),
                market_value=_parse_mixed_decimal(numeric.group("market")),
                weight=_parse_mixed_decimal(numeric.group("weight")) / Decimal("100"),
            )
            current_symbol = ""
            current_name_parts = []
            continue
        if current_symbol and not re.search(r"\d", line):
            current_name_parts.append(line)

    if not aggregated:
        raise KapFundPortfolioError("KAP_EQUITY_ROWS_MISSING")

    for symbol, (_name, shares, market_value, weight) in aggregated.items():
        if shares < 0 or market_value < 0 or weight < 0 or weight > 1:
            raise KapFundPortfolioError(
                f"KAP_EQUITY_ROW_RANGE_INVALID:{symbol}"
            )

    return aggregated


def _canonical_current_fund_id(fund_code: object) -> str:
    # Existing fund-analysis canonical identity is TEFAS-code based. KAP is the
    # evidence provider for the holdings snapshot, not a second fund identity.
    return f"fund:tefas:{normalize_fund_code(fund_code)}"




def parse_kap_portfolio_report_text(
    report_text: str,
    *,
    reference: KapPortfolioReportReference,
    ingested_at: datetime,
) -> FundPortfolioSnapshot:
    if ingested_at.tzinfo is None or ingested_at.utcoffset() is None:
        raise ValueError("ingested_at timezone-aware olmalıdır.")
    text = str(report_text or "").replace("\u00a0", " ")
    fund_code = _extract_kap_fund_code(text, reference=reference)
    canonical_fund_id = _canonical_current_fund_id(fund_code)
    section = _equity_section(text)
    aggregated = _parse_equity_rows(section)
    positions = tuple(
        FundPortfolioPosition(
            canonical_fund_id=canonical_fund_id,
            portfolio_date=reference.portfolio_date,
            symbol=symbol,
            asset_type="EQUITY",
            asset_name=values[0] or None,
            shares_held=values[1],
            market_value=values[2],
            portfolio_weight=values[3],
        )
        for symbol, values in sorted(aggregated.items())
    )
    return FundPortfolioSnapshot(
        canonical_fund_id=canonical_fund_id,
        portfolio_date=reference.portfolio_date,
        publication_date=reference.publication_at.date(),
        ingested_at=ingested_at,
        provider="KAP",
        positions=positions,
        data_quality_state=DataQualityState.VALID,
        source_reference=reference.detail_url,
    )


def _same_canonical_snapshot(existing: FundPortfolioSnapshot, incoming: FundPortfolioSnapshot) -> bool:
    # Transport/provenance may differ (direct KAP URL vs. manual upload) while
    # the canonical KAP portfolio snapshot itself is identical. Source reference
    # therefore does not participate in idempotency identity.
    return (
        existing.canonical_fund_id == incoming.canonical_fund_id
        and existing.portfolio_date == incoming.portfolio_date
        and existing.publication_date == incoming.publication_date
        and existing.provider == incoming.provider
        and existing.positions == incoming.positions
        and existing.data_quality_state == incoming.data_quality_state
    )


def _store_snapshot_idempotently(
    store: FundPortfolioSnapshotJsonStore,
    snapshot: FundPortfolioSnapshot,
) -> PortfolioSnapshotStoreResult:
    existing = tuple(
        item
        for item in store.list_snapshots()
        if item.canonical_fund_id == snapshot.canonical_fund_id
        and item.portfolio_date == snapshot.portfolio_date
        and item.provider == snapshot.provider
    )
    if existing and any(_same_canonical_snapshot(item, snapshot) for item in existing):
        return PortfolioSnapshotStoreResult(
            inserted=0,
            unchanged=1,
            total_records=len(store.list_records()),
        )
    return store.append((snapshot,))


def ingest_kap_portfolio_pdf_upload(
    raw_pdf: bytes,
    *,
    filename: str,
    report_year: int,
    report_month: int,
    publication_date: date,
    store: FundPortfolioSnapshotJsonStore,
    notification_id: str | None = None,
    source_reference: str | None = None,
    ingested_at: datetime | None = None,
    pdf_text_extractor: PdfTextExtractor | None = None,
) -> KapPortfolioIngestionResult:
    """Ingest an explicitly uploaded KAP portfolio-allocation PDF without network access.

    The user must provide the report period and publication date because those
    facts are not reliably encoded inside every attachment PDF. The canonical
    holdings parser and append-only snapshot store are reused unchanged.
    """
    if not isinstance(raw_pdf, (bytes, bytearray)) or not raw_pdf:
        raise KapFundPortfolioError("KAP_MANUAL_UPLOAD_EMPTY")
    raw = bytes(raw_pdf)
    if len(raw) > MAX_KAP_PORTFOLIO_PDF_BYTES:
        raise KapFundPortfolioError("KAP_PORTFOLIO_PDF_TOO_LARGE")

    safe_name = Path(str(filename or "")).name.strip()
    if not safe_name or not safe_name.casefold().endswith(".pdf"):
        raise KapFundPortfolioError("KAP_MANUAL_UPLOAD_FILENAME_INVALID")
    if not 2000 <= int(report_year) <= 2100:
        raise ValueError("report_year 2000-2100 aralığında olmalıdır.")
    if not 1 <= int(report_month) <= 12:
        raise ValueError("report_month 1-12 aralığında olmalıdır.")

    report_year = int(report_year)
    report_month = int(report_month)
    portfolio_last_day = calendar.monthrange(report_year, report_month)[1]
    portfolio_date = date(report_year, report_month, portfolio_last_day)
    if publication_date < portfolio_date:
        raise ValueError("publication_date portfolio_date öncesinde olamaz.")

    clean_notification = str(notification_id or "").strip()
    if clean_notification and not clean_notification.isdigit():
        raise KapFundPortfolioError("KAP_NOTIFICATION_ID_INVALID")
    clean_source = str(source_reference or "").strip()
    if len(clean_source) > 2048:
        raise KapFundPortfolioError("KAP_SOURCE_REFERENCE_TOO_LONG")

    if clean_notification:
        detail_url = f"https://www.kap.org.tr/tr/Bildirim/{clean_notification}"
    elif clean_source:
        detail_url = clean_source
    else:
        detail_url = f"manual-upload:{safe_name}"

    publication_at = datetime.combine(
        publication_date,
        datetime.min.time(),
        tzinfo=ISTANBUL,
    )
    reference = KapPortfolioReportReference(
        notification_id=clean_notification or "MANUAL",
        detail_url=detail_url,
        attachment_url=f"manual-upload:{safe_name}",
        attachment_name=safe_name,
        publication_at=publication_at,
        report_year=report_year,
        report_month=report_month,
    )

    extractor = pdf_text_extractor or extract_kap_portfolio_pdf_text
    report_text = extractor(raw)
    if re.search(
        r"FON\s+PORTF[ÖO]Y\s+DE[GĞ]ER[İI]\s+TABLOSU",
        report_text,
        re.IGNORECASE,
    ) is None:
        raise KapFundPortfolioError("KAP_MANUAL_UPLOAD_NOT_PORTFOLIO_ATTACHMENT")

    stamp = ingested_at if ingested_at is not None else datetime.now(timezone.utc)
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("ingested_at timezone-aware olmalıdır.")
    snapshot = parse_kap_portfolio_report_text(
        report_text,
        reference=reference,
        ingested_at=stamp,
    )
    store_result = _store_snapshot_idempotently(store, snapshot)
    return KapPortfolioIngestionResult(
        reference=reference,
        snapshot=snapshot,
        store_result=store_result,
    )


def ingest_kap_portfolio_report_url(
    detail_url: str,
    *,
    store: FundPortfolioSnapshotJsonStore,
    network_enabled: bool = False,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ingested_at: datetime | None = None,
    detail_fetcher: FetchBytes | None = None,
    attachment_fetcher: FetchBytes | None = None,
    pdf_text_extractor: PdfTextExtractor | None = None,
) -> KapPortfolioIngestionResult:
    if not network_enabled:
        raise KapFundPortfolioError("KAP_PORTFOLIO_NETWORK_DISABLED")
    if timeout_seconds <= 0 or timeout_seconds > 30:
        raise ValueError("timeout_seconds 1-30 aralığında olmalıdır.")
    validated_detail, notification_id = validate_kap_portfolio_detail_url(detail_url)
    detail_fetch = detail_fetcher or _default_fetch
    attachment_fetch = attachment_fetcher or _default_fetch
    extractor = pdf_text_extractor or extract_kap_portfolio_pdf_text

    raw_html, final_detail, detail_content_type = detail_fetch(validated_detail, timeout_seconds)
    final_validated, final_notification_id = validate_kap_portfolio_detail_url(final_detail)
    if final_notification_id != notification_id:
        raise KapFundPortfolioError("KAP_DETAIL_REDIRECT_MISMATCH")
    reference = parse_kap_portfolio_report_reference(
        _decode_html(raw_html, detail_content_type),
        detail_url=final_validated,
    )

    raw_pdf, final_attachment, pdf_content_type = attachment_fetch(reference.attachment_url, timeout_seconds)
    final_attachment_validated, final_attachment_id = validate_kap_attachment_url(final_attachment)
    _, expected_attachment_id = validate_kap_attachment_url(reference.attachment_url)
    if final_attachment_id != expected_attachment_id:
        raise KapFundPortfolioError("KAP_ATTACHMENT_REDIRECT_MISMATCH")
    pdf_payload = extract_kap_portfolio_pdf_payload(raw_pdf)
    lowered_content_type = pdf_content_type.casefold()
    if (
        "pdf" not in lowered_content_type
        and "octet-stream" not in lowered_content_type
        and not pdf_payload.startswith(b"%PDF-")
    ):
        raise KapFundPortfolioError("KAP_PORTFOLIO_ATTACHMENT_NOT_PDF")

    stamp = ingested_at if ingested_at is not None else datetime.now(timezone.utc)
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("ingested_at timezone-aware olmalıdır.")
    snapshot = parse_kap_portfolio_report_text(
        extractor(pdf_payload),
        reference=reference,
        ingested_at=stamp,
    )

    store_result = _store_snapshot_idempotently(store, snapshot)

    return KapPortfolioIngestionResult(
        reference=KapPortfolioReportReference(
            notification_id=reference.notification_id,
            detail_url=reference.detail_url,
            attachment_url=final_attachment_validated,
            attachment_name=reference.attachment_name,
            publication_at=reference.publication_at,
            report_year=reference.report_year,
            report_month=reference.report_month,
        ),
        snapshot=snapshot,
        store_result=store_result,
    )
