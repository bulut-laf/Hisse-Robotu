from backend.app.analysis.ranking_memory import (
    RankObservation,
    RankObservationJsonlStore,
)
from backend.app.analysis.ranking_quality_context import (
    QualityEvidence,
    build_quality_context,
)
from backend.app.analysis.ranking_visibility_context import (
    attach_quality_context,
)
from backend.app.analysis.ranking_visibility_service import (
    build_current_visibility_context,
)


def test_early_visibility_v2_end_to_end(tmp_path):
    store = RankObservationJsonlStore(
        path=tmp_path / "rank_observations.jsonl"
    )

    store.append_snapshot(
        (
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
    )

    visibility = build_current_visibility_context(store=store)[0]

    quality = build_quality_context(
        symbol="ABC",
        evidence=(
            QualityEvidence(
                family="momentum",
                state="positive",
                source_module="TEST",
            ),
        ),
    )

    merged = attach_quality_context(visibility, quality)

    assert merged.symbol == "ABC"
    assert merged.current_rank == 80
    assert merged.visibility_state == "IMPROVING"
    assert merged.quality_status == "GUCLENIYOR"
