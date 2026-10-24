from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import re
from zoneinfo import ZoneInfo

from .models import MarketEvent, NewsRecord
from .source_registry import resolve_source


ISTANBUL = ZoneInfo("Europe/Istanbul")


@dataclass(frozen=True, slots=True)
class KAPDisclosure:
    news_id: str
    event_id: str
    event_title: str
    published_at: datetime
    importance_score: int
    event_type: str
    symbols: tuple[str, ...]
    headline: str
    source_reference: str
    source_match: str
    portfolio_symbols: tuple[str, ...]

    @property
    def is_high_importance(self) -> bool:
        return self.importance_score >= 80

    @property
    def has_symbol(self) -> bool:
        return bool(self.symbols)

    @property
    def has_portfolio_touch(self) -> bool:
        return bool(self.portfolio_symbols)


@dataclass(frozen=True, slots=True)
class KAPFlowBrief:
    disclosures: tuple[KAPDisclosure, ...]
    total_disclosure_count: int
    unique_company_count: int
    high_importance_count: int
    portfolio_touch_count: int
    missing_symbol_count: int


def _require_aware(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValueError(f"{field_name} datetime olmalıdır.")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} saat dilimi içermelidir.")
    return value


def _normalize_symbol(value: str) -> str:
    symbol = str(value or "").strip().upper()
    if not symbol:
        return ""
    if "." not in symbol:
        symbol = f"{symbol}.IS"
    if not re.fullmatch(r"[A-Z0-9_]+\.[A-Z0-9_]+", symbol):
        raise ValueError(f"Geçersiz hisse sembolü: {value}")
    return symbol


def _is_verified_kap(news: NewsRecord) -> tuple[bool, str]:
    resolution = resolve_source(news.source_name, news.source_reference)
    if resolution is None or resolution.canonical_name != "KAP":
        return False, ""
    return True, resolution.matched_by


def kap_available_symbols(
    events: tuple[MarketEvent, ...],
    news: tuple[NewsRecord, ...],
) -> tuple[str, ...]:
    event_by_id = {event.event_id: event for event in events}
    symbols: set[str] = set()
    for item in news:
        is_kap, _ = _is_verified_kap(item)
        if not is_kap:
            continue
        event = event_by_id.get(item.event_id)
        if event is None:
            continue
        symbols.update(event.symbols)
    return tuple(sorted(symbols))


def build_kap_flow(
    events: tuple[MarketEvent, ...],
    news: tuple[NewsRecord, ...],
    *,
    now: datetime,
    lookback_hours: int | None = 24,
    min_importance: int = 0,
    symbol_filter: str = "",
    portfolio_symbols: tuple[str, ...] = (),
    portfolio_only: bool = False,
) -> KAPFlowBrief:
    """Arşivde doğrulanmış KAP bildirimlerini deterministik olarak listeler.

    Kaynak yalnız güvenilir kaynak sözlüğünde KAP olarak çözümlenirse akışa
    alınır. Yeni bir skor, fiyat yönü, AL/SAT kararı veya AI yorumu üretilmez.
    Portföy teması yalnız olayın açık sembolleri ile verilen portföy sembollerinin
    doğrudan kesişimidir.
    """

    now = _require_aware(now, "now")
    if lookback_hours is not None:
        if not isinstance(lookback_hours, int) or lookback_hours <= 0:
            raise ValueError("lookback_hours pozitif tam sayı veya None olmalıdır.")
        cutoff = now - timedelta(hours=lookback_hours)
    else:
        cutoff = None

    if not isinstance(min_importance, int) or not 0 <= min_importance <= 100:
        raise ValueError("min_importance 0-100 aralığında tam sayı olmalıdır.")

    normalized_filter = _normalize_symbol(symbol_filter)
    normalized_portfolio = tuple(
        dict.fromkeys(
            symbol
            for symbol in (_normalize_symbol(item) for item in portfolio_symbols)
            if symbol
        )
    )
    portfolio_set = set(normalized_portfolio)

    event_by_id = {event.event_id: event for event in events}
    disclosures: list[KAPDisclosure] = []

    for item in news:
        is_kap, matched_by = _is_verified_kap(item)
        if not is_kap:
            continue

        event = event_by_id.get(item.event_id)
        if event is None:
            raise ValueError(
                f"KAP haberi bağlı olay olmadan verildi: {item.news_id} / {item.event_id}"
            )

        published_at = _require_aware(item.published_at, "KAP yayın zamanı")
        if cutoff is not None and published_at < cutoff:
            continue
        if published_at > now:
            continue
        if event.importance_score < min_importance:
            continue
        if normalized_filter and normalized_filter not in event.symbols:
            continue

        portfolio_hits = tuple(
            symbol for symbol in event.symbols if symbol in portfolio_set
        )
        if portfolio_only and not portfolio_hits:
            continue

        disclosures.append(
            KAPDisclosure(
                news_id=item.news_id,
                event_id=event.event_id,
                event_title=event.title,
                published_at=published_at,
                importance_score=event.importance_score,
                event_type=event.event_type.value,
                symbols=event.symbols,
                headline=item.headline,
                source_reference=item.source_reference,
                source_match=matched_by,
                portfolio_symbols=portfolio_hits,
            )
        )

    disclosures.sort(
        key=lambda item: (
            -item.published_at.timestamp(),
            -item.importance_score,
            item.event_id,
            item.news_id,
        )
    )
    ordered = tuple(disclosures)
    unique_symbols = {
        symbol for item in ordered for symbol in item.symbols
    }

    return KAPFlowBrief(
        disclosures=ordered,
        total_disclosure_count=len(ordered),
        unique_company_count=len(unique_symbols),
        high_importance_count=sum(item.is_high_importance for item in ordered),
        portfolio_touch_count=sum(item.has_portfolio_touch for item in ordered),
        missing_symbol_count=sum(not item.has_symbol for item in ordered),
    )


def kap_flow_rows(brief: KAPFlowBrief) -> list[dict[str, object]]:
    return [
        {
            "Yayın zamanı": item.published_at.astimezone(ISTANBUL).strftime(
                "%Y-%m-%d %H:%M"
            ),
            "Önem": item.importance_score,
            "Hisse": ", ".join(item.symbols) or "—",
            "Portföy teması": ", ".join(item.portfolio_symbols) or "—",
            "Tür": item.event_type,
            "Bildirim": item.headline,
            "Olay": item.event_title,
            "KAP doğrulaması": (
                "Kaynak adı" if item.source_match == "source_name" else "kap.org.tr"
            ),
            "Referans": item.source_reference or "—",
            "Olay kimliği": item.event_id,
            "Haber kimliği": item.news_id,
        }
        for item in brief.disclosures
    ]
