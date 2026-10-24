from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import json
from pathlib import Path
from typing import Any, Iterable


DEFAULT_OPERATION_DIAGNOSIS_PATH = Path("backend/data/prebreakout_operation_diagnosis.json")


class RootCauseCategory(str, Enum):
    DATA = "VERI"
    RECORD_INTEGRITY = "KAYIT_BUTUNLUGU"
    HEALTH_LOCK = "SAGLIK_KILIDI"
    CALCULATION = "HESAPLAMA"
    PORTFOLIO = "PORTFOY"
    OPERATION = "OPERASYON"
    NONE = "YOK"


@dataclass(frozen=True)
class RootCauseFinding:
    category: RootCauseCategory
    code: str
    severity: str
    message: str


@dataclass(frozen=True)
class OperationDiagnosisReport:
    run_date: str
    status: str
    primary_category: RootCauseCategory
    findings: tuple[RootCauseFinding, ...]
    summary: str
    retry_recommended: bool


def _status_value(state: Any) -> str:
    value = getattr(state, "status", "")
    return str(getattr(value, "value", value) or "")


def _classify_health_check(check: Any) -> RootCauseCategory:
    code = str(getattr(check, "code", "")).lower()
    message = str(getattr(check, "message", "")).lower()
    if code in {"market_data", "run_date", "daily_report"} or "fiyat" in message or "veri" in message:
        return RootCauseCategory.DATA
    if code in {"lifecycle", "performance"}:
        return RootCauseCategory.RECORD_INTEGRITY
    if code in {"paper", "portfolio_summary"} or "portföy" in message or "portfoy" in message:
        return RootCauseCategory.PORTFOLIO
    if code == "measurability" or "hesap" in message or "ölç" in message:
        return RootCauseCategory.CALCULATION
    return RootCauseCategory.OPERATION


def operasyon_kok_nedenini_teshis_et(run_result: Any) -> OperationDiagnosisReport:
    state = getattr(run_result, "state", None)
    health = getattr(run_result, "health_report", None)
    run_date = str(getattr(state, "run_date", ""))
    status = _status_value(state)
    findings: list[RootCauseFinding] = []

    failed_step = str(getattr(state, "failed_step", "") or "")
    error_message = str(getattr(state, "error_message", "") or "")

    if status == "FAILED":
        category = RootCauseCategory.CALCULATION if failed_step == "GUNLUK_IZLEME" else RootCauseCategory.OPERATION
        findings.append(RootCauseFinding(category, failed_step or "OPERATION_FAILED", "HATA", error_message or "Günlük operasyon başarısız."))
    elif status == "BLOCKED":
        findings.append(RootCauseFinding(RootCauseCategory.HEALTH_LOCK, "OPERATION_BLOCKED", "HATA", error_message or "Sistem sağlık kilidinde."))

    if health is not None:
        for check in tuple(getattr(health, "checks", ()) or ()):
            level = str(getattr(getattr(check, "level", ""), "value", getattr(check, "level", "")))
            if level not in {"HATA", "UYARI"}:
                continue
            findings.append(RootCauseFinding(
                _classify_health_check(check),
                str(getattr(check, "code", "health_check")),
                level,
                str(getattr(check, "message", "")),
            ))

    if not findings:
        return OperationDiagnosisReport(
            run_date=run_date,
            status=status,
            primary_category=RootCauseCategory.NONE,
            findings=(),
            summary="Kök neden gerektiren operasyon hatası bulunmadı.",
            retry_recommended=False,
        )

    priority = {
        RootCauseCategory.DATA: 0,
        RootCauseCategory.RECORD_INTEGRITY: 1,
        RootCauseCategory.HEALTH_LOCK: 2,
        RootCauseCategory.CALCULATION: 3,
        RootCauseCategory.PORTFOLIO: 4,
        RootCauseCategory.OPERATION: 5,
        RootCauseCategory.NONE: 9,
    }
    primary = min((item.category for item in findings), key=lambda item: priority[item])
    error_count = sum(item.severity == "HATA" for item in findings)
    warning_count = sum(item.severity == "UYARI" for item in findings)
    summary = f"Birincil kök neden: {primary.value}. {error_count} hata, {warning_count} uyarı."
    retry_recommended = status in {"FAILED", "BLOCKED"} and primary not in {
        RootCauseCategory.DATA,
        RootCauseCategory.RECORD_INTEGRITY,
    }
    return OperationDiagnosisReport(run_date, status, primary, tuple(findings), summary, retry_recommended)


def operasyon_teshisini_kaydet(
    report: OperationDiagnosisReport,
    path: str | Path = DEFAULT_OPERATION_DIAGNOSIS_PATH,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(report)
    payload["primary_category"] = report.primary_category.value
    payload["findings"] = [
        {**asdict(item), "category": item.category.value} for item in report.findings
    ]
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(target)


def operasyon_teshisini_tabloya_cevir(report: OperationDiagnosisReport) -> list[dict[str, str]]:
    return [
        {
            "Kategori": item.category.value,
            "Kod": item.code,
            "Seviye": item.severity,
            "Açıklama": item.message,
        }
        for item in report.findings
    ]
