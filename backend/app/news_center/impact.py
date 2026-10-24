from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re

from .models import EventType, MarketEvent, MarketScope, NewsRecord


class ImpactTargetType(StrEnum):
    MARKET = "MARKET"
    SECTOR = "SECTOR"
    SYMBOL = "SYMBOL"


class ImpactRelation(StrEnum):
    DIRECT = "DIRECT"
    SENSITIVITY = "SENSITIVITY"


class ImpactTag(StrEnum):
    MARKET_WIDE = "MARKET_WIDE"
    COMPANY_SPECIFIC = "COMPANY_SPECIFIC"
    SECTOR_SPECIFIC = "SECTOR_SPECIFIC"
    RATE_SENSITIVE = "RATE_SENSITIVE"
    INFLATION_SENSITIVE = "INFLATION_SENSITIVE"
    FX_SENSITIVE = "FX_SENSITIVE"
    COMMODITY_SENSITIVE = "COMMODITY_SENSITIVE"
    REGULATORY = "REGULATORY"
    EARNINGS = "EARNINGS"
    DIVIDEND = "DIVIDEND"
    CAPITAL_ACTION = "CAPITAL_ACTION"
    FINANCING = "FINANCING"
    GEOPOLITICAL = "GEOPOLITICAL"


@dataclass(frozen=True, slots=True)
class ImpactLink:
    target_type: ImpactTargetType
    target: str
    relation: ImpactRelation
    confidence: int
    tags: tuple[ImpactTag, ...]
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if not str(self.target or "").strip():
            raise ValueError("Etki hedefi boş olamaz.")
        if not isinstance(self.confidence, int) or not 0 <= self.confidence <= 100:
            raise ValueError("Etki bağlantı güveni 0-100 aralığında tam sayı olmalıdır.")


@dataclass(frozen=True, slots=True)
class ImpactAssessment:
    tags: tuple[ImpactTag, ...]
    links: tuple[ImpactLink, ...]
    notes: tuple[str, ...]

    @property
    def has_links(self) -> bool:
        return bool(self.links)


_EVENT_TAGS: dict[EventType, tuple[ImpactTag, ...]] = {
    EventType.PARA_POLITIKASI: (ImpactTag.RATE_SENSITIVE,),
    EventType.FAIZ: (ImpactTag.RATE_SENSITIVE,),
    EventType.ENFLASYON: (ImpactTag.INFLATION_SENSITIVE,),
    EventType.DOVIZ: (ImpactTag.FX_SENSITIVE,),
    EventType.EMTIA: (ImpactTag.COMMODITY_SENSITIVE,),
    EventType.REGULASYON: (ImpactTag.REGULATORY,),
    EventType.FINANSAL_SONUCLAR: (ImpactTag.EARNINGS,),
    EventType.TEMETTU: (ImpactTag.DIVIDEND,),
    EventType.SERMAYE_ISLEMI: (ImpactTag.CAPITAL_ACTION,),
    EventType.BORCLANMA_FINANSMAN: (ImpactTag.FINANCING,),
    EventType.JEOPOLITIK: (ImpactTag.GEOPOLITICAL,),
}

_RATE_SECTORS = (
    ("Banka", 82, "Faiz/para politikası olayı bankacılık sektörünün fonlama ve marj koşullarıyla doğrudan ilişkilidir."),
    ("Gayrimenkul", 78, "Faiz/para politikası olayı finansman maliyeti nedeniyle gayrimenkul sektöründe duyarlılık yaratabilir."),
)

_FX_SECTORS = (
    ("Havacılık", 68, "Döviz hareketleri havacılık sektöründe gelir, yakıt ve finansman kalemlerini etkileyebilecek genel bir duyarlılık unsurudur."),
    ("Otomotiv", 65, "Döviz hareketleri otomotiv sektöründe ithal girdi ve ihracat gelirleri nedeniyle genel bir duyarlılık unsurudur."),
    ("Petrokimya", 65, "Döviz hareketleri petrokimya sektöründe döviz bazlı girdi ve ürün fiyatları nedeniyle genel bir duyarlılık unsurudur."),
)

_INFLATION_SECTORS = (
    ("Perakende", 70, "Enflasyon gelişmeleri perakende sektöründe fiyatlama, talep ve maliyet aktarımı açısından genel duyarlılık yaratabilir."),
    ("Gıda", 70, "Enflasyon gelişmeleri gıda sektöründe girdi maliyeti ve fiyatlama açısından genel duyarlılık yaratabilir."),
)

_COMMODITY_RULES = (
    (
        (r"\bbrent\b", r"\bpetrol\b", r"\bdoğal gaz\b", r"\bdogal gaz\b"),
        (
            ("Enerji", 86, "Petrol/doğal gaz anahtar kelimesi enerji sektörüyle doğrudan emtia duyarlılığı oluşturur."),
            ("Petrokimya", 82, "Petrol/doğal gaz fiyatları petrokimya sektörünün ana girdi maliyetleriyle ilişkilidir."),
            ("Havacılık", 76, "Petrol fiyatları havacılık sektöründe yakıt maliyeti açısından duyarlılık yaratabilir."),
            ("Ulaştırma", 72, "Petrol fiyatları ulaştırma sektöründe yakıt maliyeti açısından duyarlılık yaratabilir."),
        ),
    ),
    (
        (r"\baltın\b", r"\baltin\b", r"\bbakır\b", r"\bbakir\b"),
        (
            ("Madencilik", 86, "Metal emtia anahtar kelimesi madencilik sektörüyle doğrudan emtia duyarlılığı oluşturur."),
        ),
    ),
)


def _text_blob(event: MarketEvent, news: tuple[NewsRecord, ...]) -> str:
    parts = [event.title]
    for item in news:
        parts.extend((item.headline, item.body))
    return "\n".join(parts).casefold().replace("i̇", "i")


def _unique_tags(values) -> tuple[ImpactTag, ...]:
    return tuple(dict.fromkeys(values))


def _merge_link(
    links: dict[tuple[ImpactTargetType, str], ImpactLink],
    *,
    target_type: ImpactTargetType,
    target: str,
    relation: ImpactRelation,
    confidence: int,
    tags: tuple[ImpactTag, ...],
    reason: str,
) -> None:
    key = (target_type, target)
    incoming = ImpactLink(
        target_type=target_type,
        target=target,
        relation=relation,
        confidence=confidence,
        tags=_unique_tags(tags),
        reasons=(reason,),
    )
    existing = links.get(key)
    if existing is None:
        links[key] = incoming
        return

    # Açıkça olay kaydında bulunan DIRECT bağlantı, türetilmiş duyarlılık
    # bağlantısından daha güçlüdür. Aksi halde daha yüksek güven korunur.
    if existing.relation is ImpactRelation.DIRECT:
        relation_to_keep = existing.relation
    elif incoming.relation is ImpactRelation.DIRECT:
        relation_to_keep = incoming.relation
    else:
        relation_to_keep = existing.relation

    links[key] = ImpactLink(
        target_type=target_type,
        target=target,
        relation=relation_to_keep,
        confidence=max(existing.confidence, incoming.confidence),
        tags=_unique_tags((*existing.tags, *incoming.tags)),
        reasons=tuple(dict.fromkeys((*existing.reasons, *incoming.reasons))),
    )


def assess_event_impact(
    event: MarketEvent,
    news: tuple[NewsRecord, ...] = (),
) -> ImpactAssessment:
    """
    Piyasa olayı için deterministik etki etiketleri ve hedef bağlantıları üretir.

    Bu motor fiyat yönü (olumlu/olumsuz) tahmini yapmaz. Bağlantılar yalnız
    olay kapsamı, açık sektör/hisse etiketleri ve sınırlı duyarlılık kurallarına
    dayanır. Teknik analiz skoru ve AI bu motorun girdisi değildir.
    """

    tags: list[ImpactTag] = list(_EVENT_TAGS.get(event.event_type, ()))
    notes: list[str] = [
        "Etki bağlantıları fiyat yönü tahmini değildir; yalnız doğrudan ilişki veya genel duyarlılık gösterir."
    ]
    links: dict[tuple[ImpactTargetType, str], ImpactLink] = {}

    if event.market_scope in {
        MarketScope.GLOBAL,
        MarketScope.TURKEY_MACRO,
        MarketScope.BIST_WIDE,
    }:
        tags.append(ImpactTag.MARKET_WIDE)
        _merge_link(
            links,
            target_type=ImpactTargetType.MARKET,
            target="BIST Genel",
            relation=ImpactRelation.DIRECT,
            confidence=100,
            tags=(ImpactTag.MARKET_WIDE,),
            reason=f"Olay kapsamı {event.market_scope.value} olduğu için BIST geneli doğrudan izleme hedefidir.",
        )

    if event.market_scope is MarketScope.SECTOR or event.sectors:
        tags.append(ImpactTag.SECTOR_SPECIFIC)
    if event.market_scope is MarketScope.COMPANY or event.symbols:
        tags.append(ImpactTag.COMPANY_SPECIFIC)

    for sector in event.sectors:
        _merge_link(
            links,
            target_type=ImpactTargetType.SECTOR,
            target=sector,
            relation=ImpactRelation.DIRECT,
            confidence=100,
            tags=(ImpactTag.SECTOR_SPECIFIC,),
            reason="Sektör olay kaydında açıkça etkilenen sektör olarak yer alıyor.",
        )

    for symbol in event.symbols:
        _merge_link(
            links,
            target_type=ImpactTargetType.SYMBOL,
            target=symbol,
            relation=ImpactRelation.DIRECT,
            confidence=100,
            tags=(ImpactTag.COMPANY_SPECIFIC,),
            reason="Hisse olay kaydında açıkça etkilenen hisse olarak yer alıyor.",
        )

    if event.event_type in {EventType.PARA_POLITIKASI, EventType.FAIZ}:
        for sector, confidence, reason in _RATE_SECTORS:
            _merge_link(
                links,
                target_type=ImpactTargetType.SECTOR,
                target=sector,
                relation=ImpactRelation.SENSITIVITY,
                confidence=confidence,
                tags=(ImpactTag.RATE_SENSITIVE,),
                reason=reason,
            )

    if event.event_type is EventType.DOVIZ:
        for sector, confidence, reason in _FX_SECTORS:
            _merge_link(
                links,
                target_type=ImpactTargetType.SECTOR,
                target=sector,
                relation=ImpactRelation.SENSITIVITY,
                confidence=confidence,
                tags=(ImpactTag.FX_SENSITIVE,),
                reason=reason,
            )
        notes.append(
            "Döviz duyarlılığı sektör düzeyindedir; şirketlerin net döviz pozisyonu farklı olabileceğinden hisse yönü çıkarılmaz."
        )

    if event.event_type is EventType.ENFLASYON:
        for sector, confidence, reason in _INFLATION_SECTORS:
            _merge_link(
                links,
                target_type=ImpactTargetType.SECTOR,
                target=sector,
                relation=ImpactRelation.SENSITIVITY,
                confidence=confidence,
                tags=(ImpactTag.INFLATION_SENSITIVE,),
                reason=reason,
            )

    if event.event_type is EventType.EMTIA:
        text = _text_blob(event, news)
        for patterns, sector_rules in _COMMODITY_RULES:
            if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns):
                for sector, confidence, reason in sector_rules:
                    _merge_link(
                        links,
                        target_type=ImpactTargetType.SECTOR,
                        target=sector,
                        relation=ImpactRelation.SENSITIVITY,
                        confidence=confidence,
                        tags=(ImpactTag.COMMODITY_SENSITIVE,),
                        reason=reason,
                    )

    if event.market_scope is MarketScope.COMPANY and not event.symbols:
        notes.append(
            "Şirket kapsamındaki olayda açık hisse sembolü bulunmadığı için motor hisse uydurmadı."
        )
    if event.market_scope is MarketScope.SECTOR and not event.sectors:
        notes.append(
            "Sektör kapsamındaki olayda açık sektör etiketi bulunmadığı için motor sektör uydurmadı."
        )

    ordered_links = tuple(
        sorted(
            links.values(),
            key=lambda item: (
                {ImpactTargetType.MARKET: 0, ImpactTargetType.SECTOR: 1, ImpactTargetType.SYMBOL: 2}[item.target_type],
                -item.confidence,
                item.target.casefold(),
            ),
        )
    )
    return ImpactAssessment(
        tags=_unique_tags(tags),
        links=ordered_links,
        notes=tuple(dict.fromkeys(notes)),
    )


def impact_rows(
    event: MarketEvent,
    assessment: ImpactAssessment,
) -> list[dict[str, object]]:
    return [
        {
            "Olay": event.title,
            "Önem": event.importance_score,
            "Hedef türü": link.target_type.value,
            "Hedef": link.target,
            "Bağlantı": link.relation.value,
            "Bağlantı güveni": link.confidence,
            "Etiketler": ", ".join(tag.value for tag in link.tags) or "—",
            "Gerekçe": " ".join(link.reasons),
            "Olay kimliği": event.event_id,
        }
        for link in assessment.links
    ]
