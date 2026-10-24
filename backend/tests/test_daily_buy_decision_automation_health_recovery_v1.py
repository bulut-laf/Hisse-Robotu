from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from backend.app.operations.daily_buy_decision_scheduled_runner import (
    ScheduledRunJsonStore,
    execute_scheduled_run,
    retry_failed_or_missing_run,
    scheduler_health_rows,
)

IST = ZoneInfo("Europe/Istanbul")


@dataclass
class Decision:
    symbol: str
    decision: str


class Runtime:
    def operation_summary(self):
        return object()

    def scan(self):
        return object()

    def visibility_contexts(self):
        return ()

    def candidate_snapshot(self, operation_summary, scan_result, visibility_contexts):
        return SimpleNamespace(candidates=(SimpleNamespace(symbol="AAA"),))

    def decisions(self, cards):
        return (Decision("AAA", "AL"),)

    def persist_decision_snapshot(self, cards, decisions, phase, now):
        return None


def test_health_marks_due_missing_run_and_offers_recovery(tmp_path):
    store = ScheduledRunJsonStore(tmp_path / "state.json")
    rows = scheduler_health_rows(
        store,
        now=datetime(2026, 8, 24, 19, 0, tzinfo=IST),
    )
    by_name = {row["Koşu"]: row for row in rows}
    assert by_name["Seans sonu"]["Sağlık"] == "EKSİK KOŞU"
    assert by_name["09:00"]["Sağlık"] == "EKSİK KOŞU"
    assert by_name["Seans sonu"]["Kurtarma"] == "YENİDEN ÇALIŞTIR"


def test_failed_run_can_be_retried_and_becomes_healthy(tmp_path):
    class BrokenRuntime(Runtime):
        def scan(self):
            raise RuntimeError("boom")

    store = ScheduledRunJsonStore(tmp_path / "state.json")
    now = datetime(2026, 8, 24, 9, 5, tzinfo=IST)
    failed = execute_scheduled_run("MORNING", now=now, runtime=BrokenRuntime(), store=store)
    assert failed.status == "FAILED"
    recovered = retry_failed_or_missing_run("MORNING", now=now, runtime=Runtime(), store=store)
    assert recovered.status == "SUCCESS"
    rows = scheduler_health_rows(store, now=now)
    morning = next(row for row in rows if row["Koşu"] == "09:00")
    assert morning["Sağlık"] == "SAĞLIKLI"
    assert morning["Aday"] == 1
    assert morning["AL"] == "AAA"


def test_recovery_does_not_duplicate_successful_run(tmp_path):
    store = ScheduledRunJsonStore(tmp_path / "state.json")
    now = datetime(2026, 8, 24, 18, 30, tzinfo=IST)
    first = execute_scheduled_run("EVENING", now=now, runtime=Runtime(), store=store)
    retry = retry_failed_or_missing_run("EVENING", now=now, runtime=Runtime(), store=store)
    assert first.status == "SUCCESS"
    assert retry.status == "SKIPPED"
    assert "kurtarma" in retry.detail.lower()


def test_health_exposes_last_success_and_last_error_detail(tmp_path):
    class BrokenRuntime(Runtime):
        def scan(self):
            raise RuntimeError("network unavailable")

    store = ScheduledRunJsonStore(tmp_path / "state.json")
    execute_scheduled_run(
        "MORNING",
        now=datetime(2026, 8, 23, 9, 0, tzinfo=IST),
        runtime=Runtime(),
        store=store,
    )
    execute_scheduled_run(
        "MORNING",
        now=datetime(2026, 8, 24, 9, 0, tzinfo=IST),
        runtime=BrokenRuntime(),
        store=store,
    )
    rows = scheduler_health_rows(
        store,
        now=datetime(2026, 8, 24, 9, 10, tzinfo=IST),
    )
    morning = next(row for row in rows if row["Koşu"] == "09:00")
    assert morning["Sağlık"] == "BAŞARISIZ"
    assert "2026-08-23" in morning["Son başarılı"]
    assert "network unavailable" in morning["Son hata/detay"]
