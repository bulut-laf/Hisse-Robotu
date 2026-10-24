from datetime import date, datetime, timezone

import pytest

from backend.app.prebreakout.prebreakout_candidate_lifecycle import CandidatePriceObservation
from backend.app.prebreakout.prebreakout_live_watch import PreBreakoutLiveSignal
from backend.app.prebreakout.prebreakout_paper_portfolio import (
    PaperPortfolioConfig,
    PaperTradeStatus,
    deneme_islemini_hesapla,
    deneme_portfoyu_ozeti,
    deneme_portfoyunu_tabloya_cevir,
)


def _signal() -> PreBreakoutLiveSignal:
    return PreBreakoutLiveSignal(
        schema_version=1,
        signal_id="test-signal",
        symbol="TUPRS.IS",
        signal_date="2026-01-01",
        recorded_at_utc=datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat(),
        stage="E3",
        stage_label="E3",
        score=80,
        accepted=True,
        close=100.0,
        minimum_momentum_score=10,
        threshold_policy_enabled=False,
        threshold_policy_source="test",
        features={},
        reasons=(),
        risks=(),
        payload_sha256="test",
    )


def _obs(day: int, high: float, low: float, close: float) -> CandidatePriceObservation:
    return CandidatePriceObservation(date(2026, 1, day), high, low, close)


def test_hedefe_ulasan_deneme_islemi_maliyet_ve_kaymayi_icerir() -> None:
    trade = deneme_islemini_hesapla(_signal(), (_obs(2, 112.0, 100.0, 110.0),))
    assert trade.status is PaperTradeStatus.HEDEF
    assert trade.quantity > 0
    assert trade.transaction_cost > 0
    assert trade.net_pnl < trade.gross_pnl
    assert trade.exit_date == "2026-01-02"


def test_ayni_seansta_stop_ve_hedef_varsa_stop_onceliklidir() -> None:
    trade = deneme_islemini_hesapla(_signal(), (_obs(2, 120.0, 90.0, 110.0),))
    assert trade.status is PaperTradeStatus.STOP
    assert "temkinli stop" in trade.note


def test_20_seans_dolmadan_pozisyon_acik_kalir() -> None:
    observations = tuple(_obs(day, 103.0, 98.0, 101.0) for day in range(2, 7))
    trade = deneme_islemini_hesapla(_signal(), observations)
    assert trade.status is PaperTradeStatus.ACIK
    assert trade.observed_session_count == 5
    assert trade.exit_date is None


def test_pozisyon_buyuklugu_risk_ve_tahsis_sinirini_asmaz() -> None:
    config = PaperPortfolioConfig(initial_capital=100_000, risk_per_trade_pct=1, maximum_open_positions=10)
    trade = deneme_islemini_hesapla(_signal(), (), config=config)
    assert trade.risk_amount <= 1_000.0
    assert trade.invested_amount <= 10_000.0


def test_portfoy_ozeti_ve_tablo() -> None:
    target = deneme_islemini_hesapla(_signal(), (_obs(2, 112.0, 100.0, 110.0),))
    stopped = deneme_islemini_hesapla(_signal(), (_obs(2, 101.0, 90.0, 95.0),))
    summary = deneme_portfoyu_ozeti((target, stopped))
    assert summary.closed_trade_count == 2
    assert summary.target_count == 1
    assert summary.stop_count == 1
    assert summary.win_rate_pct == 50.0
    table = deneme_portfoyunu_tabloya_cevir((target, stopped))
    assert "Net sonuç" in table.columns
    assert len(table) == 2


def test_gecersiz_portfoy_ayari_reddedilir() -> None:
    with pytest.raises(ValueError):
        PaperPortfolioConfig(stop_loss_pct=0)
