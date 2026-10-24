from __future__ import annotations

from dataclasses import dataclass
import re

from .models import EventType, MarketScope, SourceTier
from .source_registry import SourceResolution, resolve_source


@dataclass(frozen=True, slots=True)
class ClassificationSuggestion:
    source_resolution: SourceResolution | None
    source_tier: SourceTier | None
    event_type: EventType | None
    market_scope: MarketScope | None
    sectors: tuple[str, ...]
    reasons: tuple[str, ...]

    @property
    def has_suggestion(self) -> bool:
        return any(
            (
                self.source_tier is not None,
                self.event_type is not None,
                self.market_scope is not None,
                bool(self.sectors),
            )
        )


_EVENT_RULES: tuple[tuple[EventType, tuple[str, ...]], ...] = (
    (
        EventType.PARA_POLITIKASI,
        (
            r"\bpara politikası kurulu\b",
            r"\bpara politikasi kurulu\b",
            r"\bppk\b",
            r"\bpolitika faizi\b",
            r"\bpolicy rate\b",
        ),
    ),
    (
        EventType.ENFLASYON,
        (
            r"\benflasyon\b",
            r"\btüfe\b",
            r"\btufe\b",
            r"\büfe\b",
            r"\bufe\b",
            r"\btüketici fiyat",
            r"\btuketici fiyat",
            r"\bcpi\b",
        ),
    ),
    (
        EventType.BUYUME,
        (
            r"\bgsyh\b",
            r"gayrisafi yurt içi",
            r"gayrisafi yurt ici",
            r"\bbüyüme\b",
            r"\bbuyume\b",
            r"\bgdp\b",
        ),
    ),
    (
        EventType.ISTIHDAM,
        (
            r"\bişsizlik\b",
            r"\bissizlik\b",
            r"\bistihdam\b",
            r"\bunemployment\b",
            r"\bpayrolls?\b",
        ),
    ),
    (
        EventType.FINANSAL_SONUCLAR,
        (
            r"\bfinansal sonuç",
            r"\bfinansal sonuc",
            r"\bbilanço\b",
            r"\bbilanco\b",
            r"\bnet k[âa]r\b",
            r"\bearnings\b",
        ),
    ),
    (
        EventType.TEMETTU,
        (
            r"\btemettü\b",
            r"\btemettu\b",
            r"\bdividend\b",
        ),
    ),
    (
        EventType.SERMAYE_ISLEMI,
        (
            r"\bbedelli\b",
            r"\bbedelsiz\b",
            r"sermaye artır",
            r"sermaye artir",
            r"sermaye azalt",
        ),
    ),
    (
        EventType.BORCLANMA_FINANSMAN,
        (
            r"tahvil ihr",
            r"bono ihr",
            r"borçlanma aracı",
            r"borclanma araci",
            r"kredi anlaş",
            r"kredi anlas",
        ),
    ),
    (
        EventType.REGULASYON,
        (
            r"\byönetmelik\b",
            r"\byonetmelik\b",
            r"\btebliğ\b",
            r"\bteblig\b",
            r"\bdüzenleme\b",
            r"\bduzenleme\b",
        ),
    ),
    (
        EventType.DOVIZ,
        (
            r"\bdöviz\b",
            r"\bdoviz\b",
            r"\bdolar/?tl\b",
            r"\beuro/?tl\b",
            r"\bdöviz kuru\b",
            r"\bdoviz kuru\b",
        ),
    ),
    (
        EventType.EMTIA,
        (
            r"\bbrent\b",
            r"\bpetrol\b",
            r"\baltın\b",
            r"\baltin\b",
            r"\bbakır\b",
            r"\bbakir\b",
            r"\bdoğal gaz\b",
            r"\bdogal gaz\b",
        ),
    ),
    (
        EventType.JEOPOLITIK,
        (
            r"\bjeopolitik\b",
            r"\bsavaş\b",
            r"\bsavas\b",
            r"\bçatışma\b",
            r"\bcatisma\b",
            r"\byaptırım\b",
            r"\byaptirim\b",
            r"\bateşkes\b",
            r"\bateskes\b",
        ),
    ),
    (
        EventType.FAIZ,
        (
            r"\bfaiz\b",
            r"\byield\b",
            r"\btahvil getir",
        ),
    ),
)

_SECTOR_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Banka", (r"\bbanka", r"\bbankacılık", r"\bbankacilik")),
    ("Havacılık", (r"\bhavacılık", r"\bhavacilik", r"\bairline")),
    ("Enerji", (r"\benerji",)),
    ("Otomotiv", (r"\botomotiv",)),
    ("Perakende", (r"\bperakende",)),
    ("Telekomünikasyon", (r"\btelekom",)),
    ("Sigorta", (r"\bsigorta",)),
    ("Ulaştırma", (r"\bulaştırma", r"\bulastirma")),
    ("Madencilik", (r"\bmadencilik",)),
    ("Petrokimya", (r"\bpetrokimya",)),
    ("Gıda", (r"\bgıda", r"\bgida")),
    ("Savunma", (r"\bsavunma",)),
    ("Gayrimenkul", (r"\bgayrimenkul", r"\bgyo\b")),
)

_GLOBAL_PATTERNS = (
    r"\bfed\b",
    r"\becb\b",
    r"\bavrupa merkez bankası\b",
    r"\babd\b",
    r"\beuro bölgesi\b",
    r"\beuro bolgesi\b",
    r"\bküresel\b",
    r"\bkuresel\b",
    r"\bglobal\b",
)

_BIST_PATTERNS = (
    r"\bbist\s*100\b",
    r"\bxu100\b",
    r"\bborsa istanbul\b",
    r"\bborsa i̇stanbul\b",
    r"\bendeks\b",
)

_MACRO_TYPES = {
    EventType.PARA_POLITIKASI,
    EventType.ENFLASYON,
    EventType.BUYUME,
    EventType.ISTIHDAM,
    EventType.FAIZ,
    EventType.DOVIZ,
}


def _text_blob(headline: str, body: str) -> str:
    return f"{headline or ''}\n{body or ''}".casefold().replace("i̇", "i")


def _matches(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _event_type(text: str, source: SourceResolution | None) -> tuple[EventType | None, str | None]:
    for event_type, patterns in _EVENT_RULES:
        if _matches(text, patterns):
            return event_type, f"Metin anahtar kelime kuralı {event_type.value} ile eşleşti."

    if source is not None and source.canonical_name == "KAP":
        return EventType.KAP_ACIKLAMASI, "Metin daha özel bir olay kuralıyla eşleşmedi; kaynak KAP olduğu için KAP_ACIKLAMASI önerildi."
    return None, None


def _sectors(text: str) -> tuple[str, ...]:
    return tuple(
        sector
        for sector, patterns in _SECTOR_RULES
        if _matches(text, patterns)
    )


def _market_scope(
    text: str,
    source: SourceResolution | None,
    event_type: EventType | None,
    sectors: tuple[str, ...],
) -> tuple[MarketScope | None, str | None]:
    if source is not None and source.canonical_name == "KAP":
        return MarketScope.COMPANY, "KAP kaynağı şirket kapsamı olarak değerlendirildi."
    if _matches(text, _GLOBAL_PATTERNS):
        return MarketScope.GLOBAL, "Metinde küresel merkez bankası/ülke veya global piyasa anahtar kelimesi bulundu."
    if _matches(text, _BIST_PATTERNS):
        return MarketScope.BIST_WIDE, "Metinde BIST/endeks anahtar kelimesi bulundu."
    if sectors:
        return MarketScope.SECTOR, "Metinde bir veya daha fazla sektör anahtar kelimesi bulundu."
    if (
        source is not None
        and source.tier is SourceTier.TIER_1_OFFICIAL
        and event_type in _MACRO_TYPES
        and source.canonical_name in {"TCMB", "TÜİK", "Hazine ve Maliye Bakanlığı"}
    ):
        return MarketScope.TURKEY_MACRO, "Türkiye resmî makro kaynağı ve makro olay türü eşleşti."
    return None, None


def classify_news(
    *,
    source_name: str,
    source_reference: str,
    headline: str,
    body: str,
) -> ClassificationSuggestion:
    """Manuel haber için yalnız deterministik, açıklanabilir öneriler üretir."""

    source = resolve_source(source_name, source_reference)
    text = _text_blob(headline, body)
    event_type, event_reason = _event_type(text, source)
    sectors = _sectors(text)
    market_scope, scope_reason = _market_scope(text, source, event_type, sectors)

    reasons: list[str] = []
    if source is not None:
        reasons.append(
            f"Kaynak {source.canonical_name} beyaz listede {source.tier.value} olarak eşleşti ({source.matched_by})."
        )
    if event_reason:
        reasons.append(event_reason)
    if sectors:
        reasons.append(f"Sektör anahtar kelimeleri: {', '.join(sectors)}.")
    if scope_reason:
        reasons.append(scope_reason)

    return ClassificationSuggestion(
        source_resolution=source,
        source_tier=source.tier if source is not None else None,
        event_type=event_type,
        market_scope=market_scope,
        sectors=sectors,
        reasons=tuple(reasons),
    )
