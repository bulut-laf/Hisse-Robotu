from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from backend.app.operations.daily_buy_decision_scheduled_runner import (
    ScheduledRunAuditJsonStore,
    ScheduledRunJsonStore,
    execute_scheduled_run,
    retry_failed_or_missing_run,
    scheduler_audit_rows,
    scheduler_daily_chain_rows,
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
        return SimpleNamespace(candidates=(SimpleNamespace(symbol="AAA"), SimpleNamespace(symbol="BBB")))

    def decisions(self, cards):
        return (Decision("AAA", "AL"), Decision("BBB", "BEKLE"))

    def persist_decision_snapshot(self, cards, decisions, phase, now):
        return None


def test_every_attempt_is_appended_to_audit_history(tmp_path):
    state = ScheduledRunJsonStore(tmp_path / "state.json")
    audit = ScheduledRunAuditJsonStore(tmp_path / "audit.json")
    now = datetime(2026, 8, 24, 18, 20, tzinfo=IST)
    first = execute_scheduled_run("EVENING", now=now, runtime=Runtime(), store=state, audit_store=audit)
    second = execute_scheduled_run("EVENING", now=now, runtime=Runtime(), store=state, audit_store=audit)
    assert first.status == "SUCCESS"
    assert second.status == "SKIPPED"
    history = audit.load()
    assert [item.status for item in history] == ["SUCCESS", "SKIPPED"]
    assert all(item.run_kind == "SCHEDULED" for item in history)


def test_recovery_attempt_is_distinguished_from_scheduled_run(tmp_path):
    class Broken(Runtime):
        def scan(self):
            raise RuntimeError("boom")

    state = ScheduledRunJsonStore(tmp_path / "state.json")
    audit = ScheduledRunAuditJsonStore(tmp_path / "audit.json")
    now = datetime(2026, 8, 24, 9, 5, tzinfo=IST)
    execute_scheduled_run("MORNING", now=now, runtime=Broken(), store=state, audit_store=audit)
    retry_failed_or_missing_run("MORNING", now=now, runtime=Runtime(), store=state, audit_store=audit)
    history = audit.load()
    assert history[0].run_kind == "SCHEDULED"
    assert history[0].status == "FAILED"
    assert history[1].run_kind == "RECOVERY"
    assert history[1].status == "SUCCESS"


def test_audit_rows_expose_status_candidates_buy_and_error(tmp_path):
    class Broken(Runtime):
        def scan(self):
            raise RuntimeError("network down")

    state = ScheduledRunJsonStore(tmp_path / "state.json")
    audit = ScheduledRunAuditJsonStore(tmp_path / "audit.json")
    execute_scheduled_run(
        "MORNING",
        now=datetime(2026, 8, 24, 9, 0, tzinfo=IST),
        runtime=Broken(),
        store=state,
        audit_store=audit,
    )
    rows = scheduler_audit_rows(audit)
    assert rows[0]["Tarih"] == "2026-08-24"
    assert rows[0]["Koşu"] == "09:00"
    assert rows[0]["Tür"] == "Zamanlanmış"
    assert rows[0]["Durum"] == "FAILED"
    assert rows[0]["Aday"] == 0
    assert "network down" in rows[0]["Detay/Hata"]


def test_daily_chain_marks_complete_partial_and_failed_missing(tmp_path):
    state = ScheduledRunJsonStore(tmp_path / "state.json")
    audit = ScheduledRunAuditJsonStore(tmp_path / "audit.json")
    execute_scheduled_run(
        "EVENING",
        now=datetime(2026, 8, 23, 18, 20, tzinfo=IST),
        runtime=Runtime(), store=state, audit_store=audit,
    )
    execute_scheduled_run(
        "MORNING",
        now=datetime(2026, 8, 23, 9, 0, tzinfo=IST),
        runtime=Runtime(), store=state, audit_store=audit,
    )
    execute_scheduled_run(
        "EVENING",
        now=datetime(2026, 8, 24, 18, 20, tzinfo=IST),
        runtime=Runtime(), store=state, audit_store=audit,
    )
    rows = {row["Tarih"]: row for row in scheduler_daily_chain_rows(state)}
    assert rows["2026-08-23"]["Günlük zincir"] == "TAMAMLANDI"
    assert rows["2026-08-24"]["Günlük zincir"] == "KISMİ"
