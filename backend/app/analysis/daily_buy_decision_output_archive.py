from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo

from backend.app.analysis.daily_buy_decision_cycle import (
    DailyBuyDecisionCandidate,
    DailyBuyDecisionSnapshot,
)

ISTANBUL = ZoneInfo("Europe/Istanbul")
DEFAULT_DECISION_OUTPUT_ARCHIVE_PATH = Path(
    "backend/data/daily_buy_decision_output_archive.json"
)


@dataclass(frozen=True)
class DecisionOutputArchiveRecord:
    run_date: str
    phase: str
    created_at: str
    candidates: tuple[DailyBuyDecisionCandidate, ...]


@dataclass(frozen=True)
class DailyDecisionArchiveDelta:
    current_date: str
    previous_date: str
    phase: str
    added: tuple[str, ...]
    removed: tuple[str, ...]
    decision_changes: int
    rank_changes: int
    current_buy: tuple[str, ...]
    previous_buy: tuple[str, ...]


class DecisionOutputArchiveJsonStore:
    """Daily EOD/Morning decision-board archive.

    One record per calendar date + phase is kept. Re-running the same phase for the
    same day replaces that phase's record while older days stay immutable.
    """

    def __init__(self, path: Path | str = DEFAULT_DECISION_OUTPUT_ARCHIVE_PATH) -> None:
        self.path = Path(path)

    def load(self) -> tuple[DecisionOutputArchiveRecord, ...]:
        if not self.path.exists():
            return ()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return ()
        rows = raw if isinstance(raw, list) else []
        result: list[DecisionOutputArchiveRecord] = []
        for payload in rows:
            try:
                item = dict(payload)
                candidates = tuple(
                    DailyBuyDecisionCandidate(**dict(candidate))
                    for candidate in item.get("candidates", ())
                )
                result.append(
                    DecisionOutputArchiveRecord(
                        run_date=str(item["run_date"]),
                        phase=str(item["phase"]).upper(),
                        created_at=str(item["created_at"]),
                        candidates=candidates,
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        return tuple(
            sorted(result, key=lambda value: (value.run_date, value.phase, value.created_at))
        )

    def save(self, record: DecisionOutputArchiveRecord) -> None:
        records = {
            (item.run_date, item.phase): item
            for item in self.load()
        }
        records[(record.run_date, record.phase)] = record
        ordered = sorted(
            records.values(),
            key=lambda value: (value.run_date, value.phase, value.created_at),
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(
                [
                    {
                        "run_date": item.run_date,
                        "phase": item.phase,
                        "created_at": item.created_at,
                        "candidates": [asdict(candidate) for candidate in item.candidates],
                    }
                    for item in ordered
                ],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def save_snapshot(self, snapshot: DailyBuyDecisionSnapshot) -> DecisionOutputArchiveRecord:
        created = datetime.fromisoformat(snapshot.created_at)
        if created.tzinfo is None:
            created = created.replace(tzinfo=ISTANBUL)
        run_date = created.astimezone(ISTANBUL).date().isoformat()
        record = DecisionOutputArchiveRecord(
            run_date=run_date,
            phase=str(snapshot.phase).upper(),
            created_at=snapshot.created_at,
            candidates=tuple(snapshot.candidates),
        )
        self.save(record)
        return record

    def latest(self, phase: str | None = None) -> DecisionOutputArchiveRecord | None:
        records = self.load()
        if phase is not None:
            wanted = str(phase).strip().upper()
            records = tuple(item for item in records if item.phase == wanted)
        if not records:
            return None
        return max(records, key=lambda item: (item.run_date, item.created_at))

    def by_date(self, run_date: str) -> tuple[DecisionOutputArchiveRecord, ...]:
        wanted = str(run_date).strip()
        return tuple(item for item in self.load() if item.run_date == wanted)


def _symbols(record: DecisionOutputArchiveRecord) -> tuple[str, ...]:
    return tuple(item.symbol for item in record.candidates)


def _buy_symbols(record: DecisionOutputArchiveRecord) -> tuple[str, ...]:
    return tuple(
        item.symbol
        for item in record.candidates
        if str(item.decision or "").strip().upper() == "AL"
    )


def compare_decision_archive_days(
    current: DecisionOutputArchiveRecord,
    previous: DecisionOutputArchiveRecord,
) -> DailyDecisionArchiveDelta:
    if current.phase != previous.phase:
        raise ValueError("Karşılaştırma için aynı faz gerekir.")

    current_by_symbol = {item.symbol: item for item in current.candidates}
    previous_by_symbol = {item.symbol: item for item in previous.candidates}
    current_symbols = _symbols(current)
    previous_symbols = _symbols(previous)

    shared = set(current_by_symbol).intersection(previous_by_symbol)
    decision_changes = sum(
        1
        for symbol in shared
        if current_by_symbol[symbol].decision != previous_by_symbol[symbol].decision
    )
    rank_changes = sum(
        1
        for symbol in shared
        if current_by_symbol[symbol].rank != previous_by_symbol[symbol].rank
    )

    return DailyDecisionArchiveDelta(
        current_date=current.run_date,
        previous_date=previous.run_date,
        phase=current.phase,
        added=tuple(symbol for symbol in current_symbols if symbol not in previous_by_symbol),
        removed=tuple(symbol for symbol in previous_symbols if symbol not in current_by_symbol),
        decision_changes=decision_changes,
        rank_changes=rank_changes,
        current_buy=_buy_symbols(current),
        previous_buy=_buy_symbols(previous),
    )


def latest_daily_compare(
    records: Iterable[DecisionOutputArchiveRecord],
    *,
    phase: str = "MORNING",
) -> DailyDecisionArchiveDelta | None:
    wanted = str(phase).strip().upper()
    filtered = sorted(
        (item for item in records if item.phase == wanted),
        key=lambda item: (item.run_date, item.created_at),
        reverse=True,
    )
    if len(filtered) < 2:
        return None
    return compare_decision_archive_days(filtered[0], filtered[1])


def decision_output_archive_rows(
    records: Iterable[DecisionOutputArchiveRecord],
    *,
    limit: int = 30,
) -> tuple[dict[str, object], ...]:
    ordered = sorted(
        records,
        key=lambda item: (item.run_date, item.created_at, item.phase),
        reverse=True,
    )
    rows: list[dict[str, object]] = []
    for item in ordered[: max(0, int(limit))]:
        decisions = {"AL": 0, "BEKLE": 0, "İŞLEM YOK": 0}
        for candidate in item.candidates:
            value = str(candidate.decision or "-").strip().upper()
            if value in decisions:
                decisions[value] += 1
        rows.append(
            {
                "Tarih": item.run_date,
                "Faz": item.phase,
                "Oluşturma": item.created_at,
                "Top-5": ", ".join(_symbols(item)) or "-",
                "AL": decisions["AL"],
                "BEKLE": decisions["BEKLE"],
                "İŞLEM YOK": decisions["İŞLEM YOK"],
            }
        )
    return tuple(rows)


def decision_output_board_rows(
    record: DecisionOutputArchiveRecord,
) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "Sıra": item.rank,
            "Hisse": item.symbol,
            "Karar": item.decision or "-",
            "Kaynak": item.selection_source,
            "Sıra Δ": item.rank_change if item.rank_change is not None else "-",
            "Giriş hazırlığı": item.entry_readiness,
            "Sıçrama kalite": item.jump_quality,
            "Teknik skor": item.technical_score,
        }
        for item in record.candidates
    )


def daily_decision_archive_delta_rows(
    delta: DailyDecisionArchiveDelta,
) -> tuple[dict[str, object], ...]:
    return (
        {
            "Faz": delta.phase,
            "Önceki gün": delta.previous_date,
            "Güncel gün": delta.current_date,
            "Yeni": ", ".join(delta.added) or "-",
            "Çıkan": ", ".join(delta.removed) or "-",
            "Karar değişimi": delta.decision_changes,
            "Sıra değişimi": delta.rank_changes,
            "Önceki AL": ", ".join(delta.previous_buy) or "-",
            "Güncel AL": ", ".join(delta.current_buy) or "-",
        },
    )


def decision_output_audit_rows(
    records: Iterable[DecisionOutputArchiveRecord],
    audit_records: Iterable[object],
    *,
    limit: int = 30,
) -> tuple[dict[str, object], ...]:
    """Join archived decision outputs with the latest scheduler audit for date/phase."""
    audit_by_key: dict[tuple[str, str], object] = {}
    for audit in audit_records:
        key = (
            str(getattr(audit, "run_date", "")),
            str(getattr(audit, "phase", "")).upper(),
        )
        if not all(key):
            continue
        existing = audit_by_key.get(key)
        if existing is None or str(getattr(audit, "finished_at", "")) >= str(
            getattr(existing, "finished_at", "")
        ):
            audit_by_key[key] = audit

    rows: list[dict[str, object]] = []
    ordered = sorted(
        records,
        key=lambda item: (item.run_date, item.created_at, item.phase),
        reverse=True,
    )
    for item in ordered[: max(0, int(limit))]:
        audit = audit_by_key.get((item.run_date, item.phase))
        rows.append(
            {
                "Tarih": item.run_date,
                "Faz": item.phase,
                "Top-5": ", ".join(_symbols(item)) or "-",
                "AL": ", ".join(_buy_symbols(item)) or "-",
                "Audit": str(getattr(audit, "status", "EŞLEŞME YOK")),
                "Koşu türü": str(getattr(audit, "run_kind", "-")) if audit else "-",
                "Audit bitiş": str(getattr(audit, "finished_at", "-")) if audit else "-",
            }
        )
    return tuple(rows)
