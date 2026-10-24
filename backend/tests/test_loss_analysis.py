from __future__ import annotations

from datetime import date

import pytest

from backend.app.analysis.loss_analysis import (
    analyze_trade_losses,
    cause_table,
    diagnostic_table,
    journal_table,
)
from backend.app.history.trade_journal import GERCEK_HESAP, TradeRecord
from backend.app.risk.safety_lock import SafetyPolicy


def _record(
    *,
    symbol: str,
    exit_date: date,
    entry: float,
    exit: float,
    stop: float | None = 95.0,
    target: float | None = 110.0,
    capital: float = 100_000.0,
    quantity: int = 100,
    **flags: object,
) -> TradeRecord:
    return TradeRecord(
        account_type=GERCEK_HESAP,
        symbol=symbol,
        entry_date=date(2026, 7, 1),
        exit_date=exit_date,
        entry_price=entry,
        exit_price=exit,
        quantity=quantity,
        capital_at_entry=capital,
        stop_loss=stop,
        target_price=target,
        fees=0.0,
        signal_class=str(flags.pop("signal_class", "E3")),
        created_at=f"{exit_date.isoformat()}T18:00:00",
        **flags,
    )


def _records() -> tuple[TradeRecord, ...]:
    return (
        _record(symbol="AAA", exit_date=date(2026, 7, 6), entry=100, exit=110),
        _record(
            symbol="BBB",
            exit_date=date(2026, 7, 7),
            entry=100,
            exit=90,
            stop=None,
            target=None,
            late_entry=True,
        ),
        _record(
            symbol="CCC",
            exit_date=date(2026, 7, 8),
            entry=100,
            exit=94,
            stop=96,
            target=104,
            averaging_down=True,
        ),
    )


def test_kayip_analizi_ozet_ve_beklenti_hesaplar() -> None:
    result = analyze_trade_losses(_records(), evaluation_date=date(2026, 7, 8))

    assert result.summary.trade_count == 3
    assert result.summary.winning_count == 1
    assert result.summary.losing_count == 2
    assert result.summary.net_pnl == pytest.approx(-600.0)
    assert result.summary.win_rate_pct == pytest.approx(100 / 3)
    assert result.summary.profit_factor == pytest.approx(1000 / 1600)
    assert result.summary.expectancy == pytest.approx(-200.0)
    assert result.summary.max_consecutive_losses == 2
    assert result.summary.max_drawdown == pytest.approx(1600.0)


def test_kayip_nedenleri_stop_rr_gec_giris_ve_eklemeyi_bulur() -> None:
    result = analyze_trade_losses(_records())
    text = " | ".join(cause.cause for cause in result.causes)

    assert "Stop tanımlanmamış" in text
    assert "Risk/getiri planı hesaplanmamış" in text
    assert "Geç giriş işaretlenmiş" in text
    assert "Kaybeden pozisyona ekleme yapılmış" in text
    assert "Risk/getiri oranı yetersiz" in text


def test_degerlendirme_tarihinde_gunluk_haftalik_ve_seri_baglamini_uretir() -> None:
    result = analyze_trade_losses(_records(), evaluation_date=date(2026, 7, 8))

    assert result.safety_context.daily_net_pnl == pytest.approx(-600.0)
    assert result.safety_context.weekly_net_pnl == pytest.approx(-600.0)
    assert result.safety_context.consecutive_losses == 2
    assert result.daily_pnl[-1].period == "2026-07-08"
    assert result.weekly_pnl[-1].period == "2026-07-06"


def test_risk_ve_pozisyon_siniri_asimi_kayip_nedeni_olur() -> None:
    record = _record(
        symbol="RISK",
        exit_date=date(2026, 7, 9),
        entry=100,
        exit=90,
        stop=80,
        target=120,
        quantity=500,
        capital=100_000,
    )
    result = analyze_trade_losses(
        (record,),
        policy=SafetyPolicy(max_risk_per_trade_pct=1.0, max_position_pct=30.0),
    )
    causes = result.diagnostics[0].causes

    assert "İşlem başına risk sınırı aşılmış" in causes
    assert "Pozisyon sermaye sınırı aşılmış" in causes


def test_tablo_donusturuculeri_kullaniciya_okunabilir_kayitlar_uretir() -> None:
    records = _records()
    result = analyze_trade_losses(records)

    assert journal_table(records)[0]["Sembol"] == "CCC"
    assert diagnostic_table(result)[0]["Net zarar"] < 0
    assert cause_table(result)[0]["İşlem sayısı"] >= 1
