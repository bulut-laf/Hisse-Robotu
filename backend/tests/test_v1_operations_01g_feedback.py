from backend.app.analysis.morning_candidate_feedback import (
    build_morning_candidate_feedback,
    summarize_feedback,
)


def test_candidate_feedback_records_user_observation():
    item = build_morning_candidate_feedback(
        "tuprs",
        "incelendi",
        "Haber desteği takip edildi.",
    )

    assert item.symbol == "TUPRS"
    assert item.recorded is True
    assert item.note == "Haber desteği takip edildi."


def test_feedback_summary_counts_user_states():
    result = summarize_feedback(
        (
            build_morning_candidate_feedback("A", "incelendi"),
            build_morning_candidate_feedback("B", "işlem yapıldı"),
            build_morning_candidate_feedback("C", "pas geçildi"),
        )
    )

    assert result["total"] == 3
    assert result["reviewed"] == 1
    assert result["traded"] == 1
    assert result["skipped"] == 1
