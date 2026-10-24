from backend.app.analysis.early_visibility_report import (
    build_early_visibility_report,
)
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


def test_early_visibility_runtime_output():
    store = RankObservationJsonlStore()

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

    class Memory:
        def list(self):
            return observations

    visibility = build_current_visibility_context(store=Memory())[0]

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

    payload = build_early_visibility_report(
        (
            attach_quality_context(visibility, quality),
        )
    )[0]

    assert payload["symbol"] == "ABC"
    assert payload["current_rank"] == 80
    assert payload["rank_change"] == 180
    assert payload["visibility_state"] == "IMPROVING"
    assert payload["quality_status"] == "GUCLENIYOR"
