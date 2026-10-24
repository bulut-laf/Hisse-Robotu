from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Mapping

from backend.app.analysis.next_day_selection import ExtensionState, ReboundState
from backend.app.analysis.ranking_memory import RankObservationJsonlStore
from backend.app.analysis.weekly_opportunity import (
    CONTRACT_ID,
    WeeklyOpportunityCandidate,
    WeeklyOpportunityResult,
    WeeklyOpportunityStage,
    WeeklyOpportunityState,
    WeeklyPricePlan,
)

SNAPSHOT_RECORD_TYPE = "weekly_opportunity_v1"
OUTCOME_RECORD_TYPE = "weekly_outcome_v1"


class WeeklyOpportunityPersistenceError(RuntimeError):
    pass


def _memory(store: RankObservationJsonlStore | None) -> RankObservationJsonlStore:
    return store or RankObservationJsonlStore()


def _read_jsonl(store: RankObservationJsonlStore) -> tuple[dict[str, object], ...]:
    if not store.path.exists():
        return ()
    rows = []
    for raw in store.path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        payload = json.loads(raw)
        if isinstance(payload, dict):
            rows.append(payload)
    return tuple(rows)


def _append(store: RankObservationJsonlStore, payload: Mapping[str, object]) -> None:
    store.path.parent.mkdir(parents=True, exist_ok=True)
    with store.path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(payload), ensure_ascii=False, sort_keys=True) + "\n")


def _candidate_payload(x: WeeklyOpportunityCandidate) -> dict[str, object]:
    return {
        "canonical_date": x.canonical_date,
        "symbol": x.symbol,
        "stage": x.stage.value,
        "state": x.state.value,
        "research_rank": x.research_rank,
        "evidence_families": list(x.evidence_families),
        "soft_contradictions": list(x.soft_contradictions),
        "extension": x.extension.value,
        "rebound": x.rebound.value,
        "readiness_rank": x.readiness_rank,
        "migration_rank": x.migration_rank,
        "relative_strength_rank": x.relative_strength_rank,
        "next_day_status": x.next_day_status,
        "why_visible_now": x.why_visible_now,
        "what_must_happen_next": x.what_must_happen_next,
        "what_invalidates_setup": x.what_invalidates_setup,
        "pilot_research_status": x.pilot_research_status,
        "price_plan": asdict(x.price_plan),
    }


def _candidate_from_payload(p: Mapping[str, object]) -> WeeklyOpportunityCandidate:
    pp = p.get("price_plan") if isinstance(p.get("price_plan"), Mapping) else {}
    return WeeklyOpportunityCandidate(
        canonical_date=str(p["canonical_date"]),
        symbol=str(p["symbol"]),
        stage=WeeklyOpportunityStage(str(p["stage"])),
        state=WeeklyOpportunityState(str(p["state"])),
        research_rank=int(p["research_rank"]),
        evidence_families=tuple(p.get("evidence_families", ())),
        soft_contradictions=tuple(p.get("soft_contradictions", ())),
        extension=ExtensionState(str(p["extension"])),
        rebound=ReboundState(str(p["rebound"])),
        readiness_rank=int(p["readiness_rank"]),
        migration_rank=int(p["migration_rank"]),
        relative_strength_rank=int(p["relative_strength_rank"]),
        next_day_status=str(p.get("next_day_status", "NONE")),
        why_visible_now=str(p.get("why_visible_now", "")),
        what_must_happen_next=str(p.get("what_must_happen_next", "")),
        what_invalidates_setup=str(p.get("what_invalidates_setup", "")),
        pilot_research_status=str(p.get("pilot_research_status", "PASS")),
        price_plan=WeeklyPricePlan(**dict(pp)),
    )


def snapshot_digest(result: WeeklyOpportunityResult) -> str:
    payload = {
        "contract_id": result.contract_id,
        "canonical_date": result.canonical_date,
        "candidates": [_candidate_payload(x) for x in result.candidates],
        "excluded_count": result.excluded_count,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(raw.encode("utf-8")).hexdigest()


def snapshot_record(
    result: WeeklyOpportunityResult,
    *,
    recorded_at: str | None = None,
) -> dict[str, object]:
    if result.contract_id != CONTRACT_ID:
        raise WeeklyOpportunityPersistenceError("WEEKLY_CONTRACT_MISMATCH")
    return {
        "record_type": SNAPSHOT_RECORD_TYPE,
        "as_of": result.canonical_date,
        "contract_id": result.contract_id,
        "canonical_date": result.canonical_date,
        "snapshot_digest": snapshot_digest(result),
        "candidates": [_candidate_payload(x) for x in result.candidates],
        "excluded_count": result.excluded_count,
        "recorded_at": recorded_at or datetime.now(timezone.utc).isoformat(),
    }


def list_weekly_snapshot_records(
    store: RankObservationJsonlStore | None = None,
) -> tuple[dict[str, object], ...]:
    return tuple(
        sorted(
            (
                row for row in _read_jsonl(_memory(store))
                if str(row.get("record_type", "")) == SNAPSHOT_RECORD_TYPE
            ),
            key=lambda x: str(x.get("canonical_date", "")),
        )
    )


def persist_weekly_snapshot(
    result: WeeklyOpportunityResult,
    *,
    store: RankObservationJsonlStore | None = None,
    recorded_at: str | None = None,
) -> str:
    memory = _memory(store)
    payload = snapshot_record(result, recorded_at=recorded_at)
    same = [
        row for row in list_weekly_snapshot_records(memory)
        if str(row.get("canonical_date")) == result.canonical_date
    ]
    if same:
        if len(same) != 1:
            raise WeeklyOpportunityPersistenceError("DUPLICATE_WEEKLY_SNAPSHOT_DATE")
        if str(same[0].get("snapshot_digest")) == str(payload["snapshot_digest"]):
            return "ALREADY_PRESENT"
        raise WeeklyOpportunityPersistenceError("WEEKLY_SNAPSHOT_DIGEST_CONFLICT")
    _append(memory, payload)
    return "APPENDED"


def load_weekly_snapshot(
    canonical_date: str,
    *,
    store: RankObservationJsonlStore | None = None,
) -> WeeklyOpportunityResult | None:
    rows = [
        row for row in list_weekly_snapshot_records(store)
        if str(row.get("canonical_date")) == str(canonical_date)
    ]
    if not rows:
        return None
    if len(rows) != 1:
        raise WeeklyOpportunityPersistenceError("DUPLICATE_WEEKLY_SNAPSHOT_DATE")
    row = rows[0]
    result = WeeklyOpportunityResult(
        contract_id=str(row["contract_id"]),
        canonical_date=str(row["canonical_date"]),
        candidates=tuple(
            _candidate_from_payload(x)
            for x in row.get("candidates", ())
            if isinstance(x, Mapping)
        ),
        excluded_count=int(row.get("excluded_count", 0)),
    )
    if snapshot_digest(result) != str(row.get("snapshot_digest")):
        raise WeeklyOpportunityPersistenceError("WEEKLY_SNAPSHOT_DIGEST_MISMATCH")
    return result


def list_weekly_outcome_records(
    store: RankObservationJsonlStore | None = None,
) -> tuple[dict[str, object], ...]:
    return tuple(
        sorted(
            (
                row for row in _read_jsonl(_memory(store))
                if str(row.get("record_type", "")) == OUTCOME_RECORD_TYPE
            ),
            key=lambda x: str(x.get("canonical_date", "")),
        )
    )


def persist_weekly_outcome_record(
    payload: Mapping[str, object],
    *,
    store: RankObservationJsonlStore | None = None,
) -> str:
    memory = _memory(store)
    if str(payload.get("record_type")) != OUTCOME_RECORD_TYPE:
        raise WeeklyOpportunityPersistenceError("WEEKLY_OUTCOME_RECORD_TYPE_MISMATCH")
    date = str(payload.get("canonical_date", ""))
    digest = str(payload.get("snapshot_digest", ""))
    same = [x for x in list_weekly_outcome_records(memory) if str(x.get("canonical_date")) == date]
    if same:
        if len(same) != 1:
            raise WeeklyOpportunityPersistenceError("DUPLICATE_WEEKLY_OUTCOME_DATE")
        existing = dict(same[0]); existing.pop("recorded_at", None)
        candidate = dict(payload); candidate.pop("recorded_at", None)
        if existing == candidate:
            return "ALREADY_PRESENT"
        raise WeeklyOpportunityPersistenceError("WEEKLY_OUTCOME_CONFLICT")
    if not date or not digest:
        raise WeeklyOpportunityPersistenceError("WEEKLY_OUTCOME_IDENTITY_MISSING")
    _append(memory, payload)
    return "APPENDED"
