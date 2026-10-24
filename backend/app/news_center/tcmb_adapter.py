from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
import re
from typing import Callable
from urllib.parse import unquote, urlparse
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
_ALLOWED_HOSTS = {"tcmb.gov.tr", "www.tcmb.gov.tr"}

_DETAIL_PATH = re.compile(
    r"^/wps/wcm/connect/(?:TR|tr)/TCMB(?:\+| )TR/Main(?:\+| )Menu/"
    r"Duyurular/Basin/(\d{4})/DUY(\d{4})-(\d+?)/?$",
    re.IGNORECASE,
)

_TURKISH_MONTHS = {
    "ocak": 1,
    "şubat": 2,
    "subat": 2,
    "mart": 3,
    "nisan": 4,
    "mayıs": 5,
    "mayis": 5,
    "haziran": 6,
    "temmuz": 7,
    "ağustos": 8,
    "agustos": 8,
    "eylül": 9,
    "eylul": 9,
    "ekim": 10,
    "kasım": 11,
    "kasim": 11,
    "aralık": 12,
    "aralik": 12,
}


class TcmbAdapterError(RuntimeError):
    """TCMB URL adapteri güvenlik veya ayrıştırma hatası."""


@dataclass(frozen=True, slots=True)
class TcmbFetchResult:
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


def validate_tcmb_press_url(url: str) -> tuple[str, str]:
    value = str(url or "").strip()
    parsed = urlparse(value)

    if parsed.scheme.lower() != "https":
        raise TcmbAdapterError("TCMB URL'si HTTPS olmalıdır.")

    host = (parsed.hostname or "").lower()
    if host not in _ALLOWED_HOSTS:
        raise TcmbAdapterError("Yalnız resmî tcmb.gov.tr alan adı kabul edilir.")

    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise TcmbAdapterError(
            "TCMB URL'sinde kullanıcı bilgisi veya özel port kullanılamaz."
        )

    if parsed.query or parsed.fragment:
        raise TcmbAdapterError(
            "TCMB basın duyurusu URL'sinde sorgu veya fragment kabul edilmez."
        )

    decoded_path = unquote(parsed.path or "").replace("+", " ")
    match = _DETAIL_PATH.fullmatch(decoded_path)
    if not match:
        raise TcmbAdapterError(
            "Yalnız TCMB basın duyurusu detay URL'si kabul edilir."
        )

    path_year, id_year, number = match.groups()
    if path_year != id_year:
        raise TcmbAdapterError("TCMB duyuru URL'sindeki yıl bilgileri uyuşmuyor.")

    return value, f"{id_year}-{number}"


def _default_fetch(url: str, timeout_seconds: int) -> tuple[bytes, str, str]:
    response = fetch_official_source_bytes(
        url,
        timeout_seconds,
        user_agent='Hisse-Robotu/1.0 (+local decision-support; TCMB press preview)',
        error_type=TcmbAdapterError,
        source_label='TCMB',
    )
    return response.body, response.final_url, response.content_type


def _parse_visible(raw_html: str) -> tuple[str, tuple[str, ...]]:
    parser = _VisibleTextParser()
    parser.feed(str(raw_html or ""))
    parser.close()
    text = re.sub(r"\s+", " ", " ".join(parser.parts)).strip()
    return text, tuple(parser.headings)


def _extract_published_at(text: str) -> datetime:
    match = re.search(
        r"\b(\d{1,2})\s+([A-Za-zÇĞİÖŞÜçğıöşü]+)\s+(\d{4})\b",
        text,
    )
    if not match:
        raise TcmbAdapterError("TCMB sayfasında duyuru tarihi bulunamadı.")

    day = int(match.group(1))
    month_name = match.group(2).casefold().replace("i̇", "i")
    month = _TURKISH_MONTHS.get(month_name)
    if month is None:
        raise TcmbAdapterError("TCMB duyuru ayı ayrıştırılamadı.")

    try:
        return datetime(
            int(match.group(3)),
            month,
            day,
            12,
            0,
            0,
            tzinfo=ISTANBUL,
        )
    except ValueError as exc:
        raise TcmbAdapterError("TCMB duyuru tarihi geçersiz.") from exc


def _extract_title(
    text: str,
    headings: tuple[str, ...],
    bulletin_id: str,
) -> str:
    candidates = [
        heading
        for heading in headings
        if "tcmb" not in heading.casefold()
        and heading.casefold() not in {"basın duyuruları", "basin duyurulari"}
    ]
    if candidates:
        return max(candidates, key=len)

    match = re.search(
        r"((?:Faiz|Makroihtiyati|Türkiye|TCMB|Rezerv|Zorunlu|"
        r"Para|Döviz|Finansal)[^.]{6,160}?Basın Duyurusu(?:\s*\([^)]+\))?)",
        text,
        re.IGNORECASE,
    )
    if match:
        return re.sub(r"\s+", " ", match.group(1)).strip()

    return f"TCMB Basın Duyurusu ({bulletin_id})"


def _contains_phrase(text: str, *phrases: str) -> bool:
    return any(phrase in text for phrase in phrases)


def _classify_event_type(title: str) -> EventType:
    lowered = title.casefold().replace("i̇", "i")

    if _contains_phrase(lowered, "faiz oran", "para politik"):
        return EventType.PARA_POLITIKASI

    if _contains_phrase(
        lowered,
        "makroihtiyati",
        "zorunlu karşılık",
        "zorunlu karsilik",
    ):
        return EventType.REGULASYON

    if (
        "döviz" in lowered
        or "doviz" in lowered
        or re.search(r"(?<![a-zçğıöşü])kur(?:u|un|da|lar|ları|lari)?(?![a-zçğıöşü])", lowered)
    ):
        return EventType.DOVIZ

    return EventType.DIGER


def _extract_body(text: str, title: str) -> str:
    start = text.find(title)
    if start >= 0:
        candidate = text[start + len(title):].strip(" -:|")
    else:
        candidate = text
    candidate = re.sub(r"\s+", " ", candidate).strip()
    if not candidate:
        return title
    return candidate[:10000]


def parse_tcmb_press_html(
    raw_html: str,
    *,
    source_url: str,
) -> TcmbFetchResult:
    validated_url, bulletin_id = validate_tcmb_press_url(source_url)
    text, headings = _parse_visible(raw_html)
    if not text:
        raise TcmbAdapterError("TCMB sayfasından okunabilir metin çıkarılamadı.")

    published_at = _extract_published_at(text)
    title = _extract_title(text, headings, bulletin_id)
    body = _extract_body(text, title)

    item = FeedItem(
        source_name="TCMB",
        headline=title,
        published_at=published_at,
        body=body,
        source_reference=validated_url,
        event_title=title,
        event_type=_classify_event_type(title),
        occurred_at=published_at,
        market_scope=MarketScope.TURKEY_MACRO,
        symbols=(),
        sectors=(),
        external_id=bulletin_id,
    )

    return TcmbFetchResult(
        item=item,
        bulletin_id=bulletin_id,
        source_url=validated_url,
        response_bytes=len(str(raw_html or "").encode("utf-8")),
    )


class TcmbPressUrlAdapter:
    """
    Tek bir resmî TCMB basın duyurusu detay URL'sini çeker.

    Otomatik liste taraması veya polling yapmaz. Ağ erişimi varsayılan kapalıdır.
    """

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

    def fetch(self, url: str) -> TcmbFetchResult:
        validated_url, bulletin_id = validate_tcmb_press_url(url)
        if not self.network_enabled:
            raise TcmbAdapterError(
                "TCMB ağ erişimi kapalı. Bu işlem için açık kullanıcı onayı gerekir."
            )

        raw, final_url, content_type = self._fetcher(
            validated_url,
            self.timeout_seconds,
        )

        final_validated, final_bulletin_id = validate_tcmb_press_url(final_url)
        if final_bulletin_id != bulletin_id:
            raise TcmbAdapterError(
                "TCMB yönlendirmesi farklı bir duyuru numarasına gitti."
            )

        validate_official_source_html_payload(
            raw,
            content_type,
            error_type=TcmbAdapterError,
            source_label='TCMB',
        )
        decoded = decode_official_source_html(
            raw,
            error_type=TcmbAdapterError,
            source_label='TCMB',
        )

        parsed = parse_tcmb_press_html(decoded, source_url=final_validated)
        return TcmbFetchResult(
            item=parsed.item,
            bulletin_id=parsed.bulletin_id,
            source_url=parsed.source_url,
            response_bytes=len(raw),
        )
