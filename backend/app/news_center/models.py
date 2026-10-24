from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
import re


class NewsCenterModelError(ValueError):
    """Haber Merkezi veri modeli doğrulanamadığında oluşur."""


class SourceTier(StrEnum):
    TIER_1_OFFICIAL = "TIER_1_OFFICIAL"
    TIER_2_MAJOR_FINANCIAL = "TIER_2_MAJOR_FINANCIAL"
    OTHER_VERIFIED = "OTHER_VERIFIED"
    MANUAL = "MANUAL"


class EventType(StrEnum):
    PARA_POLITIKASI = "PARA_POLITIKASI"
    ENFLASYON = "ENFLASYON"
    BUYUME = "BUYUME"
    ISTIHDAM = "ISTIHDAM"
    FAIZ = "FAIZ"
    DOVIZ = "DOVIZ"
    EMTIA = "EMTIA"
    REGULASYON = "REGULASYON"
    KAP_ACIKLAMASI = "KAP_ACIKLAMASI"
    FINANSAL_SONUCLAR = "FINANSAL_SONUCLAR"
    TEMETTU = "TEMETTU"
    SERMAYE_ISLEMI = "SERMAYE_ISLEMI"
    BORCLANMA_FINANSMAN = "BORCLANMA_FINANSMAN"
    SEKTOR = "SEKTOR"
    JEOPOLITIK = "JEOPOLITIK"
    DIGER = "DIGER"


class MarketScope(StrEnum):
    GLOBAL = "GLOBAL"
    TURKEY_MACRO = "TURKEY_MACRO"
    BIST_WIDE = "BIST_WIDE"
    SECTOR = "SECTOR"
    COMPANY = "COMPANY"
    OTHER = "OTHER"


def normalize_text(value: str, *, field_name: str) -> str:
    normalized = re.sub(r"\s+", " ", str(value or "")).strip()
    if not normalized:
        raise NewsCenterModelError(f"{field_name} boş olamaz.")
    return normalized


def normalize_optional_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_body(value: str) -> str:
    normalized = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        raise NewsCenterModelError("Haber metni boş olamaz.")
    return normalized


def _require_aware(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise NewsCenterModelError(f"{field_name} datetime olmalıdır.")
    if value.tzinfo is None or value.utcoffset() is None:
        raise NewsCenterModelError(f"{field_name} saat dilimi içermelidir.")
    return value


def normalize_symbols(values: tuple[str, ...]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in values:
        symbol = str(raw or "").strip().upper()
        if not symbol:
            continue
        if "." not in symbol:
            symbol = f"{symbol}.IS"
        if not re.fullmatch(r"[A-Z0-9_]+\.[A-Z0-9_]+", symbol):
            raise NewsCenterModelError(f"Geçersiz hisse sembolü: {raw}")
        if symbol not in seen:
            result.append(symbol)
            seen.add(symbol)
    return tuple(result)


def normalize_sectors(values: tuple[str, ...]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in values:
        sector = re.sub(r"\s+", " ", str(raw or "")).strip()
        if not sector:
            continue
        key = sector.casefold()
        if key not in seen:
            result.append(sector)
            seen.add(key)
    return tuple(result)


@dataclass(frozen=True, slots=True)
class ImportanceBreakdown:
    source_reliability: int
    market_scope: int
    event_significance: int
    time_sensitivity: int

    def __post_init__(self) -> None:
        limits = {
            "source_reliability": 30,
            "market_scope": 25,
            "event_significance": 30,
            "time_sensitivity": 15,
        }
        for field_name, maximum in limits.items():
            value = getattr(self, field_name)
            if not isinstance(value, int) or not 0 <= value <= maximum:
                raise NewsCenterModelError(
                    f"{field_name} 0-{maximum} aralığında tam sayı olmalıdır."
                )

    @property
    def total(self) -> int:
        return (
            self.source_reliability
            + self.market_scope
            + self.event_significance
            + self.time_sensitivity
        )


@dataclass(frozen=True, slots=True)
class MarketEvent:
    event_id: str
    title: str
    event_type: EventType
    occurred_at: datetime
    market_scope: MarketScope
    sectors: tuple[str, ...]
    symbols: tuple[str, ...]
    importance_score: int
    importance_breakdown: ImportanceBreakdown
    news_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "event_id",
            normalize_text(self.event_id, field_name="event_id"),
        )
        object.__setattr__(
            self,
            "title",
            normalize_text(self.title, field_name="Olay başlığı"),
        )
        object.__setattr__(
            self,
            "occurred_at",
            _require_aware(self.occurred_at, "Olay zamanı"),
        )
        object.__setattr__(self, "sectors", normalize_sectors(self.sectors))
        object.__setattr__(self, "symbols", normalize_symbols(self.symbols))

        if not isinstance(self.event_type, EventType):
            object.__setattr__(self, "event_type", EventType(self.event_type))
        if not isinstance(self.market_scope, MarketScope):
            object.__setattr__(
                self,
                "market_scope",
                MarketScope(self.market_scope),
            )
        if not isinstance(self.importance_breakdown, ImportanceBreakdown):
            raise NewsCenterModelError(
                "importance_breakdown geçerli bir ImportanceBreakdown olmalıdır."
            )
        if self.importance_score != self.importance_breakdown.total:
            raise NewsCenterModelError(
                "Önem skoru, önem bileşenleri toplamıyla eşleşmelidir."
            )
        if not 0 <= self.importance_score <= 100:
            raise NewsCenterModelError("Önem skoru 0-100 aralığında olmalıdır.")

        normalized_news_ids = tuple(
            normalize_text(item, field_name="news_id")
            for item in self.news_ids
        )
        object.__setattr__(
            self,
            "news_ids",
            tuple(dict.fromkeys(normalized_news_ids)),
        )


@dataclass(frozen=True, slots=True)
class NewsRecord:
    news_id: str
    event_id: str
    source_name: str
    source_tier: SourceTier
    headline: str
    published_at: datetime
    body: str
    source_reference: str
    content_hash: str
    archived_at: datetime

    def __post_init__(self) -> None:
        for field_name, label in (
            ("news_id", "news_id"),
            ("event_id", "event_id"),
            ("source_name", "Kaynak adı"),
            ("headline", "Haber başlığı"),
        ):
            object.__setattr__(
                self,
                field_name,
                normalize_text(getattr(self, field_name), field_name=label),
            )

        if not isinstance(self.source_tier, SourceTier):
            object.__setattr__(
                self,
                "source_tier",
                SourceTier(self.source_tier),
            )
        object.__setattr__(
            self,
            "published_at",
            _require_aware(self.published_at, "Yayın zamanı"),
        )
        object.__setattr__(self, "body", normalize_body(self.body))
        object.__setattr__(
            self,
            "source_reference",
            normalize_optional_text(self.source_reference),
        )
        object.__setattr__(
            self,
            "archived_at",
            _require_aware(self.archived_at, "Arşiv zamanı"),
        )

        content_hash = str(self.content_hash or "").strip().lower()
        if not re.fullmatch(r"[0-9a-f]{64}", content_hash):
            raise NewsCenterModelError(
                "content_hash 64 karakterlik SHA-256 özeti olmalıdır."
            )
        object.__setattr__(self, "content_hash", content_hash)
