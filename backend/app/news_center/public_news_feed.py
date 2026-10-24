from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
import hashlib
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from .classifier import classify_news
from .feed_ingestion import FeedItem
from .models import EventType, MarketScope


PUBLIC_NEWS_MAX_RESPONSE_BYTES = 2_000_000
PUBLIC_NEWS_DEFAULT_TIMEOUT_SECONDS = 10
PUBLIC_NEWS_MIN_TIMEOUT_SECONDS = 1
PUBLIC_NEWS_MAX_TIMEOUT_SECONDS = 30
PUBLIC_NEWS_MAX_ITEMS_PER_FEED = 40
PUBLIC_NEWS_USER_AGENT = "Hisse-Robotu/1.1 public-news-feed"


class PublicNewsFeedError(RuntimeError):
    """Halka açık haber akışı güvenli biçimde okunamadığında oluşur."""


@dataclass(frozen=True, slots=True)
class PublicNewsFeedSpec:
    slug: str
    canonical_name: str
    channel_name: str
    feed_url: str
    allowed_hosts: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PublicNewsFeedFetchResult:
    spec: PublicNewsFeedSpec
    items: tuple[FeedItem, ...]
    fetched_at: datetime
    final_url: str


PUBLIC_NEWS_FEEDS: tuple[PublicNewsFeedSpec, ...] = (
    PublicNewsFeedSpec(
        slug="aa_ekonomi",
        canonical_name="Anadolu Ajansı",
        channel_name="AA Ekonomi",
        feed_url="https://www.aa.com.tr/tr/teyithatti/rss/news?cat=ekonomi",
        allowed_hosts=("aa.com.tr",),
    ),
    PublicNewsFeedSpec(
        slug="trt_ekonomi",
        canonical_name="TRT Haber",
        channel_name="TRT Haber Ekonomi",
        feed_url="https://www.trthaber.com/ekonomi_articles.rss",
        allowed_hosts=("trthaber.com",),
    ),
    PublicNewsFeedSpec(
        slug="trt_son_dakika",
        canonical_name="TRT Haber",
        channel_name="TRT Haber Son Dakika",
        feed_url="https://www.trthaber.com/sondakika_articles.rss",
        allowed_hosts=("trthaber.com",),
    ),
)


class _HtmlTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = re.sub(r"\s+", " ", str(data or "")).strip()
        if text:
            self.parts.append(text)


def public_news_feed_specs() -> tuple[PublicNewsFeedSpec, ...]:
    return PUBLIC_NEWS_FEEDS


def _host_allowed(url: str, allowed_hosts: tuple[str, ...]) -> bool:
    try:
        host = (urlsplit(str(url or "")).hostname or "").lower().strip(".")
    except ValueError:
        return False
    if host.startswith("www."):
        host = host[4:]
    return any(
        host == allowed or host.endswith(f".{allowed}")
        for allowed in (item.lower().strip(".") for item in allowed_hosts)
    )


def _clean_html_text(value: str) -> str:
    raw = unescape(str(value or ""))
    parser = _HtmlTextExtractor()
    try:
        parser.feed(raw)
        parser.close()
    except Exception:
        pass
    text = " ".join(parser.parts) if parser.parts else re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", text).strip()


def _local_name(tag: str) -> str:
    return str(tag or "").rsplit("}", 1)[-1].lower()


def _child_text(node: ET.Element, *names: str) -> str:
    wanted = {name.lower() for name in names}
    for child in list(node):
        if _local_name(child.tag) in wanted:
            return "".join(child.itertext()).strip()
    return ""


def _entry_link(node: ET.Element) -> str:
    direct = _child_text(node, "link")
    if direct:
        return direct.strip()
    for child in list(node):
        if _local_name(child.tag) != "link":
            continue
        href = str(child.attrib.get("href") or "").strip()
        rel = str(child.attrib.get("rel") or "alternate").strip().lower()
        if href and rel in {"", "alternate"}:
            return href
    return ""


def _parse_datetime(value: str) -> datetime | None:
    raw = re.sub(r"\s+", " ", str(value or "")).strip()
    if not raw:
        return None
    try:
        parsed = parsedate_to_datetime(raw)
    except (TypeError, ValueError, OverflowError):
        parsed = None
    if parsed is None:
        candidate = raw.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError:
            return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _entry_nodes(root: ET.Element) -> tuple[ET.Element, ...]:
    root_name = _local_name(root.tag)
    if root_name == "rss":
        for child in list(root):
            if _local_name(child.tag) == "channel":
                return tuple(item for item in list(child) if _local_name(item.tag) == "item")
    if root_name == "feed":
        return tuple(item for item in list(root) if _local_name(item.tag) == "entry")
    return tuple(item for item in root.iter() if _local_name(item.tag) in {"item", "entry"})


def parse_public_news_feed(
    spec: PublicNewsFeedSpec,
    body: bytes,
    *,
    max_items: int = PUBLIC_NEWS_MAX_ITEMS_PER_FEED,
) -> tuple[FeedItem, ...]:
    if not isinstance(max_items, int) or not 1 <= max_items <= PUBLIC_NEWS_MAX_ITEMS_PER_FEED:
        raise ValueError(
            f"max_items 1-{PUBLIC_NEWS_MAX_ITEMS_PER_FEED} aralığında olmalıdır."
        )
    if not body:
        raise PublicNewsFeedError(f"{spec.channel_name} RSS yanıtı boş.")

    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        raise PublicNewsFeedError(
            f"{spec.channel_name} RSS/XML yanıtı çözülemedi."
        ) from exc

    items: list[FeedItem] = []
    seen_ids: set[str] = set()
    for node in _entry_nodes(root):
        headline = _clean_html_text(_child_text(node, "title"))
        link = _entry_link(node).strip()
        body_text = _clean_html_text(
            _child_text(node, "description", "summary", "content")
        )
        published_at = _parse_datetime(
            _child_text(node, "pubdate", "published", "updated", "date")
        )
        external_id = _clean_html_text(_child_text(node, "guid", "id")) or link

        if not headline or published_at is None:
            continue
        if link and not _host_allowed(link, spec.allowed_hosts):
            # Bir RSS kaydı kaynak alan adının dışına yönlendiriyorsa içeriği otomatik kabul etme.
            continue
        if not body_text:
            body_text = headline

        unique_key = external_id or hashlib.sha256(
            f"{headline}\n{published_at.isoformat()}".encode("utf-8")
        ).hexdigest()
        if unique_key in seen_ids:
            continue
        seen_ids.add(unique_key)

        suggestion = classify_news(
            source_name=spec.canonical_name,
            source_reference=link or spec.feed_url,
            headline=headline,
            body=body_text,
        )
        items.append(
            FeedItem(
                source_name=spec.canonical_name,
                headline=headline,
                published_at=published_at,
                body=body_text,
                source_reference=link or spec.feed_url,
                event_title=headline,
                event_type=suggestion.event_type or EventType.DIGER,
                occurred_at=published_at,
                market_scope=suggestion.market_scope or MarketScope.OTHER,
                sectors=suggestion.sectors,
                symbols=(),
                external_id=external_id,
            )
        )
        if len(items) >= max_items:
            break

    return tuple(sorted(items, key=lambda item: item.published_at, reverse=True))


def fetch_public_news_feed(
    spec: PublicNewsFeedSpec,
    *,
    timeout_seconds: int = PUBLIC_NEWS_DEFAULT_TIMEOUT_SECONDS,
    max_items: int = PUBLIC_NEWS_MAX_ITEMS_PER_FEED,
) -> PublicNewsFeedFetchResult:
    if (
        not isinstance(timeout_seconds, int)
        or not PUBLIC_NEWS_MIN_TIMEOUT_SECONDS
        <= timeout_seconds
        <= PUBLIC_NEWS_MAX_TIMEOUT_SECONDS
    ):
        raise ValueError("timeout_seconds 1-30 aralığında tam sayı olmalıdır.")
    if not _host_allowed(spec.feed_url, spec.allowed_hosts):
        raise PublicNewsFeedError(
            f"{spec.channel_name} kayıtlı RSS adresi izin verilen alan adıyla eşleşmiyor."
        )

    request = Request(
        spec.feed_url,
        headers={
            "User-Agent": PUBLIC_NEWS_USER_AGENT,
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*;q=0.1",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            final_url = response.geturl()
            content_type = str(response.headers.get("Content-Type", ""))
            body = response.read(PUBLIC_NEWS_MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        raise PublicNewsFeedError(
            f"{spec.channel_name} HTTP hatası: {exc.code}"
        ) from exc
    except URLError as exc:
        raise PublicNewsFeedError(
            f"{spec.channel_name} bağlantı hatası: {exc.reason}"
        ) from exc
    except TimeoutError as exc:
        raise PublicNewsFeedError(
            f"{spec.channel_name} bağlantısı zaman aşımına uğradı."
        ) from exc

    if not _host_allowed(final_url, spec.allowed_hosts):
        raise PublicNewsFeedError(
            f"{spec.channel_name} beklenmeyen alan adına yönlendirildi."
        )
    if len(body) > PUBLIC_NEWS_MAX_RESPONSE_BYTES:
        raise PublicNewsFeedError(
            f"{spec.channel_name} yanıtı güvenlik boyutu sınırını aşıyor."
        )
    lowered_type = content_type.lower()
    if lowered_type and not any(
        token in lowered_type
        for token in ("xml", "rss", "atom", "text/plain", "application/octet-stream")
    ):
        raise PublicNewsFeedError(
            f"{spec.channel_name} yanıtı RSS/XML değil: {content_type or 'bilinmiyor'}"
        )

    items = parse_public_news_feed(spec, body, max_items=max_items)
    return PublicNewsFeedFetchResult(
        spec=spec,
        items=items,
        fetched_at=datetime.now(timezone.utc),
        final_url=final_url,
    )
