from datetime import datetime, timezone

from backend.app.analysis.daily_buy_decision_recommendation_governance import (
    APPROVED,
    PENDING,
    REJECTED,
    RecommendationGovernanceJsonStore,
    governance_rows,
    review_governance_record,
    sync_governance_records,
)
from backend.app.analysis.daily_buy_decision_threshold_recommendation import ThresholdRecommendation


def _recommendation(evidence: str = "kanıt") -> ThresholdRecommendation:
    return ThresholdRecommendation(
        dimension="Teknik skor",
        horizon="1S",
        recommendation="EŞİK İNCELEME ADAYI",
        preferred_segment="80+",
        review_segment="<70",
        evidence=evidence,
        sample_size=12,
    )


def test_sync_registers_unseen_recommendation_as_pending():
    records = sync_governance_records((), (_recommendation(),), now=datetime(2026, 8, 23, tzinfo=timezone.utc))
    assert len(records) == 1
    assert records[0].status == PENDING
    assert records[0].reviewed_at is None


def test_sync_is_idempotent_for_same_recommendation():
    first = sync_governance_records((), (_recommendation(),))
    second = sync_governance_records(first, (_recommendation(),))
    assert len(second) == 1
    assert second[0].recommendation_id == first[0].recommendation_id


def test_manual_approval_changes_only_governance_status():
    records = sync_governance_records((), (_recommendation(),))
    updated = review_governance_record(records, records[0].recommendation_id, APPROVED)
    assert updated[0].status == APPROVED
    assert updated[0].recommendation == records[0].recommendation
    assert updated[0].reviewed_at is not None


def test_manual_rejection_is_supported():
    records = sync_governance_records((), (_recommendation(),))
    updated = review_governance_record(records, records[0].recommendation_id, REJECTED)
    assert updated[0].status == REJECTED


def test_store_round_trip(tmp_path):
    store = RecommendationGovernanceJsonStore(tmp_path / "governance.json")
    records = sync_governance_records((), (_recommendation(),))
    store.save(records)
    assert store.load() == records


def test_rows_are_ui_ready():
    records = sync_governance_records((), (_recommendation(),))
    row = governance_rows(records)[0]
    assert row["Durum"] == PENDING
    assert row["Öneri"] == "EŞİK İNCELEME ADAYI"
    assert "Kanıt" in row
