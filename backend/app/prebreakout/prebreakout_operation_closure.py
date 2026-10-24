from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Iterable

from backend.app.prebreakout.prebreakout_alarm_journal import (
    AlarmHistoryRecord,
    AlarmResolutionStatus,
    DecisionJournalRecord,
)
from backend.app.prebreakout.prebreakout_operation_action_summary import (
    OperationActionSummary,
    UserActionPriority,
)


DEFAULT_OPERATION_CLOSURE_PATH = Path(
    "backend/data/prebreakout_operation_closure_summary.json"
)


@dataclass(frozen=True)
class DailyOperationClosureSummary:
    run_date: str
    decision: str
    confidence_score: int
    priority: str
    open_risk_count: int
    critical_open_risk_count: int
    open_risks: tuple[str, ...]
    pending_actions: tuple[str, ...]
    retry_allowed: bool
    decision_recorded: bool
    closure_ready: bool
    headline: str
    final_message: str


def _normalize(text: object) -> str:
    return str(text or "").strip()


def _unique(items: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        value = _normalize(item)
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return tuple(result)


def _is_critical_level(level: object) -> bool:
    normalized = _normalize(getattr(level, "value", level)).upper()
    return normalized in {"KRİTİK", "KRITIK", "CRITICAL"}


def _is_open_status(status: object) -> bool:
    value = getattr(status, "value", status)
    normalized = _normalize(value).upper()
    return normalized in {"AÇIK", "ACIK", "OPEN"}


def _decision_record_for_date(
    run_date: str,
    records: Iterable[DecisionJournalRecord],
) -> DecisionJournalRecord | None:
    matches = [record for record in records if record.run_date == run_date]
    return matches[-1] if matches else None


def gunluk_operasyon_kapanisini_olustur(
    action_summary: OperationActionSummary,
    alarm_history: Iterable[AlarmHistoryRecord],
    decision_journal: Iterable[DecisionJournalRecord] = (),
    *,
    max_open_risks: int = 5,
    max_pending_actions: int = 5,
) -> DailyOperationClosureSummary:
    """Gün sonu operasyon durumunu tek ve değişmez bir kapanış özetinde toplar.

    Kapanış özeti herhangi bir alarmı çözmez, karar kaydı yazmaz veya yeniden
    deneme başlatmaz. Yalnızca mevcut durumun gün sonunda kapanmaya hazır olup
    olmadığını gösterir.
    """
    run_date = action_summary.run_date
    open_records = tuple(
        record
        for record in alarm_history
        if record.run_date <= run_date and _is_open_status(record.status)
    )

    open_risks = _unique(
        f"{record.level} — {record.title}: {record.message}" for record in open_records
    )[: max(1, int(max_open_risks))]
    critical_count = sum(1 for record in open_records if _is_critical_level(record.level))

    pending_actions = _unique(action_summary.actions)[: max(1, int(max_pending_actions))]
    decision_record = _decision_record_for_date(run_date, decision_journal)
    decision_recorded = decision_record is not None

    priority_value = getattr(action_summary.priority, "value", action_summary.priority)
    decision_value = getattr(action_summary.decision, "value", action_summary.decision)

    has_stop_priority = action_summary.priority is UserActionPriority.STOP
    closure_ready = (
        critical_count == 0
        and not has_stop_priority
        and decision_recorded
    )

    if critical_count:
        headline = "Günlük operasyon kapanışı bekliyor"
        final_message = (
            f"{critical_count} kritik açık risk var. Kritik riskler çözülmeden "
            "günlük operasyonu kapatma."
        )
    elif has_stop_priority:
        headline = "Günlük operasyon kapanışı engellendi"
        final_message = (
            "Günlük karar DUR/BEKLE seviyesinde. Önerilen doğrulamalar "
            "tamamlanmadan kapanış yapma."
        )
    elif not decision_recorded:
        headline = "Günlük karar kaydı eksik"
        final_message = (
            "Operasyon kararı karar günlüğüne kaydedilmeden günü tamamlanmış sayma."
        )
    elif open_records:
        headline = "Günlük operasyon kapanabilir; açık riskleri izle"
        final_message = (
            f"{len(open_records)} açık risk izlenmeye devam ediyor; kritik risk yok. "
            "Günlük karar kaydı mevcut."
        )
    else:
        headline = "Günlük operasyon güvenle kapatılabilir"
        final_message = "Açık kritik risk yok ve günlük karar kaydı tamamlandı."

    return DailyOperationClosureSummary(
        run_date=run_date,
        decision=_normalize(decision_value),
        confidence_score=int(action_summary.score),
        priority=_normalize(priority_value),
        open_risk_count=len(open_records),
        critical_open_risk_count=critical_count,
        open_risks=open_risks,
        pending_actions=pending_actions,
        retry_allowed=bool(action_summary.retry_allowed),
        decision_recorded=decision_recorded,
        closure_ready=closure_ready,
        headline=headline,
        final_message=final_message,
    )


def operasyon_kapanis_ozetini_kaydet(
    summary: DailyOperationClosureSummary,
    path: str | Path = DEFAULT_OPERATION_CLOSURE_PATH,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    payload = asdict(summary)
    payload["open_risks"] = list(summary.open_risks)
    payload["pending_actions"] = list(summary.pending_actions)
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(target)


def operasyon_kapanis_ozetini_tabloya_cevir(
    summary: DailyOperationClosureSummary,
) -> list[dict[str, str]]:
    rows = [
        {"Alan": "Tarih", "Değer": summary.run_date},
        {"Alan": "Karar", "Değer": summary.decision},
        {"Alan": "Güven skoru", "Değer": f"{summary.confidence_score}/100"},
        {"Alan": "Öncelik", "Değer": summary.priority},
        {"Alan": "Açık risk", "Değer": str(summary.open_risk_count)},
        {"Alan": "Kritik açık risk", "Değer": str(summary.critical_open_risk_count)},
        {"Alan": "Karar günlüğü", "Değer": "Tamam" if summary.decision_recorded else "Eksik"},
        {"Alan": "Kapanış", "Değer": "Hazır" if summary.closure_ready else "Bekliyor"},
    ]
    rows.extend(
        {"Alan": f"Açık risk {index}", "Değer": value}
        for index, value in enumerate(summary.open_risks, start=1)
    )
    rows.extend(
        {"Alan": f"Bekleyen aksiyon {index}", "Değer": value}
        for index, value in enumerate(summary.pending_actions, start=1)
    )
    return rows
