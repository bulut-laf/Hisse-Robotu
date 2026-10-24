from backend.app.analysis.real_usage_result_summary import (
    build_real_usage_result_summary,
)


def test_turbo_13_real_usage_summary():
    result = build_real_usage_result_summary(
        candidate_count=5,
        reviewed_count=5,
        tracked_count=3,
        completed_count=1,
    )

    assert result.candidate_count == 5
    assert result.reviewed_count == 5
    assert result.tracked_count == 3
    assert result.completed_count == 1
    assert result.usage_state == "GERÇEK KULLANIM ÖZETİ HAZIR"
