from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from backend.app.operations.daily_buy_decision_scheduled_runner import (
    ScheduledRunJsonStore,
    execute_scheduled_run,
    scheduler_status_rows,
)

IST = ZoneInfo("Europe/Istanbul")


@dataclass
class Decision:
    symbol: str
    decision: str


class Runtime:
    def __init__(self):
        self.persisted = []
        self.scan_count = 0

    def operation_summary(self):
        return object()

    def scan(self):
        self.scan_count += 1
        return object()

    def visibility_contexts(self):
        return ()

    def candidate_snapshot(self, operation_summary, scan_result, visibility_contexts):
        return SimpleNamespace(candidates=(SimpleNamespace(symbol="AAA"), SimpleNamespace(symbol="BBB")))

    def decisions(self, cards):
        return (Decision("AAA", "AL"), Decision("BBB", "BEKLE"))

    def persist_decision_snapshot(self, cards, decisions, phase, now):
        self.persisted.append((phase, len(cards), tuple(item.decision for item in decisions)))


def test_scheduled_run_persists_evening_snapshot_and_state(tmp_path):
    runtime = Runtime()
    store = ScheduledRunJsonStore(tmp_path / "state.json")
    record = execute_scheduled_run(
        "EVENING",
        now=datetime(2026, 8, 24, 18, 20, tzinfo=IST),
        runtime=runtime,
        store=store,
    )
    assert record.status == "SUCCESS"
    assert record.candidate_count == 2
    assert record.buy_symbols == ("AAA",)
    assert runtime.persisted == [("EVENING", 2, ("AL", "BEKLE"))]
    assert store.latest("EVENING").status == "SUCCESS"


def test_same_phase_same_day_is_idempotent(tmp_path):
    runtime = Runtime()
    store = ScheduledRunJsonStore(tmp_path / "state.json")
    now = datetime(2026, 8, 24, 9, 0, tzinfo=IST)
    first = execute_scheduled_run("MORNING", now=now, runtime=runtime, store=store)
    second = execute_scheduled_run("MORNING", now=now, runtime=runtime, store=store)
    assert first.status == "SUCCESS"
    assert second.status == "SKIPPED"
    assert runtime.scan_count == 1


def test_scheduler_status_has_both_daily_phases(tmp_path):
    runtime = Runtime()
    store = ScheduledRunJsonStore(tmp_path / "state.json")
    execute_scheduled_run(
        "EVENING",
        now=datetime(2026, 8, 24, 18, 20, tzinfo=IST),
        runtime=runtime,
        store=store,
    )
    rows = scheduler_status_rows(store)
    assert [row["Koşu"] for row in rows] == ["Seans sonu", "09:00"]
    assert rows[0]["Durum"] == "SUCCESS"
    assert rows[1]["Durum"] == "HENÜZ YOK"


def test_failed_run_is_recorded_without_hiding_error(tmp_path):
    class BrokenRuntime(Runtime):
        def scan(self):
            raise RuntimeError("scan failed")

    store = ScheduledRunJsonStore(tmp_path / "state.json")
    record = execute_scheduled_run(
        "MORNING",
        now=datetime(2026, 8, 24, 9, 0, tzinfo=IST),
        runtime=BrokenRuntime(),
        store=store,
    )
    assert record.status == "FAILED"
    assert "scan failed" in record.detail
    assert store.latest("MORNING").status == "FAILED"
