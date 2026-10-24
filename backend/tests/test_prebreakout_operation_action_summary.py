from pathlib import Path
import json

from backend.app.prebreakout.prebreakout_operation_action_summary import (
    UserActionPriority,
    operasyon_aksiyon_ozeti_olustur,
    operasyon_aksiyon_ozetini_kaydet,
    operasyon_aksiyon_ozetini_tabloya_cevir,
)
from backend.app.prebreakout.prebreakout_operation_confidence import (
    DailyOperationDecision,
    OperationConfidenceReport,
)
from backend.app.prebreakout.prebreakout_operation_diagnosis import RootCauseCategory
from backend.app.prebreakout.prebreakout_operation_recovery import (
    OperationRecoveryGuide,
    RecoveryAction,
    RecoveryStep,
)


def _confidence(decision, score=100, category=RootCauseCategory.NONE, errors=0, warnings=0):
    return OperationConfidenceReport(
        run_date="2026-08-01",
        score=score,
        decision=decision,
        health_ready=errors == 0,
        error_count=errors,
        warning_count=warnings,
        primary_category=category,
        reasons=("Teknik ayrıntı 1", "Teknik ayrıntı 2", "Teknik ayrıntı 3"),
        summary="test",
    )


def _recovery(category=RootCauseCategory.NONE, retry=False):
    steps = (
        RecoveryStep(1, RecoveryAction.MANUAL_REVIEW, "Kontrol et", "İlgili girdiyi doğrula."),
        RecoveryStep(2, RecoveryAction.RETRY_OPERATION, "Yeniden dene", "Doğrulama sonrası güvenli yeniden dene."),
    )
    return OperationRecoveryGuide("2026-08-01", "TEST", category, steps, retry, "test")


def test_calistir_karari_tek_net_aksiyona_donusur():
    summary = operasyon_aksiyon_ozeti_olustur(
        _confidence(DailyOperationDecision.RUN), _recovery()
    )
    assert summary.priority is UserActionPriority.NORMAL
    assert summary.actions == ("Günlük operasyon akışına normal şekilde devam et.",)
    assert summary.final_message.startswith("ÇALIŞTIR")


def test_bekle_karari_kritik_nedeni_sadelestirir_ve_retry_kapatir():
    summary = operasyon_aksiyon_ozeti_olustur(
        _confidence(DailyOperationDecision.WAIT, 30, RootCauseCategory.DATA, errors=1),
        _recovery(RootCauseCategory.DATA, retry=True),
    )
    assert summary.priority is UserActionPriority.STOP
    assert not summary.retry_allowed
    assert any("Piyasa verisi" in item for item in summary.why)
    assert "yeniden çalıştırma" in summary.final_message


def test_incele_karari_guvenli_retry_bilgisini_korur():
    summary = operasyon_aksiyon_ozeti_olustur(
        _confidence(DailyOperationDecision.REVIEW, 65, RootCauseCategory.CALCULATION),
        _recovery(RootCauseCategory.CALCULATION, retry=True),
    )
    assert summary.priority is UserActionPriority.ATTENTION
    assert summary.retry_allowed
    assert "kontrollü yeniden deneme" in summary.final_message


def test_neden_ve_aksiyon_listeleri_sinirlanir():
    summary = operasyon_aksiyon_ozeti_olustur(
        _confidence(DailyOperationDecision.REVIEW, 60, RootCauseCategory.OPERATION, warnings=2),
        _recovery(RootCauseCategory.OPERATION),
        max_reasons=2,
        max_actions=1,
    )
    assert len(summary.why) == 2
    assert len(summary.actions) == 1


def test_aksiyon_ozeti_atomik_json_kaydedilir(tmp_path: Path):
    summary = operasyon_aksiyon_ozeti_olustur(
        _confidence(DailyOperationDecision.RUN), _recovery()
    )
    path = tmp_path / "action_summary.json"
    operasyon_aksiyon_ozetini_kaydet(summary, path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["decision"] == "ÇALIŞTIR"
    assert payload["priority"] == "NORMAL"
    assert payload["actions"]
    assert not path.with_suffix(".json.tmp").exists()


def test_aksiyon_ozeti_tabloya_cevrilir():
    summary = operasyon_aksiyon_ozeti_olustur(
        _confidence(DailyOperationDecision.WAIT, 25, RootCauseCategory.HEALTH_LOCK, errors=1),
        _recovery(RootCauseCategory.HEALTH_LOCK),
    )
    rows = operasyon_aksiyon_ozetini_tabloya_cevir(summary)
    assert {row["Alan"] for row in rows} >= {"Karar", "Güven skoru", "Öncelik", "Yeniden deneme"}
