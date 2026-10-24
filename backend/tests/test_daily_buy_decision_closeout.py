from types import SimpleNamespace

from backend.app.analysis.daily_buy_decision_closeout import (
    build_daily_buy_decisions,
    daily_buy_decision_rows,
)


def _card(**overrides):
    values = dict(
        symbol="AAA",
        technical_score=78,
        technical_view="Pozitif Teknik Görünüm",
        research_priority="HIGH",
        visibility_state="IMPROVING",
        rank_change=20,
        data_blocked=False,
        volume_ratio=1.35,
        risk_reward=1.8,
        risks=(),
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def test_closeout_marks_strong_confirmed_candidate_as_buy():
    decision = build_daily_buy_decisions((_card(),))[0]
    assert decision.decision == "AL"
    assert decision.priority == 1


def test_closeout_waits_when_confirmation_is_incomplete():
    decision = build_daily_buy_decisions((_card(volume_ratio=0.82),))[0]
    assert decision.decision == "BEKLE"


def test_closeout_rejects_weak_risk_reward_or_negative_view():
    assert build_daily_buy_decisions((_card(risk_reward=0.9),))[0].decision == "İŞLEM YOK"
    assert build_daily_buy_decisions((_card(technical_view="Negatif Teknik Görünüm"),))[0].decision == "İŞLEM YOK"


def test_partial_data_is_non_blocking():
    decision = build_daily_buy_decisions((_card(data_blocked=True),))[0]
    assert decision.decision == "AL"
    assert decision.data_status == "KISMİ"
    assert any("son güvenilir veriyle" in item for item in decision.cautions)


def test_rows_expose_priority_and_final_decision():
    rows = daily_buy_decision_rows(build_daily_buy_decisions((_card(), _card(symbol="BBB"))))
    assert rows[0]["Öncelik"] == "#1"
    assert rows[1]["Öncelik"] == "#2"
    assert rows[0]["Karar"] == "AL"
