from __future__ import annotations

import inspect
import json

import pytest

from app.analysis.next_day_observation_memory import (
    NextDayObservationPersistenceError,
    OUTCOME_RECORD_TYPE,
    SELECTION_RECORD_TYPE,
    final_outcome_record,
    list_final_outcome_records,
    list_frozen_selection_records,
    load_final_outcomes,
    load_frozen_selection,
    persist_final_outcome,
    persist_frozen_selection,
)
from app.analysis.next_day_outcome import evaluate_next_day_selection
from app.analysis.next_day_selection import (
    NextDayCandidateEvidence,
    select_next_day_candidates,
)
from app.analysis.next_day_walk_forward import build_walk_forward_readiness
from app.analysis.ranking_memory import RankObservationJsonlStore


def _selection(symbol: str = "AAA"):
    return select_next_day_candidates(
        (
            NextDayCandidateEvidence(
                canonical_date="2026-08-28",
                symbol=symbol,
                research_rank=1,
                evidence_families=("F1", "F3", "F4"),
            ),
        )
    )


def _complete_outcome(selection):
    return evaluate_next_day_selection(
        selection,
        t1_date="2026-08-31",
        t_close_by_symbol={"AAA": 100.0},
        t1_bars_by_symbol={
            "AAA": {"open": 101.0, "high": 104.0, "low": 99.0, "close": 103.0},
        },
        universe_t_close_by_symbol={"AAA": 100.0, "BBB": 100.0},
        universe_t1_bars_by_symbol={
            "AAA": {"open": 101.0, "high": 104.0, "low": 99.0, "close": 103.0},
            "BBB": {"open": 100.0, "high": 101.0, "low": 98.0, "close": 99.0},
        },
    )


def test_selection_roundtrip_is_append_only_and_idempotent(tmp_path):
    store = RankObservationJsonlStore(path=tmp_path / "rank_observations.jsonl")
    selection = _selection()

    assert persist_frozen_selection(
        selection,
        store=store,
        recorded_at="2026-08-28T18:31:00+03:00",
    ) == "APPENDED"

    assert persist_frozen_selection(
        selection,
        store=store,
        recorded_at="2026-08-28T18:32:00+03:00",
    ) == "ALREADY_PRESENT"

    records = list_frozen_selection_records(store)
    assert len(records) == 1
    assert records[0]["record_type"] == SELECTION_RECORD_TYPE
    assert records[0]["canonical_date"] == "2026-08-28"

    loaded = load_frozen_selection("2026-08-28", store=store)
    assert loaded is not None
    assert [x.symbol for x in loaded.primary] == ["AAA"]
    assert loaded.reserve == ()


def test_same_date_different_digest_hard_fails(tmp_path):
    store = RankObservationJsonlStore(path=tmp_path / "rank_observations.jsonl")
    persist_frozen_selection(_selection("AAA"), store=store)

    with pytest.raises(
        NextDayObservationPersistenceError,
        match="FROZEN_SELECTION_DIGEST_CONFLICT",
    ):
        persist_frozen_selection(_selection("BBB"), store=store)


def test_existing_rank_reader_ignores_next_day_record_type(tmp_path):
    path = tmp_path / "rank_observations.jsonl"
    rank_payload = {
        "as_of": "2026-08-28",
        "symbol": "AAA",
        "rank": 1,
        "ranked_universe_size": 10,
        "universe_source": "TEST",
        "profile_name": "DEFAULT",
    }
    path.write_text(
        json.dumps(rank_payload, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    store = RankObservationJsonlStore(path=path)
    assert len(store.list()) == 1

    persist_frozen_selection(_selection(), store=store)

    assert len(store.list()) == 1
    assert store.list()[0].symbol == "AAA"
    assert len(list_frozen_selection_records(store)) == 1


def test_final_outcome_roundtrip_and_walk_forward_compatibility(tmp_path):
    store = RankObservationJsonlStore(path=tmp_path / "rank_observations.jsonl")
    selection = _selection()
    persist_frozen_selection(selection, store=store)
    outcome = _complete_outcome(selection)

    assert persist_final_outcome(
        outcome,
        store=store,
        recorded_at="2026-08-31T18:31:00+03:00",
    ) == "APPENDED"

    assert persist_final_outcome(
        outcome,
        store=store,
        recorded_at="2026-08-31T18:32:00+03:00",
    ) == "ALREADY_PRESENT"

    raw = list_final_outcome_records(store)
    assert len(raw) == 1
    assert raw[0]["record_type"] == OUTCOME_RECORD_TYPE

    loaded = load_final_outcomes(store=store)
    assert len(loaded) == 1
    assert loaded[0].selection_digest == outcome.selection_digest
    assert loaded[0].outcomes[0].status == "HIT"

    readiness = build_walk_forward_readiness(
        loaded,
        required_valid_sessions=1,
    )
    assert readiness.ready_for_review is True
    assert readiness.valid_session_count == 1


def test_pending_outcome_is_never_written_as_final(tmp_path):
    store = RankObservationJsonlStore(path=tmp_path / "rank_observations.jsonl")
    selection = _selection()
    pending = evaluate_next_day_selection(
        selection,
        t1_date="2026-08-31",
        t_close_by_symbol={},
        t1_bars_by_symbol={},
        universe_t_close_by_symbol={"AAA": 100.0},
        universe_t1_bars_by_symbol={
            "AAA": {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0},
        },
    )

    with pytest.raises(
        NextDayObservationPersistenceError,
        match="PENDING",
    ):
        final_outcome_record(pending)

    assert list_final_outcome_records(store) == ()


def test_adapter_reuses_existing_store_and_defines_no_new_store_class():
    import app.analysis.next_day_observation_memory as module

    source = inspect.getsource(module)
    assert "RankObservationJsonlStore" in source
    assert "class NextDayObservationStore" not in source
    assert "class NextDaySelectionStore" not in source
    assert "class NextDayOutcomeStore" not in source
    assert "rank_observations.jsonl" not in source
