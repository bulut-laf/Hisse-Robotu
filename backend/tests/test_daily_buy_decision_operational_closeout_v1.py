from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from backend.app.analysis.daily_buy_decision_operational_closeout import (
    build_operational_closeout,
    operational_closeout_rows,
)

ISTANBUL = ZoneInfo("Europe/Istanbul")


class StateStore:
    def __init__(self, rows):
        self.rows = rows
    def load(self):
        return self.rows


class ListStore:
    def __init__(self, rows):
        self.rows = rows
    def load(self):
        return tuple(self.rows)


def run_record(phase, status="SUCCESS", count=5):
    return SimpleNamespace(
        phase=phase,
        run_date="2026-08-24",
        status=status,
        candidate_count=count,
        buy_symbols=("AAA",),
        detail="ok",
        finished_at=f"2026-08-24T{'09:01:00' if phase == 'MORNING' else '18:21:00'}+03:00",
        run_kind="SCHEDULED",
    )


def archive(phase, count=5):
    return SimpleNamespace(
        phase=phase,
        run_date="2026-08-24",
        created_at=f"2026-08-24T{'09:01:00' if phase == 'MORNING' else '18:21:00'}+03:00",
        candidates=tuple(range(count)),
    )


def test_closeout_complete_when_both_phases_audit_and_archive_match():
    morning = run_record("MORNING")
    evening = run_record("EVENING")
    result = build_operational_closeout(
        now=datetime(2026, 8, 24, 18, 40, tzinfo=ISTANBUL),
        scheduler_store=StateStore({
            "2026-08-24:MORNING": morning,
            "2026-08-24:EVENING": evening,
        }),
        audit_store=ListStore([morning, evening]),
        archive_store=ListStore([archive("MORNING"), archive("EVENING")]),
    )
    assert result.status == "COMPLETE"
    assert result.missing_links == ()
    assert all(row["Durum"] == "TAMAM" for row in operational_closeout_rows(result))


def test_closeout_waits_before_evening_schedule_if_morning_complete():
    morning = run_record("MORNING")
    result = build_operational_closeout(
        now=datetime(2026, 8, 24, 12, 0, tzinfo=ISTANBUL),
        scheduler_store=StateStore({"2026-08-24:MORNING": morning}),
        audit_store=ListStore([morning]),
        archive_store=ListStore([archive("MORNING")]),
    )
    assert result.status == "WAITING"
    assert not result.missing_links
    assert any(row["Durum"] == "BEKLİYOR" for row in operational_closeout_rows(result))


def test_closeout_incomplete_when_due_evening_missing():
    morning = run_record("MORNING")
    result = build_operational_closeout(
        now=datetime(2026, 8, 24, 18, 40, tzinfo=ISTANBUL),
        scheduler_store=StateStore({"2026-08-24:MORNING": morning}),
        audit_store=ListStore([morning]),
        archive_store=ListStore([archive("MORNING")]),
    )
    assert result.status == "INCOMPLETE"
    assert any("18:20 Seans Sonu" in item for item in result.missing_links)


def test_closeout_incomplete_when_archive_count_mismatch():
    morning = run_record("MORNING")
    evening = run_record("EVENING")
    result = build_operational_closeout(
        now=datetime(2026, 8, 24, 18, 40, tzinfo=ISTANBUL),
        scheduler_store=StateStore({
            "2026-08-24:MORNING": morning,
            "2026-08-24:EVENING": evening,
        }),
        audit_store=ListStore([morning, evening]),
        archive_store=ListStore([archive("MORNING", 5), archive("EVENING", 4)]),
    )
    assert result.status == "INCOMPLETE"
    assert any("aday sayısı uyuşmuyor" in item for item in result.missing_links)
