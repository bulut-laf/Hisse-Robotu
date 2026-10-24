from backend.app.analysis.ranking_memory import RankObservation
from backend.app.analysis.ranking_quality_context import (
    QualityEvidence,
    build_quality_context,
)
from backend.app.analysis.ranking_visibility_context import (
    attach_quality_context,
    build_visibility_context_from_trajectory,
)


def test_visibility_quality_flow():
    observations = (
        RankObservation(
            symbol="ABC",
            as_of="2026-08-17",
            rank=260,
            ranked_universe_size=500,
            universe_source="TEST",
            profile_name="DEFAULT",
        ),
        RankObservation(
            symbol="ABC",
            as_of="2026-08-19",
            rank=80,
            ranked_universe_size=500,
            universe_source="TEST",
            profile_name="DEFAULT",
        ),
    )

    visibility = build_visibility_context_from_trajectory(observations)[0]

    quality = build_quality_context(
        symbol="ABC",
        evidence=(
            QualityEvidence(
                family="momentum",
                state="positive",
                source_module="TEST",
            ),
            QualityEvidence(
                family="trend",
                state="positive",
                source_module="TEST",
            ),
        ),
    )

    merged = attach_quality_context(visibility, quality)

    assert merged.symbol == "ABC"
    assert merged.current_rank == 80
    assert merged.quality_status == "GUCLENIYOR"
    assert merged.data_blocked is False
