from __future__ import annotations

import inspect
from pathlib import Path

import pandas as pd

from backend.app.analysis.next_day_observation_memory import (
    list_final_outcome_records,
    persist_frozen_selection,
)
from backend.app.analysis.next_day_outcome_runtime_adapter import (
    settle_pending_next_day_outcomes,
)
from backend.app.analysis.next_day_selection import (
    NextDayCandidateEvidence,
    select_next_day_candidates,
)
from backend.app.analysis.ranking_memory import (
    RankObservation,
    RankObservationJsonlStore,
)


def _selection():
    return select_next_day_candidates(
        (
            NextDayCandidateEvidence(
                canonical_date="2026-08-31",
                symbol="AAA",
                research_rank=1,
                evidence_families=("F1", "F3", "F4"),
            ),
        )
    )


def _rank_rows():
    return (
        RankObservation(
            as_of="2026-08-31",
            symbol="AAA",
            rank=1,
            ranked_universe_size=2,
            universe_source="TEST_CANONICAL",
            profile_name="dengeli",
        ),
        RankObservation(
            as_of="2026-08-31",
            symbol="BBB",
            rank=2,
            ranked_universe_size=2,
            universe_source="TEST_CANONICAL",
            profile_name="dengeli",
        ),
    )


def _frame(t_close, t1_open, t1_high, t1_low, t1_close):
    return pd.DataFrame(
        {
            "Open": [t_close, t1_open],
            "High": [t_close, t1_high],
            "Low": [t_close, t1_low],
            "Close": [t_close, t1_close],
            "Volume": [1000.0, 1100.0],
        },
        index=pd.to_datetime(["2026-08-31", "2026-09-01"]),
    )


def test_complete_t1_is_persisted_using_rank_memory_universe(tmp_path):
    store = RankObservationJsonlStore(tmp_path / "rank_observations.jsonl")
    store.append_snapshot(_rank_rows())
    persist_frozen_selection(_selection(), store=store)

    calls = []

    def fetcher(symbols, **kwargs):
        calls.append((tuple(symbols), dict(kwargs)))
        from backend.app.data.batch_market_data import BatchMarketDataResult
        return BatchMarketDataResult(
            veriler={
                "AAA.IS": _frame(100.0, 101.0, 104.0, 99.0, 103.0),
                "BBB.IS": _frame(100.0, 100.0, 101.0, 98.0, 99.0),
            },
            hatalar=(),
        )

    result = settle_pending_next_day_outcomes(
        current_date="2026-09-01",
        market_data_fetcher=fetcher,
        store=store,
    )

    assert len(result) == 1
    assert result[0].status == "APPENDED"
    assert result[0].t1_date == "2026-09-01"
    assert calls[0][0] == ("AAA", "BBB")
    final = list_final_outcome_records(store)
    assert len(final) == 1
    assert final[0]["canonical_date"] == "2026-08-31"


def test_missing_candidate_t1_stays_pending_and_writes_nothing(tmp_path):
    store = RankObservationJsonlStore(tmp_path / "rank_observations.jsonl")
    store.append_snapshot(_rank_rows())
    persist_frozen_selection(_selection(), store=store)

    def fetcher(symbols, **kwargs):
        from backend.app.data.batch_market_data import BatchMarketDataResult
        aaa = pd.DataFrame(
            {
                "Open": [100.0],
                "High": [100.0],
                "Low": [100.0],
                "Close": [100.0],
                "Volume": [1000.0],
            },
            index=pd.to_datetime(["2026-08-31"]),
        )
        return BatchMarketDataResult(
            veriler={
                "AAA.IS": aaa,
                "BBB.IS": _frame(100.0, 100.0, 101.0, 98.0, 99.0),
            },
            hatalar=(),
        )

    result = settle_pending_next_day_outcomes(
        current_date="2026-09-01",
        market_data_fetcher=fetcher,
        store=store,
    )

    assert result[0].status == "PENDING_DATA"
    assert list_final_outcome_records(store) == ()


def test_same_day_selection_does_not_fetch_or_settle(tmp_path):
    store = RankObservationJsonlStore(tmp_path / "rank_observations.jsonl")
    store.append_snapshot(_rank_rows())
    persist_frozen_selection(_selection(), store=store)

    calls = []
    result = settle_pending_next_day_outcomes(
        current_date="2026-08-31",
        market_data_fetcher=lambda *a, **k: calls.append(1),
        store=store,
    )
    assert result == ()
    assert calls == []


def test_ambiguous_rank_universe_fails_closed_without_fetch(tmp_path):
    store = RankObservationJsonlStore(tmp_path / "rank_observations.jsonl")
    rows = list(_rank_rows())
    rows.extend(
        (
            RankObservation(
                as_of="2026-08-31",
                symbol="AAA",
                rank=1,
                ranked_universe_size=2,
                universe_source="OTHER",
                profile_name="dengeli",
            ),
            RankObservation(
                as_of="2026-08-31",
                symbol="CCC",
                rank=2,
                ranked_universe_size=2,
                universe_source="OTHER",
                profile_name="dengeli",
            ),
        )
    )
    store.append_snapshot(rows)
    persist_frozen_selection(_selection(), store=store)

    calls = []
    result = settle_pending_next_day_outcomes(
        current_date="2026-09-01",
        market_data_fetcher=lambda *a, **k: calls.append(1),
        store=store,
    )
    assert result[0].status == "BLOCKED"
    assert "AMBIGUOUS" in result[0].detail
    assert calls == []
    assert list_final_outcome_records(store) == ()


def test_adapter_has_no_scanner_universe_repo_score_or_trade_authority():
    import backend.app.analysis.next_day_outcome_runtime_adapter as module

    source = inspect.getsource(module)
    forbidden = (
        "BatchStockScanner",
        "BistUniverseRepository",
        "MarketScanRequest",
        "BistMarketScannerService",
        "weighted_score",
        "composite_score",
        "buy_order",
        "sell_order",
        "position_size",
        "class NextDayOutcomeStore",
    )
    assert all(token not in source for token in forbidden)
    assert "toplu_fiyat_verisi_getir" in source
    assert "RankObservationJsonlStore" in source
    assert "persist_final_outcome" in source


def test_phase7c_observer_calls_settlement_fail_open_before_current_write():
    source = Path(
        "backend/app/analysis/next_day_runtime_observer.py"
    ).read_text(encoding="utf-8")

    assert source.count("# NEXT_DAY_PHASE8_T1_OUTCOME_SETTLEMENT_V1") == 1
    marker = source.index("# NEXT_DAY_PHASE8_T1_OUTCOME_SETTLEMENT_V1")
    settle = source.index("settle_pending_next_day_outcomes(", marker)
    persist = source.index("persist_frozen_selection(selection)", settle)

    assert settle < persist
    block = source[marker:persist]
    assert "try:" in block
    assert "except Exception:" in block
    assert "pass" in block
