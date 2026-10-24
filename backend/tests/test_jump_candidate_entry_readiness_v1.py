from types import SimpleNamespace

from backend.app.analysis.jump_candidate_entry_readiness import (
    EARLY,
    OVEREXTENDED,
    READY,
    WAIT_CONFIRMATION,
    evaluate_jump_candidate_entry_readiness,
)
from backend.app.analysis.morning_candidate_flow import (
    build_morning_candidate_cards,
    morning_candidate_rows,
)


def candidate(*, score=76, view="Pozitif Teknik Görünüm", volume=1.35, rr=2.0, close=100.0, ema9=99.0, atr=2.0, resistance=2.5):
    return SimpleNamespace(
        sembol="TEST.IS",
        kapanis=close,
        ema9=ema9,
        atr14=atr,
        hacim_orani=volume,
        sinyal=SimpleNamespace(
            skor=score,
            karar=view,
            pozitif_nedenler=("trend",),
            riskler=(),
        ),
        risk_plani=SimpleNamespace(risk_odul_orani=rr),
        destek_direnc=SimpleNamespace(direnc_uzaklik_yuzde=resistance),
    )


def test_entry_readiness_ready():
    result = evaluate_jump_candidate_entry_readiness(candidate())
    assert result.state == READY
    assert result.ready is True
    assert result.extension_atr == 0.5


def test_entry_readiness_waits_for_confirmation():
    result = evaluate_jump_candidate_entry_readiness(candidate(score=66, volume=1.05))
    assert result.state == WAIT_CONFIRMATION
    assert result.ready is False


def test_entry_readiness_marks_early_when_quality_not_complete():
    result = evaluate_jump_candidate_entry_readiness(candidate(score=55, volume=0.8))
    assert result.state == EARLY


def test_entry_readiness_marks_overextended():
    result = evaluate_jump_candidate_entry_readiness(candidate(close=106.0, ema9=100.0, atr=2.0))
    assert result.state == OVEREXTENDED
    assert result.extension_atr == 3.0


def test_morning_card_exposes_entry_readiness():
    scan = SimpleNamespace(adaylar=(candidate(),))
    cards = build_morning_candidate_cards(scan, limit=1)
    assert cards[0].entry_readiness == READY
    rows = morning_candidate_rows(cards)
    assert rows[0]["Giriş hazırlığı"] == READY
    assert rows[0]["Uzama (ATR)"] == 0.5
