from dataclasses import dataclass
from pathlib import Path
import json

from backend.app.prebreakout.prebreakout_operation_diagnosis import (
    OperationDiagnosisReport,
    RootCauseCategory,
)
from backend.app.prebreakout.prebreakout_operation_recovery import (
    RecoveryAction,
    operasyon_kurtarma_rehberi_olustur,
    operasyon_kurtarma_rehberini_kaydet,
)


def _diagnosis(category: RootCauseCategory, *, retry: bool) -> OperationDiagnosisReport:
    return OperationDiagnosisReport(
        run_date="2026-08-01",
        status="FAILED" if category is not RootCauseCategory.NONE else "COMPLETED",
        primary_category=category,
        findings=(),
        summary="test",
        retry_recommended=retry,
    )


def test_veri_sorununda_otomatik_yeniden_deneme_onerilmez() -> None:
    guide = operasyon_kurtarma_rehberi_olustur(_diagnosis(RootCauseCategory.DATA, retry=False))
    assert guide.safe_retry_allowed is False
    assert guide.steps[0].action is RecoveryAction.VERIFY_DATA
    assert all(step.action is not RecoveryAction.RETRY_OPERATION for step in guide.steps)


def test_kayit_butunlugu_sorununda_once_zincir_dogrulanir() -> None:
    guide = operasyon_kurtarma_rehberi_olustur(_diagnosis(RootCauseCategory.RECORD_INTEGRITY, retry=False))
    assert guide.steps[0].action is RecoveryAction.REPAIR_RECORD_CHAIN
    assert guide.safe_retry_allowed is False


def test_saglik_kilidinde_duzeltme_sonrasi_yeniden_deneme_var() -> None:
    guide = operasyon_kurtarma_rehberi_olustur(_diagnosis(RootCauseCategory.HEALTH_LOCK, retry=True))
    assert guide.safe_retry_allowed is True
    assert guide.steps[-1].action is RecoveryAction.RETRY_OPERATION


def test_hesaplama_hatasinda_once_inceleme_sonra_yeniden_deneme() -> None:
    guide = operasyon_kurtarma_rehberi_olustur(_diagnosis(RootCauseCategory.CALCULATION, retry=True))
    assert [step.action for step in guide.steps] == [
        RecoveryAction.REVIEW_CALCULATION,
        RecoveryAction.RETRY_OPERATION,
    ]


def test_saglikli_operasyonda_kurtarma_adimi_gerekmez() -> None:
    guide = operasyon_kurtarma_rehberi_olustur(_diagnosis(RootCauseCategory.NONE, retry=False))
    assert guide.safe_retry_allowed is False
    assert guide.steps[0].action is RecoveryAction.NONE


def test_kurtarma_rehberi_atomik_json_kaydedilir(tmp_path: Path) -> None:
    guide = operasyon_kurtarma_rehberi_olustur(_diagnosis(RootCauseCategory.PORTFOLIO, retry=False))
    path = tmp_path / "recovery.json"
    operasyon_kurtarma_rehberini_kaydet(guide, path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["primary_category"] == "PORTFOY"
    assert payload["steps"][0]["action"] == "PORTFOYU_DOGRULA"
    assert not path.with_suffix(".json.tmp").exists()
