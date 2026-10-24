from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from backend.app.analysis.daily_buy_decision_cycle import (
    DailyBuyDecisionJsonStore,
    build_daily_buy_decision_snapshot,
    compare_evening_morning,
    resolve_daily_buy_decision_phase,
)

ISTANBUL = ZoneInfo("Europe/Istanbul")


def _card(rank, symbol, status="TEKNİK ADAY", change=10, blocked=False):
    return SimpleNamespace(
        rank=rank,
        symbol=symbol,
        technical_score=80,
        technical_view="Pozitif Teknik Görünüm",
        research_priority="HIGH",
        visibility_state="IMPROVING",
        rank_change=change,
        operational_status=status,
        data_blocked=blocked,
    )


def test_daily_buy_decision_store_keeps_evening_and_morning(tmp_path: Path):
    store = DailyBuyDecisionJsonStore(tmp_path / "cycle.json")
    evening = build_daily_buy_decision_snapshot(
        (_card(1, "AAA"),),
        phase="EVENING",
        now=datetime(2026, 8, 24, 18, 0, tzinfo=ISTANBUL),
    )
    morning = build_daily_buy_decision_snapshot(
        (_card(1, "AAA"),),
        phase="MORNING",
        now=datetime(2026, 8, 25, 9, 0, tzinfo=ISTANBUL),
    )
    store.save(evening)
    store.save(morning)
    loaded = store.load()
    assert set(loaded) == {"EVENING", "MORNING"}
    assert loaded["EVENING"].candidates[0].symbol == "AAA"


def test_compare_evening_morning_exposes_rank_and_status_changes():
    evening = build_daily_buy_decision_snapshot(
        (_card(1, "AAA", "TEKNİK ADAY", 20), _card(2, "BBB")),
        phase="EVENING",
    )
    morning = build_daily_buy_decision_snapshot(
        (_card(1, "BBB"), _card(2, "AAA", "KISMİ VERİ — İNCELEMEYE DEVAM", 31, True)),
        phase="MORNING",
    )
    changes = {item.symbol: item for item in compare_evening_morning(evening, morning)}
    assert changes["AAA"].rank_delta == -1
    assert "Durum" in changes["AAA"].change_reason
    assert "Sıralama hareketi güncellendi" in changes["AAA"].change_reason
    assert "Veri kalite durumu değişti" in changes["AAA"].change_reason


def test_resolve_daily_buy_decision_phase_uses_istanbul_operation_windows():
    assert resolve_daily_buy_decision_phase(
        datetime(2026, 8, 24, 18, 0, tzinfo=ISTANBUL)
    ) == "EVENING"
    assert resolve_daily_buy_decision_phase(
        datetime(2026, 8, 25, 9, 0, tzinfo=ISTANBUL)
    ) == "MORNING"
    assert resolve_daily_buy_decision_phase(
        datetime(2026, 8, 25, 14, 0, tzinfo=ISTANBUL)
    ) is None
