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
_ALLOWED_HOSTS = {"resmigazete.gov.tr", "www.resmigazete.gov.tr"}
_DETAIL_PATH = re.compile(
    r"^/eskiler/(\d{4})/(\d{2})/(\d{8})-(\d+)\.htm$",
    re.IGNORECASE,
)

_LEGAL_TITLE_MARKERS = (
    "kanun",
    "yönetmelik",
    "yonetmelik",
    "tebliğ",
    "teblig",
    "karar",
    "genelge",
    "esaslar",
    "usul ve esas",
)


class ResmiGazeteAdapterError(RuntimeError):
    """Resmî Gazete adapteri güvenlik veya ayrıştırma hatası."""


@dataclass(frozen=True, slots=True)
class ResmiGazeteFetchResult:
    item: FeedItem
    article_id: str
    source_url: str
    response_bytes: int


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.candidates: list[str] = []
        self._skip_depth = 0
        self._candidate_depth = 0
        self._candidate_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
            return
        if lowered in {"h1", "h2", "h3", "h4", "strong", "b"} and self._skip_depth == 0:
            self._candidate_depth += 1
            if self._candidate_depth == 1:
                self._candidate_parts = []

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style", "noscript", "svg"}:
            if self._skip_depth:
                self._skip_depth -= 1
            return
        if lowered in {"h1", "h2", "h3", "h4", "strong", "b"} and self._candidate_depth:
            self._candidate_depth -= 1
            if self._candidate_depth == 0:
                candidate = re.sub(
                    r"\s+",
                    " ",
                    " ".join(self._candidate_parts),
                ).strip()
                if candidate:
                    self.candidates.append(candidate)
                self._candidate_parts = []

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        value = re.sub(r"\s+", " ", data).strip()
        if not value:
            return
        self.parts.append(value)
        if self._candidate_depth:
            self._candidate_parts.append(value)


FetchBytes = Callable[[str, int], tuple[bytes, str, str]]


def validate_resmi_gazete_article_url(url: str) -> tuple[str, str, datetime]:
    value = str(url or "").strip()
    parsed = urlparse(value)

    if parsed.scheme.lower() != "https":
        raise ResmiGazeteAdapterError(
            "Resmî Gazete URL'si HTTPS olmalıdır."
        )

    host = (parsed.hostname or "").lower()
    if host not in _ALLOWED_HOSTS:
        raise ResmiGazeteAdapterError(
            "Yalnız resmî resmigazete.gov.tr alan adı kabul edilir."
        )

    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ResmiGazeteAdapterError(
            "Resmî Gazete URL'sinde kullanıcı bilgisi veya özel port kullanılamaz."
        )

    if parsed.query or parsed.fragment:
        raise ResmiGazeteAdapterError(
            "Resmî Gazete URL'sinde sorgu veya fragment kabul edilmez."
        )

    decoded_path = unquote(parsed.path or "")
    match = _DETAIL_PATH.fullmatch(decoded_path)
    if not match:
        raise ResmiGazeteAdapterError(
            "Yalnız tekil Resmî Gazete HTML mevzuat URL'si kabul edilir: "
            "/eskiler/YYYY/MM/YYYYMMDD-N.htm"
        )

    folder_year, folder_month, date_token, item_no = match.groups()
    if date_token[:4] != folder_year or date_token[4:6] != folder_month:
        raise ResmiGazeteAdapterError(
            "Resmî Gazete URL tarih klasörü ile dosya tarihi uyuşmuyor."
        )

    try:
        published_at = datetime(
            int(date_token[:4]),
            int(date_token[4:6]),
            int(date_token[6:8]),
            0,
            0,
            0,
            tzinfo=ISTANBUL,
        )
    except ValueError as exc:
        raise ResmiGazeteAdapterError(
            "Resmî Gazete URL'sindeki tarih geçersiz."
        ) from exc

    article_id = f"{date_token}-{item_no}"
    return value, article_id, published_at


def _default_fetch(url: str, timeout_seconds: int) -> tuple[bytes, str, str]:
    response = fetch_official_source_bytes(
        url,
        timeout_seconds,
        user_agent='Hisse-Robotu/1.0 (+local decision-support; Resmi Gazete article preview)',
        error_type=ResmiGazeteAdapterError,
        source_label='Resmî Gazete',
    )
    return response.body, response.final_url, response.content_type


def _parse_visible(raw_html: str) -> tuple[str, tuple[str, ...]]:
    parser = _VisibleTextParser()
    parser.feed(str(raw_html or ""))
    parser.close()
    text = re.sub(r"\s+", " ", " ".join(parser.parts)).strip()
    return text, tuple(parser.candidates)


def _meaningful_candidate(value: str) -> bool:
    normalized = re.sub(r"\s+", " ", str(value or "")).strip()
    lowered = normalized.casefold().replace("i̇", "i")

    if len(normalized) < 8 or len(normalized) > 400:
        return False
    if lowered in {
        "resmî gazete",
        "resmi gazete",
        "yürütme ve idare bölümü",
        "yurutme ve idare bolumu",
        "yasama bölümü",
        "yasama bolumu",
        "ilan bölümü",
        "ilan bolumu",
    }:
        return False
    if re.fullmatch(r"sayı\s*:?\s*\d+", lowered):
        return False
    if re.fullmatch(r"\d{1,2}\s+\w+\s+\d{4}", lowered):
        return False
    return True


def _extract_title(
    candidates: tuple[str, ...],
    article_id: str,
) -> str:
    meaningful = tuple(
        candidate for candidate in candidates
        if _meaningful_candidate(candidate)
    )

    for candidate in meaningful:
        lowered = candidate.casefold().replace("i̇", "i")
        if any(marker in lowered for marker in _LEGAL_TITLE_MARKERS):
            return candidate

    if meaningful:
        return meaningful[0]

    return f"Resmî Gazete Mevzuatı ({article_id})"


def _classify_title(title: str) -> tuple[EventType, MarketScope]:
    lowered = title.casefold().replace("i̇", "i")

    if any(
        phrase in lowered
        for phrase in (
            "sermaye piyasası",
            "sermaye piyasasi",
            "pay piyasası",
            "pay piyasasi",
            "borsa istanbul",
            "borsa i̇stanbul",
        )
    ):
        return EventType.REGULASYON, MarketScope.BIST_WIDE

    if any(phrase in lowered for phrase in ("döviz", "doviz", "kambiyo")):
        return EventType.DOVIZ, MarketScope.TURKEY_MACRO

    if any(
        phrase in lowered
        for phrase in (
            "borçlanma",
            "borclanma",
            "tahvil",
            "hazine bonosu",
            "kira sertifikası",
            "kira sertifikasi",
        )
    ):
        return EventType.BORCLANMA_FINANSMAN, MarketScope.TURKEY_MACRO

    if any(
        phrase in lowered
        for phrase in (
            "enflasyon",
            "fiyat istikrarı",
            "fiyat istikrari",
        )
    ):
        return EventType.ENFLASYON, MarketScope.TURKEY_MACRO

    fiscal_or_financial = (
        "vergi",
        "özel tüketim vergisi",
        "ozel tuketim vergisi",
        "katma değer vergisi",
        "katma deger vergisi",
        "bütçe",
        "butce",
        "kamu mali",
        "bankacılık",
        "bankacilik",
        "finansal",
    )
    if any(phrase in lowered for phrase in fiscal_or_financial):
        return EventType.REGULASYON, MarketScope.TURKEY_MACRO

    if any(marker in lowered for marker in _LEGAL_TITLE_MARKERS):
        return EventType.REGULASYON, MarketScope.OTHER

    return EventType.DIGER, MarketScope.OTHER


def _extract_body(text: str, title: str) -> str:
    start = text.find(title)
    body = text[start + len(title):] if start >= 0 else text

    for marker in (
        "Sayfa :",
        "Resmî Gazete'nin kurumsal mobil uygulaması",
        "Resmi Gazete'nin kurumsal mobil uygulaması",
        "Cumhurbaşkanlığı Mevzuat Bilgi Sistemi",
    ):
        idx = body.find(marker)
        if idx >= 0:
            body = body[:idx]

    body = re.sub(r"\s+", " ", body).strip(" -:|")
    return (body or title)[:10000]


def parse_resmi_gazete_article_html(
    raw_html: str,
    *,
    source_url: str,
) -> ResmiGazeteFetchResult:
    (
        validated_url,
        article_id,
        published_at,
    ) = validate_resmi_gazete_article_url(source_url)

    text, candidates = _parse_visible(raw_html)
    if not text:
        raise ResmiGazeteAdapterError(
            "Resmî Gazete sayfasından okunabilir metin çıkarılamadı."
        )

    title = _extract_title(candidates, article_id)
    body = _extract_body(text, title)
    event_type, market_scope = _classify_title(title)

    item = FeedItem(
        source_name="Resmî Gazete",
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
        external_id=article_id,
    )

    return ResmiGazeteFetchResult(
        item=item,
        article_id=article_id,
        source_url=validated_url,
        response_bytes=len(str(raw_html or "").encode("utf-8")),
    )


class ResmiGazeteArticleUrlAdapter:
    """
    Tek bir resmî Resmî Gazete HTML mevzuat URL'sini çeker.

    Günlük sayı indeksini, PDF eklerini veya aynı sayının diğer maddelerini
    otomatik takip etmez. Ağ erişimi varsayılan kapalıdır.
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

    def fetch(self, url: str) -> ResmiGazeteFetchResult:
        (
            validated_url,
            article_id,
            _,
        ) = validate_resmi_gazete_article_url(url)

        if not self.network_enabled:
            raise ResmiGazeteAdapterError(
                "Resmî Gazete ağ erişimi kapalı. "
                "Bu işlem için açık kullanıcı onayı gerekir."
            )

        raw, final_url, content_type = self._fetcher(
            validated_url,
            self.timeout_seconds,
        )

        (
            final_validated,
            final_article_id,
            _,
        ) = validate_resmi_gazete_article_url(final_url)

        if final_article_id != article_id:
            raise ResmiGazeteAdapterError(
                "Resmî Gazete yönlendirmesi farklı bir mevzuat maddesine gitti."
            )

        validate_official_source_html_payload(
            raw,
            content_type,
            error_type=ResmiGazeteAdapterError,
            source_label='Resmî Gazete',
        )
        decoded = decode_official_source_html(
            raw,
            error_type=ResmiGazeteAdapterError,
            source_label='Resmî Gazete',
        )

        parsed = parse_resmi_gazete_article_html(
            decoded,
            source_url=final_validated,
        )
        return ResmiGazeteFetchResult(
            item=parsed.item,
            article_id=parsed.article_id,
            source_url=parsed.source_url,
            response_bytes=len(raw),
        )
