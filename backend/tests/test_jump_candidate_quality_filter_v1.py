from types import SimpleNamespace

from backend.app.analysis.jump_candidate_quality import evaluate_jump_candidate_quality
from backend.app.analysis.morning_candidate_flow import build_morning_candidate_cards


def _candidate(symbol, score=75, volume=1.3, rr=2.0, close=100.0, ema9=98.0, atr14=2.0):
    return SimpleNamespace(
        sembol=symbol,
        kapanis=close,
        ema9=ema9,
        atr14=atr14,
        hacim_orani=volume,
        sinyal=SimpleNamespace(
            skor=score,
            karar="Pozitif Teknik Görünüm",
            pozitif_nedenler=(),
            riskler=(),
        ),
        risk_plani=SimpleNamespace(risk_odul_orani=rr),
    )


def _visibility(symbol, change):
    return SimpleNamespace(
        symbol=symbol,
        research_priority="NORMAL",
        visibility_state="IMPROVING",
        rank_change=change,
        data_blocked=False,
    )


def test_jump_quality_gate_accepts_balanced_candidate():
    result = evaluate_jump_candidate_quality(_candidate("AAA.IS"))
    assert result.eligible is True
    assert result.technical_ok is True
    assert result.volume_ok is True
    assert result.risk_reward_ok is True
    assert result.entry_ok is True


def test_jump_quality_gate_rejects_overextended_candidate():
    result = evaluate_jump_candidate_quality(
        _candidate("AAA.IS", close=110.0, ema9=100.0, atr14=2.0)
    )
    assert result.eligible is False
    assert result.entry_ok is False
    assert result.extension_atr == 5.0


def test_movement_pool_skips_low_quality_jump_and_uses_next_eligible_mover():
    candidates = (
        _candidate("A.IS", score=90),
        _candidate("B.IS", score=88),
        _candidate("C.IS", score=86),
        _candidate("BAD.IS", score=55, volume=0.7, rr=1.1),
        _candidate("GOOD.IS", score=74, volume=1.4, rr=2.2),
        _candidate("F.IS", score=72),
    )
    scan_result = SimpleNamespace(adaylar=candidates)
    contexts = (
        _visibility("BAD", 80),
        _visibility("GOOD", 45),
    )

    cards = build_morning_candidate_cards(
        scan_result,
        visibility_contexts=contexts,
        limit=5,
        include_movement_pool=True,
    )

    symbols = [card.symbol for card in cards]
    assert "GOOD" in symbols
    good = next(card for card in cards if card.symbol == "GOOD")
    assert good.selection_source == "SICRAMA"
    assert good.jump_quality == "UYGUN"
    bad = next((card for card in cards if card.symbol == "BAD"), None)
    if bad is not None:
        assert bad.selection_source == "TARAMA"
        assert bad.jump_quality == "FİLTRE DIŞI"


def test_missing_extension_inputs_do_not_block_backward_compatible_candidates():
    candidate = SimpleNamespace(
        sembol="OLD.IS",
        hacim_orani=1.2,
        sinyal=SimpleNamespace(
            skor=70,
            karar="Pozitif Teknik Görünüm",
            pozitif_nedenler=(),
            riskler=(),
        ),
        risk_plani=SimpleNamespace(risk_odul_orani=2.0),
    )
    result = evaluate_jump_candidate_quality(candidate)
    assert result.eligible is True
    assert result.extension_atr is None


def test_dashboard_exposes_jump_quality_gate():
    from pathlib import Path
    source = Path("backend/dashboard.py").read_text(encoding="utf-8")
    assert "Sıçrama kalite kapısı" in source
    assert "jump_quality_reason" in source
