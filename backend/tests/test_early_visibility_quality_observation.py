from backend.app.analysis.ranking_visibility_context import (
    RankingVisibilityContext,
)

from backend.app.analysis.ranking_quality_context import (
    EarlyVisibilityQualityContext,
)

from backend.app.analysis.ranking_visibility_explanation import (
    build_visibility_explanation,
)


def test_quality_observation_is_reflected_in_explanation():
    visibility = RankingVisibilityContext(
        symbol="TEST",
        current_rank=40,
        previous_rank=100,
        rank_change=60,
        visibility_state="IMPROVING",
        zone_transition="YENI_TOP50",
        research_priority="HIGH",
    )

    quality = EarlyVisibilityQualityContext(
        symbol="TEST",
        status="DESTEKLENIYOR",
        evidence=(),
        unique_family_count=3,
        next_review_module="Fırsat Radarı",
        data_blocked=False,
    )

    result = build_visibility_explanation(
        visibility,
        quality,
    )

    assert result.symbol == "TEST"
    assert "Kalite durumu: DESTEKLENIYOR." in result.quality_reason
    assert result.research_action == "Fırsat Radarı"


def test_blocked_quality_keeps_data_warning():
    visibility = RankingVisibilityContext(
        symbol="TEST",
        current_rank=40,
        previous_rank=100,
        rank_change=60,
        visibility_state="IMPROVING",
        zone_transition=None,
        research_priority="HIGH",
    )

    quality = EarlyVisibilityQualityContext(
        symbol="TEST",
        status="VERI_BLOKLU",
        evidence=(),
        unique_family_count=0,
        next_review_module="Gecikmeli Veri Pilotu",
        data_blocked=True,
    )

    result = build_visibility_explanation(
        visibility,
        quality,
    )

    assert "kullanılamıyor" in result.quality_reason
