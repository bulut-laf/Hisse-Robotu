from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re
from typing import Mapping

from .impact import (
    ImpactAssessment,
    ImpactLink,
    ImpactRelation,
    ImpactTargetType,
    assess_event_impact,
)
from .models import MarketEvent, NewsRecord


class PortfolioMatchType(StrEnum):
    DIRECT_SYMBOL = "DIRECT_SYMBOL"
    SECTOR = "SECTOR"
    MARKET = "MARKET"


_MATCH_PRIORITY: dict[PortfolioMatchType, int] = {
    PortfolioMatchType.DIRECT_SYMBOL: 3,
    PortfolioMatchType.SECTOR: 2,
    PortfolioMatchType.MARKET: 1,
}


@dataclass(frozen=True, slots=True)
class PortfolioMember:
    symbol: str
    sector: str = ""

    def __post_init__(self) -> None:
        normalized_symbol = _normalize_symbol(self.symbol)
        object.__setattr__(self, "symbol", normalized_symbol)
        object.__setattr__(self, "sector", _normalize_display_text(self.sector))


@dataclass(frozen=True, slots=True)
class PortfolioImpactHit:
    event_id: str
    event_title: str
    occurred_at: object
    importance_score: int
    symbol: str
    sector: str
    match_type: PortfolioMatchType
    relation: ImpactRelation
    confidence: int
    tags: tuple[str, ...]
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if not 0 <= int(self.importance_score) <= 100:
            raise ValueError("Olay önem skoru 0-100 aralığında olmalıdır.")
        if not 0 <= int(self.confidence) <= 100:
            raise ValueError("Portföy etki güveni 0-100 aralığında olmalıdır.")


@dataclass(frozen=True, slots=True)
class PortfolioImpactRadar:
    member_count: int
    affected_member_count: int
    direct_symbol_hit_count: int
    high_importance_event_count: int
    hits: tuple[PortfolioImpactHit, ...]

    @property
    def affected_symbols(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(hit.symbol for hit in self.hits))


_SECTOR_ALIASES: dict[str, str] = {
    "banka": "banka",
    "bankacilik": "banka",
    "gayrimenkul": "gayrimenkul",
    "gyo": "gayrimenkul",
    "havacilik": "havacilik",
    "havayolu": "havacilik",
    "ulastirma": "ulastirma",
    "lojistik": "ulastirma",
    "tasimacilik": "ulastirma",
    "otomotiv": "otomotiv",
    "petrokimya": "petrokimya",
    "perakende": "perakende",
    "gida": "gida",
    "enerji": "enerji",
    "madencilik": "madencilik",
}


def _normalize_display_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _fold(value: str) -> str:
    text = _normalize_display_text(value).casefold().replace("i̇", "i")
    translation = str.maketrans(
        {
            "ç": "c",
            "ğ": "g",
            "ı": "i",
            "ö": "o",
            "ş": "s",
            "ü": "u",
        }
    )
    return text.translate(translation)


def _normalize_symbol(value: str) -> str:
    symbol = str(value or "").strip().upper()
    if not symbol:
        raise ValueError("Portföy hisse sembolü boş olamaz.")
    if "." not in symbol:
        symbol = f"{symbol}.IS"
    if not re.fullmatch(r"[A-Z0-9_]+\.[A-Z0-9_]+", symbol):
        raise ValueError(f"Geçersiz portföy hisse sembolü: {value}")
    return symbol


def _sector_key(value: str) -> str:
    folded = _fold(value)
    if not folded:
        return ""
    compact = re.sub(r"[^a-z0-9]+", " ", folded).strip()
    if compact in _SECTOR_ALIASES:
        return _SECTOR_ALIASES[compact]

    # Yalnız tek ve açık bir sektör anahtar kelimesi bulunduğunda eşleştir.
    matches = {
        canonical
        for alias, canonical in _SECTOR_ALIASES.items()
        if re.search(rf"\b{re.escape(alias)}\b", compact)
    }
    return next(iter(matches)) if len(matches) == 1 else compact


def _candidate_for_member(
    member: PortfolioMember,
    assessment: ImpactAssessment,
) -> tuple[PortfolioMatchType, ImpactLink] | None:
    candidates: list[tuple[PortfolioMatchType, ImpactLink]] = []
    member_sector = _sector_key(member.sector)

    for link in assessment.links:
        if (
            link.target_type is ImpactTargetType.SYMBOL
            and _normalize_symbol(link.target) == member.symbol
        ):
            candidates.append((PortfolioMatchType.DIRECT_SYMBOL, link))
            continue

        if (
            link.target_type is ImpactTargetType.SECTOR
            and member_sector
            and _sector_key(link.target) == member_sector
        ):
            candidates.append((PortfolioMatchType.SECTOR, link))
            continue

        if link.target_type is ImpactTargetType.MARKET:
            candidates.append((PortfolioMatchType.MARKET, link))

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda item: (
            _MATCH_PRIORITY[item[0]],
            item[1].confidence,
            1 if item[1].relation is ImpactRelation.DIRECT else 0,
        ),
    )


def build_portfolio_impact_radar(
    events: tuple[MarketEvent, ...],
    news_by_event: Mapping[str, tuple[NewsRecord, ...]],
    members: tuple[PortfolioMember, ...],
) -> PortfolioImpactRadar:
    """
    Haber Merkezi olaylarını açık portföy üyeleriyle deterministik kesiştirir.

    Aynı olay-hisse çifti için tek satır üretilir. Öncelik doğrudan hisse,
    ardından sektör ve son olarak piyasa geneli bağlantısıdır. Motor fiyat
    yönü, AL/SAT kararı veya teknik skor üretmez.
    """

    unique_members: list[PortfolioMember] = []
    seen_symbols: set[str] = set()
    for member in members:
        if member.symbol in seen_symbols:
            continue
        unique_members.append(member)
        seen_symbols.add(member.symbol)

    hits: list[PortfolioImpactHit] = []
    high_importance_events: set[str] = set()

    for event in events:
        assessment = assess_event_impact(
            event,
            tuple(news_by_event.get(event.event_id, ())),
        )
        event_has_hit = False
        for member in unique_members:
            candidate = _candidate_for_member(member, assessment)
            if candidate is None:
                continue

            match_type, link = candidate
            event_has_hit = True
            hits.append(
                PortfolioImpactHit(
                    event_id=event.event_id,
                    event_title=event.title,
                    occurred_at=event.occurred_at,
                    importance_score=event.importance_score,
                    symbol=member.symbol,
                    sector=member.sector,
                    match_type=match_type,
                    relation=link.relation,
                    confidence=link.confidence,
                    tags=tuple(tag.value for tag in link.tags),
                    reasons=link.reasons,
                )
            )
        if event_has_hit and event.importance_score >= 80:
            high_importance_events.add(event.event_id)

    ordered_hits = tuple(
        sorted(
            hits,
            key=lambda item: (
                -item.importance_score,
                -_MATCH_PRIORITY[item.match_type],
                -item.confidence,
                str(item.occurred_at),
                item.symbol,
            ),
        )
    )
    affected = {item.symbol for item in ordered_hits}
    direct_count = sum(
        item.match_type is PortfolioMatchType.DIRECT_SYMBOL
        for item in ordered_hits
    )
    return PortfolioImpactRadar(
        member_count=len(unique_members),
        affected_member_count=len(affected),
        direct_symbol_hit_count=direct_count,
        high_importance_event_count=len(high_importance_events),
        hits=ordered_hits,
    )


def portfolio_impact_rows(
    radar: PortfolioImpactRadar,
) -> list[dict[str, object]]:
    return [
        {
            "Olay zamanı": (
                item.occurred_at.isoformat(timespec="minutes")
                if hasattr(item.occurred_at, "isoformat")
                else str(item.occurred_at)
            ),
            "Önem": item.importance_score,
            "Hisse": item.symbol,
            "Sektör": item.sector or "—",
            "Eşleşme": item.match_type.value,
            "Bağlantı": item.relation.value,
            "Bağlantı güveni": item.confidence,
            "Olay": item.event_title,
            "Etiketler": ", ".join(item.tags) or "—",
            "Gerekçe": " ".join(item.reasons),
            "Olay kimliği": item.event_id,
        }
        for item in radar.hits
    ]


def portfolio_symbol_summary_rows(
    radar: PortfolioImpactRadar,
) -> list[dict[str, object]]:
    grouped: dict[str, list[PortfolioImpactHit]] = {}
    for hit in radar.hits:
        grouped.setdefault(hit.symbol, []).append(hit)

    rows: list[dict[str, object]] = []
    for symbol, hits in grouped.items():
        strongest = max(
            hits,
            key=lambda item: (
                _MATCH_PRIORITY[item.match_type],
                item.confidence,
                item.importance_score,
            ),
        )
        rows.append(
            {
                "Hisse": symbol,
                "Sektör": strongest.sector or "—",
                "Olay sayısı": len({item.event_id for item in hits}),
                "En güçlü eşleşme": strongest.match_type.value,
                "Maks. olay önemi": max(item.importance_score for item in hits),
                "Maks. bağlantı güveni": max(item.confidence for item in hits),
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            -int(row["Maks. olay önemi"]),
            -int(row["Maks. bağlantı güveni"]),
            str(row["Hisse"]),
        ),
    )
