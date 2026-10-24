from types import SimpleNamespace

from backend.app.analysis.morning_operation_review import (
    build_morning_operation_review,
)


def test_operation_review_tracks_feedback_completion():
    result = build_morning_operation_review(
        (
            SimpleNamespace(user_state="incelendi"),
            SimpleNamespace(user_state="pas geçildi"),
        )
    )

    assert result.total_candidates == 2
    assert result.reviewed_candidates == 2
    assert result.pending_candidates == 0
    assert result.review_state == "GERİ BİLDİRİM TAMAMLANDI"
