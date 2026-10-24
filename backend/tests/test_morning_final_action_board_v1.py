from dataclasses import dataclass

from backend.app.analysis.morning_final_action_board import (
    build_morning_final_actions,
    morning_final_action_rows,
)


@dataclass
class Card:
    symbol: str
    selection_source: str = "TARAMA"
    entry_readiness: str = "GİRİŞE HAZIR"
    jump_quality: str = "UYGUN"


@dataclass
class Decision:
    priority: int
    symbol: str
    decision: str
    technical_score: int = 72
    volume_ratio: float = 1.2
    risk_reward: float = 1.7
    data_status: str = "UYGUN"
    reasons: tuple[str, ...] = ("Teknik skor güçlü",)
    cautions: tuple[str, ...] = ()


def test_final_action_board_puts_al_first_without_changing_top5_priority():
    cards = (Card("AAA"), Card("BBB"), Card("CCC"))
    decisions = (
        Decision(1, "AAA", "BEKLE"),
        Decision(2, "BBB", "AL"),
        Decision(3, "CCC", "İŞLEM YOK"),
    )
    actions = build_morning_final_actions(cards, decisions)
    assert [item.symbol for item in actions] == ["BBB", "AAA", "CCC"]
    assert actions[0].original_priority == 2
    assert actions[0].action == "AL ADAYI"


def test_final_action_board_preserves_source_readiness_and_quality():
    cards = (Card("XYZ", "SICRAMA", "TEYİT BEKLİYOR", "UYGUN"),)
    decisions = (Decision(1, "XYZ", "BEKLE"),)
    item = build_morning_final_actions(cards, decisions)[0]
    assert item.selection_source == "SICRAMA"
    assert item.entry_readiness == "TEYİT BEKLİYOR"
    assert item.jump_quality == "UYGUN"
    assert item.action == "İZLE / TEYİT BEKLE"


def test_final_action_rows_are_read_only_display_contract():
    actions = build_morning_final_actions((Card("AAA"),), (Decision(1, "AAA", "AL"),))
    row = morning_final_action_rows(actions)[0]
    assert row["Sabah aksiyon"] == "AL ADAYI"
    assert row["Karar"] == "AL"
    assert row["Top-5 sırası"] == "#1"
