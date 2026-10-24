from __future__ import annotations

from datetime import date
import inspect
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from backend.app.analysis.next_day_selection import (
    ExtensionState,
    NextDayCandidateEvidence,
    ReboundState,
    select_next_day_candidates,
)
from backend.app.analysis.ranking_memory import RankObservation, RankObservationJsonlStore
from backend.app.analysis.weekly_opportunity import (
    WeeklyOpportunityEvidence,
    WeeklyOpportunityStage,
    WeeklyOpportunityState,
    classify_weekly_opportunities,
)
from backend.app.analysis.weekly_opportunity_memory import (
    list_weekly_outcome_records,
    list_weekly_snapshot_records,
    load_weekly_snapshot,
    persist_weekly_snapshot,
)
from backend.app.analysis.weekly_opportunity_outcome import settle_weekly_outcomes
from backend.app.analysis.weekly_opportunity_runtime import (
    observe_weekly_opportunity_runtime,
    price_plan_from_candidate,
)
from backend.app.data.batch_market_data import BatchMarketDataResult


def ev(families, *, symbol="AAA", date_="2026-09-04", **kwargs):
    return WeeklyOpportunityEvidence(
        canonical_date=date_,
        symbol=symbol,
        research_rank=kwargs.pop("research_rank", 1),
        evidence_families=tuple(families),
        **kwargs,
    )


def test_stage_progression_and_single_factor_guard():
    result = classify_weekly_opportunities((
        ev(("F1",), symbol="ZERO"),
        ev(("F1", "F2"), symbol="W1"),
        ev(("F1", "F2", "F3"), symbol="W2"),
        ev(("F1", "F3", "F4"), symbol="W3"),
        ev(("F1", "F2", "F3", "F4"), symbol="W4"),
    ))
    stages = {x.symbol: x.stage for x in result.candidates}
    assert "ZERO" not in stages
    assert stages["W1"] is WeeklyOpportunityStage.W1
    assert stages["W2"] is WeeklyOpportunityStage.W2
    assert stages["W3"] is WeeklyOpportunityStage.W3
    assert stages["W4"] is WeeklyOpportunityStage.W4


def test_hard_block_and_rebound_trap_are_excluded():
    result = classify_weekly_opportunities((
        ev(("F1","F2","F3","F4"), symbol="HARD", hard_contradictions=("X",)),
        ev(("F1","F2","F3","F4"), symbol="TRAP", rebound=ReboundState.TRAP),
        ev(("F1","F2"), symbol="OK"),
    ))
    assert [x.symbol for x in result.candidates] == ["OK"]
    assert result.excluded_count == 2


def test_severe_extension_is_never_w3_or_w4():
    result = classify_weekly_opportunities((
        ev(("F1","F2","F3","F4","F5"), extension=ExtensionState.SEVERE),
    ))
    assert result.candidates[0].stage is WeeklyOpportunityStage.W2
    assert result.candidates[0].state is WeeklyOpportunityState.EXTENDED
    assert result.candidates[0].pilot_research_status == "PASS"


def test_ordering_is_deterministic_and_not_score_based():
    result = classify_weekly_opportunities((
        ev(("F1","F2","F3"), symbol="BBB", research_rank=2),
        ev(("F1","F2","F3","F4"), symbol="CCC", research_rank=3),
        ev(("F1","F2","F3","F4"), symbol="AAA", research_rank=1),
    ))
    assert [x.symbol for x in result.candidates] == ["AAA", "CCC", "BBB"]
    source = inspect.getsource(classify_weekly_opportunities)
    assert "weighted" not in source.lower()
    assert "composite" not in source.lower()


def test_price_plan_reuses_exact_risk_contract_and_does_not_invent_second_target_or_zone():
    candidate = SimpleNamespace(
        sembol="AAA",
        kapanis=100.0,
        risk_plani=SimpleNamespace(
            giris_fiyati=100.0,
            stop_loss=96.0,
            hedef_fiyat=108.0,
            risk_odul_orani=2.0,
        ),
    )
    plan = price_plan_from_candidate(candidate)
    assert plan.current_price == 100.0
    assert plan.ideal_entry == 100.0
    assert plan.stop_loss == 96.0
    assert plan.target_1 == 108.0
    assert plan.risk_reward == 2.0
    assert plan.target_2 is None
    assert plan.entry_zone_low is None
    assert plan.entry_zone_high is None


def test_weekly_snapshot_reuses_ranking_jsonl_store_and_is_idempotent(tmp_path):
    store = RankObservationJsonlStore(tmp_path / "rank_observations.jsonl")
    result = classify_weekly_opportunities((ev(("F1","F2","F3","F4")),))
    assert persist_weekly_snapshot(result, store=store) == "APPENDED"
    assert persist_weekly_snapshot(result, store=store) == "ALREADY_PRESENT"
    assert len(store.list()) == 0
    assert len(list_weekly_snapshot_records(store)) == 1
    assert load_weekly_snapshot("2026-09-04", store=store) is not None


def _next_day_evidence(date_="2026-09-04"):
    return (
        NextDayCandidateEvidence(
            canonical_date=date_,
            symbol="AAA",
            research_rank=1,
            evidence_families=("F1","F2","F3","F4"),
        ),
        NextDayCandidateEvidence(
            canonical_date=date_,
            symbol="BBB",
            research_rank=2,
            evidence_families=("F1","F2","F3"),
        ),
    )


def _scan():
    def row(symbol):
        return SimpleNamespace(
            sembol=symbol,
            kapanis=100.0,
            risk_plani=SimpleNamespace(
                giris_fiyati=100.0,
                stop_loss=96.0,
                hedef_fiyat=108.0,
                risk_odul_orani=2.0,
            ),
        )
    return SimpleNamespace(tum_sonuclar=(row("AAA"), row("BBB")))


def test_runtime_freezes_only_friday_and_cross_references_next_day(tmp_path, monkeypatch):
    store = RankObservationJsonlStore(tmp_path / "rank_observations.jsonl")
    monkeypatch.setattr(
        "backend.app.analysis.weekly_opportunity_runtime.settle_weekly_outcomes",
        lambda **kwargs: (),
    )
    selection = select_next_day_candidates(_next_day_evidence())
    result = observe_weekly_opportunity_runtime(
        scan_result=_scan(),
        evidence=_next_day_evidence(),
        selection=selection,
        store=store,
    )
    assert result["status"] == "APPENDED"
    snap = load_weekly_snapshot("2026-09-04", store=store)
    roles = {x.symbol: x.next_day_status for x in snap.candidates}
    assert roles["AAA"] == "PRIMARY"

    monday_evidence = _next_day_evidence("2026-09-07")
    monday_selection = select_next_day_candidates(monday_evidence)
    result2 = observe_weekly_opportunity_runtime(
        scan_result=_scan(),
        evidence=monday_evidence,
        selection=monday_selection,
        store=store,
    )
    assert result2["status"] == "NOT_FRIDAY"


def _frame(values):
    dates = pd.to_datetime([
        "2026-09-04","2026-09-07","2026-09-08",
        "2026-09-09","2026-09-10","2026-09-11",
    ])
    return pd.DataFrame(
        {
            "Open": values,
            "High": [x * 1.02 for x in values],
            "Low": [x * 0.98 for x in values],
            "Close": values,
            "Volume": [1000.0] * 6,
        },
        index=dates,
    )


def test_t1_t3_t5_outcome_finalizes_without_new_store(tmp_path):
    store = RankObservationJsonlStore(tmp_path / "rank_observations.jsonl")
    store.append_snapshot((
        RankObservation("2026-09-04","AAA",1,2,"TEST","dengeli"),
        RankObservation("2026-09-04","BBB",2,2,"TEST","dengeli"),
    ))
    result = classify_weekly_opportunities((
        ev(("F1","F2","F3","F4"), symbol="AAA"),
        ev(("F1","F2","F3"), symbol="BBB", research_rank=2),
    ))
    persist_weekly_snapshot(result, store=store)

    def fetcher(symbols, **kwargs):
        return BatchMarketDataResult(
            veriler={
                "AAA.IS": _frame([100,102,103,105,106,108]),
                "BBB.IS": _frame([100,100,101,101,102,102]),
            },
            hatalar=(),
        )

    settled = settle_weekly_outcomes(
        current_date="2026-09-11",
        market_data_fetcher=fetcher,
        store=store,
    )
    assert settled[0]["status"] == "APPENDED"
    records = list_weekly_outcome_records(store)
    assert records[0]["t1_date"] == "2026-09-07"
    assert records[0]["t3_date"] == "2026-09-09"
    assert records[0]["t5_date"] == "2026-09-11"
    assert len(store.list()) == 2


def test_modules_have_no_scanner_new_score_or_trade_authority():
    import backend.app.analysis.weekly_opportunity as weekly
    import backend.app.analysis.weekly_opportunity_runtime as runtime
    source = inspect.getsource(weekly) + inspect.getsource(runtime)
    for token in (
        "BatchStockScanner",
        "BistMarketScannerService",
        "MarketScanRequest",
        "weighted_score",
        "composite_score",
        "buy_order",
        "sell_order",
        "position_size",
        "class WeeklyOpportunityStore",
    ):
        assert token not in source
