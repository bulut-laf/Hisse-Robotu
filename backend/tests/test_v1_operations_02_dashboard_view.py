from types import SimpleNamespace

from backend.app.analysis.morning_operation_dashboard_view import (
    build_morning_operation_dashboard_view,
)


def test_dashboard_view_summarizes_existing_operation_state():
    result = build_morning_operation_dashboard_view(
        (
            SimpleNamespace(
                research_priority="HIGH",
                data_blocked=False,
            ),
            SimpleNamespace(
                research_priority="NORMAL",
                data_blocked=True,
            ),
        ),
        feedback_items=(),
    )

    assert result.candidate_count == 2
    assert result.high_priority_count == 1
    assert result.blocked_count == 1
    assert result.user_review_pending == 2
    assert result.dashboard_state == "OPERASYON HAZIR"
