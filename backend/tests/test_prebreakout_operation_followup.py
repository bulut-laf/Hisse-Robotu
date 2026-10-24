from pathlib import Path
from types import SimpleNamespace

from backend.app.prebreakout.prebreakout_alarm_journal import (
    DecisionJournalRecord,
    alarm_gecmisini_yukle,
    gunluk_karari_kaydet,
    karar_gunlugunu_yukle,
)
from backend.app.prebreakout.prebreakout_operation_archive import (
    DailyOperationArchiveRecord,
    gunluk_operasyon_arsivini_kaydet,
)
from backend.app.prebreakout.prebreakout_operation_followup import (
    PENDING_DECISION,
    gunluk_operasyon_takibini_guncelle,
)


def _run_result(run_date: str, status: str = "COMPLETED", *, portfolio: float = 0.0):
    return SimpleNamespace(
        state=SimpleNamespace(
            run_date=run_date,
            status=SimpleNamespace(value=status),
            attempt_count=1,
        ),
        monitor_result=SimpleNamespace(
            new_signal_count=1,
            total_signal_count=5,
            lifecycle_records=(1,),
            performance_records=(1,),
            paper_trades=(1,),
            portfolio_summary=SimpleNamespace(portfolio_return_pct=portfolio),
            missing_observation_symbols=(),
        ),
        health_report=SimpleNamespace(
            ready=(status == "COMPLETED"),
            warning_count=0,
            error_count=(1 if status in {"FAILED", "BLOCKED"} else 0),
        ),
    )


def _paths(tmp_path: Path):
    return (
        tmp_path / "archive.jsonl",
        tmp_path / "alarms.jsonl",
        tmp_path / "decisions.jsonl",
    )


def test_gunluk_takip_karar_bekliyor_kaydini_otomatik_olusturur(tmp_path: Path):
    archive, alarms, decisions = _paths(tmp_path)
    run = _run_result("2026-08-02")
    from backend.app.prebreakout.prebreakout_operation_archive import gunluk_operasyon_arsiv_kaydi_olustur
    gunluk_operasyon_arsivini_kaydet(gunluk_operasyon_arsiv_kaydi_olustur(run), archive)

    result = gunluk_operasyon_takibini_guncelle(
        run,
        archive_path=archive,
        alarm_history_path=alarms,
        decision_journal_path=decisions,
    )

    assert result.decision.decision == PENDING_DECISION
    assert karar_gunlugunu_yukle(decisions)[0].run_date == "2026-08-02"


def test_kullanici_karari_otomatik_takip_tarafindan_ezilmez(tmp_path: Path):
    archive, alarms, decisions = _paths(tmp_path)
    run = _run_result("2026-08-02")
    from backend.app.prebreakout.prebreakout_operation_archive import gunluk_operasyon_arsiv_kaydi_olustur
    gunluk_operasyon_arsivini_kaydet(gunluk_operasyon_arsiv_kaydi_olustur(run), archive)
    gunluk_karari_kaydet(
        DecisionJournalRecord("2026-08-02", "İZLE", "Manuel karar", ()), decisions
    )

    result = gunluk_operasyon_takibini_guncelle(
        run,
        archive_path=archive,
        alarm_history_path=alarms,
        decision_journal_path=decisions,
    )

    assert result.decision.decision == "İZLE"
    assert karar_gunlugunu_yukle(decisions)[0].rationale == "Manuel karar"


def test_failed_operasyon_kritik_alarm_olarak_arsivlenir(tmp_path: Path):
    archive, alarms, decisions = _paths(tmp_path)
    run = _run_result("2026-08-02", "FAILED")
    from backend.app.prebreakout.prebreakout_operation_archive import gunluk_operasyon_arsiv_kaydi_olustur
    gunluk_operasyon_arsivini_kaydet(gunluk_operasyon_arsiv_kaydi_olustur(run), archive)

    result = gunluk_operasyon_takibini_guncelle(
        run,
        archive_path=archive,
        alarm_history_path=alarms,
        decision_journal_path=decisions,
    )

    rows = alarm_gecmisini_yukle(alarms)
    assert result.alarm_count == 1
    assert rows[0].code == "OPERATION_FAILED"
    assert rows[0].level == "KRİTİK"
    assert "OPERATION_FAILED" in result.decision.alarm_codes


def test_blocked_operasyon_kritik_alarm_olarak_arsivlenir(tmp_path: Path):
    archive, alarms, decisions = _paths(tmp_path)
    run = _run_result("2026-08-02", "BLOCKED")
    from backend.app.prebreakout.prebreakout_operation_archive import gunluk_operasyon_arsiv_kaydi_olustur
    gunluk_operasyon_arsivini_kaydet(gunluk_operasyon_arsiv_kaydi_olustur(run), archive)

    gunluk_operasyon_takibini_guncelle(
        run,
        archive_path=archive,
        alarm_history_path=alarms,
        decision_journal_path=decisions,
    )

    rows = alarm_gecmisini_yukle(alarms)
    assert any(row.code == "OPERATION_BLOCKED" for row in rows)


def test_ayni_gun_tekrar_takip_alarm_kaydini_cogaltmaz(tmp_path: Path):
    archive, alarms, decisions = _paths(tmp_path)
    run = _run_result("2026-08-02", "FAILED")
    from backend.app.prebreakout.prebreakout_operation_archive import gunluk_operasyon_arsiv_kaydi_olustur
    gunluk_operasyon_arsivini_kaydet(gunluk_operasyon_arsiv_kaydi_olustur(run), archive)

    for _ in range(2):
        gunluk_operasyon_takibini_guncelle(
            run,
            archive_path=archive,
            alarm_history_path=alarms,
            decision_journal_path=decisions,
        )

    assert len(alarm_gecmisini_yukle(alarms)) == 1
    assert len(karar_gunlugunu_yukle(decisions)) == 1


def test_onceki_gune_gore_portfoy_alarm_kodu_karara_baglanir(tmp_path: Path):
    archive, alarms, decisions = _paths(tmp_path)
    gunluk_operasyon_arsivini_kaydet(
        DailyOperationArchiveRecord(
            "2026-08-01", "COMPLETED", 1, 1, 4, 1, 1, 1, 2.0,
            True, 0, 0, 0,
        ),
        archive,
    )
    run = _run_result("2026-08-02", "COMPLETED", portfolio=-2.0)
    from backend.app.prebreakout.prebreakout_operation_archive import gunluk_operasyon_arsiv_kaydi_olustur
    gunluk_operasyon_arsivini_kaydet(gunluk_operasyon_arsiv_kaydi_olustur(run), archive)

    result = gunluk_operasyon_takibini_guncelle(
        run,
        archive_path=archive,
        alarm_history_path=alarms,
        decision_journal_path=decisions,
    )

    assert "PORTFOLIO_DROP_CRITICAL" in result.decision.alarm_codes
