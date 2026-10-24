from types import SimpleNamespace

from backend.app.analysis.morning_candidate_outcome import (
    build_morning_candidate_outcomes,
)


def test_morning_candidate_outcome_records_without_creating_signal():
    result = build_morning_candidate_outcomes(
        (
            SimpleNamespace(symbol="TUPRS", rank=1),
        )
    )

    assert result[0].symbol == "TUPRS"
    assert result[0].observation_state == "RECORDED"
    assert result[0].outcome_state == "WAITING_FOR_CLOSE_DATA"
