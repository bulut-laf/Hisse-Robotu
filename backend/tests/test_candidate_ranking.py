from backend.app.decision_engine.candidate_ranking import (
    rank_candidates,
)


def test_candidate_ranking():
    result = rank_candidates(
        [
            {"symbol": "THYAO", "score": 60},
            {"symbol": "AKBNK", "score": 85},
        ]
    )

    assert result[0]["symbol"] == "AKBNK"
    assert result[1]["symbol"] == "THYAO"


def test_candidate_ranking_empty():
    result = rank_candidates([])

    assert result == []
