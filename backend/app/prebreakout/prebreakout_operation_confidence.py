from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import json
from pathlib import Path
from typing import Any

from backend.app.prebreakout.prebreakout_operation_diagnosis import (
    OperationDiagnosisReport,
    RootCauseCategory,
)
from backend.app.prebreakout.prebreakout_operation_recovery import OperationRecoveryGuide


DEFAULT_OPERATION_CONFIDENCE_PATH = Path("backend/data/prebreakout_operation_confidence.json")


class DailyOperationDecision(str, Enum):
    RUN = "ÇALIŞTIR"
    WAIT = "BEKLE"
    REVIEW = "İNCELE"


@dataclass(frozen=True)
class OperationConfidenceReport:
    run_date: str
    score: int
    decision: DailyOperationDecision
    health_ready: bool
    error_count: int
    warning_count: int
    primary_category: RootCauseCategory
    reasons: tuple[str, ...]
    summary: str


def _health_counts(health_report: Any) -> tuple[bool, int, int]:
    if health_report is None:
        return False, 1, 0
    return (
        bool(getattr(health_report, "ready", False)),
        int(getattr(health_report, "error_count", 0) or 0),
        int(getattr(health_report, "warning_count", 0) or 0),
    )


def operasyon_guvenini_degerlendir(
    run_result: Any,
    diagnosis: OperationDiagnosisReport,
    recovery: OperationRecoveryGuide,
) -> OperationConfidenceReport:
    state = getattr(run_result, "state", None)
    status_obj = getattr(state, "status", "")
    status = str(getattr(status_obj, "value", status_obj) or "")
    run_date = str(getattr(state, "run_date", diagnosis.run_date) or diagnosis.run_date)
    health_ready, error_count, warning_count = _health_counts(
        getattr(run_result, "health_report", None)
    )

    score = 100
    reasons: list[str] = []

    if status == "COMPLETED":
        reasons.append("Günlük operasyon tamamlandı.")
    elif status == "SKIPPED":
        score -= 5
        reasons.append("Günlük operasyon daha önce tamamlandığı için tekrar çalıştırılmadı.")
    elif status == "BLOCKED":
        score -= 55
        reasons.append("Operasyon sistem sağlık kilidi nedeniyle bloke edildi.")
    elif status == "FAILED":
        score -= 45
        reasons.append("Günlük operasyon başarısız oldu.")
    else:
        score -= 25
        reasons.append(f"Operasyon durumu kesin değil: {status or 'BİLİNMİYOR'}.")

    score -= min(error_count * 20, 60)
    score -= min(warning_count * 5, 20)
    if error_count:
        reasons.append(f"Sistem sağlık raporunda {error_count} hata var.")
    if warning_count:
        reasons.append(f"Sistem sağlık raporunda {warning_count} uyarı var.")

    category_penalty = {
        RootCauseCategory.NONE: 0,
        RootCauseCategory.DATA: 35,
        RootCauseCategory.RECORD_INTEGRITY: 35,
        RootCauseCategory.HEALTH_LOCK: 30,
        RootCauseCategory.CALCULATION: 20,
        RootCauseCategory.PORTFOLIO: 15,
        RootCauseCategory.OPERATION: 20,
    }[diagnosis.primary_category]
    score -= category_penalty
    if diagnosis.primary_category is not RootCauseCategory.NONE:
        reasons.append(f"Birincil kök neden: {diagnosis.primary_category.value}.")

    score = max(0, min(100, int(score)))

    hard_wait_categories = {
        RootCauseCategory.DATA,
        RootCauseCategory.RECORD_INTEGRITY,
        RootCauseCategory.HEALTH_LOCK,
    }
    if (
        status == "BLOCKED"
        or diagnosis.primary_category in hard_wait_categories
        or (not health_ready and status != "SKIPPED")
    ):
        decision = DailyOperationDecision.WAIT
    elif status == "FAILED" or diagnosis.primary_category in {
        RootCauseCategory.CALCULATION,
        RootCauseCategory.PORTFOLIO,
        RootCauseCategory.OPERATION,
    }:
        decision = DailyOperationDecision.REVIEW
    elif score >= 80 and status in {"COMPLETED", "SKIPPED"}:
        decision = DailyOperationDecision.RUN
    else:
        decision = DailyOperationDecision.REVIEW

    if decision is DailyOperationDecision.RUN:
        summary = f"Operasyon güven skoru {score}/100 — ÇALIŞTIR. Mevcut kontroller günlük kullanıma izin veriyor."
    elif decision is DailyOperationDecision.WAIT:
        summary = f"Operasyon güven skoru {score}/100 — BEKLE. Kritik neden giderilmeden günlük operasyonu yeniden çalıştırma."
    else:
        retry_text = " Kontrollü yeniden deneme mümkündür." if recovery.safe_retry_allowed else " Önce manuel doğrulama gerekir."
        summary = f"Operasyon güven skoru {score}/100 — İNCELE.{retry_text}"

    return OperationConfidenceReport(
        run_date=run_date,
        score=score,
        decision=decision,
        health_ready=health_ready,
        error_count=error_count,
        warning_count=warning_count,
        primary_category=diagnosis.primary_category,
        reasons=tuple(reasons),
        summary=summary,
    )


def operasyon_guven_raporunu_kaydet(
    report: OperationConfidenceReport,
    path: str | Path = DEFAULT_OPERATION_CONFIDENCE_PATH,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(report)
    payload["decision"] = report.decision.value
    payload["primary_category"] = report.primary_category.value
    payload["reasons"] = list(report.reasons)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(target)


def operasyon_guvenini_tabloya_cevir(report: OperationConfidenceReport) -> list[dict[str, str]]:
    return [
        {"Alan": "Karar", "Değer": report.decision.value},
        {"Alan": "Güven skoru", "Değer": f"{report.score}/100"},
        {"Alan": "Sistem hazır", "Değer": "Evet" if report.health_ready else "Hayır"},
        {"Alan": "Kök neden", "Değer": report.primary_category.value},
        {"Alan": "Hata", "Değer": str(report.error_count)},
        {"Alan": "Uyarı", "Değer": str(report.warning_count)},
    ]
