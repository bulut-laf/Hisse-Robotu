from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
import re
from unicodedata import normalize as unicode_normalize

from .models import EventType, MarketEvent, MarketScope, NewsRecord


class GroupingDecision(StrEnum):
    AUTO_ATTACH = "AUTO_ATTACH"
    REVIEW = "REVIEW"


@dataclass(frozen=True, slots=True)
class EventMatch:
    event_id: str
    event_title: str
    decision: GroupingDecision
    reasons: tuple[str, ...]
    title_similarity: float
    time_gap_minutes: int


_STOPWORDS = {
    "aciklama", "aciklamasi", "aciklamaya", "acikladi", "aciklandi",
    "açıklama", "açıklaması", "açıkladı", "açıklandı",
    "ile", "icin", "için", "ve", "veya", "bir", "bu", "son", "yeni",
    "hakkinda", "hakkında", "duyuru", "bildirim", "haber", "gore", "göre",
    "the", "and", "for", "from", "with", "on", "in", "of", "to", "a",
}

_MACRO_SCOPES = {
    MarketScope.GLOBAL,
    MarketScope.TURKEY_MACRO,
    MarketScope.BIST_WIDE,
}


def _asciiish(value: str) -> str:
    table = str.maketrans(
        {
            "ç": "c",
            "ğ": "g",
            "ı": "i",
            "ö": "o",
            "ş": "s",
            "ü": "u",
            "Ç": "c",
            "Ğ": "g",
            "İ": "i",
            "I": "i",
            "Ö": "o",
            "Ş": "s",
            "Ü": "u",
        }
    )
    value = unicode_normalize("NFKC", str(value or "")).translate(table).casefold()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _stem_token(token: str) -> str:
    # Başlık eşleştirmesinde sık görülen sınırlı Türkçe belirtme/iyelik
    # eklerini normalize eder. Amaç dilbilimsel kök bulma değil;
    # "kararı/kararını" gibi aynı olay sözcüklerini eşitlemektir.
    for suffix in ("larini", "lerini", "inin", "unun", "ini", "unu", "nin", "nun", "yi", "yu"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 4:
            return token[: -len(suffix)]
    if token.endswith(("i", "u")) and len(token) >= 6:
        return token[:-1]
    return token


def _tokens(value: str) -> frozenset[str]:
    result: set[str] = set()
    for token in _asciiish(value).split():
        if len(token) < 2 or token in _STOPWORDS:
            continue
        stemmed = _stem_token(token)
        if len(stemmed) >= 2 and stemmed not in _STOPWORDS:
            result.add(stemmed)
    return frozenset(result)


def title_similarity(left: str, right: str) -> float:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    union = left_tokens | right_tokens
    if not union:
        return 0.0
    return len(left_tokens & right_tokens) / len(union)


def _normalized_reference(value: str) -> str:
    value = _asciiish(value)
    if not value:
        return ""
    return re.sub(r"\s+", "", value)


def _reference_is_strong(value: str) -> bool:
    if not value:
        return False
    return len(value) >= 8 and (any(char.isdigit() for char in value) or "http" in value)


def _same_local_date(left: datetime, right: datetime) -> bool:
    return left.astimezone(right.tzinfo).date() == right.date()


def _time_gap_minutes(left: datetime, right: datetime) -> int:
    return int(abs((left - right).total_seconds()) // 60)


def _headline_similarity(
    requested_title: str,
    event: MarketEvent,
    attached_news: tuple[NewsRecord, ...],
) -> float:
    candidates = [event.title, *(item.headline for item in attached_news)]
    return max((title_similarity(requested_title, item) for item in candidates), default=0.0)


def evaluate_event_match(
    *,
    requested_title: str,
    event_type: EventType,
    market_scope: MarketScope,
    occurred_at: datetime,
    symbols: tuple[str, ...],
    source_reference: str,
    event: MarketEvent,
    attached_news: tuple[NewsRecord, ...],
) -> EventMatch | None:
    """Tek bir mevcut olaya karşı deterministik eşleşme kararı üretir."""

    if event_type is EventType.DIGER or event.event_type is EventType.DIGER:
        return None
    if event.event_type is not event_type:
        return None
    if market_scope is MarketScope.OTHER or event.market_scope is MarketScope.OTHER:
        return None
    if event.market_scope is not market_scope:
        return None

    gap = _time_gap_minutes(occurred_at, event.occurred_at)
    same_date = _same_local_date(occurred_at, event.occurred_at)
    similarity = _headline_similarity(requested_title, event, attached_news)

    requested_symbols = set(symbols)
    existing_symbols = set(event.symbols)
    symbol_overlap = bool(requested_symbols & existing_symbols)

    request_ref = _normalized_reference(source_reference)
    existing_refs = {
        _normalized_reference(item.source_reference)
        for item in attached_news
        if item.source_reference
    }
    same_strong_reference = (
        _reference_is_strong(request_ref) and request_ref in existing_refs
    )

    if same_strong_reference:
        return EventMatch(
            event_id=event.event_id,
            event_title=event.title,
            decision=GroupingDecision.AUTO_ATTACH,
            reasons=(
                "Aynı güçlü kaynak referansı mevcut olayda bulundu.",
                f"Olay türü ve piyasa kapsamı eşleşti: {event_type.value} / {market_scope.value}.",
            ),
            title_similarity=similarity,
            time_gap_minutes=gap,
        )

    if market_scope is MarketScope.COMPANY:
        if not requested_symbols or not existing_symbols or not symbol_overlap:
            return None
        if gap <= 240 and similarity >= 0.55:
            return EventMatch(
                event_id=event.event_id,
                event_title=event.title,
                decision=GroupingDecision.AUTO_ATTACH,
                reasons=(
                    "Aynı şirket/hisse kesişimi bulundu.",
                    "Olay türü ve şirket kapsamı eşleşti.",
                    "Olay zamanları en fazla 4 saat farklı.",
                    f"Başlık benzerliği yeterli: {similarity:.2f}.",
                ),
                title_similarity=similarity,
                time_gap_minutes=gap,
            )
        if same_date and gap <= 1440 and similarity >= 0.30:
            return EventMatch(
                event_id=event.event_id,
                event_title=event.title,
                decision=GroupingDecision.REVIEW,
                reasons=(
                    "Aynı şirket/hisse ve olay türü bulundu.",
                    "Aynı gün içinde benzer başlık var ancak otomatik birleştirme eşiği sağlanmadı.",
                    f"Başlık benzerliği: {similarity:.2f}.",
                ),
                title_similarity=similarity,
                time_gap_minutes=gap,
            )
        return None

    if market_scope in _MACRO_SCOPES:
        if not same_date:
            return None
        if gap <= 480 and similarity >= 0.45:
            return EventMatch(
                event_id=event.event_id,
                event_title=event.title,
                decision=GroupingDecision.AUTO_ATTACH,
                reasons=(
                    "Makro/BIST olay türü ve kapsamı aynı.",
                    "Olaylar aynı takvim gününde ve en fazla 8 saat farklı.",
                    f"Başlık benzerliği yeterli: {similarity:.2f}.",
                ),
                title_similarity=similarity,
                time_gap_minutes=gap,
            )
        if gap <= 1440 and similarity >= 0.30:
            return EventMatch(
                event_id=event.event_id,
                event_title=event.title,
                decision=GroupingDecision.REVIEW,
                reasons=(
                    "Makro/BIST olay türü, kapsamı ve günü eşleşti.",
                    "Başlık benzerliği yalnız inceleme eşiğini geçti.",
                    f"Başlık benzerliği: {similarity:.2f}.",
                ),
                title_similarity=similarity,
                time_gap_minutes=gap,
            )
        return None

    # Sektör gibi diğer kontrollü kapsamlar: otomatik eşik daha katıdır.
    if same_date and gap <= 360 and similarity >= 0.60:
        return EventMatch(
            event_id=event.event_id,
            event_title=event.title,
            decision=GroupingDecision.AUTO_ATTACH,
            reasons=(
                "Olay türü, kapsam ve gün eşleşti.",
                "Olay zamanları en fazla 6 saat farklı.",
                f"Başlık benzerliği yüksek: {similarity:.2f}.",
            ),
            title_similarity=similarity,
            time_gap_minutes=gap,
        )
    if same_date and similarity >= 0.35:
        return EventMatch(
            event_id=event.event_id,
            event_title=event.title,
            decision=GroupingDecision.REVIEW,
            reasons=(
                "Olay türü, kapsam ve gün eşleşti.",
                "Benzerlik otomatik birleştirme için yeterli değil; kullanıcı incelemesi gerekir.",
                f"Başlık benzerliği: {similarity:.2f}.",
            ),
            title_similarity=similarity,
            time_gap_minutes=gap,
        )
    return None


def best_event_match(
    *,
    requested_title: str,
    event_type: EventType,
    market_scope: MarketScope,
    occurred_at: datetime,
    symbols: tuple[str, ...],
    source_reference: str,
    events: tuple[MarketEvent, ...],
    news: tuple[NewsRecord, ...],
) -> EventMatch | None:
    news_by_event: dict[str, list[NewsRecord]] = {}
    for item in news:
        news_by_event.setdefault(item.event_id, []).append(item)

    matches: list[EventMatch] = []
    for event in events:
        match = evaluate_event_match(
            requested_title=requested_title,
            event_type=event_type,
            market_scope=market_scope,
            occurred_at=occurred_at,
            symbols=symbols,
            source_reference=source_reference,
            event=event,
            attached_news=tuple(news_by_event.get(event.event_id, ())),
        )
        if match is not None:
            matches.append(match)

    if not matches:
        return None

    def rank(item: EventMatch) -> tuple[int, float, int]:
        decision_rank = 1 if item.decision is GroupingDecision.AUTO_ATTACH else 0
        return (decision_rank, item.title_similarity, -item.time_gap_minutes)

    return max(matches, key=rank)
