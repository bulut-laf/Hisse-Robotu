from types import SimpleNamespace

from backend.app.analysis.morning_decision_flow import (
    build_morning_decision_flow,
)


def test_turbo_03_decision_flow():
    result = build_morning_decision_flow(
        (
            SimpleNamespace(data_blocked=False),
            SimpleNamespace(data_blocked=True),
        )
    )

    assert result.candidate_count == 2
    assert result.inspect_count == 1
    assert result.blocked_count == 1
    assert result.decision_state == "İNCELEMEYE HAZIR"
