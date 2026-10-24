from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import json
from pathlib import Path

from backend.app.prebreakout.prebreakout_operation_diagnosis import (
    OperationDiagnosisReport,
    RootCauseCategory,
)


DEFAULT_OPERATION_RECOVERY_PATH = Path("backend/data/prebreakout_operation_recovery.json")


class RecoveryAction(str, Enum):
    VERIFY_DATA = "VERIYI_DOGRULA"
    REPAIR_RECORD_CHAIN = "KAYIT_ZINCIRINI_DOGRULA"
    RESOLVE_HEALTH_LOCK = "SAGLIK_KILIDINI_GIDER"
    RETRY_OPERATION = "OPERASYONU_YENIDEN_DENE"
    VERIFY_PORTFOLIO = "PORTFOYU_DOGRULA"
    REVIEW_CALCULATION = "HESAPLAMAYI_INCELE"
    MANUAL_REVIEW = "MANUEL_INCELEME"
    NONE = "ISLEM_GEREKMIYOR"


@dataclass(frozen=True)
class RecoveryStep:
    order: int
    action: RecoveryAction
    title: str
    instruction: str
    automatic: bool = False


@dataclass(frozen=True)
class OperationRecoveryGuide:
    run_date: str
    diagnosis_status: str
    primary_category: RootCauseCategory
    steps: tuple[RecoveryStep, ...]
    safe_retry_allowed: bool
    summary: str


def _steps_for_category(category: RootCauseCategory) -> tuple[RecoveryStep, ...]:
    if category is RootCauseCategory.DATA:
        return (
            RecoveryStep(1, RecoveryAction.VERIFY_DATA, "Piyasa verisini doğrula", "Eksik/eski fiyat gözlemlerini ve veri tarihini kontrol et."),
            RecoveryStep(2, RecoveryAction.MANUAL_REVIEW, "Veri düzelmeden yeniden deneme yapma", "Veri tazeliği ve bütünlüğü doğrulanmadan operasyonu yeniden çalıştırma."),
        )
    if category is RootCauseCategory.RECORD_INTEGRITY:
        return (
            RecoveryStep(1, RecoveryAction.REPAIR_RECORD_CHAIN, "Kayıt zincirini doğrula", "Canlı izleme, yaşam döngüsü ve performans kayıt sayımlarını karşılaştır."),
            RecoveryStep(2, RecoveryAction.MANUAL_REVIEW, "Tutarsız kaydı incele", "Kayıt bütünlüğü sağlanmadan otomatik yeniden deneme yapma."),
        )
    if category is RootCauseCategory.HEALTH_LOCK:
        return (
            RecoveryStep(1, RecoveryAction.RESOLVE_HEALTH_LOCK, "Sağlık kilidini gider", "HATA seviyesindeki sistem sağlık kontrollerini çöz."),
            RecoveryStep(2, RecoveryAction.RETRY_OPERATION, "Güvenli yeniden dene", "Sağlık raporu hazır duruma geldikten sonra günlük operasyonu yeniden çalıştır."),
        )
    if category is RootCauseCategory.CALCULATION:
        return (
            RecoveryStep(1, RecoveryAction.REVIEW_CALCULATION, "Hesaplama hatasını incele", "Başarısız adımın hata mesajını ve ilgili hesaplama girdilerini doğrula."),
            RecoveryStep(2, RecoveryAction.RETRY_OPERATION, "Güvenli yeniden dene", "Girdi bütünlüğü doğrulandıktan sonra idempotent günlük operasyonu yeniden çalıştır."),
        )
    if category is RootCauseCategory.PORTFOLIO:
        return (
            RecoveryStep(1, RecoveryAction.VERIFY_PORTFOLIO, "Portföy tutarlılığını doğrula", "Deneme işlemleri ile portföy özetindeki işlem sayısı ve sonuçları karşılaştır."),
            RecoveryStep(2, RecoveryAction.RETRY_OPERATION, "Gerekirse yeniden hesapla", "Portföy kayıtları tutarlıysa günlük operasyonu güvenli biçimde yeniden çalıştır."),
        )
    if category is RootCauseCategory.OPERATION:
        return (
            RecoveryStep(1, RecoveryAction.MANUAL_REVIEW, "Operasyon hatasını incele", "Başarısız adım ve hata mesajını incele; veri veya kayıt sorunu olmadığını doğrula."),
            RecoveryStep(2, RecoveryAction.RETRY_OPERATION, "Güvenli yeniden dene", "Kök neden giderildikten sonra günlük operasyonu yeniden çalıştır."),
        )
    return (
        RecoveryStep(1, RecoveryAction.NONE, "İşlem gerekmiyor", "Operasyon için kurtarma adımı gerektiren bir kök neden bulunmadı."),
    )


def operasyon_kurtarma_rehberi_olustur(
    diagnosis: OperationDiagnosisReport,
) -> OperationRecoveryGuide:
    steps = _steps_for_category(diagnosis.primary_category)
    safe_retry_allowed = bool(diagnosis.retry_recommended) and diagnosis.primary_category not in {
        RootCauseCategory.DATA,
        RootCauseCategory.RECORD_INTEGRITY,
        RootCauseCategory.NONE,
    }
    if diagnosis.primary_category is RootCauseCategory.NONE:
        summary = "Kurtarma işlemi gerekmiyor; operasyon teşhisinde hata bulunmadı."
    elif safe_retry_allowed:
        summary = f"{diagnosis.primary_category.value}: kontrollü düzeltme sonrası güvenli yeniden deneme yapılabilir."
    else:
        summary = f"{diagnosis.primary_category.value}: otomatik yeniden deneme önerilmez; önce doğrulama gerekir."
    return OperationRecoveryGuide(
        run_date=diagnosis.run_date,
        diagnosis_status=diagnosis.status,
        primary_category=diagnosis.primary_category,
        steps=steps,
        safe_retry_allowed=safe_retry_allowed,
        summary=summary,
    )


def operasyon_kurtarma_rehberini_kaydet(
    guide: OperationRecoveryGuide,
    path: str | Path = DEFAULT_OPERATION_RECOVERY_PATH,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(guide)
    payload["primary_category"] = guide.primary_category.value
    payload["steps"] = [
        {**asdict(step), "action": step.action.value}
        for step in guide.steps
    ]
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(target)


def operasyon_kurtarma_rehberini_tabloya_cevir(
    guide: OperationRecoveryGuide,
) -> list[dict[str, str]]:
    return [
        {
            "Sıra": str(step.order),
            "Eylem": step.action.value,
            "Başlık": step.title,
            "Önerilen adım": step.instruction,
            "Otomatik": "Evet" if step.automatic else "Hayır",
        }
        for step in guide.steps
    ]
