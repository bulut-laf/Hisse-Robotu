from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, median
from typing import Iterable, Mapping

from ..data.fundamental_score_store import StoredFundamentalScore
from .sector_reference import SectorReference
from .sector_score_ranking import quality_class


class SectorStrengthMapError(ValueError):
    """Sektör güç haritası üretilemedi."""


@dataclass(frozen=True)
class SectorStrengthItem:
    rank: int
    sector: str
    period_key: str
    company_count: int
    average_score: float
    median_score: float
    strong_count: int
    balanced_count: int
    watch_count: int
    weak_count: int
    previous_period_key: str | None
    previous_median_score: float | None
    median_change: float | None
    direction: str


@dataclass(frozen=True)
class SectorStrengthMap:
    current_period_key: str
    previous_period_key: str | None
    sector_count: int
    items: tuple[SectorStrengthItem, ...]


def sector_direction(
    change: float | None,
    *,
    change_threshold: float = 3.0,
) -> str:
    if change_threshold <= 0:
        raise SectorStrengthMapError(
            "Sektör değişim eşiği sıfırdan büyük olmalıdır."
        )
    if change is None:
        return "Önceki dönem yok"
    if change >= change_threshold:
        return "Güçleniyor"
    if change <= -change_threshold:
        return "Zayıflıyor"
    return "Yatay"


def build_sector_strength_map(
    scores: Iterable[StoredFundamentalScore],
    references: Mapping[str, SectorReference],
    *,
    minimum_company_count: int = 3,
    strong_threshold: int = 80,
    balanced_threshold: int = 65,
    watch_threshold: int = 50,
    change_threshold: float = 3.0,
) -> SectorStrengthMap:
    if minimum_company_count < 2:
        raise SectorStrengthMapError(
            "Asgari şirket sayısı en az 2 olmalıdır."
        )

    eligible = [
        item
        for item in scores
        if item.symbol in references
        and not item.score.locked
        and item.score.total_score is not None
    ]
    if not eligible:
        raise SectorStrengthMapError(
            "Karşılaştırılabilir sektör skoru bulunamadı."
        )

    period_ends = sorted(
        {item.period_end for item in eligible},
        reverse=True,
    )
    current_end = period_ends[0]
    previous_end = period_ends[1] if len(period_ends) > 1 else None

    current_items = [
        item for item in eligible if item.period_end == current_end
    ]
    previous_items = (
        [item for item in eligible if item.period_end == previous_end]
        if previous_end is not None
        else []
    )

    current_by_sector: dict[str, list[StoredFundamentalScore]] = {}
    previous_by_sector: dict[str, list[StoredFundamentalScore]] = {}

    for item in current_items:
        current_by_sector.setdefault(
            references[item.symbol].sector,
            [],
        ).append(item)

    for item in previous_items:
        previous_by_sector.setdefault(
            references[item.symbol].sector,
            [],
        ).append(item)

    rows = []
    for sector, members in current_by_sector.items():
        if len(members) < minimum_company_count:
            continue

        values = [int(item.score.total_score or 0) for item in members]
        current_median = float(median(values))
        classes = [
            quality_class(
                value,
                strong_threshold=strong_threshold,
                balanced_threshold=balanced_threshold,
                watch_threshold=watch_threshold,
            )
            for value in values
        ]

        previous_members = previous_by_sector.get(sector, [])
        previous_median = None
        previous_period_key = None
        if len(previous_members) >= minimum_company_count:
            previous_values = [
                int(item.score.total_score or 0)
                for item in previous_members
            ]
            previous_median = float(median(previous_values))
            previous_period_key = previous_members[0].period_key

        change = (
            round(current_median - previous_median, 2)
            if previous_median is not None
            else None
        )

        rows.append(
            {
                "sector": sector,
                "period_key": members[0].period_key,
                "company_count": len(members),
                "average_score": round(float(mean(values)), 2),
                "median_score": current_median,
                "strong_count": classes.count("Güçlü"),
                "balanced_count": classes.count("Dengeli"),
                "watch_count": classes.count("İzlenmeli"),
                "weak_count": classes.count("Zayıf"),
                "previous_period_key": previous_period_key,
                "previous_median_score": previous_median,
                "median_change": change,
                "direction": sector_direction(
                    change,
                    change_threshold=change_threshold,
                ),
            }
        )

    if not rows:
        raise SectorStrengthMapError(
            "Güç haritası için yeterli şirket bulunan sektör yok."
        )

    ordered = sorted(
        rows,
        key=lambda row: (
            -row["median_score"],
            -row["average_score"],
            row["sector"],
        ),
    )

    items = tuple(
        SectorStrengthItem(rank=index, **row)
        for index, row in enumerate(ordered, start=1)
    )

    return SectorStrengthMap(
        current_period_key=items[0].period_key,
        previous_period_key=(
            next(
                (
                    item.previous_period_key
                    for item in items
                    if item.previous_period_key is not None
                ),
                None,
            )
        ),
        sector_count=len(items),
        items=items,
    )


def sector_strength_rows(
    result: SectorStrengthMap,
) -> list[dict[str, object]]:
    return [
        {
            "Sıra": item.rank,
            "Sektör": item.sector,
            "Şirket sayısı": item.company_count,
            "Ortalama skor": item.average_score,
            "Medyan skor": item.median_score,
            "Güçlü": item.strong_count,
            "Dengeli": item.balanced_count,
            "İzlenmeli": item.watch_count,
            "Zayıf": item.weak_count,
            "Önceki dönem": item.previous_period_key,
            "Önceki medyan": item.previous_median_score,
            "Medyan değişimi": item.median_change,
            "Yön": item.direction,
        }
        for item in result.items
    ]
