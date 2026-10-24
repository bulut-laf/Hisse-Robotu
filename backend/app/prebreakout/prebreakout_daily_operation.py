from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from enum import Enum
import json
from pathlib import Path
from typing import Mapping, Sequence

from backend.app.prebreakout.prebreakout_candidate_lifecycle import CandidatePriceObservation
from backend.app.prebreakout.prebreakout_daily_monitor import (
    DEFAULT_DAILY_REPORT_PATH,
    DEFAULT_PAPER_TRADES_PATH,
    DailyMonitorResult,
    gunluk_izleme_akisini_calistir,
)
from backend.app.prebreakout.prebreakout_live_watch import DEFAULT_LIVE_WATCH_PATH
from backend.app.prebreakout.prebreakout_models import PreBreakoutResult
from backend.app.prebreakout.prebreakout_operational_health import (
    OperationalHealthReport,
    operasyon_sagligini_degerlendir,
)
from backend.app.prebreakout.prebreakout_operation_archive import (
    DEFAULT_OPERATION_ARCHIVE_PATH,
    gunluk_operasyon_arsiv_kaydi_olustur,
    gunluk_operasyon_arsivini_kaydet,
)
from backend.app.prebreakout.prebreakout_operation_followup import (
    gunluk_operasyon_takibini_guncelle,
)
from backend.app.prebreakout.prebreakout_alarm_journal import (
    DEFAULT_ALARM_HISTORY_PATH,
    DEFAULT_DECISION_JOURNAL_PATH,
)
from backend.app.prebreakout.prebreakout_threshold_policy import PreBreakoutThresholdPolicy
from backend.app.prebreakout.prebreakout_operation_diagnosis import (
    DEFAULT_OPERATION_DIAGNOSIS_PATH,
    operasyon_kok_nedenini_teshis_et,
    operasyon_teshisini_kaydet,
)
from backend.app.prebreakout.prebreakout_operation_recovery import (
    DEFAULT_OPERATION_RECOVERY_PATH,
    operasyon_kurtarma_rehberi_olustur,
    operasyon_kurtarma_rehberini_kaydet,
)


DEFAULT_DAILY_OPERATION_STATE_PATH = Path("backend/data/prebreakout_daily_operation_state.json")


class DailyOperationStatus(str, Enum):
    RUNNING = "RUNNING"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"


@dataclass(frozen=True)
class DailyOperationState:
    run_date: str
    status: DailyOperationStatus
    attempt_count: int
    completed_steps: tuple[str, ...] = ()
    failed_step: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class DailyOperationRunResult:
    state: DailyOperationState
    monitor_result: DailyMonitorResult | None
    health_report: OperationalHealthReport | None


def gunluk_operasyon_durumunu_yukle(
    path: str | Path = DEFAULT_DAILY_OPERATION_STATE_PATH,
) -> DailyOperationState | None:
    target = Path(path)
    if not target.exists():
        return None
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
        return DailyOperationState(
            run_date=str(payload["run_date"]),
            status=DailyOperationStatus(str(payload["status"])),
            attempt_count=int(payload["attempt_count"]),
            completed_steps=tuple(str(item) for item in payload.get("completed_steps", ())),
            failed_step=payload.get("failed_step"),
            error_message=payload.get("error_message"),
        )
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None


def gunluk_operasyon_durumunu_kaydet(
    state: DailyOperationState,
    path: str | Path = DEFAULT_DAILY_OPERATION_STATE_PATH,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(state)
    payload["status"] = state.status.value
    payload["completed_steps"] = list(state.completed_steps)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(target)


def _state(
    run_date: date,
    status: DailyOperationStatus,
    attempt_count: int,
    completed_steps: Sequence[str],
    *,
    failed_step: str | None = None,
    error_message: str | None = None,
) -> DailyOperationState:
    return DailyOperationState(
        run_date=run_date.isoformat(),
        status=status,
        attempt_count=attempt_count,
        completed_steps=tuple(completed_steps),
        failed_step=failed_step,
        error_message=error_message,
    )


def gunluk_operasyonu_guvenli_calistir(
    results: Sequence[PreBreakoutResult],
    run_date: date,
    policy: PreBreakoutThresholdPolicy,
    observations_by_symbol: Mapping[str, Sequence[CandidatePriceObservation]],
    *,
    state_path: str | Path = DEFAULT_DAILY_OPERATION_STATE_PATH,
    live_watch_path: str | Path = DEFAULT_LIVE_WATCH_PATH,
    lifecycle_path: str | Path = "backend/data/prebreakout_candidate_lifecycle.json",
    performance_path: str | Path = "backend/data/prebreakout_live_performance.json",
    paper_trades_path: str | Path = DEFAULT_PAPER_TRADES_PATH,
    daily_report_path: str | Path = DEFAULT_DAILY_REPORT_PATH,
    force: bool = False,
    archive_path: str | Path = DEFAULT_OPERATION_ARCHIVE_PATH,
    alarm_history_path: str | Path = DEFAULT_ALARM_HISTORY_PATH,
    decision_journal_path: str | Path = DEFAULT_DECISION_JOURNAL_PATH,
    diagnosis_path: str | Path = DEFAULT_OPERATION_DIAGNOSIS_PATH,
    recovery_path: str | Path = DEFAULT_OPERATION_RECOVERY_PATH,
) -> DailyOperationRunResult:
    """Sprint-103 günlük operasyonunu güvenli ve tekrar çalıştırılabilir biçimde yürütür.

    Başarısız bir koşu yeniden çalıştırıldığında Sprint-99 zincirinin tekrar-kayıt
    koruması kullanılır. Sağlık kontrolü hazır değilse koşu tamamlanmış sayılmaz.
    """
    previous = gunluk_operasyon_durumunu_yukle(state_path)
    if (
        previous is not None
        and previous.run_date == run_date.isoformat()
        and previous.status is DailyOperationStatus.COMPLETED
        and not force
    ):
        skipped = _state(
            run_date,
            DailyOperationStatus.SKIPPED,
            previous.attempt_count,
            previous.completed_steps,
        )
        return DailyOperationRunResult(skipped, None, None)

    attempt_count = (
        previous.attempt_count + 1
        if previous is not None and previous.run_date == run_date.isoformat()
        else 1
    )
    completed_steps: list[str] = []
    running = _state(run_date, DailyOperationStatus.RUNNING, attempt_count, completed_steps)
    gunluk_operasyon_durumunu_kaydet(running, state_path)

    try:
        monitor_result = gunluk_izleme_akisini_calistir(
            results,
            run_date,
            policy,
            observations_by_symbol,
            live_watch_path=live_watch_path,
            lifecycle_path=lifecycle_path,
            performance_path=performance_path,
            paper_trades_path=paper_trades_path,
            daily_report_path=daily_report_path,
        )
        completed_steps.append("GUNLUK_IZLEME")
    except Exception as error:
        failed = _state(
            run_date,
            DailyOperationStatus.FAILED,
            attempt_count,
            completed_steps,
            failed_step="GUNLUK_IZLEME",
            error_message=str(error),
        )
        gunluk_operasyon_durumunu_kaydet(failed, state_path)
        run_result = DailyOperationRunResult(failed, None, None)
        gunluk_operasyon_arsivini_kaydet(
            gunluk_operasyon_arsiv_kaydi_olustur(run_result), archive_path
        )
        gunluk_operasyon_takibini_guncelle(
            run_result,
            archive_path=archive_path,
            alarm_history_path=alarm_history_path,
            decision_journal_path=decision_journal_path,
        )
        diagnosis = operasyon_kok_nedenini_teshis_et(run_result)
        operasyon_teshisini_kaydet(diagnosis, diagnosis_path)
        operasyon_kurtarma_rehberini_kaydet(
            operasyon_kurtarma_rehberi_olustur(diagnosis), recovery_path
        )
        return run_result

    try:
        health_report = operasyon_sagligini_degerlendir(
            monitor_result,
            expected_run_date=run_date,
        )
        completed_steps.append("SISTEM_SAGLIGI")
    except Exception as error:
        failed = _state(
            run_date,
            DailyOperationStatus.FAILED,
            attempt_count,
            completed_steps,
            failed_step="SISTEM_SAGLIGI",
            error_message=str(error),
        )
        gunluk_operasyon_durumunu_kaydet(failed, state_path)
        run_result = DailyOperationRunResult(failed, monitor_result, None)
        gunluk_operasyon_arsivini_kaydet(
            gunluk_operasyon_arsiv_kaydi_olustur(run_result), archive_path
        )
        gunluk_operasyon_takibini_guncelle(
            run_result,
            archive_path=archive_path,
            alarm_history_path=alarm_history_path,
            decision_journal_path=decision_journal_path,
        )
        diagnosis = operasyon_kok_nedenini_teshis_et(run_result)
        operasyon_teshisini_kaydet(diagnosis, diagnosis_path)
        operasyon_kurtarma_rehberini_kaydet(
            operasyon_kurtarma_rehberi_olustur(diagnosis), recovery_path
        )
        return run_result

    if not health_report.ready:
        blocked = _state(
            run_date,
            DailyOperationStatus.BLOCKED,
            attempt_count,
            completed_steps,
            failed_step="SISTEM_SAGLIGI",
            error_message=f"{health_report.error_count} hata nedeniyle sistem hazır değil.",
        )
        gunluk_operasyon_durumunu_kaydet(blocked, state_path)
        run_result = DailyOperationRunResult(blocked, monitor_result, health_report)
        gunluk_operasyon_arsivini_kaydet(
            gunluk_operasyon_arsiv_kaydi_olustur(run_result), archive_path
        )
        gunluk_operasyon_takibini_guncelle(
            run_result,
            archive_path=archive_path,
            alarm_history_path=alarm_history_path,
            decision_journal_path=decision_journal_path,
        )
        diagnosis = operasyon_kok_nedenini_teshis_et(run_result)
        operasyon_teshisini_kaydet(diagnosis, diagnosis_path)
        operasyon_kurtarma_rehberini_kaydet(
            operasyon_kurtarma_rehberi_olustur(diagnosis), recovery_path
        )
        return run_result

    completed_steps.append("TAMAMLANDI")
    completed = _state(
        run_date,
        DailyOperationStatus.COMPLETED,
        attempt_count,
        completed_steps,
    )
    gunluk_operasyon_durumunu_kaydet(completed, state_path)
    run_result = DailyOperationRunResult(completed, monitor_result, health_report)
    gunluk_operasyon_arsivini_kaydet(
        gunluk_operasyon_arsiv_kaydi_olustur(run_result), archive_path
    )
    gunluk_operasyon_takibini_guncelle(
        run_result,
        archive_path=archive_path,
        alarm_history_path=alarm_history_path,
        decision_journal_path=decision_journal_path,
    )
    diagnosis = operasyon_kok_nedenini_teshis_et(run_result)
    operasyon_teshisini_kaydet(diagnosis, diagnosis_path)
    operasyon_kurtarma_rehberini_kaydet(
        operasyon_kurtarma_rehberi_olustur(diagnosis), recovery_path
    )
    return run_result
