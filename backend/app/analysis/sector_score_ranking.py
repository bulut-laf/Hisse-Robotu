from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Iterable, Mapping

from ..data.fundamental_score_store import StoredFundamentalScore
from .sector_reference import SectorReference


class SectorScoreRankingError(ValueError):
    """Sektör bazlı temel skor sıralaması üretilemedi."""


@dataclass(frozen=True)
class SectorScoreRankingItem:
    rank: int
    symbol: str
    sector: str
    period_key: str
    total_score: int
    sector_median: float
    median_difference: float
    quality_class: str
    relative_position: str
    profitability_score: int
    growth_score: int
    leverage_score: int
    liquidity_score: int
    cash_flow_score: int


@dataclass(frozen=True)
class SectorScoreRanking:
    sector: str
    period_key: str
    peer_count: int
    sector_median: float
    items: tuple[SectorScoreRankingItem, ...]


def quality_class(
    total_score: int,
    *,
    strong_threshold: int = 80,
    balanced_threshold: int = 65,
    watch_threshold: int = 50,
) -> str:
    if not (
        0 <= watch_threshold
        < balanced_threshold
        < strong_threshold
        <= 100
    ):
        raise SectorScoreRankingError(
            "Kalite eşikleri Zayıf < İzlenmeli < Dengeli < "
            "Güçlü sırasını korumalıdır."
        )
    if total_score >= strong_threshold:
        return "Güçlü"
    if total_score >= balanced_threshold:
        return "Dengeli"
    if total_score >= watch_threshold:
        return "İzlenmeli"
    return "Zayıf"


def relative_position(
    total_score: int,
    sector_median: float,
) -> str:
    difference = float(total_score) - sector_median
    if difference >= 10:
        return "Sektör medyanının belirgin üzerinde"
    if difference <= -10:
        return "Sektör medyanının belirgin altında"
    return "Sektör medyanına yakın"


def build_sector_score_ranking(
    scores: Iterable[StoredFundamentalScore],
    references: Mapping[str, SectorReference],
    sector: str,
    *,
    minimum_peer_count: int = 3,
    strong_threshold: int = 80,
    balanced_threshold: int = 65,
    watch_threshold: int = 50,
) -> SectorScoreRanking:
    normalized_sector = sector.strip()
    if not normalized_sector:
        raise SectorScoreRankingError(
            "Sektör adı boş olamaz."
        )
    if minimum_peer_count < 2:
        raise SectorScoreRankingError(
            "Asgari şirket sayısı en az 2 olmalıdır."
        )

    eligible: list[StoredFundamentalScore] = []
    for stored in scores:
        reference = references.get(stored.symbol)
        if reference is None:
            continue
        if reference.sector != normalized_sector:
            continue
        if stored.score.locked:
            continue
        if stored.score.total_score is None:
            continue
        eligible.append(stored)

    if not eligible:
        raise SectorScoreRankingError(
            "Sektörde karşılaştırılabilir temel skor bulunamadı."
        )

    latest_period_end = max(
        item.period_end for item in eligible
    )
    same_period = [
        item
        for item in eligible
        if item.period_end == latest_period_end
    ]

    if len(same_period) < minimum_peer_count:
        raise SectorScoreRankingError(
            "Sektör sıralaması için aynı güncel bilanço "
            f"döneminde en az {minimum_peer_count} şirket gerekir."
        )

    period_keys = {item.period_key for item in same_period}
    if len(period_keys) != 1:
        raise SectorScoreRankingError(
            "Aynı tarihli temel skorların dönem anahtarları "
            "uyumlu değil."
        )

    total_scores = [
        int(item.score.total_score)
        for item in same_period
        if item.score.total_score is not None
    ]
    sector_median = float(median(total_scores))

    ordered = sorted(
        same_period,
        key=lambda item: (
            -int(item.score.total_score or 0),
            item.symbol,
        ),
    )

    items = tuple(
        SectorScoreRankingItem(
            rank=index,
            symbol=item.symbol,
            sector=normalized_sector,
            period_key=item.period_key,
            total_score=int(item.score.total_score or 0),
            sector_median=sector_median,
            median_difference=round(
                float(item.score.total_score or 0)
                - sector_median,
                2,
            ),
            quality_class=quality_class(
                int(item.score.total_score or 0),
                strong_threshold=strong_threshold,
                balanced_threshold=balanced_threshold,
                watch_threshold=watch_threshold,
            ),
            relative_position=relative_position(
                int(item.score.total_score or 0),
                sector_median,
            ),
            profitability_score=item.score.profitability.score,
            growth_score=item.score.growth.score,
            leverage_score=item.score.leverage.score,
            liquidity_score=item.score.liquidity.score,
            cash_flow_score=item.score.cash_flow.score,
        )
        for index, item in enumerate(ordered, start=1)
    )

    return SectorScoreRanking(
        sector=normalized_sector,
        period_key=ordered[0].period_key,
        peer_count=len(items),
        sector_median=sector_median,
        items=items,
    )


def sector_score_ranking_rows(
    ranking: SectorScoreRanking,
) -> list[dict[str, object]]:
    return [
        {
            "Sıra": item.rank,
            "Şirket": item.symbol,
            "Temel skor": item.total_score,
            "Kalite sınıfı": item.quality_class,
            "Sektör medyanı": item.sector_median,
            "Medyan farkı": item.median_difference,
            "Göreli konum": item.relative_position,
            "Kârlılık": item.profitability_score,
            "Büyüme": item.growth_score,
            "Borçluluk": item.leverage_score,
            "Likidite": item.liquidity_score,
            "Nakit akışı": item.cash_flow_score,
        }
        for item in ranking.items
    ]
