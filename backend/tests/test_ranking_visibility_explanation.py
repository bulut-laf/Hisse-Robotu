from backend.app.analysis.ranking_visibility_explanation import (
    build_visibility_explanation,
)

from backend.app.analysis.ranking_visibility_context import (
    RankingVisibilityContext,
)

from backend.app.analysis.ranking_quality_context import (
    EarlyVisibilityQualityContext,
)


def _context(state: str, change: int):
    return RankingVisibilityContext(
        symbol="TEST",
        current_rank=100,
        previous_rank=200,
        rank_change=change,
        visibility_state=state,
        zone_transition=None,
        research_priority="HIGH",
    )


def test_improving_explanation():
    result = build_visibility_explanation(
        _context("IMPROVING", 100)
    )

    assert result.headline == "Görünürlük kazanıyor"
    assert "iyileşme" in result.rank_reason


def test_weakening_explanation():
    result = build_visibility_explanation(
        _context("WEAKENING", -20)
    )

    assert result.headline == "İvme zayıflıyor"
    assert "zayıflama" in result.rank_reason


def test_stable_explanation():
    result = build_visibility_explanation(
        _context("STABLE", 0)
    )

    assert result.headline == "Stabil görünürlük"
    assert "değişimi" in result.rank_reason


def test_blocked_quality_explanation():
    quality = EarlyVisibilityQualityContext(
        symbol="TEST",
        status="VERI_BLOKLU",
        evidence=(),
        unique_family_count=0,
        next_review_module="Gecikmeli Veri Pilotu",
        data_blocked=True,
    )

    result = build_visibility_explanation(
        _context("IMPROVING", 100),
        quality,
    )

    assert "kullanılamıyor" in result.quality_reason