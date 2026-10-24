from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from backend.app.analysis.daily_buy_decision_cycle import (
    DailyBuyDecisionCandidate,
    DailyBuyDecisionSnapshot,
)
from backend.app.analysis.daily_buy_decision_output_archive import (
    DecisionOutputArchiveJsonStore,
    compare_decision_archive_days,
    latest_daily_compare,
)

ISTANBUL = ZoneInfo("Europe/Istanbul")


def _candidate(rank: int, symbol: str, decision: str) -> DailyBuyDecisionCandidate:
    return DailyBuyDecisionCandidate(
        rank=rank,
        symbol=symbol,
        technical_score=70,
        technical_view="Nötr Teknik Görünüm",
        research_priority="NORMAL",
        visibility_state="IMPROVING",
        rank_change=5,
        operational_status="HAZIR",
        data_blocked=False,
        decision=decision,
        selection_source="TARAMA",
        jump_quality="UYGUN",
        entry_readiness="GİRİŞE HAZIR",
    )


def _snapshot(day: int, phase: str, candidates: tuple[DailyBuyDecisionCandidate, ...]):
    return DailyBuyDecisionSnapshot(
        phase=phase,
        created_at=datetime(2026, 8, day, 9 if phase == "MORNING" else 18, 20, tzinfo=ISTANBUL).isoformat(),
        candidates=candidates,
    )


def test_archive_keeps_daily_phase_history_and_upserts_same_day(tmp_path: Path):
    store = DecisionOutputArchiveJsonStore(tmp_path / "archive.json")
    store.save_snapshot(_snapshot(23, "MORNING", (_candidate(1, "AAA", "AL"),)))
    store.save_snapshot(_snapshot(24, "MORNING", (_candidate(1, "BBB", "BEKLE"),)))
    store.save_snapshot(_snapshot(24, "MORNING", (_candidate(1, "CCC", "AL"),)))

    records = store.load()
    assert len(records) == 2
    assert records[-1].run_date == "2026-08-24"
    assert records[-1].candidates[0].symbol == "CCC"


def test_daily_compare_tracks_added_removed_decision_and_rank_changes(tmp_path: Path):
    store = DecisionOutputArchiveJsonStore(tmp_path / "archive.json")
    previous = store.save_snapshot(
        _snapshot(23, "MORNING", (_candidate(1, "AAA", "AL"), _candidate(2, "BBB", "BEKLE")))
    )
    current = store.save_snapshot(
        _snapshot(24, "MORNING", (_candidate(2, "AAA", "BEKLE"), _candidate(1, "CCC", "AL")))
    )
    delta = compare_decision_archive_days(current, previous)
    assert delta.added == ("CCC",)
    assert delta.removed == ("BBB",)
    assert delta.decision_changes == 1
    assert delta.rank_changes == 1
    assert delta.previous_buy == ("AAA",)
    assert delta.current_buy == ("CCC",)


def test_latest_daily_compare_requires_two_same_phase_records(tmp_path: Path):
    store = DecisionOutputArchiveJsonStore(tmp_path / "archive.json")
    store.save_snapshot(_snapshot(23, "EVENING", (_candidate(1, "AAA", "AL"),)))
    assert latest_daily_compare(store.load(), phase="MORNING") is None
