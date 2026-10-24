from backend.app.prebreakout.prebreakout_operation_alerts import (
    OperationTrendAlarmLevel,
    gunluk_yonetici_ozetini_hesapla,
    operasyon_trend_alarmlarini_degerlendir,
)
from backend.app.prebreakout.prebreakout_operation_archive import DailyOperationArchiveRecord


def _record(**overrides):
    values = dict(
        run_date="2026-08-01",
        status="COMPLETED",
        attempt_count=1,
        new_signal_count=2,
        total_signal_count=8,
        lifecycle_count=8,
        performance_count=6,
        paper_trade_count=4,
        portfolio_return_pct=2.0,
        health_ready=True,
        warning_count=0,
        error_count=0,
        missing_observation_count=0,
    )
    values.update(overrides)
    return DailyOperationArchiveRecord(**values)


def test_normal_degisim_alarm_uretmez():
    previous = _record(run_date="2026-07-31", portfolio_return_pct=1.5)
    current = _record(portfolio_return_pct=1.8)
    assert operasyon_trend_alarmlarini_degerlendir(current, previous) == ()


def test_sistem_sagligi_kaybi_kritik_alarmdir():
    previous = _record(run_date="2026-07-31", health_ready=True)
    current = _record(health_ready=False)
    alarms = operasyon_trend_alarmlarini_degerlendir(current, previous)
    assert alarms[0].code == "HEALTH_LOST"
    assert alarms[0].level is OperationTrendAlarmLevel.CRITICAL


def test_portfoy_belirgin_gerilemesi_uyari_uretir():
    previous = _record(run_date="2026-07-31", portfolio_return_pct=3.0)
    current = _record(portfolio_return_pct=1.5)
    alarms = operasyon_trend_alarmlarini_degerlendir(current, previous)
    assert any(item.code == "PORTFOLIO_DROP_WARNING" for item in alarms)


def test_yonetici_ozeti_en_yuksek_alarm_seviyesini_kullanir():
    previous = _record(run_date="2026-07-31", health_ready=True, portfolio_return_pct=4.0)
    current = _record(health_ready=False, error_count=2, portfolio_return_pct=0.0)
    summary = gunluk_yonetici_ozetini_hesapla((previous, current))
    assert summary is not None
    assert summary.level is OperationTrendAlarmLevel.CRITICAL
    assert "kritik" in summary.headline.lower()
