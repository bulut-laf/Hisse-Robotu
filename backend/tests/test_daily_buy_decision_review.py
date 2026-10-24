from backend.app.analysis.daily_buy_decision_outcomes import BuyDecisionOutcomeRecord
from backend.app.analysis.daily_buy_decision_review import (
    build_daily_decision_reviews,
    daily_decision_review_rows,
    daily_decision_review_summary,
)


def _record(**overrides):
    values = dict(
        decision_id="2026-08-20:MORNING:AAA",
        decision_date="2026-08-20",
        phase="MORNING",
        symbol="AAA",
        priority=1,
        decision="AL",
        reference_price=100.0,
        technical_score=82,
        volume_ratio=1.4,
        risk_reward=2.2,
        rank_change=35,
        research_priority="HIGH",
        visibility_state="IMPROVING",
        return_1s=1.5,
        return_3s=2.0,
        return_5s=3.0,
    )
    values.update(overrides)
    return BuyDecisionOutcomeRecord(**values)


def test_review_uses_latest_available_horizon():
    review = build_daily_decision_reviews((_record(),))[0]
    assert review.horizon == "5S"
    assert review.return_pct == 3.0
    assert review.outcome == "POZITIF"


def test_review_falls_back_to_shorter_horizon():
    review = build_daily_decision_reviews((_record(return_5s=None, return_3s=-1.0),))[0]
    assert review.horizon == "3S"
    assert review.outcome == "NEGATIF"


def test_review_marks_pending_without_outcome():
    review = build_daily_decision_reviews((_record(return_1s=None, return_3s=None, return_5s=None),))[0]
    assert review.horizon == "BEKLIYOR"
    assert review.outcome == "BEKLIYOR"


def test_review_reports_context_evidence_without_causal_claim():
    review = build_daily_decision_reviews((_record(),))[0]
    assert "Teknik skor 80+" in review.supporting_evidence
    assert "Hacim teyidi güçlü" in review.supporting_evidence
    assert "Sıralama ivmesi +30 ve üzeri" in review.supporting_evidence


def test_review_rows_are_ui_ready():
    rows = daily_decision_review_rows(build_daily_decision_reviews((_record(),)))
    assert rows[0]["Hisse"] == "AAA"
    assert rows[0]["Sonuç"] == "POZITIF"
    assert "Destekleyen kanıt" in rows[0]


def test_review_summary_groups_by_decision_date():
    records = (
        _record(),
        _record(decision_id="2026-08-20:MORNING:BBB", symbol="BBB", priority=2, return_5s=-2.0),
    )
    summary = daily_decision_review_summary(build_daily_decision_reviews(records))
    assert summary[0]["AL kararı"] == 2
    assert summary[0]["Değerlendirilen"] == 2
    assert summary[0]["Pozitif"] == 1
    assert summary[0]["Negatif"] == 1
    assert summary[0]["İsabet (%)"] == 50.0
