from backend.app.analysis.ranking_memory import RankObservation
from backend.app.analysis.ranking_visibility_service import (
    build_current_visibility_context,
)


def test_visibility_service_builds_context():
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

    result = build_current_visibility_context(store=Memory())

    assert len(result) == 1
    assert result[0].symbol == "ABC"
    assert result[0].current_rank == 80
    assert result[0].visibility_state == "IMPROVING"
