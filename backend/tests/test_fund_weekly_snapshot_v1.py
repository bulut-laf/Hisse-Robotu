from datetime import date, datetime, timezone

import pytest

from backend.app.funds.analysis_engine import FundAnalysisClass, FundAnalysisResult
from backend.app.funds.weekly_snapshot import FundWeeklySnapshotStore, build_weekly_snapshot


def item(code="AAA", cls=FundAnalysisClass.B):
    return FundAnalysisResult(f"fund:tefas:{code}", "equity", cls, cls.value, ("F1", "F2"), (), (), (), "TEST", "x")


def test_weekly_snapshot_is_sorted_idempotent_and_has_no_scheduler_authority(tmp_path):
    snapshot = build_weekly_snapshot(date(2026, 9, 4), (item("BBB"), item("AAA")), observed_at=datetime(2026, 9, 4, tzinfo=timezone.utc))
    store = FundWeeklySnapshotStore(tmp_path / "funds" / "weekly.jsonl")
    assert tuple(x.canonical_fund_id for x in snapshot.results) == ("fund:tefas:AAA", "fund:tefas:BBB")
    assert snapshot.scheduler_authority == "NONE"
    assert store.append(snapshot) == "APPENDED" and store.append(snapshot) == "ALREADY_PRESENT"


def test_same_week_changed_result_conflicts_instead_of_overwrite(tmp_path):
    store = FundWeeklySnapshotStore(tmp_path / "weekly.jsonl")
    store.append(build_weekly_snapshot(date(2026, 9, 4), (item(),), observed_at=datetime(2026, 9, 4, tzinfo=timezone.utc)))
    with pytest.raises(ValueError, match="CONFLICT"):
        store.append(build_weekly_snapshot(date(2026, 9, 4), (item(cls=FundAnalysisClass.D),), observed_at=datetime(2026, 9, 5, tzinfo=timezone.utc)))
