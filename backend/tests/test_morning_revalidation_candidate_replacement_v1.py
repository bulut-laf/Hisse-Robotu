from types import SimpleNamespace

from backend.app.analysis.daily_buy_decision_closeout import build_daily_buy_decisions
from backend.app.analysis.daily_buy_decision_cycle import (
    build_daily_buy_decision_snapshot,
    compare_evening_morning_replacements,
    daily_buy_decision_replacement_rows,
)


def _card(symbol, rank, *, source="TARAMA", readiness="TEYİT BEKLİYOR", quality="-", score=70):
    return SimpleNamespace(
        rank=rank,
        symbol=symbol,
        technical_score=score,
        technical_view="Nötr Teknik Görünüm",
        research_priority="NORMAL",
        visibility_state="IMPROVING",
        rank_change=10,
        operational_status="TEKNİK ADAY",
        data_blocked=False,
        volume_ratio=1.2,
        risk_reward=1.5,
        selection_source=source,
        jump_quality=quality,
        entry_readiness=readiness,
        risks=(),
    )


def _snapshot(cards, phase):
    decisions = build_daily_buy_decisions(cards)
    return build_daily_buy_decision_snapshot(cards, phase=phase, decisions=decisions)


def test_revalidation_pairs_evening_exit_with_morning_entry():
    evening_cards = (
        _card("AAA", 1),
        _card("BBB", 2),
        _card("CCC", 3),
        _card("DDD", 4),
        _card("EEE", 5),
    )
    morning_cards = (
        _card("AAA", 1),
        _card("BBB", 2),
        _card("CCC", 3),
        _card("NEW", 4, source="SICRAMA", readiness="GİRİŞE HAZIR", quality="UYGUN", score=78),
        _card("DDD", 5),
    )
    replacements = compare_evening_morning_replacements(
        _snapshot(evening_cards, "EVENING"),
        _snapshot(morning_cards, "MORNING"),
    )
    assert len(replacements) == 1
    item = replacements[0]
    assert item.outgoing_symbol == "EEE"
    assert item.incoming_symbol == "NEW"
    assert "sıçrama havuzundan" in item.replacement_context
    assert "Giriş hazırlığı: GİRİŞE HAZIR" in item.replacement_context
    assert "Sıçrama kalite kapısı: UYGUN" in item.replacement_context


def test_revalidation_has_no_replacement_when_membership_is_same():
    cards = tuple(_card(symbol, rank) for rank, symbol in enumerate(("AAA", "BBB", "CCC", "DDD", "EEE"), 1))
    replacements = compare_evening_morning_replacements(
        _snapshot(cards, "EVENING"),
        _snapshot(cards, "MORNING"),
    )
    assert replacements == ()


def test_replacement_rows_expose_outgoing_and_incoming_decisions():
    evening = (_card("OLD", 5),)
    morning = (_card("NEW", 4, source="SICRAMA", readiness="GİRİŞE HAZIR", quality="UYGUN", score=78),)
    rows = daily_buy_decision_replacement_rows(
        compare_evening_morning_replacements(
            _snapshot(evening, "EVENING"),
            _snapshot(morning, "MORNING"),
        )
    )
    assert rows[0]["Listeden çıkan"] == "OLD"
    assert rows[0]["Listeye giren"] == "NEW"
    assert rows[0]["Sabah karar"] in {"AL", "BEKLE", "İŞLEM YOK"}
