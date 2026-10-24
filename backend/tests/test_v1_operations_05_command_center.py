from backend.app.analysis.morning_command_center import (
    build_morning_command_center,
)


def test_command_center_combines_morning_state():
    result = build_morning_command_center(
        candidates_count=5,
        priority_count=2,
        blocked_count=0,
        pending_review_count=5,
    )

    assert result.candidate_count == 5
    assert result.priority_count == 2
    assert result.blocked_count == 0
    assert result.pending_review_count == 5
    assert result.state == "SABAH OPERASYON HAZIR"
