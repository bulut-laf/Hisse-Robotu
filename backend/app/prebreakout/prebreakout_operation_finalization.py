from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import json
from pathlib import Path
from typing import Iterable

from backend.app.prebreakout.prebreakout_operation_closure import DailyOperationClosureSummary


DEFAULT_OPERATION_FINALIZATION_PATH = Path(
    "backend/data/prebreakout_operation_finalization.json"
)


class OperationPhaseStatus(str, Enum):
    READY = "HAZIR"
    BLOCKED = "BLOKE"


@dataclass(frozen=True)
class OperationSystemCheck:
    code: str
    title: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class OperationFinalizationReport:
    run_date: str
    status: OperationPhaseStatus
    passed_check_count: int
    failed_check_count: int
    checks: tuple[OperationSystemCheck, ...]
    closure_ready: bool
    final_message: str


_REQUIRED_MODULES: tuple[tuple[str, str], ...] = (
    ("DAILY", "backend/app/prebreakout/prebreakout_daily_operation.py"),
    ("ALARM", "backend/app/prebreakout/prebreakout_alarm_journal.py"),
    ("DIAG", "backend/app/prebreakout/prebreakout_operation_diagnosis.py"),
    ("RECOVERY", "backend/app/prebreakout/prebreakout_operation_recovery.py"),
    ("CONFIDENCE", "backend/app/prebreakout/prebreakout_operation_confidence.py"),
    ("ACTION", "backend/app/prebreakout/prebreakout_operation_action_summary.py"),
    ("CLOSURE", "backend/app/prebreakout/prebreakout_operation_closure.py"),
)


def _module_checks(project_root: str | Path = ".") -> tuple[OperationSystemCheck, ...]:
    root = Path(project_root)
    checks: list[OperationSystemCheck] = []
    for code, relative in _REQUIRED_MODULES:
        exists = (root / relative).is_file()
        checks.append(
            OperationSystemCheck(
                code=f"MOD_{code}",
                title=f"{code} modülü",
                passed=exists,
                detail="Mevcut" if exists else f"Eksik: {relative}",
            )
        )
    return tuple(checks)


def operasyon_fazini_sonlandir(
    closure: DailyOperationClosureSummary,
    *,
    project_root: str | Path = ".",
    extra_checks: Iterable[OperationSystemCheck] = (),
) -> OperationFinalizationReport:
    """Operasyon katmanını değiştirmeden final sağlık kontrolü üretir.

    Bu fonksiyon hiçbir alarmı çözmez, veri dosyasını onarmaz ve günlük
    operasyonu yeniden çalıştırmaz. Yalnızca kapanış özetini ve zorunlu
    modüllerin varlığını doğrular.
    """
    checks = list(_module_checks(project_root))
    checks.append(
        OperationSystemCheck(
            code="CLOSURE_READY",
            title="Günlük operasyon kapanışı",
            passed=bool(closure.closure_ready),
            detail=(
                "Kapanış hazır"
                if closure.closure_ready
                else f"Kapanış bekliyor: {closure.final_message}"
            ),
        )
    )
    checks.append(
        OperationSystemCheck(
            code="CRITICAL_RISK",
            title="Kritik açık risk",
            passed=closure.critical_open_risk_count == 0,
            detail=(
                "Kritik açık risk yok"
                if closure.critical_open_risk_count == 0
                else f"{closure.critical_open_risk_count} kritik açık risk var"
            ),
        )
    )
    checks.extend(tuple(extra_checks))

    failed = sum(1 for item in checks if not item.passed)
    passed = len(checks) - failed
    status = OperationPhaseStatus.READY if failed == 0 else OperationPhaseStatus.BLOCKED
    final_message = (
        "Operasyon katmanı final kontrolünden geçti; faz kapatılabilir."
        if status is OperationPhaseStatus.READY
        else f"Operasyon katmanı kapatılamaz; {failed} kontrol başarısız."
    )
    return OperationFinalizationReport(
        run_date=closure.run_date,
        status=status,
        passed_check_count=passed,
        failed_check_count=failed,
        checks=tuple(checks),
        closure_ready=bool(closure.closure_ready),
        final_message=final_message,
    )


def operasyon_final_raporunu_kaydet(
    report: OperationFinalizationReport,
    path: str | Path = DEFAULT_OPERATION_FINALIZATION_PATH,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    payload = asdict(report)
    payload["status"] = report.status.value
    payload["checks"] = [asdict(item) for item in report.checks]
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(target)


def operasyon_final_raporunu_tabloya_cevir(
    report: OperationFinalizationReport,
) -> list[dict[str, str]]:
    rows = [
        {"Alan": "Tarih", "Değer": report.run_date},
        {"Alan": "Final durum", "Değer": report.status.value},
        {"Alan": "Başarılı kontrol", "Değer": str(report.passed_check_count)},
        {"Alan": "Başarısız kontrol", "Değer": str(report.failed_check_count)},
        {"Alan": "Kapanış", "Değer": "Hazır" if report.closure_ready else "Bekliyor"},
    ]
    rows.extend(
        {
            "Alan": check.title,
            "Değer": f"{'OK' if check.passed else 'HATA'} — {check.detail}",
        }
        for check in report.checks
    )
    return rows
