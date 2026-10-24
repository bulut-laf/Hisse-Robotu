from types import SimpleNamespace

from backend.app.analysis.morning_operation_summary import (
    build_morning_operation_summary,
)


def test_morning_operation_summary_counts_candidate_outcomes():
    result = build_morning_operation_summary(
        (
            SimpleNamespace(
                observation_state="RECORDED",
                outcome_state="CLOSE_DATA_AVAILABLE",
            ),
            SimpleNamespace(
                observation_state="RECORDED",
                outcome_state="WAITING_FOR_CLOSE_DATA",
            ),
        )
    )

    assert result.candidate_count == 2
    assert result.recorded_count == 2
    assert result.available_close_count == 1
    assert result.pending_close_count == 1
    assert result.summary_state == "GÜN SONU VERİSİ HAZIR"
