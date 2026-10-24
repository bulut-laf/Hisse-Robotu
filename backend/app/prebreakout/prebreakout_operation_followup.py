from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.app.prebreakout.prebreakout_alarm_journal import (
    DEFAULT_ALARM_HISTORY_PATH,
    DEFAULT_DECISION_JOURNAL_PATH,
    DecisionJournalRecord,
    alarm_gecmisini_yukle,
    gunluk_alarmlari_arsivle,
    gunluk_karari_kaydet,
    karar_gunlugunu_yukle,
)
from backend.app.prebreakout.prebreakout_operation_alerts import (
    OperationExecutiveSummary,
    OperationTrendAlarm,
    OperationTrendAlarmLevel,
    gunluk_yonetici_ozetini_hesapla,
)
from backend.app.prebreakout.prebreakout_operation_archive import (
    DEFAULT_OPERATION_ARCHIVE_PATH,
    DailyOperationArchiveRecord,
    gunluk_operasyon_arsiv_kaydi_olustur,
    gunluk_operasyon_arsivini_yukle,
)


PENDING_DECISION = "KARAR_BEKLIYOR"


@dataclass(frozen=True)
class DailyOperationFollowUpResult:
    archive_record: DailyOperationArchiveRecord
    executive_summary: OperationExecutiveSummary | None
    alarm_count: int
    decision: DecisionJournalRecord


def _run_status_alarm(record: DailyOperationArchiveRecord) -> OperationTrendAlarm | None:
    status = record.status.upper()
    if status == "FAILED":
        return OperationTrendAlarm(
            code="OPERATION_FAILED",
            level=OperationTrendAlarmLevel.CRITICAL,
            title="Günlük operasyon başarısız",
            message="Günlük operasyon tamamlanamadı; hata nedeni incelenmeli ve güvenli yeniden deneme yapılmalı.",
        )
    if status == "BLOCKED":
        return OperationTrendAlarm(
            code="OPERATION_BLOCKED",
            level=OperationTrendAlarmLevel.CRITICAL,
            title="Günlük operasyon sağlık kilidinde",
            message="Operasyon tamamlandı sayılmadı; sistem sağlığı düzelmeden karar üretilmemeli.",
        )
    return None


def _pending_decision(
    record: DailyOperationArchiveRecord,
    summary: OperationExecutiveSummary | None,
    alarms: tuple[OperationTrendAlarm, ...],
) -> DecisionJournalRecord:
    if summary is None:
        rationale = f"{record.run_date}: günlük operasyon kaydı mevcut; karar bekleniyor."
    else:
        rationale = f"{summary.headline}. {summary.detail}"
    return DecisionJournalRecord(
        run_date=record.run_date,
        decision=PENDING_DECISION,
        rationale=rationale,
        alarm_codes=tuple(dict.fromkeys(alarm.code for alarm in alarms)),
    )


def gunluk_operasyon_takibini_guncelle(
    run_result: Any,
    *,
    archive_path: str | Path = DEFAULT_OPERATION_ARCHIVE_PATH,
    alarm_history_path: str | Path = DEFAULT_ALARM_HISTORY_PATH,
    decision_journal_path: str | Path = DEFAULT_DECISION_JOURNAL_PATH,
) -> DailyOperationFollowUpResult:
    """Arşivlenmiş günlük operasyonun alarm ve karar günlüğünü senkronize eder.

    Günlük operasyon arşivi Sprint-104 tarafından yazılmış olmalıdır. Bu fonksiyon
    aynı gün tekrar çağrılsa da alarm geçmişini çoğaltmaz ve kullanıcının daha önce
    verdiği kararı `KARAR_BEKLIYOR` ile ezmez.
    """
    current = gunluk_operasyon_arsiv_kaydi_olustur(run_result)
    archive_rows = tuple(
        row for row in gunluk_operasyon_arsivini_yukle(archive_path) if row.run_date <= current.run_date
    )

    summary = gunluk_yonetici_ozetini_hesapla(archive_rows)
    trend_alarms = tuple(summary.alarms) if summary is not None else ()
    status_alarm = _run_status_alarm(current)
    alarms = (
        trend_alarms
        if status_alarm is None
        else (status_alarm,) + tuple(a for a in trend_alarms if a.code != status_alarm.code)
    )

    history = gunluk_alarmlari_arsivle(current.run_date, alarms, alarm_history_path)

    decisions = {item.run_date: item for item in karar_gunlugunu_yukle(decision_journal_path)}
    decision = decisions.get(current.run_date)
    if decision is None:
        decision = _pending_decision(current, summary, alarms)
        gunluk_karari_kaydet(decision, decision_journal_path)

    todays_alarm_count = sum(1 for item in history if item.run_date == current.run_date)
    return DailyOperationFollowUpResult(
        archive_record=current,
        executive_summary=summary,
        alarm_count=todays_alarm_count,
        decision=decision,
    )
