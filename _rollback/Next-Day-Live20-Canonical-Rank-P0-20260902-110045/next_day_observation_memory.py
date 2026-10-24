from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Mapping

from .next_day_outcome import (
    NextDayCandidateOutcome,
    NextDayOutcomeResult,
    NextDayTierOutcomeSummary,
    OUTCOME_CONTRACT_ID,
    selection_digest,
)
from .next_day_selection import (
    ExtensionState,
    NextDayRole,
    NextDaySelectionItem,
    NextDaySelectionResult,
    ReboundState,
    STRATEGY_ID,
)
from .ranking_memory import RankObservationJsonlStore

SELECTION_RECORD_TYPE = "next_day_selection_v1"
OUTCOME_RECORD_TYPE = "next_day_outcome_v1"


class NextDayObservationPersistenceError(RuntimeError):
    pass


def _memory(store: RankObservationJsonlStore | None) -> RankObservationJsonlStore:
    return store or RankObservationJsonlStore()


def _now_iso(recorded_at: str | None) -> str:
    return str(recorded_at or datetime.now(timezone.utc).isoformat())


def _read_jsonl(store: RankObservationJsonlStore) -> tuple[dict[str, object], ...]:
    path = Path(store.path)
    if not path.exists():
        return ()
    rows: list[dict[str, object]] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        raw = raw.strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise NextDayObservationPersistenceError(
                f"RANKING_MEMORY_JSON_INVALID_LINE={line_no}"
            ) from exc
        if not isinstance(payload, dict):
            raise NextDayObservationPersistenceError(
                f"RANKING_MEMORY_RECORD_NOT_OBJECT_LINE={line_no}"
            )
        rows.append(payload)
    return tuple(rows)


def _append_jsonl(store: RankObservationJsonlStore, payload: Mapping[str, object]) -> None:
    path = Path(store.path)
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(
        dict(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    with path.open("a", encoding="utf-8") as handle:
        handle.write(encoded + "\n")


def _selection_item_to_payload(item: NextDaySelectionItem) -> dict[str, object]:
    return {
        "canonical_date": item.canonical_date,
        "symbol": item.symbol,
        "role": item.role.value,
        "selection_order": int(item.selection_order),
        "research_rank": int(item.research_rank),
        "evidence_families": list(item.evidence_families),
        "contradiction_state": item.contradiction_state,
        "extension_state": item.extension_state.value,
        "rebound_state": item.rebound_state.value,
        "exclusion_reason": item.exclusion_reason,
        "explanation": item.explanation,
        "warnings": list(item.warnings),
        "next_action": item.next_action,
        "evaluation_identity": item.evaluation_identity,
    }


def _selection_item_from_payload(payload: Mapping[str, object]) -> NextDaySelectionItem:
    return NextDaySelectionItem(
        canonical_date=str(payload["canonical_date"]),
        symbol=str(payload["symbol"]),
        role=NextDayRole(str(payload["role"])),
        selection_order=int(payload["selection_order"]),
        research_rank=int(payload["research_rank"]),
        evidence_families=tuple(str(x) for x in payload.get("evidence_families", ())),
        contradiction_state=str(payload.get("contradiction_state", "NONE")),
        extension_state=ExtensionState(str(payload.get("extension_state", "CLEAN"))),
        rebound_state=ReboundState(str(payload.get("rebound_state", "NO"))),
        exclusion_reason=(
            str(payload["exclusion_reason"])
            if payload.get("exclusion_reason") is not None
            else None
        ),
        explanation=str(payload.get("explanation", "")),
        warnings=tuple(str(x) for x in payload.get("warnings", ())),
        next_action=str(payload.get("next_action", "Tek Hisse İnceleme")),
        evaluation_identity=str(payload["evaluation_identity"]),
    )


def frozen_selection_record(
    selection: NextDaySelectionResult,
    *,
    recorded_at: str | None = None,
) -> dict[str, object]:
    if selection.strategy_id != STRATEGY_ID or not selection.strategy_frozen:
        raise NextDayObservationPersistenceError("SELECTION_NOT_FROZEN_STRATEGY_V1")
    digest = selection_digest(selection)
    return {
        "record_type": SELECTION_RECORD_TYPE,
        "as_of": selection.canonical_date,
        "canonical_date": selection.canonical_date,
        "strategy_id": selection.strategy_id,
        "strategy_frozen": True,
        "selection_digest": digest,
        "primary": [_selection_item_to_payload(x) for x in selection.primary],
        "reserve": [_selection_item_to_payload(x) for x in selection.reserve],
        "recorded_at": _now_iso(recorded_at),
    }


def _selection_from_record(payload: Mapping[str, object]) -> NextDaySelectionResult:
    if str(payload.get("record_type")) != SELECTION_RECORD_TYPE:
        raise NextDayObservationPersistenceError("SELECTION_RECORD_TYPE_MISMATCH")
    selection = NextDaySelectionResult(
        canonical_date=str(payload["canonical_date"]),
        primary=tuple(
            _selection_item_from_payload(x)
            for x in payload.get("primary", ())
            if isinstance(x, Mapping)
        ),
        reserve=tuple(
            _selection_item_from_payload(x)
            for x in payload.get("reserve", ())
            if isinstance(x, Mapping)
        ),
        excluded=(),
        strategy_id=str(payload.get("strategy_id", "")),
        strategy_frozen=bool(payload.get("strategy_frozen", False)),
    )
    expected = str(payload.get("selection_digest", ""))
    actual = selection_digest(selection)
    if expected != actual:
        raise NextDayObservationPersistenceError("FROZEN_SELECTION_DIGEST_CORRUPT")
    return selection


def list_frozen_selection_records(
    store: RankObservationJsonlStore | None = None,
) -> tuple[dict[str, object], ...]:
    memory = _memory(store)
    rows = (
        row for row in _read_jsonl(memory)
        if str(row.get("record_type", "")) == SELECTION_RECORD_TYPE
    )
    return tuple(sorted(rows, key=lambda x: (str(x.get("canonical_date", "")), str(x.get("recorded_at", "")))))


def persist_frozen_selection(
    selection: NextDaySelectionResult,
    *,
    store: RankObservationJsonlStore | None = None,
    recorded_at: str | None = None,
) -> str:
    memory = _memory(store)
    payload = frozen_selection_record(selection, recorded_at=recorded_at)
    same_date = [
        row for row in list_frozen_selection_records(memory)
        if str(row.get("canonical_date")) == selection.canonical_date
    ]
    if same_date:
        digests = {str(row.get("selection_digest", "")) for row in same_date}
        if len(same_date) == 1 and digests == {str(payload["selection_digest"])}:
            _selection_from_record(same_date[0])
            return "ALREADY_PRESENT"
        raise NextDayObservationPersistenceError("FROZEN_SELECTION_DIGEST_CONFLICT")
    _append_jsonl(memory, payload)
    return "APPENDED"


def load_frozen_selection(
    canonical_date: str,
    *,
    store: RankObservationJsonlStore | None = None,
) -> NextDaySelectionResult | None:
    memory = _memory(store)
    matches = [
        row for row in list_frozen_selection_records(memory)
        if str(row.get("canonical_date")) == str(canonical_date)
    ]
    if not matches:
        return None
    if len(matches) != 1:
        raise NextDayObservationPersistenceError("DUPLICATE_FROZEN_SELECTION_DATE")
    return _selection_from_record(matches[0])


def _candidate_outcome_to_payload(item: NextDayCandidateOutcome) -> dict[str, object]:
    return {
        "evaluation_identity": item.evaluation_identity,
        "canonical_date": item.canonical_date,
        "t1_date": item.t1_date,
        "symbol": item.symbol,
        "role": item.role.value,
        "selection_order": int(item.selection_order),
        "t_close": item.t_close,
        "t1_open": item.t1_open,
        "t1_high": item.t1_high,
        "t1_low": item.t1_low,
        "t1_close": item.t1_close,
        "close_to_close_return": item.close_to_close_return,
        "relative_return": item.relative_return,
        "mfe": item.mfe,
        "mae": item.mae,
        "benchmark_return": item.benchmark_return,
        "status": item.status,
        "missing_reason": item.missing_reason,
    }


def _candidate_outcome_from_payload(payload: Mapping[str, object]) -> NextDayCandidateOutcome:
    return NextDayCandidateOutcome(
        evaluation_identity=str(payload["evaluation_identity"]),
        canonical_date=str(payload["canonical_date"]),
        t1_date=str(payload["t1_date"]),
        symbol=str(payload["symbol"]),
        role=NextDayRole(str(payload["role"])),
        selection_order=int(payload["selection_order"]),
        t_close=payload.get("t_close"),
        t1_open=payload.get("t1_open"),
        t1_high=payload.get("t1_high"),
        t1_low=payload.get("t1_low"),
        t1_close=payload.get("t1_close"),
        close_to_close_return=payload.get("close_to_close_return"),
        relative_return=payload.get("relative_return"),
        mfe=payload.get("mfe"),
        mae=payload.get("mae"),
        benchmark_return=float(payload["benchmark_return"]),
        status=str(payload["status"]),
        missing_reason=(str(payload["missing_reason"]) if payload.get("missing_reason") is not None else None),
    )


def _summary_to_payload(item: NextDayTierOutcomeSummary) -> dict[str, object]:
    return {
        "role": item.role.value,
        "candidate_count": int(item.candidate_count),
        "evaluated_count": int(item.evaluated_count),
        "pending_count": int(item.pending_count),
        "hit_count": int(item.hit_count),
        "miss_count": int(item.miss_count),
        "hit_rate": item.hit_rate,
        "median_relative_return": item.median_relative_return,
        "average_relative_return": item.average_relative_return,
        "median_mfe": item.median_mfe,
        "median_mae": item.median_mae,
        "basket_success": item.basket_success,
    }


def _summary_from_payload(payload: Mapping[str, object]) -> NextDayTierOutcomeSummary:
    return NextDayTierOutcomeSummary(
        role=NextDayRole(str(payload["role"])),
        candidate_count=int(payload["candidate_count"]),
        evaluated_count=int(payload["evaluated_count"]),
        pending_count=int(payload["pending_count"]),
        hit_count=int(payload["hit_count"]),
        miss_count=int(payload["miss_count"]),
        hit_rate=payload.get("hit_rate"),
        median_relative_return=payload.get("median_relative_return"),
        average_relative_return=payload.get("average_relative_return"),
        median_mfe=payload.get("median_mfe"),
        median_mae=payload.get("median_mae"),
        basket_success=payload.get("basket_success"),
    )


def final_outcome_record(
    outcome: NextDayOutcomeResult,
    *,
    recorded_at: str | None = None,
) -> dict[str, object]:
    if outcome.contract_id != OUTCOME_CONTRACT_ID or outcome.strategy_id != STRATEGY_ID:
        raise NextDayObservationPersistenceError("OUTCOME_CONTRACT_OR_STRATEGY_MISMATCH")
    if any(row.status == "PENDING" for row in outcome.outcomes):
        raise NextDayObservationPersistenceError("PENDING_OUTCOME_FINAL_WRITE_BLOCKED")
    if outcome.primary.pending_count or outcome.reserve.pending_count:
        raise NextDayObservationPersistenceError("PENDING_SUMMARY_FINAL_WRITE_BLOCKED")
    return {
        "record_type": OUTCOME_RECORD_TYPE,
        "as_of": outcome.canonical_date,
        "contract_id": outcome.contract_id,
        "strategy_id": outcome.strategy_id,
        "canonical_date": outcome.canonical_date,
        "t1_date": outcome.t1_date,
        "selection_digest": outcome.selection_digest,
        "benchmark_return": outcome.benchmark_return,
        "outcomes": [_candidate_outcome_to_payload(x) for x in outcome.outcomes],
        "primary": _summary_to_payload(outcome.primary),
        "reserve": _summary_to_payload(outcome.reserve),
        "primary_reserve_relative_spread": outcome.primary_reserve_relative_spread,
        "recorded_at": _now_iso(recorded_at),
    }


def _outcome_from_record(payload: Mapping[str, object]) -> NextDayOutcomeResult:
    if str(payload.get("record_type")) != OUTCOME_RECORD_TYPE:
        raise NextDayObservationPersistenceError("OUTCOME_RECORD_TYPE_MISMATCH")
    outcome = NextDayOutcomeResult(
        contract_id=str(payload["contract_id"]),
        strategy_id=str(payload["strategy_id"]),
        canonical_date=str(payload["canonical_date"]),
        t1_date=str(payload["t1_date"]),
        selection_digest=str(payload["selection_digest"]),
        benchmark_return=float(payload["benchmark_return"]),
        outcomes=tuple(
            _candidate_outcome_from_payload(x)
            for x in payload.get("outcomes", ())
            if isinstance(x, Mapping)
        ),
        primary=_summary_from_payload(payload["primary"]),
        reserve=_summary_from_payload(payload["reserve"]),
        primary_reserve_relative_spread=payload.get("primary_reserve_relative_spread"),
    )
    if any(row.status == "PENDING" for row in outcome.outcomes):
        raise NextDayObservationPersistenceError("PERSISTED_OUTCOME_CONTAINS_PENDING")
    return outcome


def list_final_outcome_records(
    store: RankObservationJsonlStore | None = None,
) -> tuple[dict[str, object], ...]:
    memory = _memory(store)
    rows = (
        row for row in _read_jsonl(memory)
        if str(row.get("record_type", "")) == OUTCOME_RECORD_TYPE
    )
    return tuple(sorted(rows, key=lambda x: (str(x.get("canonical_date", "")), str(x.get("t1_date", "")), str(x.get("recorded_at", "")))))


def persist_final_outcome(
    outcome: NextDayOutcomeResult,
    *,
    store: RankObservationJsonlStore | None = None,
    recorded_at: str | None = None,
) -> str:
    memory = _memory(store)
    payload = final_outcome_record(outcome, recorded_at=recorded_at)
    same_date = [
        row for row in list_final_outcome_records(memory)
        if str(row.get("canonical_date")) == outcome.canonical_date
    ]
    if same_date:
        if len(same_date) != 1:
            raise NextDayObservationPersistenceError("DUPLICATE_FINAL_OUTCOME_DATE")
        existing = dict(same_date[0])
        existing.pop("recorded_at", None)
        candidate = dict(payload)
        candidate.pop("recorded_at", None)
        if existing == candidate:
            _outcome_from_record(same_date[0])
            return "ALREADY_PRESENT"
        raise NextDayObservationPersistenceError("FROZEN_OUTCOME_CONFLICT")
    _append_jsonl(memory, payload)
    return "APPENDED"


def load_final_outcomes(
    *,
    store: RankObservationJsonlStore | None = None,
) -> tuple[NextDayOutcomeResult, ...]:
    return tuple(_outcome_from_record(x) for x in list_final_outcome_records(store))
