from types import SimpleNamespace

from backend.app.analysis.jump_candidate_priority_merge import (
    merge_jump_and_scan_candidates,
)
from backend.app.analysis.morning_candidate_flow import (
    build_morning_candidate_cards,
    morning_candidate_rows,
)


def candidate(symbol, *, score=76, volume=1.35, rr=2.0, close=100.0, ema9=99.0, atr=2.0):
    return SimpleNamespace(
        sembol=symbol,
        kapanis=close,
        ema9=ema9,
        atr14=atr,
        hacim_orani=volume,
        sinyal=SimpleNamespace(
            skor=score,
            karar="Pozitif Teknik Görünüm" if score >= 70 else "Nötr Teknik Görünüm",
            pozitif_nedenler=(),
            riskler=(),
        ),
        risk_plani=SimpleNamespace(risk_odul_orani=rr),
    )


def vis(symbol, change):
    return SimpleNamespace(
        symbol=symbol,
        research_priority="NORMAL",
        visibility_state="IMPROVING",
        rank_change=change,
        data_blocked=False,
    )


def test_ready_jump_challenger_can_replace_weaker_waiting_scan_candidate():
    candidates = (
        candidate("A.IS", score=80),
        candidate("B.IS", score=79),
        candidate("C.IS", score=78),
        candidate("D.IS", score=66, volume=1.05),
        candidate("E.IS", score=65, volume=1.05),
        candidate("JUMP.IS", score=82, volume=1.5),
    )
    visibility = {"JUMP": vis("JUMP", 40)}
    merged = merge_jump_and_scan_candidates(candidates, visibility, limit=5)
    symbols = [item.candidate.sembol for item in merged]
    assert "JUMP.IS" in symbols
    jump = next(item for item in merged if item.candidate.sembol == "JUMP.IS")
    assert jump.source == "SICRAMA"
    assert "GİRİŞE HAZIR" in jump.priority_reason


def test_same_readiness_keeps_original_scan_order_without_jump_bonus():
    candidates = tuple(candidate(f"S{i}.IS", score=80) for i in range(1, 7))
    visibility = {"S6": vis("S6", 100)}
    merged = merge_jump_and_scan_candidates(candidates, visibility, limit=5)
    assert [item.candidate.sembol for item in merged] == [
        "S1.IS", "S2.IS", "S3.IS", "S4.IS", "S5.IS"
    ]


def test_overextended_jump_does_not_displace_scan_core():
    candidates = (
        candidate("A.IS"), candidate("B.IS"), candidate("C.IS"),
        candidate("D.IS"), candidate("E.IS"),
        candidate("FAR.IS", close=110.0, ema9=100.0, atr=2.0),
    )
    merged = merge_jump_and_scan_candidates(
        candidates, {"FAR": vis("FAR", 80)}, limit=5
    )
    assert "FAR.IS" not in [item.candidate.sembol for item in merged]


def test_morning_cards_expose_priority_reason():
    candidates = tuple(candidate(f"S{i}.IS", score=80) for i in range(1, 7))
    cards = build_morning_candidate_cards(
        SimpleNamespace(adaylar=candidates),
        visibility_contexts=(vis("S6", 50),),
        limit=5,
        include_movement_pool=True,
    )
    assert all(card.priority_reason for card in cards)
    rows = morning_candidate_rows(cards)
    assert "Top-5 öncelik nedeni" in rows[0]
