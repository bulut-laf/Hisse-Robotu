from backend.app.analysis.morning_release_center import (
    build_morning_release_center,
)


def test_turbo_01_release_center_combines_existing_operation_outputs():
    result = build_morning_release_center(
        market_state="NORMAL",
        candidate_count=5,
        priority_count=2,
        pending_action_count=5,
    )

    assert result.market_state == "NORMAL"
    assert result.candidate_count == 5
    assert result.priority_count == 2
    assert result.pending_action_count == 5
    assert result.release_state == "V1 SABAH OPERASYONU HAZIR"
