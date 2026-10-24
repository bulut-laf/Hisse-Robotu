from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable
from zoneinfo import ZoneInfo

ISTANBUL = ZoneInfo("Europe/Istanbul")
PHASE_SCHEDULE = {"MORNING": (9, 0), "EVENING": (18, 20)}
PHASE_LABELS = {"MORNING": "09:00 Sabah", "EVENING": "18:20 Seans Sonu"}


@dataclass(frozen=True)
class OperationalCloseoutCheck:
    check: str
    status: str
    detail: str


@dataclass(frozen=True)
class OperationalCloseoutResult:
    run_date: str
    status: str
    checks: tuple[OperationalCloseoutCheck, ...]
    missing_links: tuple[str, ...]
    headline: str


def _phase_due(phase: str, now: datetime) -> bool:
    hour, minute = PHASE_SCHEDULE[phase]
    return (now.hour, now.minute) >= (hour, minute)


def _state_records(store: object) -> dict[str, object]:
    try:
        raw = store.load()
    except (OSError, ValueError, TypeError):
        return {}
    return dict(raw) if isinstance(raw, dict) else {}


def _audit_records(store: object) -> tuple[object, ...]:
    try:
        raw = store.load()
    except (OSError, ValueError, TypeError):
        return ()
    return tuple(raw or ())


def _archive_records(store: object) -> tuple[object, ...]:
    try:
        raw = store.load()
    except (OSError, ValueError, TypeError):
        return ()
    return tuple(raw or ())


def build_operational_closeout(
    *,
    now: datetime | None = None,
    scheduler_store: object | None = None,
    audit_store: object | None = None,
    archive_store: object | None = None,
) -> OperationalCloseoutResult:
    timestamp = now or datetime.now(ISTANBUL)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=ISTANBUL)
    timestamp = timestamp.astimezone(ISTANBUL)
    run_date = timestamp.date().isoformat()

    if scheduler_store is None:
        from backend.app.operations.daily_buy_decision_scheduled_runner import ScheduledRunJsonStore
        scheduler_store = ScheduledRunJsonStore()
    if audit_store is None:
        from backend.app.operations.daily_buy_decision_scheduled_runner import ScheduledRunAuditJsonStore
        audit_store = ScheduledRunAuditJsonStore()
    if archive_store is None:
        from backend.app.analysis.daily_buy_decision_output_archive import DecisionOutputArchiveJsonStore
        archive_store = DecisionOutputArchiveJsonStore()

    states = _state_records(scheduler_store)
    audits = _audit_records(audit_store)
    archives = _archive_records(archive_store)

    checks: list[OperationalCloseoutCheck] = []
    missing: list[str] = []
    waiting = False

    for phase in ("MORNING", "EVENING"):
        label = PHASE_LABELS[phase]
        due = _phase_due(phase, timestamp)
        state = states.get(f"{run_date}:{phase}")

        if not due:
            waiting = True
            checks.append(OperationalCloseoutCheck(label, "BEKLİYOR", "Planlanan çalışma saati henüz gelmedi."))
            continue

        if state is None:
            missing.append(f"{label}: zamanlanmış koşu kaydı yok")
            checks.append(OperationalCloseoutCheck(label, "EKSİK", "Zamanlanmış/recovery koşu kaydı bulunamadı."))
            continue

        state_status = str(getattr(state, "status", "")).upper()
        if state_status != "SUCCESS":
            detail = str(getattr(state, "detail", "")) or f"Durum: {state_status or '-'}"
            missing.append(f"{label}: koşu başarılı değil ({state_status or 'BİLİNMİYOR'})")
            checks.append(OperationalCloseoutCheck(label, "BAŞARISIZ", detail))
            continue

        candidate_count = int(getattr(state, "candidate_count", 0) or 0)
        checks.append(
            OperationalCloseoutCheck(
                label,
                "TAMAM",
                f"Koşu başarılı · {candidate_count} aday · AL: {', '.join(tuple(getattr(state, 'buy_symbols', ()) or ())) or '-'}",
            )
        )

        phase_audits = [
            item for item in audits
            if str(getattr(item, "run_date", "")) == run_date
            and str(getattr(item, "phase", "")).upper() == phase
            and str(getattr(item, "status", "")).upper() in {"SUCCESS", "SKIPPED"}
        ]
        if phase_audits:
            latest_audit = max(phase_audits, key=lambda item: str(getattr(item, "finished_at", "")))
            checks.append(
                OperationalCloseoutCheck(
                    f"{label} Audit",
                    "TAMAM",
                    f"{getattr(latest_audit, 'run_kind', 'SCHEDULED')} · {getattr(latest_audit, 'status', '-')}",
                )
            )
        else:
            missing.append(f"{label}: audit eşleşmesi yok")
            checks.append(OperationalCloseoutCheck(f"{label} Audit", "EKSİK", "Başarılı koşuyla eşleşen audit kaydı bulunamadı."))

        phase_archives = [
            item for item in archives
            if str(getattr(item, "run_date", "")) == run_date
            and str(getattr(item, "phase", "")).upper() == phase
        ]
        if phase_archives:
            latest_archive = max(phase_archives, key=lambda item: str(getattr(item, "created_at", "")))
            archive_count = len(tuple(getattr(latest_archive, "candidates", ()) or ()))
            if archive_count == candidate_count:
                checks.append(
                    OperationalCloseoutCheck(
                        f"{label} Karar Arşivi",
                        "TAMAM",
                        f"Scheduler ile aday sayısı eşleşiyor ({archive_count}).",
                    )
                )
            else:
                missing.append(f"{label}: scheduler/arşiv aday sayısı uyuşmuyor")
                checks.append(
                    OperationalCloseoutCheck(
                        f"{label} Karar Arşivi",
                        "UYUMSUZ",
                        f"Scheduler {candidate_count} aday, arşiv {archive_count} aday.",
                    )
                )
        else:
            missing.append(f"{label}: karar arşivi yok")
            checks.append(OperationalCloseoutCheck(f"{label} Karar Arşivi", "EKSİK", "Günlük karar çıktı arşivi bulunamadı."))

    if missing:
        status = "INCOMPLETE"
        headline = f"Operasyonel kapanış eksik: {len(missing)} halka doğrulanamadı."
    elif waiting:
        status = "WAITING"
        headline = "Bugünkü operasyon zinciri henüz tamamlanma saatini bekliyor."
    else:
        status = "COMPLETE"
        headline = "EOD → 09:00 karar zinciri, audit ve karar arşivi birlikte doğrulandı."

    return OperationalCloseoutResult(
        run_date=run_date,
        status=status,
        checks=tuple(checks),
        missing_links=tuple(missing),
        headline=headline,
    )


def operational_closeout_rows(result: OperationalCloseoutResult) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "Kontrol": item.check,
            "Durum": item.status,
            "Detay": item.detail,
        }
        for item in result.checks
    )
