from backend.app.analysis.early_visibility_report import (
    build_early_visibility_report,
)
from backend.app.analysis.ranking_visibility_context import (
    RankingVisibilityContext,
)


def test_early_visibility_report_payload():
    contexts = (
        RankingVisibilityContext(
            symbol="ABC",
            current_rank=80,
            previous_rank=260,
            rank_change=180,
            visibility_state="IMPROVING",
            zone_transition="YENI_TOP100",
            research_priority="HIGH",
            quality_status="GUCLENIYOR",
            data_blocked=False,
        ),
    )

    result = build_early_visibility_report(contexts)

    assert len(result) == 1
    assert result[0]["symbol"] == "ABC"
    assert result[0]["current_rank"] == 80
    assert result[0]["visibility_state"] == "IMPROVING"
    assert result[0]["quality_status"] == "GUCLENIYOR"
