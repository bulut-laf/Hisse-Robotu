from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import json
from pathlib import Path
from typing import Iterable

from backend.app.prebreakout.prebreakout_operation_alerts import OperationTrendAlarm


DEFAULT_ALARM_HISTORY_PATH = Path("backend/data/prebreakout_alarm_history.jsonl")
DEFAULT_DECISION_JOURNAL_PATH = Path("backend/data/prebreakout_decision_journal.jsonl")


class AlarmResolutionStatus(str, Enum):
    OPEN = "AÇIK"
    RESOLVED = "ÇÖZÜLDÜ"


@dataclass(frozen=True)
class AlarmHistoryRecord:
    alarm_id: str
    run_date: str
    code: str
    level: str
    title: str
    message: str
    status: AlarmResolutionStatus
    resolved_date: str | None = None
    resolution_note: str = ""


@dataclass(frozen=True)
class DecisionJournalRecord:
    run_date: str
    decision: str
    rationale: str
    alarm_codes: tuple[str, ...] = ()


def _alarm_id(run_date: str, code: str) -> str:
    return f"{run_date}:{code}"


def _atomic_write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    content = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows
    )
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def alarm_gecmisini_yukle(
    path: str | Path = DEFAULT_ALARM_HISTORY_PATH,
) -> tuple[AlarmHistoryRecord, ...]:
    target = Path(path)
    if not target.exists():
        return ()
    records: list[AlarmHistoryRecord] = []
    try:
        for line in target.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            payload["status"] = AlarmResolutionStatus(payload["status"])
            records.append(AlarmHistoryRecord(**payload))
    except (OSError, ValueError, TypeError, json.JSONDecodeError, KeyError):
        return ()
    return tuple(sorted(records, key=lambda item: (item.run_date, item.code)))


def gunluk_alarmlari_arsivle(
    run_date: str,
    alarms: Iterable[OperationTrendAlarm],
    path: str | Path = DEFAULT_ALARM_HISTORY_PATH,
) -> tuple[AlarmHistoryRecord, ...]:
    target = Path(path)
    existing = {item.alarm_id: item for item in alarm_gecmisini_yukle(target)}
    current_ids: set[str] = set()

    for alarm in alarms:
        alarm_id = _alarm_id(run_date, alarm.code)
        current_ids.add(alarm_id)
        previous = existing.get(alarm_id)
        existing[alarm_id] = AlarmHistoryRecord(
            alarm_id=alarm_id,
            run_date=run_date,
            code=alarm.code,
            level=alarm.level.value,
            title=alarm.title,
            message=alarm.message,
            status=(previous.status if previous else AlarmResolutionStatus.OPEN),
            resolved_date=(previous.resolved_date if previous else None),
            resolution_note=(previous.resolution_note if previous else ""),
        )

    rows = [existing[key] for key in sorted(existing)]
    _atomic_write_jsonl(target, (asdict(item) for item in rows))
    return tuple(rows)


def alarmi_cozuldu_isaretle(
    alarm_id: str,
    resolved_date: str,
    note: str,
    path: str | Path = DEFAULT_ALARM_HISTORY_PATH,
) -> AlarmHistoryRecord:
    target = Path(path)
    existing = {item.alarm_id: item for item in alarm_gecmisini_yukle(target)}
    if alarm_id not in existing:
        raise KeyError(f"Alarm bulunamadı: {alarm_id}")
    current = existing[alarm_id]
    updated = AlarmHistoryRecord(
        alarm_id=current.alarm_id,
        run_date=current.run_date,
        code=current.code,
        level=current.level,
        title=current.title,
        message=current.message,
        status=AlarmResolutionStatus.RESOLVED,
        resolved_date=resolved_date,
        resolution_note=note.strip(),
    )
    existing[alarm_id] = updated
    rows = [existing[key] for key in sorted(existing)]
    _atomic_write_jsonl(target, (asdict(item) for item in rows))
    return updated


def karar_gunlugunu_yukle(
    path: str | Path = DEFAULT_DECISION_JOURNAL_PATH,
) -> tuple[DecisionJournalRecord, ...]:
    target = Path(path)
    if not target.exists():
        return ()
    records: list[DecisionJournalRecord] = []
    try:
        for line in target.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            payload["alarm_codes"] = tuple(payload.get("alarm_codes", ()))
            records.append(DecisionJournalRecord(**payload))
    except (OSError, ValueError, TypeError, json.JSONDecodeError, KeyError):
        return ()
    return tuple(sorted(records, key=lambda item: item.run_date))


def gunluk_karari_kaydet(
    record: DecisionJournalRecord,
    path: str | Path = DEFAULT_DECISION_JOURNAL_PATH,
) -> None:
    target = Path(path)
    existing = {item.run_date: item for item in karar_gunlugunu_yukle(target)}
    existing[record.run_date] = DecisionJournalRecord(
        run_date=record.run_date,
        decision=record.decision.strip(),
        rationale=record.rationale.strip(),
        alarm_codes=tuple(dict.fromkeys(record.alarm_codes)),
    )
    rows = [existing[key] for key in sorted(existing)]
    _atomic_write_jsonl(target, (asdict(item) for item in rows))


def alarm_gecmisini_tabloya_cevir(
    records: Iterable[AlarmHistoryRecord],
) -> list[dict[str, str]]:
    return [
        {
            "Tarih": item.run_date,
            "Seviye": item.level,
            "Alarm": item.title,
            "Durum": item.status.value,
            "Çözüm tarihi": item.resolved_date or "",
            "Çözüm notu": item.resolution_note,
        }
        for item in records
    ]


def karar_gunlugunu_tabloya_cevir(
    records: Iterable[DecisionJournalRecord],
) -> list[dict[str, str]]:
    return [
        {
            "Tarih": item.run_date,
            "Karar": item.decision,
            "Gerekçe": item.rationale,
            "İlgili alarmlar": ", ".join(item.alarm_codes),
        }
        for item in records
    ]
