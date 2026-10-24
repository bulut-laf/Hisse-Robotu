from __future__ import annotations

import pytest

from backend.app.risk.safety_lock import (
    KILIT_ACIK,
    KILITLI,
    SafetyLockContext,
    SafetyPolicy,
    TradeProposal,
    evaluate_trade_safety,
)


def _proposal(**changes: object) -> TradeProposal:
    values: dict[str, object] = {
        "symbol": "THYAO",
        "capital": 100_000.0,
        "entry_price": 100.0,
        "quantity": 200,
        "stop_loss": 95.0,
        "target_price": 110.0,
    }
    values.update(changes)
    return TradeProposal(**values)  # type: ignore[arg-type]


def test_guvenli_islem_on_kontrolu_acik_sonucu_verir() -> None:
    result = evaluate_trade_safety(_proposal())

    assert result.allowed is True
    assert result.status == KILIT_ACIK
    assert result.risk_pct == pytest.approx(1.0)
    assert result.reward_risk == pytest.approx(2.0)
    assert result.position_pct == pytest.approx(20.0)


def test_stop_ve_hedef_olmadan_islem_kilitlenir() -> None:
    result = evaluate_trade_safety(_proposal(stop_loss=None, target_price=None))

    assert result.allowed is False
    assert result.status == KILITLI
    assert any("Stop-loss" in reason for reason in result.blocking_reasons)
    assert any("Hedef" in reason for reason in result.blocking_reasons)


def test_risk_rr_ve_pozisyon_sinirlari_birlikte_kilitler() -> None:
    result = evaluate_trade_safety(
        _proposal(quantity=500, stop_loss=90.0, target_price=110.0),
        policy=SafetyPolicy(
            max_risk_per_trade_pct=1.0,
            min_reward_risk=2.0,
            max_position_pct=30.0,
        ),
    )

    text = " | ".join(result.blocking_reasons)
    assert "Pozisyon büyüklüğü" in text
    assert "Planlanan işlem riski" in text
    assert "Risk/getiri" in text


def test_gunluk_haftalik_ve_ardisik_zarar_kilidi_calismayi_durdurur() -> None:
    result = evaluate_trade_safety(
        _proposal(),
        context=SafetyLockContext(
            daily_net_pnl=-2_000.0,
            weekly_net_pnl=-4_500.0,
            consecutive_losses=3,
        ),
    )

    text = " | ".join(result.blocking_reasons)
    assert "Günlük zarar" in text
    assert "Haftalık zarar" in text
    assert "Ardışık 3 zarar" in text


def test_kaybedene_ekleme_ve_asiri_yukselmis_giris_engellenir() -> None:
    result = evaluate_trade_safety(
        _proposal(averaging_down=True, overextended_entry=True)
    )

    assert result.allowed is False
    assert len(result.blocking_reasons) == 2
