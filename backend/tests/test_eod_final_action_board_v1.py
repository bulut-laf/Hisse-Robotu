from dataclasses import dataclass

from backend.app.analysis.eod_final_action_board import (
    build_eod_final_actions,
    eod_final_action_rows,
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


def test_eod_board_puts_al_first_without_changing_top5_priority():
    cards = (Card("AAA"), Card("BBB"), Card("CCC"))
    decisions = (
        Decision(1, "AAA", "BEKLE"),
        Decision(2, "BBB", "AL"),
        Decision(3, "CCC", "İŞLEM YOK"),
    )
    actions = build_eod_final_actions(cards, decisions)
    assert [item.symbol for item in actions] == ["BBB", "AAA", "CCC"]
    assert actions[0].original_priority == 2
    assert actions[0].action == "ERTESİ GÜN AL ADAYI"


def test_eod_board_preserves_source_readiness_and_quality():
    cards = (Card("XYZ", "SICRAMA", "TEYİT BEKLİYOR", "UYGUN"),)
    decisions = (Decision(1, "XYZ", "BEKLE"),)
    item = build_eod_final_actions(cards, decisions)[0]
    assert item.selection_source == "SICRAMA"
    assert item.entry_readiness == "TEYİT BEKLİYOR"
    assert item.jump_quality == "UYGUN"
    assert item.action == "ERTESİ GÜN İZLE / TEYİT BEKLE"


def test_eod_rows_are_read_only_display_contract():
    actions = build_eod_final_actions((Card("AAA"),), (Decision(1, "AAA", "AL"),))
    row = eod_final_action_rows(actions)[0]
    assert row["Seans sonu aksiyon"] == "ERTESİ GÜN AL ADAYI"
    assert row["Karar"] == "AL"
    assert row["Top-5 sırası"] == "#1"


def test_dashboard_wires_eod_board_without_new_score_engine():
    from pathlib import Path
    source = Path("backend/dashboard.py").read_text(encoding="utf-8")
    assert "EOD_FINAL_ACTION_BOARD_V1" in source
    assert "Seans Sonu — Ertesi Gün Ön Aksiyon Listesi" in source
    assert "build_eod_final_actions" in source
    assert "eod_final_action_rows" in source
