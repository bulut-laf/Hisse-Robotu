from backend.app.analysis.morning_workflow_closure import (
    build_morning_workflow_closure,
)


def test_turbo_07_workflow_closure():
    result = build_morning_workflow_closure(
        reviewed_count=3,
        pending_count=2,
        tracked_count=1,
    )

    assert result.reviewed_count == 3
    assert result.pending_count == 2
    assert result.tracked_count == 1
    assert result.closure_state == "SABAH OPERASYON AKIŞI TAMAMLANDI"
