# TASK_ENGINE_V1
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class WorkflowPhase(str, Enum):
    PRE_SESSION = "PRE_SESSION"
    IN_SESSION = "IN_SESSION"
    POST_SESSION = "POST_SESSION"
    WEEKLY_REVIEW = "WEEKLY_REVIEW"


@dataclass(frozen=True)
class QualityState:
    data_ready: bool = True
    freshness_ok: bool = True
    security_lock: bool = False


@dataclass(frozen=True)
class Task:
    task_id: str
    title: str
    target_module: str
    phase: WorkflowPhase
    blocked: bool = False
    reason: str | None = None


def block_reason(state: QualityState) -> str | None:
    if not state.data_ready:
        return "Veri hazır değil."
    if not state.freshness_ok:
        return "Veri güncelliği doğrulanmadı."
    if state.security_lock:
        return "Güvenlik kilidi aktif."
    return None
def quality_summary(state: QualityState) -> str:
    if not state.data_ready:
        return "Veri hazır değil."

    if not state.freshness_ok:
        return "Veri güncelliği doğrulanmadı."

    if state.security_lock:
        return "Güvenlik kilidi aktif."

    return "Kalite kontrolleri geçildi."

def build_tasks(
    *,
    phase: WorkflowPhase,
    quality: QualityState,
    shortlist_count: int = 0,
    open_position_count: int = 0,
) -> tuple[Task, ...]:
    reason=block_reason(quality)
    blocked=reason is not None

    if phase is WorkflowPhase.PRE_SESSION:
        return (
            Task("data_quality","Veri ve tazelik kontrolü","Günlük Operasyon Paneli",phase),
            Task("regime","Piyasa rejimini doğrula","Piyasa Rejimi",phase,blocked,reason),
            Task("news","Haber ve olay riskini kontrol et","Piyasa Haber, Olay ve Etki Merkezi",phase,blocked,reason),
            Task("pre_session","Seans öncesi bağlamı incele","Seans Öncesi Bağlam",phase,blocked,reason),
            Task("shortlist",f"Bugünkü kısa listeyi gözden geçir ({shortlist_count})","Momentum Keşif",phase,blocked,reason),
        )

    if phase is WorkflowPhase.IN_SESSION:
        return (
            Task("watchlist",f"Kısa listedeki adayları izle ({shortlist_count})","Momentum Keşif",phase,blocked,reason),
            Task("technical","İşleme yaklaşan adayları teknik olarak doğrula","Güncel Teknik Analiz",phase,blocked,reason),
            Task("risk","Yeni işlem risk kontrolünü uygula","İşlem Kayıp Analizi",phase,blocked,reason),
            Task("positions",f"Açık pozisyonları yönet ({open_position_count})","Gölge Portföy",phase),
        )

    if phase is WorkflowPhase.POST_SESSION:
        return (
            Task("positions",f"Açık pozisyonları güncelle ({open_position_count})","Gölge Portföy",phase),
            Task("outcomes","Sinyal sonuçlarını güncelle","Sinyal Sonuçları",phase),
            Task("journal","İşlem günlüğü ve kayıp analizini kontrol et","İşlem Kayıp Analizi",phase),
            Task("tomorrow","Ertesi gün aday listesini hazırla","Ön Yükseliş Hazırlık",phase,blocked,reason),
        )

    if phase is WorkflowPhase.WEEKLY_REVIEW:
        return (
            Task("regime","Haftalık piyasa rejimini doğrula","Piyasa Rejimi",phase,blocked,reason),
            Task("radar","Fırsat Radarı haftalık taramasını çalıştır","Fırsat Radarı",phase,blocked,reason),
            Task("momentum","Momentum adaylarını tara","Momentum Keşif",phase,blocked,reason),
            Task("prebreakout","Ön yükseliş adaylarını tara","Ön Yükseliş Hazırlık",phase,blocked,reason),
            Task("validation","Toplu doğrulamayı gözden geçir","Ön Yükseliş Toplu Doğrulama",phase,blocked,reason),
            Task("performance","Haftalık performansı incele","Haftalık Performans Raporu",phase),
        )

    raise ValueError(phase)
