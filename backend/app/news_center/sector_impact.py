from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .impact import (
    ImpactRelation,
    ImpactTag,
    ImpactTargetType,
    assess_event_impact,
)
from .models import MarketEvent, NewsRecord


@dataclass(frozen=True, slots=True)
class SectorEventHit:
    sector: str
    event_id: str
    event_title: str
    occurred_at: datetime
    importance_score: int
    relation: ImpactRelation
    confidence: int
    tags: tuple[ImpactTag, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SectorImpactSummary:
    sector: str
    event_count: int
    high_importance_event_count: int
    direct_event_count: int
    sensitivity_event_count: int
    max_importance_score: int
    max_link_confidence: int
    latest_event_at: datetime
    tags: tuple[ImpactTag, ...]


@dataclass(frozen=True, slots=True)
class SectorImpactMap:
    summaries: tuple[SectorImpactSummary, ...]
    hits: tuple[SectorEventHit, ...]
    sector_count: int
    event_count: int
    high_importance_event_count: int
    direct_sector_count: int


def _unique(values):
    return tuple(dict.fromkeys(values))


def build_sector_impact_map(
    events: tuple[MarketEvent, ...],
    news_by_event: dict[str, tuple[NewsRecord, ...]] | None = None,
    *,
    since: datetime | None = None,
) -> SectorImpactMap:
    """Deterministik sektör gündem yoğunluğu görünümü üretir.

    Harita yalnız ``assess_event_impact`` tarafından üretilmiş SECTOR
    bağlantılarını toplulaştırır. Pozitif/negatif fiyat yönü, AL/SAT kararı,
    teknik skor veya AI girdisi üretmez/kullanmaz.
    """

    if since is not None and (since.tzinfo is None or since.utcoffset() is None):
        raise ValueError("since saat dilimi içermelidir.")

    news_by_event = news_by_event or {}
    hits: list[SectorEventHit] = []
    included_event_ids: set[str] = set()
    high_event_ids: set[str] = set()

    for event in events:
        if since is not None and event.occurred_at < since:
            continue

        assessment = assess_event_impact(
            event,
            tuple(news_by_event.get(event.event_id, ())),
        )
        event_has_sector_link = False
        for link in assessment.links:
            if link.target_type is not ImpactTargetType.SECTOR:
                continue
            event_has_sector_link = True
            hits.append(
                SectorEventHit(
                    sector=link.target,
                    event_id=event.event_id,
                    event_title=event.title,
                    occurred_at=event.occurred_at,
                    importance_score=event.importance_score,
                    relation=link.relation,
                    confidence=link.confidence,
                    tags=link.tags,
                    reasons=link.reasons,
                )
            )
        if event_has_sector_link:
            included_event_ids.add(event.event_id)
            if event.importance_score >= 80:
                high_event_ids.add(event.event_id)

    grouped: dict[str, list[SectorEventHit]] = {}
    for hit in hits:
        grouped.setdefault(hit.sector, []).append(hit)

    summaries: list[SectorImpactSummary] = []
    direct_sectors: set[str] = set()
    for sector, sector_hits in grouped.items():
        direct_count = sum(
            1 for hit in sector_hits if hit.relation is ImpactRelation.DIRECT
        )
        sensitivity_count = sum(
            1 for hit in sector_hits if hit.relation is ImpactRelation.SENSITIVITY
        )
        if direct_count:
            direct_sectors.add(sector)
        summaries.append(
            SectorImpactSummary(
                sector=sector,
                event_count=len({hit.event_id for hit in sector_hits}),
                high_importance_event_count=len(
                    {
                        hit.event_id
                        for hit in sector_hits
                        if hit.importance_score >= 80
                    }
                ),
                direct_event_count=direct_count,
                sensitivity_event_count=sensitivity_count,
                max_importance_score=max(hit.importance_score for hit in sector_hits),
                max_link_confidence=max(hit.confidence for hit in sector_hits),
                latest_event_at=max(hit.occurred_at for hit in sector_hits),
                tags=_unique(
                    tag
                    for hit in sector_hits
                    for tag in hit.tags
                ),
            )
        )

    summaries.sort(
        key=lambda item: (
            -item.high_importance_event_count,
            -item.max_importance_score,
            -item.event_count,
            -item.max_link_confidence,
            item.sector.casefold(),
        )
    )
    hits.sort(
        key=lambda item: (
            -item.occurred_at.timestamp(),
            -item.importance_score,
            item.sector.casefold(),
            item.event_id,
        )
    )

    return SectorImpactMap(
        summaries=tuple(summaries),
        hits=tuple(hits),
        sector_count=len(summaries),
        event_count=len(included_event_ids),
        high_importance_event_count=len(high_event_ids),
        direct_sector_count=len(direct_sectors),
    )


def sector_summary_rows(
    sector_map: SectorImpactMap,
) -> list[dict[str, object]]:
    return [
        {
            "Sektör": item.sector,
            "Olay": item.event_count,
            "Önem ≥80": item.high_importance_event_count,
            "Doğrudan": item.direct_event_count,
            "Duyarlılık": item.sensitivity_event_count,
            "En yüksek önem": item.max_importance_score,
            "En yüksek bağlantı güveni": item.max_link_confidence,
            "Son olay": item.latest_event_at.isoformat(timespec="minutes"),
            "Etiketler": ", ".join(tag.value for tag in item.tags) or "—",
        }
        for item in sector_map.summaries
    ]


def sector_event_rows(
    sector_map: SectorImpactMap,
) -> list[dict[str, object]]:
    return [
        {
            "Olay zamanı": item.occurred_at.isoformat(timespec="minutes"),
            "Sektör": item.sector,
            "Olay": item.event_title,
            "Önem": item.importance_score,
            "Bağlantı": item.relation.value,
            "Bağlantı güveni": item.confidence,
            "Etiketler": ", ".join(tag.value for tag in item.tags) or "—",
            "Gerekçe": " ".join(item.reasons),
            "Olay kimliği": item.event_id,
        }
        for item in sector_map.hits
    ]
