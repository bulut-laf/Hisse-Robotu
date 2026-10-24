from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
import re
from typing import Callable
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from .feed_ingestion import FeedItem
from .models import EventType, MarketScope
from .official_source_http import (
    OFFICIAL_SOURCE_DEFAULT_TIMEOUT_SECONDS,
    OFFICIAL_SOURCE_MAX_RESPONSE_BYTES,
    decode_official_source_html,
    fetch_official_source_bytes,
    validate_official_source_html_payload,
    validate_official_source_timeout,
)


ISTANBUL = ZoneInfo("Europe/Istanbul")
MAX_RESPONSE_BYTES = OFFICIAL_SOURCE_MAX_RESPONSE_BYTES
DEFAULT_TIMEOUT_SECONDS = OFFICIAL_SOURCE_DEFAULT_TIMEOUT_SECONDS
_ALLOWED_HOSTS = {"veriportali.tuik.gov.tr"}
_DETAIL_PATH = re.compile(r"^/tr/press/(\d+)/?$", re.IGNORECASE)

_TURKISH_MONTHS = {
    "ocak": 1, "şubat": 2, "subat": 2, "mart": 3, "nisan": 4,
    "mayıs": 5, "mayis": 5, "haziran": 6, "temmuz": 7,
    "ağustos": 8, "agustos": 8, "eylül": 9, "eylul": 9,
    "ekim": 10, "kasım": 11, "kasim": 11, "aralık": 12, "aralik": 12,
}


class TuikAdapterError(RuntimeError):
    """TÜİK URL adapteri güvenlik veya ayrıştırma hatası."""


@dataclass(frozen=True, slots=True)
class TuikFetchResult:
    item: FeedItem
    bulletin_id: str
    source_url: str
    response_bytes: int


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.headings: list[str] = []
        self._skip_depth = 0
        self._heading_depth = 0
        self._heading_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
        if lowered in {"h1", "h2", "h3"} and self._skip_depth == 0:
            self._heading_depth += 1
            self._heading_parts = []

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        if lowered in {"h1", "h2", "h3"} and self._heading_depth:
            heading = re.sub(r"\s+", " ", " ".join(self._heading_parts)).strip()
            if heading:
                self.headings.append(heading)
            self._heading_depth -= 1
            self._heading_parts = []

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        value = re.sub(r"\s+", " ", data).strip()
        if not value:
            return
        self.parts.append(value)
        if self._heading_depth:
            self._heading_parts.append(value)


FetchBytes = Callable[[str, int], tuple[bytes, str, str]]


def validate_tuik_press_url(url: str) -> tuple[str, str]:
    value = str(url or "").strip()
    parsed = urlparse(value)
    if parsed.scheme.lower() != "https":
        raise TuikAdapterError("TÜİK URL'si HTTPS olmalıdır.")
    host = (parsed.hostname or "").lower()
    if host not in _ALLOWED_HOSTS:
        raise TuikAdapterError("Yalnız resmî veriportali.tuik.gov.tr alan adı kabul edilir.")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise TuikAdapterError("TÜİK URL'sinde kullanıcı bilgisi veya özel port kullanılamaz.")
    if parsed.query or parsed.fragment:
        raise TuikAdapterError("TÜİK haber bülteni URL'sinde sorgu veya fragment kabul edilmez.")
    match = _DETAIL_PATH.fullmatch(parsed.path or "")
    if not match:
        raise TuikAdapterError(
            "Yalnız TÜİK Veri Portalı haber bülteni detay URL'si kabul edilir: /tr/press/<sayı>"
        )
    return value, match.group(1)


def _default_fetch(url: str, timeout_seconds: int) -> tuple[bytes, str, str]:
    response = fetch_official_source_bytes(
        url,
        timeout_seconds,
        user_agent='Hisse-Robotu/1.0 (+local decision-support; TUIK press preview)',
        error_type=TuikAdapterError,
        source_label='TÜİK',
    )
    return response.body, response.final_url, response.content_type


def _parse_visible(raw_html: str) -> tuple[str, tuple[str, ...]]:
    parser = _VisibleTextParser()
    parser.feed(str(raw_html or ""))
    parser.close()
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip(), tuple(parser.headings)


def _extract_published_at(text: str) -> datetime:
    match = re.search(
        r"Yayım Tarihi\s*:?\s*(\d{1,2})\s+([A-Za-zÇĞİÖŞÜçğıöşü]+)\s+(\d{4})\s+(\d{2}):(\d{2})",
        text,
        re.IGNORECASE,
    )
    if not match:
        raise TuikAdapterError("TÜİK sayfasında Yayım Tarihi bulunamadı.")
    month_name = match.group(2).casefold().replace("i̇", "i")
    month = _TURKISH_MONTHS.get(month_name)
    if month is None:
        raise TuikAdapterError("TÜİK yayım ayı ayrıştırılamadı.")
    try:
        return datetime(
            int(match.group(3)), month, int(match.group(1)),
            int(match.group(4)), int(match.group(5)), tzinfo=ISTANBUL,
        )
    except ValueError as exc:
        raise TuikAdapterError("TÜİK Yayım Tarihi geçersiz.") from exc


def _extract_bulletin_number(text: str) -> str:
    match = re.search(r"\bSayı\s*:?\s*(\d+)\b", text, re.IGNORECASE)
    if not match:
        raise TuikAdapterError("TÜİK sayfasında bülten Sayı alanı bulunamadı.")
    return match.group(1)


def _extract_title(headings: tuple[str, ...], bulletin_id: str) -> str:
    ignored = {"veri portalı", "veri portali", "haber bülteni", "haber bulteni", "metaveri"}
    for heading in headings:
        normalized = heading.casefold().replace("i̇", "i")
        if normalized in ignored or "türkiye istatistik kurumu" in normalized:
            continue
        if len(heading) >= 8:
            return heading
    return f"TÜİK Haber Bülteni ({bulletin_id})"


def _classify_event_type(title: str) -> EventType:
    lowered = title.casefold().replace("i̇", "i")
    if any(x in lowered for x in (
        "tüketici fiyat endeksi", "tuketici fiyat endeksi",
        "üretici fiyat endeksi", "uretici fiyat endeksi", "enflasyon",
    )):
        return EventType.ENFLASYON
    if any(x in lowered for x in (
        "işgücü", "isgucu", "işsizlik", "issizlik",
        "ücretli çalışan", "ucretli calisan", "istihdam",
    )):
        return EventType.ISTIHDAM
    if any(x in lowered for x in (
        "gayrisafi yurt içi hasıla", "gayrisafi yurt ici hasila", "gsyh", "büyüme", "buyume",
    )):
        return EventType.BUYUME
    if any(x in lowered for x in (
        "sanayi üretim", "sanayi uretim", "ciro endeks",
        "ticaret satış hacim", "ticaret satis hacim",
        "hizmet üretim", "hizmet uretim",
    )):
        return EventType.SEKTOR
    return EventType.DIGER


def _extract_body(text: str, title: str) -> str:
    start = text.find(title)
    body = text[start + len(title):].strip(" -:|") if start >= 0 else text
    for marker in (
        "Bu konu ile ilgili bir sonraki haber bülteninin yayımlanma tarihi",
        "Metaveri", "İletişim",
    ):
        idx = body.find(marker)
        if idx >= 0:
            body = body[:idx]
    body = re.sub(r"\s+", " ", body).strip()
    return (body or title)[:10000]


def parse_tuik_press_html(raw_html: str, *, source_url: str) -> TuikFetchResult:
    validated_url, url_bulletin_id = validate_tuik_press_url(source_url)
    text, headings = _parse_visible(raw_html)
    if not text:
        raise TuikAdapterError("TÜİK sayfasından okunabilir metin çıkarılamadı.")
    published_at = _extract_published_at(text)
    page_bulletin_id = _extract_bulletin_number(text)
    if page_bulletin_id != url_bulletin_id:
        raise TuikAdapterError("TÜİK URL bülten numarası ile sayfadaki Sayı alanı uyuşmuyor.")
    title = _extract_title(headings, url_bulletin_id)
    item = FeedItem(
        source_name="TÜİK",
        headline=title,
        published_at=published_at,
        body=_extract_body(text, title),
        source_reference=validated_url,
        event_title=title,
        event_type=_classify_event_type(title),
        occurred_at=published_at,
        market_scope=MarketScope.TURKEY_MACRO,
        symbols=(),
        sectors=(),
        external_id=url_bulletin_id,
    )
    return TuikFetchResult(
        item=item,
        bulletin_id=url_bulletin_id,
        source_url=validated_url,
        response_bytes=len(str(raw_html or "").encode("utf-8")),
    )


class TuikPressUrlAdapter:
    """Tek resmî TÜİK Veri Portalı haber bülteni URL'sini çeker."""

    def __init__(
        self,
        *,
        network_enabled: bool = False,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        fetcher: FetchBytes | None = None,
    ) -> None:
        self.network_enabled = bool(network_enabled)
        self.timeout_seconds = validate_official_source_timeout(timeout_seconds)
        self._fetcher = fetcher or _default_fetch

    def fetch(self, url: str) -> TuikFetchResult:
        validated_url, bulletin_id = validate_tuik_press_url(url)
        if not self.network_enabled:
            raise TuikAdapterError("TÜİK ağ erişimi kapalı. Bu işlem için açık kullanıcı onayı gerekir.")
        raw, final_url, content_type = self._fetcher(validated_url, self.timeout_seconds)
        final_validated, final_bulletin_id = validate_tuik_press_url(final_url)
        if final_bulletin_id != bulletin_id:
            raise TuikAdapterError("TÜİK yönlendirmesi farklı bir bülten numarasına gitti.")
        validate_official_source_html_payload(
            raw,
            content_type,
            error_type=TuikAdapterError,
            source_label='TÜİK',
        )
        decoded = decode_official_source_html(
            raw,
            error_type=TuikAdapterError,
            source_label='TÜİK',
        )

        parsed = parse_tuik_press_html(decoded, source_url=final_validated)
        return TuikFetchResult(
            item=parsed.item,
            bulletin_id=parsed.bulletin_id,
            source_url=parsed.source_url,
            response_bytes=len(raw),
        )
