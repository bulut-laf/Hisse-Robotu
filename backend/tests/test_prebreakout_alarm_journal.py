from pathlib import Path

from backend.app.prebreakout.prebreakout_alarm_journal import (
    AlarmResolutionStatus,
    DecisionJournalRecord,
    alarm_gecmisini_yukle,
    alarmi_cozuldu_isaretle,
    gunluk_alarmlari_arsivle,
    gunluk_karari_kaydet,
    karar_gunlugunu_yukle,
)
from backend.app.prebreakout.prebreakout_operation_alerts import (
    OperationTrendAlarm,
    OperationTrendAlarmLevel,
)


def _alarm(code: str = "HEALTH_LOST") -> OperationTrendAlarm:
    return OperationTrendAlarm(
        code=code,
        level=OperationTrendAlarmLevel.CRITICAL,
        title="Sistem sağlığı bozuldu",
        message="Test alarmı",
    )


def test_alarm_arsivi_ayni_gun_ayni_alarmi_cogaltmaz(tmp_path: Path):
    path = tmp_path / "alarms.jsonl"
    gunluk_alarmlari_arsivle("2026-08-01", (_alarm(),), path)
    gunluk_alarmlari_arsivle("2026-08-01", (_alarm(),), path)
    rows = alarm_gecmisini_yukle(path)
    assert len(rows) == 1
    assert rows[0].status is AlarmResolutionStatus.OPEN


def test_alarm_cozuldu_isaretlenebilir(tmp_path: Path):
    path = tmp_path / "alarms.jsonl"
    gunluk_alarmlari_arsivle("2026-08-01", (_alarm(),), path)
    updated = alarmi_cozuldu_isaretle(
        "2026-08-01:HEALTH_LOST", "2026-08-02", "Veri yenilendi", path
    )
    assert updated.status is AlarmResolutionStatus.RESOLVED
    assert updated.resolved_date == "2026-08-02"
    assert updated.resolution_note == "Veri yenilendi"


def test_bilinmeyen_alarm_cozulemez(tmp_path: Path):
    path = tmp_path / "alarms.jsonl"
    try:
        alarmi_cozuldu_isaretle("yok", "2026-08-02", "not", path)
    except KeyError:
        pass
    else:
        raise AssertionError("Bilinmeyen alarm için KeyError bekleniyordu")


def test_gunluk_karar_ayni_tarihte_guncellenir(tmp_path: Path):
    path = tmp_path / "decisions.jsonl"
    gunluk_karari_kaydet(DecisionJournalRecord("2026-08-01", "BEKLE", "İlk karar"), path)
    gunluk_karari_kaydet(
        DecisionJournalRecord("2026-08-01", "İZLE", "Güncellendi", ("HEALTH_LOST",)),
        path,
    )
    rows = karar_gunlugunu_yukle(path)
    assert len(rows) == 1
    assert rows[0].decision == "İZLE"
    assert rows[0].alarm_codes == ("HEALTH_LOST",)


def test_bozuk_json_alarm_arsivi_guvenli_bos_doner(tmp_path: Path):
    path = tmp_path / "alarms.jsonl"
    path.write_text("{bozuk", encoding="utf-8")
    assert alarm_gecmisini_yukle(path) == ()
