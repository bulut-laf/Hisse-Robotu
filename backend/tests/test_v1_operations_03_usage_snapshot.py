from types import SimpleNamespace

from backend.app.analysis.morning_usage_snapshot import (
    build_morning_usage_snapshot,
)


def test_usage_snapshot_combines_existing_operation_data():
    result = build_morning_usage_snapshot(
        (
            SimpleNamespace(research_priority="HIGH"),
            SimpleNamespace(research_priority="NORMAL"),
        ),
        (
            SimpleNamespace(user_state="incelendi"),
        ),
    )

    assert result.candidate_count == 2
    assert result.priority_count == 1
    assert result.reviewed_count == 1
    assert result.pending_review_count == 1
    assert result.usage_state == "GÜNLÜK OPERASYON AKTİF"
