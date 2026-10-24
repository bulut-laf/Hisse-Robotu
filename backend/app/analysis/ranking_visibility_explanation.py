from __future__ import annotations

from dataclasses import dataclass

from backend.app.analysis.ranking_visibility_context import (
    RankingVisibilityContext,
)

from backend.app.analysis.ranking_quality_context import (
    EarlyVisibilityQualityContext,
)


@dataclass(frozen=True)
class VisibilityExplanation:
    symbol: str
    headline: str
    summary: str
    rank_reason: str
    lifecycle_reason: str
    quality_reason: str
    research_action: str


def _headline(state: str) -> str:
    return {
        "IMPROVING": "Görünürlük kazanıyor",
        "WEAKENING": "İvme zayıflıyor",
        "STABLE": "Stabil görünürlük",
    }.get(
        str(state).upper(),
        "Görünürlük durumu belirsiz",
    )


def _rank_reason(
    visibility: RankingVisibilityContext,
) -> str:
    if visibility.rank_change > 0:
        return "Araştırma sıralamasında iyileşme görülüyor."

    if visibility.rank_change < 0:
        return "Araştırma sıralamasında zayıflama görülüyor."

    return "Belirgin sıra değişimi oluşmadı."


def _quality_reason(
    quality: EarlyVisibilityQualityContext | None,
) -> str:
    if quality is None:
        return "Kalite bağlamı bulunmuyor."

    if quality.data_blocked:
        return "Veri karşılaştırması kullanılamıyor."

    return f"Kalite durumu: {quality.status}."


def build_visibility_explanation(
    visibility: RankingVisibilityContext,
    quality: EarlyVisibilityQualityContext | None = None,
) -> VisibilityExplanation:
    headline = _headline(
        visibility.visibility_state
    )

    return VisibilityExplanation(
        symbol=visibility.symbol,
        headline=headline,
        summary=(
            f"{visibility.symbol} için "
            f"{headline.lower()} durumu."
        ),
        rank_reason=_rank_reason(visibility),
        lifecycle_reason=(
            f"Durum: {visibility.visibility_state}"
        ),
        quality_reason=_quality_reason(quality),
        research_action=(
            quality.next_review_module
            if quality is not None
            else "Ana Research Sıralaması"
        ),
    )