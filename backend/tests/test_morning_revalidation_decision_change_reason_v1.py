from types import SimpleNamespace

from backend.app.analysis.daily_buy_decision_closeout import build_daily_buy_decisions
from backend.app.analysis.daily_buy_decision_cycle import (
    build_daily_buy_decision_snapshot,
    compare_evening_morning,
    daily_buy_decision_change_rows,
)


def _card(
    *,
    symbol="AAA",
    rank=1,
    score=75,
    view="Pozitif Teknik Görünüm",
    volume=1.20,
    rr=1.80,
    readiness="GİRİŞE HAZIR",
    source="SICRAMA",
    quality="UYGUN",
    rank_change=20,
):
    return SimpleNamespace(
        rank=rank,
        symbol=symbol,
        technical_score=score,
        technical_view=view,
        research_priority="HIGH",
        visibility_state="IMPROVING",
        rank_change=rank_change,
        operational_status="TEKNİK ADAY",
        data_blocked=False,
        volume_ratio=volume,
        risk_reward=rr,
        selection_source=source,
        jump_quality=quality,
        entry_readiness=readiness,
        risks=(),
    )


def _snapshot(card, phase):
    decisions = build_daily_buy_decisions((card,))
    return build_daily_buy_decision_snapshot((card,), phase=phase, decisions=decisions)


def test_morning_revalidation_explains_al_to_bekle_from_volume_loss():
    evening_card = _card(volume=1.20)
    morning_card = _card(volume=0.85)
    change = compare_evening_morning(
        _snapshot(evening_card, "EVENING"),
        _snapshot(morning_card, "MORNING"),
    )[0]
    assert change.evening_decision == "AL"
    assert change.morning_decision == "BEKLE"
    assert "Karar AL→BEKLE" in change.change_reason
    assert "Hacim teyidi kayboldu" in change.change_reason


def test_morning_revalidation_explains_bekle_to_al_from_entry_readiness():
    evening_card = _card(readiness="TEYİT BEKLİYOR")
    morning_card = _card(readiness="GİRİŞE HAZIR")
    change = compare_evening_morning(
        _snapshot(evening_card, "EVENING"),
        _snapshot(morning_card, "MORNING"),
    )[0]
    assert change.evening_decision == "BEKLE"
    assert change.morning_decision == "AL"
    assert "Karar BEKLE→AL" in change.change_reason
    assert "Giriş hazırlığı TEYİT BEKLİYOR→GİRİŞE HAZIR" in change.change_reason


def test_change_rows_show_evening_and_morning_closeout_decision():
    card = _card()
    change = compare_evening_morning(_snapshot(card, "EVENING"), _snapshot(card, "MORNING"))[0]
    row = daily_buy_decision_change_rows((change,))[0]
    assert row["Akşam karar"] == "AL"
    assert row["Sabah karar"] == "AL"
