from pathlib import Path
import json

from backend.app.prebreakout.prebreakout_alarm_journal import (
    AlarmHistoryRecord,
    AlarmResolutionStatus,
    DecisionJournalRecord,
)
from backend.app.prebreakout.prebreakout_operation_action_summary import (
    OperationActionSummary,
    UserActionPriority,
)
from backend.app.prebreakout.prebreakout_operation_closure import (
    gunluk_operasyon_kapanisini_olustur,
    operasyon_kapanis_ozetini_kaydet,
    operasyon_kapanis_ozetini_tabloya_cevir,
)
from backend.app.prebreakout.prebreakout_operation_confidence import DailyOperationDecision


def _action(priority=UserActionPriority.NORMAL, retry=True):
    return OperationActionSummary(
        run_date="2026-08-01",
        decision=DailyOperationDecision.RUN,
        score=91,
        priority=priority,
        headline="test",
        why=("neden",),
        actions=("Veriyi doğrula.", "Günlük operasyonu izle."),
        retry_allowed=retry,
        final_message="test",
    )


def _alarm(level="UYARI", status=AlarmResolutionStatus.OPEN, code="A1"):
    return AlarmHistoryRecord(
        alarm_id=f"2026-08-01:{code}",
        run_date="2026-08-01",
        code=code,
        level=level,
        title="Test alarmı",
        message="Kontrol gerekli.",
        status=status,
    )


def _decision():
    return DecisionJournalRecord(
        run_date="2026-08-01",
        decision="ÇALIŞTIR",
        rationale="Kontroller tamamlandı.",
        alarm_codes=(),
    )


def test_kritik_acik_risk_kapanisi_engeller():
    result = gunluk_operasyon_kapanisini_olustur(
        _action(), (_alarm("KRİTİK"),), (_decision(),)
    )
    assert result.critical_open_risk_count == 1
    assert not result.closure_ready
    assert "kritik açık risk" in result.final_message


def test_uyari_acik_kalsa_da_karar_kaydi_varsa_kapanis_hazir_olabilir():
    result = gunluk_operasyon_kapanisini_olustur(
        _action(), (_alarm("UYARI"),), (_decision(),)
    )
    assert result.open_risk_count == 1
    assert result.critical_open_risk_count == 0
    assert result.closure_ready
    assert "açık riskleri izle" in result.headline


def test_cozulmus_alarm_acik_risk_sayilmaz():
    result = gunluk_operasyon_kapanisini_olustur(
        _action(), (_alarm(status=AlarmResolutionStatus.RESOLVED),), (_decision(),)
    )
    assert result.open_risk_count == 0
    assert result.closure_ready


def test_karar_gunlugu_eksikse_kapanis_hazir_degil():
    result = gunluk_operasyon_kapanisini_olustur(_action(), (), ())
    assert not result.decision_recorded
    assert not result.closure_ready
    assert "karar" in result.headline.lower()


def test_dur_onceligi_kapanisi_engeller():
    result = gunluk_operasyon_kapanisini_olustur(
        _action(UserActionPriority.STOP, retry=False), (), (_decision(),)
    )
    assert not result.closure_ready
    assert "engellendi" in result.headline


def test_onceki_gun_acik_alarm_hala_acik_risk_olarak_tasinir():
    old_alarm = AlarmHistoryRecord(
        alarm_id="2026-07-31:OLD",
        run_date="2026-07-31",
        code="OLD",
        level="UYARI",
        title="Eski açık risk",
        message="Henüz çözülmedi.",
        status=AlarmResolutionStatus.OPEN,
    )
    result = gunluk_operasyon_kapanisini_olustur(
        _action(), (old_alarm,), (_decision(),)
    )
    assert result.open_risk_count == 1
    assert any("Eski açık risk" in item for item in result.open_risks)


def test_kapanis_ozeti_atomik_json_kaydedilir(tmp_path: Path):
    result = gunluk_operasyon_kapanisini_olustur(_action(), (), (_decision(),))
    path = tmp_path / "closure.json"
    operasyon_kapanis_ozetini_kaydet(result, path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["closure_ready"] is True
    assert payload["decision_recorded"] is True
    assert not path.with_suffix(".json.tmp").exists()


def test_kapanis_ozeti_tabloya_cevrilir():
    result = gunluk_operasyon_kapanisini_olustur(_action(), (), (_decision(),))
    rows = operasyon_kapanis_ozetini_tabloya_cevir(result)
    fields = {row["Alan"] for row in rows}
    assert {"Karar", "Güven skoru", "Açık risk", "Kritik açık risk", "Kapanış"} <= fields
