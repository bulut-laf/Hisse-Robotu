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
_ALLOWED_HOSTS = {"borsaistanbul.com", "www.borsaistanbul.com"}
_DETAIL_PATH = re.compile(r"^/duyuru/(\d+)/([a-z0-9-]+)/?$", re.IGNORECASE)


class BorsaIstanbulAdapterError(RuntimeError):
    """Borsa İstanbul duyuru adapteri güvenlik veya ayrıştırma hatası."""


@dataclass(frozen=True, slots=True)
class BorsaIstanbulFetchResult:
    item: FeedItem
    announcement_id: str
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
        if lowered in {"h1", "h2", "h3", "h4"} and self._skip_depth == 0:
            self._heading_depth += 1
            self._heading_parts = []

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        if lowered in {"h1", "h2", "h3", "h4"} and self._heading_depth:
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


def validate_borsa_istanbul_announcement_url(url: str) -> tuple[str, str]:
    value = str(url or "").strip()
    parsed = urlparse(value)

    if parsed.scheme.lower() != "https":
        raise BorsaIstanbulAdapterError(
            "Borsa İstanbul URL'si HTTPS olmalıdır."
        )

    host = (parsed.hostname or "").lower()
    if host not in _ALLOWED_HOSTS:
        raise BorsaIstanbulAdapterError(
            "Yalnız resmî borsaistanbul.com alan adı kabul edilir."
        )

    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise BorsaIstanbulAdapterError(
            "Borsa İstanbul URL'sinde kullanıcı bilgisi veya özel port kullanılamaz."
        )

    if parsed.query or parsed.fragment:
        raise BorsaIstanbulAdapterError(
            "Borsa İstanbul duyuru URL'sinde sorgu veya fragment kabul edilmez."
        )

    decoded_path = unquote(parsed.path or "")
    match = _DETAIL_PATH.fullmatch(decoded_path)
    if not match:
        raise BorsaIstanbulAdapterError(
            "Yalnız Borsa İstanbul tekil duyuru detay URL'si kabul edilir: "
            "/duyuru/<id>/<slug>"
        )

    numeric_id, slug = match.groups()
    return value, f"{numeric_id}:{slug.lower()}"


def _default_fetch(url: str, timeout_seconds: int) -> tuple[bytes, str, str]:
    response = fetch_official_source_bytes(
        url,
        timeout_seconds,
        user_agent='Hisse-Robotu/1.0 (+local decision-support; Borsa Istanbul announcement preview)',
        error_type=BorsaIstanbulAdapterError,
        source_label='Borsa İstanbul',
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
        r"\b(\d{2})\.(\d{2})\.(\d{4})\b",
        text,
    )
    if not match:
        raise BorsaIstanbulAdapterError(
            "Borsa İstanbul sayfasında duyuru tarihi bulunamadı."
        )

    day, month, year = map(int, match.groups())
    try:
        return datetime(year, month, day, 12, 0, 0, tzinfo=ISTANBUL)
    except ValueError as exc:
        raise BorsaIstanbulAdapterError(
            "Borsa İstanbul duyuru tarihi geçersiz."
        ) from exc


def _extract_title(
    headings: tuple[str, ...],
    announcement_id: str,
) -> str:
    ignored = {
        "tüm duyurular",
        "tum duyurular",
        "duyurular",
        "borsa istanbul",
        "borsa i̇stanbul",
        "borsa istanbul a.ş.",
        "borsa istanbul a.s.",
    }

    for heading in headings:
        normalized = heading.casefold().replace("i̇", "i")
        if normalized in ignored:
            continue
        if len(heading) >= 8:
            return heading

    return f"Borsa İstanbul Duyurusu ({announcement_id})"


def _classify_title(title: str) -> tuple[EventType, MarketScope]:
    lowered = title.casefold().replace("i̇", "i")

    regulatory_phrases = (
        "prosedür",
        "prosedur",
        "kural set",
        "piyasa yapıcılık",
        "piyasa yapicilik",
        "işlem saat",
        "islem saat",
        "takas süresi",
        "takas suresi",
        "emir/işlem",
        "emir/islem",
        "devre kesici",
        "pazar",
        "işlem yasağı",
        "islem yasagi",
        "işleme açılmaması",
        "isleme acilmamasi",
        "işleme açılması",
        "isleme acilmasi",
    )
    if any(phrase in lowered for phrase in regulatory_phrases):
        return EventType.REGULASYON, MarketScope.BIST_WIDE

    index_phrases = (
        "bist ",
        "endeks",
        "endeksi",
        "endeksleri",
    )
    if any(phrase in lowered for phrase in index_phrases):
        return EventType.DIGER, MarketScope.BIST_WIDE

    return EventType.DIGER, MarketScope.OTHER


def _extract_body(text: str, title: str) -> str:
    start = text.find(title)
    body = text[start + len(title):] if start >= 0 else text

    for marker in (
        "Borsa İstanbul A.Ş. ©",
        "Telif Hakkı ve Çekince",
        "Kişisel Verilerin Korunması",
        "Bilgi Toplumu Hizmetleri",
    ):
        idx = body.find(marker)
        if idx >= 0:
            body = body[:idx]

    body = re.sub(r"\s+", " ", body).strip(" -:|")
    return (body or title)[:10000]


def parse_borsa_istanbul_announcement_html(
    raw_html: str,
    *,
    source_url: str,
) -> BorsaIstanbulFetchResult:
    validated_url, announcement_id = validate_borsa_istanbul_announcement_url(
        source_url
    )
    text, headings = _parse_visible(raw_html)
    if not text:
        raise BorsaIstanbulAdapterError(
            "Borsa İstanbul sayfasından okunabilir metin çıkarılamadı."
        )

    published_at = _extract_published_at(text)
    title = _extract_title(headings, announcement_id)
    body = _extract_body(text, title)
    event_type, market_scope = _classify_title(title)

    item = FeedItem(
        source_name="Borsa İstanbul",
        headline=title,
        published_at=published_at,
        body=body,
        source_reference=validated_url,
        event_title=title,
        event_type=event_type,
        occurred_at=published_at,
        market_scope=market_scope,
        symbols=(),
        sectors=(),
        external_id=announcement_id,
    )

    return BorsaIstanbulFetchResult(
        item=item,
        announcement_id=announcement_id,
        source_url=validated_url,
        response_bytes=len(str(raw_html or "").encode("utf-8")),
    )


class BorsaIstanbulAnnouncementUrlAdapter:
    """
    Tek bir resmî Borsa İstanbul duyuru detay URL'sini çeker.

    Ek/PDF bağlantılarını takip etmez. Otomatik liste taraması veya polling
    yapmaz. Ağ erişimi varsayılan kapalıdır.
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

    def fetch(self, url: str) -> BorsaIstanbulFetchResult:
        validated_url, announcement_id = validate_borsa_istanbul_announcement_url(
            url
        )
        if not self.network_enabled:
            raise BorsaIstanbulAdapterError(
                "Borsa İstanbul ağ erişimi kapalı. "
                "Bu işlem için açık kullanıcı onayı gerekir."
            )

        raw, final_url, content_type = self._fetcher(
            validated_url,
            self.timeout_seconds,
        )

        final_validated, final_announcement_id = (
            validate_borsa_istanbul_announcement_url(final_url)
        )
        if final_announcement_id != announcement_id:
            raise BorsaIstanbulAdapterError(
                "Borsa İstanbul yönlendirmesi farklı bir duyuru adresine gitti."
            )

        validate_official_source_html_payload(
            raw,
            content_type,
            error_type=BorsaIstanbulAdapterError,
            source_label='Borsa İstanbul',
        )
        decoded = decode_official_source_html(
            raw,
            error_type=BorsaIstanbulAdapterError,
            source_label='Borsa İstanbul',
        )

        parsed = parse_borsa_istanbul_announcement_html(
            decoded,
            source_url=final_validated,
        )
        return BorsaIstanbulFetchResult(
            item=parsed.item,
            announcement_id=parsed.announcement_id,
            source_url=parsed.source_url,
            response_bytes=len(raw),
        )
