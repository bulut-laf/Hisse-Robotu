from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import argparse
import json
from pathlib import Path
from typing import Protocol
from zoneinfo import ZoneInfo

ISTANBUL = ZoneInfo("Europe/Istanbul")
DEFAULT_STATE_PATH = Path("backend/data/daily_buy_decision_scheduler_state.json")
DEFAULT_AUDIT_PATH = Path("backend/data/daily_buy_decision_scheduler_audit.json")
VALID_PHASES = ("EVENING", "MORNING")
PHASE_SCHEDULE = {"MORNING": (9, 0), "EVENING": (18, 20)}


@dataclass(frozen=True)
class ScheduledRunRecord:
    phase: str
    run_date: str
    started_at: str
    finished_at: str
    status: str
    candidate_count: int
    buy_symbols: tuple[str, ...]
    detail: str = ""
    run_kind: str = "SCHEDULED"


class ScheduledRunRuntime(Protocol):
    def operation_summary(self) -> object: ...
    def scan(self) -> object: ...
    def visibility_contexts(self) -> tuple[object, ...]: ...
    def candidate_snapshot(self, operation_summary: object, scan_result: object, visibility_contexts: tuple[object, ...]) -> object: ...
    def decisions(self, cards: tuple[object, ...]) -> tuple[object, ...]: ...
    def persist_decision_snapshot(self, cards: tuple[object, ...], decisions: tuple[object, ...], phase: str, now: datetime) -> None: ...


class ScheduledRunJsonStore:
    def __init__(self, path: Path | str = DEFAULT_STATE_PATH) -> None:
        self.path = Path(path)

    def load(self) -> dict[str, ScheduledRunRecord]:
        if not self.path.exists():
            return {}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return {}
        result: dict[str, ScheduledRunRecord] = {}
        for key, payload in dict(raw).items():
            try:
                payload = dict(payload)
                payload["buy_symbols"] = tuple(payload.get("buy_symbols", ()))
                result[str(key)] = ScheduledRunRecord(**payload)
            except (TypeError, ValueError):
                continue
        return result

    def save(self, record: ScheduledRunRecord) -> None:
        records = self.load()
        key = f"{record.run_date}:{record.phase}"
        records[key] = record
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {key: asdict(value) for key, value in sorted(records.items())}
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def latest(self, phase: str | None = None) -> ScheduledRunRecord | None:
        records = self.load().values()
        if phase is not None:
            wanted = str(phase).strip().upper()
            records = [item for item in records if item.phase == wanted]
        records = list(records)
        if not records:
            return None
        return max(records, key=lambda item: (item.run_date, item.finished_at))

    def latest_success(self, phase: str | None = None) -> ScheduledRunRecord | None:
        records = [item for item in self.load().values() if item.status == "SUCCESS"]
        if phase is not None:
            wanted = str(phase).strip().upper()
            records = [item for item in records if item.phase == wanted]
        if not records:
            return None
        return max(records, key=lambda item: (item.run_date, item.finished_at))


class ScheduledRunAuditJsonStore:
    """Append-only audit trail for every scheduled/recovery attempt."""

    def __init__(self, path: Path | str = DEFAULT_AUDIT_PATH) -> None:
        self.path = Path(path)

    def load(self) -> tuple[ScheduledRunRecord, ...]:
        if not self.path.exists():
            return ()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return ()
        rows = raw if isinstance(raw, list) else []
        result: list[ScheduledRunRecord] = []
        for payload in rows:
            try:
                item = dict(payload)
                item["buy_symbols"] = tuple(item.get("buy_symbols", ()))
                result.append(ScheduledRunRecord(**item))
            except (TypeError, ValueError):
                continue
        return tuple(result)

    def append(self, record: ScheduledRunRecord) -> None:
        records = list(self.load())
        records.append(record)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps([asdict(item) for item in records], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def latest(self, limit: int = 50) -> tuple[ScheduledRunRecord, ...]:
        if limit <= 0:
            return ()
        records = sorted(
            self.load(),
            key=lambda item: (item.run_date, item.finished_at, item.phase),
            reverse=True,
        )
        return tuple(records[:limit])


def _normalize_phase(phase: str) -> str:
    value = str(phase or "").strip().upper()
    if value not in VALID_PHASES:
        raise ValueError("phase EVENING veya MORNING olmalıdır.")
    return value


def _default_runtime() -> ScheduledRunRuntime:
    from backend.app.analysis.daily_buy_decision_closeout import build_daily_buy_decisions
    from backend.app.analysis.daily_buy_decision_cycle import (
        DailyBuyDecisionJsonStore,
        build_daily_buy_decision_snapshot,
    )
    from backend.app.analysis.daily_operation_panel import build_daily_operation_summary
    from backend.app.analysis.morning_operation_snapshot import build_morning_operation_snapshot
    from backend.app.analysis.ranking_visibility_service import build_current_visibility_context
    from backend.app.analysis.market_scanner import MarketScanRequest
    from backend.app.compliance.dashboard_market_scanner_source_factory import build_dashboard_market_scanner
    from backend.app.data.delayed_data_pilot import DelayedDataPilotStore
    from backend.app.analysis.signal_outcome_tracking import SignalOutcomeJsonStore
    from backend.app.history.trade_journal import TradeJournalStore, TradeJournalError
    from backend.app.analysis.shadow_portfolio import ShadowPortfolioStore, ShadowPortfolioError

    class Runtime:
        def operation_summary(self) -> object:
            pilot_store = DelayedDataPilotStore()
            signal_store = SignalOutcomeJsonStore()
            trade_store = TradeJournalStore()
            shadow_store = ShadowPortfolioStore()
            try:
                trades = trade_store.list_records()
            except TradeJournalError:
                trades = ()
            try:
                shadow = shadow_store.list()
            except ShadowPortfolioError:
                shadow = ()
            return build_daily_operation_summary(
                pilot_records=pilot_store.list(),
                signal_outcomes=signal_store.list(),
                trade_records=trades,
                shadow_positions=shadow,
            )

        def scan(self) -> object:
            service = build_dashboard_market_scanner(vbts_hard_block=False)
            request = MarketScanRequest(
                evren="BIST 100",
                profil_adi="dengeli",
                maksimum_aday=15,
                ozel_semboller=(),
                internetten_evren_guncelle=True,
                sektor_baglami_aktif=True,
            )
            return service.calistir(request)

        def visibility_contexts(self) -> tuple[object, ...]:
            try:
                return tuple(build_current_visibility_context())
            except Exception:
                return ()

        def candidate_snapshot(self, operation_summary: object, scan_result: object, visibility_contexts: tuple[object, ...]) -> object:
            return build_morning_operation_snapshot(
                operation_summary=operation_summary,
                scan_result=scan_result,
                visibility_contexts=visibility_contexts,
                limit=5,
            )

        def decisions(self, cards: tuple[object, ...]) -> tuple[object, ...]:
            return tuple(build_daily_buy_decisions(cards))

        def persist_decision_snapshot(self, cards: tuple[object, ...], decisions: tuple[object, ...], phase: str, now: datetime) -> None:
            snapshot = build_daily_buy_decision_snapshot(
                cards,
                phase=phase,
                now=now,
                decisions=decisions,
            )
            DailyBuyDecisionJsonStore().save(snapshot)
            from backend.app.analysis.daily_buy_decision_output_archive import (
                DecisionOutputArchiveJsonStore,
            )
            DecisionOutputArchiveJsonStore().save_snapshot(snapshot)

    return Runtime()


def execute_scheduled_run(
    phase: str,
    *,
    now: datetime | None = None,
    runtime: ScheduledRunRuntime | None = None,
    store: ScheduledRunJsonStore | None = None,
    force: bool = False,
    audit_store: ScheduledRunAuditJsonStore | None = None,
    run_kind: str = "SCHEDULED",
) -> ScheduledRunRecord:
    phase_value = _normalize_phase(phase)
    timestamp = (now or datetime.now(ISTANBUL)).astimezone(ISTANBUL)
    run_date = timestamp.date().isoformat()
    state_store = store or ScheduledRunJsonStore()
    history_store = audit_store or ScheduledRunAuditJsonStore()
    key = f"{run_date}:{phase_value}"
    existing = state_store.load().get(key)
    if existing is not None and existing.status == "SUCCESS" and not force:
        skipped = ScheduledRunRecord(
            phase=phase_value,
            run_date=run_date,
            started_at=existing.started_at,
            finished_at=existing.finished_at,
            status="SKIPPED",
            candidate_count=existing.candidate_count,
            buy_symbols=existing.buy_symbols,
            detail="Aynı gün/faz için başarılı otomatik koşu zaten mevcut.",
            run_kind=run_kind,
        )
        history_store.append(skipped)
        return skipped

    started_at = timestamp.isoformat(timespec="seconds")
    engine = runtime or _default_runtime()
    try:
        summary = engine.operation_summary()
        scan_result = engine.scan()
        visibility = engine.visibility_contexts()
        candidate_snapshot = engine.candidate_snapshot(summary, scan_result, visibility)
        cards = tuple(getattr(candidate_snapshot, "candidates", ()) or ())
        decisions = engine.decisions(cards)
        engine.persist_decision_snapshot(cards, decisions, phase_value, timestamp)
        buy_symbols = tuple(
            str(getattr(item, "symbol", "")).strip().upper()
            for item in decisions
            if str(getattr(item, "decision", "")).strip().upper() == "AL"
        )
        finished = datetime.now(ISTANBUL).isoformat(timespec="seconds")
        record = ScheduledRunRecord(
            phase=phase_value,
            run_date=run_date,
            started_at=started_at,
            finished_at=finished,
            status="SUCCESS",
            candidate_count=len(cards),
            buy_symbols=buy_symbols,
            detail="Seans sonu/sabah günlük karar koşusu tamamlandı.",
            run_kind=run_kind,
        )
    except Exception as error:
        finished = datetime.now(ISTANBUL).isoformat(timespec="seconds")
        record = ScheduledRunRecord(
            phase=phase_value,
            run_date=run_date,
            started_at=started_at,
            finished_at=finished,
            status="FAILED",
            candidate_count=0,
            buy_symbols=(),
            detail=f"{type(error).__name__}: {error}",
            run_kind=run_kind,
        )
    state_store.save(record)
    history_store.append(record)
    return record


def scheduler_status_rows(store: ScheduledRunJsonStore | None = None) -> tuple[dict[str, object], ...]:
    state_store = store or ScheduledRunJsonStore()
    rows: list[dict[str, object]] = []
    for phase, label in (("EVENING", "Seans sonu"), ("MORNING", "09:00")):
        item = state_store.latest(phase)
        rows.append({
            "Koşu": label,
            "Durum": item.status if item else "HENÜZ YOK",
            "Son çalışma": item.finished_at if item else "-",
            "Aday": item.candidate_count if item else 0,
            "AL": ", ".join(item.buy_symbols) if item and item.buy_symbols else "-",
            "Detay": item.detail if item else "-",
        })
    return tuple(rows)


def _phase_due(phase: str, now: datetime) -> bool:
    hour, minute = PHASE_SCHEDULE[_normalize_phase(phase)]
    return (now.hour, now.minute) >= (hour, minute)


def scheduler_health_rows(
    store: ScheduledRunJsonStore | None = None,
    *,
    now: datetime | None = None,
) -> tuple[dict[str, object], ...]:
    state_store = store or ScheduledRunJsonStore()
    timestamp = (now or datetime.now(ISTANBUL)).astimezone(ISTANBUL)
    today = timestamp.date().isoformat()
    rows: list[dict[str, object]] = []
    for phase, label in (("EVENING", "Seans sonu"), ("MORNING", "09:00")):
        latest = state_store.latest(phase)
        latest_success = state_store.latest_success(phase)
        today_record = state_store.load().get(f"{today}:{phase}")
        due = _phase_due(phase, timestamp)
        if today_record is not None and today_record.status == "SUCCESS":
            health = "SAĞLIKLI"
            recovery = "GEREK YOK"
        elif today_record is not None and today_record.status == "FAILED":
            health = "BAŞARISIZ"
            recovery = "YENİDEN ÇALIŞTIR"
        elif due:
            health = "EKSİK KOŞU"
            recovery = "YENİDEN ÇALIŞTIR"
        else:
            health = "ZAMANI BEKLİYOR"
            recovery = "GEREK YOK"
        rows.append({
            "Koşu": label,
            "Sağlık": health,
            "Bugünkü durum": today_record.status if today_record else "HENÜZ YOK",
            "Son başarılı": (f"{latest_success.run_date} · {latest_success.finished_at}" if latest_success else "-"),
            "Son çalışma": latest.finished_at if latest else "-",
            "Aday": today_record.candidate_count if today_record else 0,
            "AL": ", ".join(today_record.buy_symbols) if today_record and today_record.buy_symbols else "-",
            "Kurtarma": recovery,
            "Son hata/detay": latest.detail if latest else "-",
        })
    return tuple(rows)


def retry_failed_or_missing_run(
    phase: str,
    *,
    now: datetime | None = None,
    runtime: ScheduledRunRuntime | None = None,
    store: ScheduledRunJsonStore | None = None,
    audit_store: ScheduledRunAuditJsonStore | None = None,
) -> ScheduledRunRecord:
    phase_value = _normalize_phase(phase)
    timestamp = (now or datetime.now(ISTANBUL)).astimezone(ISTANBUL)
    state_store = store or ScheduledRunJsonStore()
    today = timestamp.date().isoformat()
    existing = state_store.load().get(f"{today}:{phase_value}")
    history_store = audit_store or ScheduledRunAuditJsonStore()
    if existing is not None and existing.status == "SUCCESS":
        skipped = ScheduledRunRecord(
            phase=phase_value,
            run_date=today,
            started_at=existing.started_at,
            finished_at=existing.finished_at,
            status="SKIPPED",
            candidate_count=existing.candidate_count,
            buy_symbols=existing.buy_symbols,
            detail="Başarılı koşu mevcut; kurtarma tekrarına gerek yok.",
            run_kind="RECOVERY",
        )
        history_store.append(skipped)
        return skipped
    return execute_scheduled_run(
        phase_value,
        now=timestamp,
        runtime=runtime,
        store=state_store,
        audit_store=history_store,
        force=True,
        run_kind="RECOVERY",
    )


def scheduler_audit_rows(
    audit_store: ScheduledRunAuditJsonStore | None = None,
    *,
    limit: int = 50,
) -> tuple[dict[str, object], ...]:
    store = audit_store or ScheduledRunAuditJsonStore()
    phase_label = {"EVENING": "Seans sonu", "MORNING": "09:00"}
    kind_label = {"SCHEDULED": "Zamanlanmış", "RECOVERY": "Kurtarma"}
    return tuple(
        {
            "Tarih": item.run_date,
            "Koşu": phase_label.get(item.phase, item.phase),
            "Tür": kind_label.get(item.run_kind, item.run_kind),
            "Durum": item.status,
            "Başlangıç": item.started_at,
            "Bitiş": item.finished_at,
            "Aday": item.candidate_count,
            "AL": ", ".join(item.buy_symbols) if item.buy_symbols else "-",
            "Detay/Hata": item.detail or "-",
        }
        for item in store.latest(limit)
    )


def scheduler_daily_chain_rows(
    state_store: ScheduledRunJsonStore | None = None,
    *,
    limit_days: int = 14,
) -> tuple[dict[str, object], ...]:
    store = state_store or ScheduledRunJsonStore()
    records = store.load()
    dates = sorted({item.run_date for item in records.values()}, reverse=True)[:max(0, limit_days)]
    rows: list[dict[str, object]] = []
    for run_date in dates:
        evening = records.get(f"{run_date}:EVENING")
        morning = records.get(f"{run_date}:MORNING")
        evening_ok = evening is not None and evening.status == "SUCCESS"
        morning_ok = morning is not None and morning.status == "SUCCESS"
        if evening_ok and morning_ok:
            chain = "TAMAMLANDI"
        elif evening_ok or morning_ok:
            chain = "KISMİ"
        else:
            chain = "BAŞARISIZ/EKSİK"
        rows.append({
            "Tarih": run_date,
            "EOD": evening.status if evening else "YOK",
            "EOD aday": evening.candidate_count if evening else 0,
            "09:00": morning.status if morning else "YOK",
            "09:00 aday": morning.candidate_count if morning else 0,
            "Günlük zincir": chain,
        })
    return tuple(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hisse Robotu otomatik günlük karar koşusu")
    parser.add_argument("--phase", required=True, choices=VALID_PHASES)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    record = execute_scheduled_run(args.phase, force=args.force)
    print(json.dumps(asdict(record), ensure_ascii=False))
    return 0 if record.status in {"SUCCESS", "SKIPPED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
