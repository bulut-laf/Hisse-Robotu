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
_ALLOWED_HOSTS = {"kap.org.tr", "www.kap.org.tr"}
_DETAIL_PATH = re.compile(r"^/tr/Bildirim/(\d+)/?$", re.IGNORECASE)


class KapAdapterError(RuntimeError):
    """KAP URL adapteri güvenlik veya ayrıştırma hatası."""


@dataclass(frozen=True, slots=True)
class KapFetchResult:
    item: FeedItem
    notification_id: str
    source_url: str
    response_bytes: int


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            value = re.sub(r"\s+", " ", data).strip()
            if value:
                self.parts.append(value)


FetchBytes = Callable[[str, int], tuple[bytes, str, str]]


def validate_kap_detail_url(url: str) -> tuple[str, str]:
    value = str(url or "").strip()
    parsed = urlparse(value)

    if parsed.scheme.lower() != "https":
        raise KapAdapterError("KAP URL'si HTTPS olmalıdır.")
    host = (parsed.hostname or "").lower()
    if host not in _ALLOWED_HOSTS:
        raise KapAdapterError("Yalnız resmî kap.org.tr alan adı kabul edilir.")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise KapAdapterError("KAP URL'sinde kullanıcı bilgisi veya özel port kullanılamaz.")

    match = _DETAIL_PATH.fullmatch(parsed.path or "")
    if not match:
        raise KapAdapterError(
            "Yalnız KAP bildirim detay URL'si kabul edilir: /tr/Bildirim/<numara>"
        )
    if parsed.query or parsed.fragment:
        raise KapAdapterError("KAP bildirim URL'sinde sorgu veya fragment kabul edilmez.")

    return value, match.group(1)


def _default_fetch(url: str, timeout_seconds: int) -> tuple[bytes, str, str]:
    response = fetch_official_source_bytes(
        url,
        timeout_seconds,
        user_agent='Hisse-Robotu/1.0 (+local decision-support; KAP detail preview)',
        error_type=KapAdapterError,
        source_label='KAP',
    )
    return response.body, response.final_url, response.content_type


def _visible_text(raw_html: str) -> str:
    parser = _VisibleTextParser()
    parser.feed(raw_html)
    parser.close()
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def _extract_between(
    text: str,
    start_labels: tuple[str, ...],
    end_labels: tuple[str, ...],
) -> str:
    start = -1
    used_label = ""
    lowered = text.casefold()
    for label in start_labels:
        idx = lowered.find(label.casefold())
        if idx >= 0 and (start < 0 or idx < start):
            start = idx
            used_label = label
    if start < 0:
        return ""

    content_start = start + len(used_label)
    end = len(text)
    for label in end_labels:
        idx = lowered.find(label.casefold(), content_start)
        if idx >= 0:
            end = min(end, idx)

    value = text[content_start:end]
    value = re.sub(r"^[\s|:;\-–—]+", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _extract_published_at(text: str) -> datetime:
    match = re.search(
        r"Gönderim Tarihi\s+(\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}:\d{2})",
        text,
        re.IGNORECASE,
    )
    if not match:
        raise KapAdapterError("KAP sayfasında Gönderim Tarihi bulunamadı.")
    try:
        parsed = datetime.strptime(match.group(1), "%d.%m.%Y %H:%M:%S")
    except ValueError as exc:
        raise KapAdapterError("KAP Gönderim Tarihi ayrıştırılamadı.") from exc
    return parsed.replace(tzinfo=ISTANBUL)


def _extract_symbols(text: str) -> tuple[str, ...]:
    segment = _extract_between(
        text,
        ("İlgili Şirketler", "İlgili Şirketler Related Companies"),
        (
            "İlgili Fonlar",
            "Türkçe",
            "İngilizce",
            "Açıklamalar",
            "Yapılan açıklama düzeltme mi?",
            "Yapılan Açıklama Düzeltme mi?",
        ),
    )
    if not segment:
        return ()

    result: list[str] = []
    seen: set[str] = set()
    for token in re.findall(r"\b[A-Z0-9]{3,6}\b", segment.upper()):
        if token in {"RELATED", "COMPANIES", "ODA", "KAP"}:
            continue
        symbol = f"{token}.IS"
        if symbol not in seen:
            result.append(symbol)
            seen.add(symbol)
    return tuple(result)


def parse_kap_detail_html(
    raw_html: str,
    *,
    source_url: str,
) -> KapFetchResult:
    validated_url, notification_id = validate_kap_detail_url(source_url)
    text = _visible_text(str(raw_html or ""))
    if not text:
        raise KapAdapterError("KAP sayfasından okunabilir metin çıkarılamadı.")

    published_at = _extract_published_at(text)

    summary = _extract_between(
        text,
        ("Özet Bilgi",),
        (
            "Yapılan açıklama düzeltme mi?",
            "Yapılan Açıklama Düzeltme mi?",
            "İlgili Şirketler",
            "Açıklamalar",
            "Türkçe",
            "İngilizce",
        ),
    )
    explanations = _extract_between(
        text,
        ("Açıklamalar", "Açıklamalar Explanations"),
        (
            "Bildirimlerin MKK tarafından",
            "oda_",
        ),
    )
    symbols = _extract_symbols(text)

    headline = summary or f"KAP Bildirimi {notification_id}"
    body = explanations or summary or headline

    item = FeedItem(
        source_name="KAP",
        headline=headline,
        published_at=published_at,
        body=body,
        source_reference=validated_url,
        event_title=headline,
        event_type=EventType.KAP_ACIKLAMASI,
        occurred_at=published_at,
        market_scope=MarketScope.COMPANY if symbols else MarketScope.OTHER,
        symbols=symbols,
        sectors=(),
        external_id=notification_id,
    )
    return KapFetchResult(
        item=item,
        notification_id=notification_id,
        source_url=validated_url,
        response_bytes=len(raw_html.encode("utf-8")),
    )


class KapUrlAdapter:
    """
    Tek bir resmî KAP bildirim detay URL'sini çeker.

    Otomatik tarama/polling yapmaz. Ağ erişimi varsayılan kapalıdır ve adapter
    ancak network_enabled=True ile açıkça etkinleştirilirse GET isteği yapar.
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

    def fetch(self, url: str) -> KapFetchResult:
        validated_url, notification_id = validate_kap_detail_url(url)
        if not self.network_enabled:
            raise KapAdapterError(
                "KAP ağ erişimi kapalı. Bu işlem için açık kullanıcı onayı gerekir."
            )

        raw, final_url, content_type = self._fetcher(
            validated_url,
            self.timeout_seconds,
        )

        final_validated, final_notification_id = validate_kap_detail_url(final_url)
        if final_notification_id != notification_id:
            raise KapAdapterError("KAP yönlendirmesi farklı bir bildirim numarasına gitti.")

        validate_official_source_html_payload(
            raw,
            content_type,
            error_type=KapAdapterError,
            source_label='KAP',
        )
        decoded = decode_official_source_html(
            raw,
            error_type=KapAdapterError,
            source_label='KAP',
        )

        parsed = parse_kap_detail_html(decoded, source_url=final_validated)
        return KapFetchResult(
            item=parsed.item,
            notification_id=parsed.notification_id,
            source_url=parsed.source_url,
            response_bytes=len(raw),
        )
