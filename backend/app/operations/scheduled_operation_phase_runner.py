from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, time
from typing import Any, Iterable, Protocol
from zoneinfo import ZoneInfo

from backend.app.analysis.eod_candidate_output import build_eod_candidate_output
from backend.app.analysis.eod_candidate_output_archive import (
    EodCandidateOutputJsonStore,
    make_eod_output_record,
)
from backend.app.operations.scheduled_intraday_batch import run_scheduled_intraday_batch

from backend.app.analysis.daily_buy_decision_output_archive import (
    DecisionOutputArchiveJsonStore,
)
from backend.app.analysis.eod_candidate_performance_runtime import settle_eod_candidate_performance_history
from backend.app.analysis.scan_top10_next_session import settle_scan_top10_next_session
from backend.app.data.batch_market_data import toplu_fiyat_verisi_getir
from backend.app.operations.daily_buy_decision_scheduled_runner import (
    execute_scheduled_run,
)
from backend.app.analysis.momentum_discovery import (
    MomentumDiscoveryRequest,
    MomentumDiscoveryService,
    TARAMA_EVRENLERI,
)
from backend.app.operations.preclose_partial_daily_preview import (
    preclose_preview_rows,
    run_preclose_partial_preview,
)
from backend.app.operations.scheduled_intraday_batch import (
    fetch_scheduled_intraday_batch,
)

ISTANBUL = ZoneInfo("Europe/Istanbul")

PREOPEN = "PREOPEN"
POSTOPEN = "POSTOPEN"
PRECLOSE = "PRECLOSE"
CANONICAL_CLOSE = "CANONICAL_CLOSE"

VALID_PHASES = (
    PREOPEN,
    POSTOPEN,
    PRECLOSE,
    CANONICAL_CLOSE,
)

PHASE_SCHEDULE = {
    PREOPEN: (8, 45),
    POSTOPEN: (10, 20),
    PRECLOSE: (17, 20),
    CANONICAL_CLOSE: (18, 30),
}

# SCHEDULED_OPERATION_PHASE_RUNNER_INTEGRATION_V1
# One scheduled-operation dispatcher. Not a second scheduler.
# Preview phases are read-only and never call decision-output persistence.


class ScheduledOperationPhaseError(ValueError):
    """A scheduled operation phase cannot be executed safely."""


@dataclass(frozen=True)
class ScheduledOperationPhaseResult:
    phase: str
    run_date: str
    observed_at: str
    status: str
    candidate_count: int
    detail_rows: tuple[dict[str, object], ...]
    delegated_legacy_phase: str | None = None
    preview_only: bool = True
    canonical: bool = False
    ranking_write_allowed: bool = False
    profile_write_allowed: bool = False
    al_sat_decision_allowed: bool = False


class ScheduledOperationRuntime(Protocol):
    def preopen_context(
        self,
        *,
        now: datetime,
    ) -> ScheduledOperationPhaseResult: ...

    def postopen_gap_entry(
        self,
        *,
        now: datetime,
    ) -> ScheduledOperationPhaseResult: ...

    def preclose_preview(
        self,
        *,
        now: datetime,
    ) -> ScheduledOperationPhaseResult: ...

    def canonical_close(
        self,
        *,
        now: datetime,
    ) -> ScheduledOperationPhaseResult: ...


def _local_now(value: datetime | None) -> datetime:
    current = value or datetime.now(ISTANBUL)
    if current.tzinfo is None:
        return current.replace(tzinfo=ISTANBUL)
    return current.astimezone(ISTANBUL)


def _normalize_phase(value: str) -> str:
    phase = str(value or "").strip().upper()
    if phase not in VALID_PHASES:
        raise ScheduledOperationPhaseError(
            f"GeР вЂњР’В§ersiz scheduled operation phase: {value!r}"
        )
    return phase


def _schedule_guard(phase: str, now: datetime) -> None:
    clock = now.timetz().replace(tzinfo=None)

    if phase == PREOPEN:
        if clock < time(8, 45) or clock >= time(10, 0):
            raise ScheduledOperationPhaseError(
                "PREOPEN yalnР вЂќР’В±z 08:45Р Р†Р вЂљРІР‚Сљ09:59 aralР вЂќР’В±Р вЂќРЎСџР вЂќР’В±nda Р вЂњР’В§alР вЂќР’В±Р вЂўРЎСџР вЂќР’В±r."
            )
        return

    if phase == POSTOPEN:
        if clock < time(10, 20) or clock >= time(17, 20):
            raise ScheduledOperationPhaseError(
                "POSTOPEN yalnР вЂќР’В±z 10:20Р Р†Р вЂљРІР‚Сљ17:19 aralР вЂќР’В±Р вЂќРЎСџР вЂќР’В±nda Р вЂњР’В§alР вЂќР’В±Р вЂўРЎСџР вЂќР’В±r."
            )
        return

    if phase == PRECLOSE:
        if clock < time(17, 20) or clock >= time(18, 30):
            raise ScheduledOperationPhaseError(
                "PRECLOSE yalnР вЂќР’В±z 17:20Р Р†Р вЂљРІР‚Сљ18:29 aralР вЂќР’В±Р вЂќРЎСџР вЂќР’В±nda Р вЂњР’В§alР вЂќР’В±Р вЂўРЎСџР вЂќР’В±r."
            )
        return

    if phase == CANONICAL_CLOSE and clock < time(18, 30):
        raise ScheduledOperationPhaseError(
            "CANONICAL_CLOSE 18:30 Р вЂњР’В¶ncesinde Р вЂњР’В§alР вЂќР’В±Р вЂўРЎСџtР вЂќР’В±rР вЂќР’В±lamaz."
        )


def _plain(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _extract_symbols(value: Any) -> tuple[str, ...]:
    """Extract candidate symbols from an existing archive record without schema invention."""

    payload = _plain(value)
    found: list[str] = []

    def walk(item: Any) -> None:
        if isinstance(item, dict):
            for key, value in item.items():
                normalized_key = str(key).strip().lower()
                if normalized_key in {
                    "symbol",
                    "sembol",
                    "hisse",
                    "ticker",
                }:
                    text = str(value or "").strip().upper()
                    if text:
                        if "." not in text:
                            text = f"{text}.IS"
                        found.append(text)
                else:
                    walk(value)
        elif isinstance(item, list):
            for value in item:
                walk(value)

    walk(payload)

    ordered: list[str] = []
    seen: set[str] = set()
    for symbol in found:
        if symbol not in seen:
            seen.add(symbol)
            ordered.append(symbol)

    return tuple(ordered)


def _record_candidate_count(record: Any, symbols: tuple[str, ...]) -> int:
    for field in ("candidate_count", "aday_sayisi", "count"):
        value = getattr(record, field, None)
        if value is None and isinstance(record, dict):
            value = record.get(field)
        try:
            if value is not None:
                return max(0, int(value))
        except (TypeError, ValueError):
            pass
    return len(symbols)


def _pct(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return round((numerator / denominator - 1.0) * 100.0, 4)


class ProductionScheduledOperationRuntime:
    """Production adapter using only existing stores, data seams, and canonical runner."""

    def _latest_evening_record(self) -> Any | None:
        return DecisionOutputArchiveJsonStore().latest("EVENING")

    def preopen_context(
        self,
        *,
        now: datetime,
    ) -> ScheduledOperationPhaseResult:
        record = self._latest_evening_record()
        if record is None:
            return ScheduledOperationPhaseResult(
                phase=PREOPEN,
                run_date=now.date().isoformat(),
                observed_at=now.isoformat(),
                status="BLOCKED_NO_PRIOR_CLOSE_CONTEXT",
                candidate_count=0,
                detail_rows=(),
            )

        symbols = _extract_symbols(record)
        count = _record_candidate_count(record, symbols)
        rows = tuple(
            {
                "Hisse": symbol.removesuffix(".IS"),
                "Durum": "PREOPEN CONTEXT ONLY",
            }
            for symbol in symbols[:100]
        )

        return ScheduledOperationPhaseResult(
            phase=PREOPEN,
            run_date=now.date().isoformat(),
            observed_at=now.isoformat(),
            status="PREOPEN_CONTEXT_READY",
            candidate_count=count,
            detail_rows=rows,
        )

    def postopen_gap_entry(
        self,
        *,
        now: datetime,
    ) -> ScheduledOperationPhaseResult:
        record = self._latest_evening_record()
        if record is None:
            return ScheduledOperationPhaseResult(
                phase=POSTOPEN,
                run_date=now.date().isoformat(),
                observed_at=now.isoformat(),
                status="BLOCKED_NO_PRIOR_CLOSE_CONTEXT",
                candidate_count=0,
                detail_rows=(),
            )

        symbols = _extract_symbols(record)
        if not symbols:
            return ScheduledOperationPhaseResult(
                phase=POSTOPEN,
                run_date=now.date().isoformat(),
                observed_at=now.isoformat(),
                status="BLOCKED_NO_PRIOR_CLOSE_SYMBOLS",
                candidate_count=0,
                detail_rows=(),
            )

        # Limit follows the existing daily-decision board use case; this is not a universe rescan.
        symbols = symbols[:100]

        daily = toplu_fiyat_verisi_getir(
            symbols,
            islem_gunu=2,
            indirme_donemi="1mo",
        )
        intraday = fetch_scheduled_intraday_batch(
            symbols,
            now=now,
        )

        rows: list[dict[str, object]] = []

        for symbol in symbols:
            frame = daily.veriler.get(symbol)
            snapshot = intraday.snapshots.get(symbol)
            if frame is None or frame.empty or snapshot is None:
                continue
            if snapshot.locked:
                continue

            prior_close = float(frame.iloc[-1]["Close"])
            gap = _pct(float(snapshot.day_open), prior_close)
            move_from_open = _pct(
                float(snapshot.last_price),
                float(snapshot.day_open),
            )

            rows.append(
                {
                    "Hisse": symbol.removesuffix(".IS"),
                    "Р вЂњРІР‚вЂњnceki kapanР вЂќР’В±Р вЂўРЎСџ": round(prior_close, 4),
                    "AР вЂњР’В§Р вЂќР’В±lР вЂќР’В±Р вЂўРЎСџ": round(float(snapshot.day_open), 4),
                    "GР вЂњРЎВncel gecikmeli fiyat": round(float(snapshot.last_price), 4),
                    "Gap %": gap,
                    "AР вЂњР’В§Р вЂќР’В±lР вЂќР’В±Р вЂўРЎСџtan hareket %": move_from_open,
                    "Gecikme dk": round(float(snapshot.measured_delay_minutes), 2),
                    "Durum": "POSTOPEN GAP / ENTRY EVIDENCE Р вЂ™Р’В· NOT AL/SAT",
                }
            )

        status = (
            "POSTOPEN_GAP_ENTRY_EVIDENCE_READY"
            if rows
            else "BLOCKED_NO_USABLE_POSTOPEN_EVIDENCE"
        )

        return ScheduledOperationPhaseResult(
            phase=POSTOPEN,
            run_date=now.date().isoformat(),
            observed_at=now.isoformat(),
            status=status,
            candidate_count=len(rows),
            detail_rows=tuple(rows),
        )

    def preclose_preview(
        self,
        *,
        now: datetime,
    ) -> ScheduledOperationPhaseResult:
        preview = run_preclose_partial_preview(now=now)
        rows = preclose_preview_rows(preview)

        return ScheduledOperationPhaseResult(
            phase=PRECLOSE,
            run_date=now.date().isoformat(),
            observed_at=now.isoformat(),
            status="PRECLOSE_PREVIEW_READY",
            candidate_count=len(rows),
            detail_rows=rows,
        )

    def canonical_close(
        self,
        *,
        now: datetime,
    ) -> ScheduledOperationPhaseResult:
        # EOD_V8_CANONICAL_INTEGRATION
        # Eski karar zinciri tek kez calisir; EOD katmani sonucu degistirmez.
        legacy = execute_scheduled_run(
            "EVENING",
            now=now,
        )

        count = int(getattr(legacy, "candidate_count", 0) or 0)
        status = str(getattr(legacy, "status", "SUCCESS") or "SUCCESS")

        # Momentum gecmisi: best-effort; AL-SAT sonucunu degistirmez.
        try:
            from backend.app.analysis.scan_top10_next_session_v2 import record_scan_top10_snapshot
            momentum_result = MomentumDiscoveryService().calistir(
                MomentumDiscoveryRequest(
                    evren=TARAMA_EVRENLERI[4],
                    maksimum_aday=25,
                    minimum_skor=55,
                    internetten_evren_guncelle=False,
                )
            )
            record_scan_top10_snapshot(
                run_date=now.date().isoformat(),
                candidates=momentum_result.adaylar,
            )
        except Exception:
            pass

        # EOD arР вЂўРЎСџivi best-effort'tur; hata eski sonucu veya yetkileri degistirmez.
        symbols: tuple[str, ...] = ()
        try:
            legacy_record = DecisionOutputArchiveJsonStore().latest("EVENING")
            symbols = tuple(_extract_symbols(legacy_record)) if legacy_record else ()

            if symbols:
                batch = run_scheduled_intraday_batch(symbols, now=now)
                output = build_eod_candidate_output(
                    symbols,
                    batch.eod_decisions,
                )
                record = make_eod_output_record(
                    now=now,
                    candidate_symbols=symbols,
                    batch=batch,
                    output=output,
                )
            else:
                record = make_eod_output_record(
                    now=now,
                    candidate_symbols=(),
                )

            EodCandidateOutputJsonStore().save_record(record)
            # EOD_V9C_REV1_PERFORMANCE_HISTORY_HOOK
            # Best-effort measurement only; never changes legacy AL/BEKLE output.
            try:
                settle_eod_candidate_performance_history(
                    current_date=now.date().isoformat(),
                )
            except Exception:
                pass
            # TOP10_NEXT_SESSION_PERFORMANCE_HOOK
            try:
                settle_scan_top10_next_session(current_date=now.date().isoformat())
            except Exception:
                pass

            # TOP10_NEXT_SESSION_PERFORMANCE_V2_HOOK
            try:
                from backend.app.analysis.scan_top10_next_session_v2 import settle_scan_top10_next_session as settle_scan_top10_next_session_v2
                settle_scan_top10_next_session_v2(current_date=now.date().isoformat())
            except Exception:
                pass

        except Exception as error:
            try:
                error_record = make_eod_output_record(
                    now=now,
                    candidate_symbols=symbols,
                    error=f"{type(error).__name__}: {error}",
                )
                EodCandidateOutputJsonStore().save_record(error_record)
            except Exception:
                pass

        return ScheduledOperationPhaseResult(
            phase=CANONICAL_CLOSE,
            run_date=now.date().isoformat(),
            observed_at=now.isoformat(),
            status=status,
            candidate_count=count,
            detail_rows=(),
            delegated_legacy_phase="EVENING",
            preview_only=False,
            canonical=True,
            ranking_write_allowed=True,
            profile_write_allowed=True,
            al_sat_decision_allowed=True,
        )
def execute_operation_phase(
    phase: str,
    *,
    now: datetime | None = None,
    runtime: ScheduledOperationRuntime | None = None,
    enforce_schedule: bool = True,
) -> ScheduledOperationPhaseResult:
    normalized = _normalize_phase(phase)
    observed_at = _local_now(now)

    if enforce_schedule:
        _schedule_guard(normalized, observed_at)

    service = runtime or ProductionScheduledOperationRuntime()

    if normalized == PREOPEN:
        result = service.preopen_context(now=observed_at)
    elif normalized == POSTOPEN:
        result = service.postopen_gap_entry(now=observed_at)
    elif normalized == PRECLOSE:
        result = service.preclose_preview(now=observed_at)
    else:
        result = service.canonical_close(now=observed_at)

    if result.phase != normalized:
        raise ScheduledOperationPhaseError(
            f"Runtime yanlР вЂќР’В±Р вЂўРЎСџ phase dР вЂњР’В¶ndР вЂњРЎВrdР вЂњРЎВ: {result.phase!r}"
        )

    # Hard safety guard: only canonical close may expose write authority.
    if normalized != CANONICAL_CLOSE and (
        result.canonical
        or result.ranking_write_allowed
        or result.profile_write_allowed
        or result.al_sat_decision_allowed
    ):
        raise ScheduledOperationPhaseError(
            f"{normalized} preview phase yazma/karar yetkisi taР вЂўРЎСџР вЂќР’В±yamaz."
        )

    return result


def operation_phase_rows(
    result: ScheduledOperationPhaseResult,
) -> tuple[dict[str, object], ...]:
    return result.detail_rows


def _jsonable(result: ScheduledOperationPhaseResult) -> dict[str, object]:
    return {
        "phase": result.phase,
        "run_date": result.run_date,
        "observed_at": result.observed_at,
        "status": result.status,
        "candidate_count": result.candidate_count,
        "detail_rows": list(result.detail_rows),
        "delegated_legacy_phase": result.delegated_legacy_phase,
        "preview_only": result.preview_only,
        "canonical": result.canonical,
        "ranking_write_allowed": result.ranking_write_allowed,
        "profile_write_allowed": result.profile_write_allowed,
        "al_sat_decision_allowed": result.al_sat_decision_allowed,
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", required=True, choices=VALID_PHASES)
    args = parser.parse_args(list(argv) if argv is not None else None)

    result = execute_operation_phase(args.phase)
    print(
        json.dumps(
            _jsonable(result),
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())





