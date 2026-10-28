from types import SimpleNamespace

import pandas as pd

from backend.app.analysis.eod_candidate_output_archive import EodCandidateOutputJsonStore
from backend.app.analysis.scan_top10_next_session_v2 import (
    CONTRACT_ID,
    ScanTop10NextSessionV2JsonStore,
    record_scan_top10_snapshot,
    settle_scan_top10_next_session,
)


def test_v2_measures_ten_valid_ohlc_candidates(tmp_path):
    source = EodCandidateOutputJsonStore(tmp_path / "source.json")
    source.save_record({"run_date": "2026-10-26", "phase": "CANONICAL_CLOSE",
                        "candidate_symbols": [f"S{i}" for i in range(12)]})
    dates = pd.to_datetime(["2026-10-26", "2026-10-27"])
    frames = {}
    for i in range(10):
        close = 11 if i % 2 == 0 else 9
        frames[f"S{i}"] = pd.DataFrame(
            {"High": [11, 12], "Low": [9, 8], "Close": [10, close]}, index=dates
        )
    store = ScanTop10NextSessionV2JsonStore(tmp_path / "out.json")
    result = settle_scan_top10_next_session(
        current_date="2026-10-27", source_store=source, outcome_store=store,
        market_data_fetcher=lambda *args, **kwargs: SimpleNamespace(veriler=frames),
    )
    record = store.load()["records"][0]
    assert result["processed_count"] == 1
    assert record["contract_id"] == CONTRACT_ID
    assert record["candidate_count"] == 10
    assert record["summary"]["evaluated_count"] == 10
    assert record["summary"]["rising_count"] == 5
    assert record["summary"]["falling_count"] == 5
    assert record["summary"]["hit_rate_pct"] == 50.0


def test_v2_freezes_first_ten_real_candidates_and_reference_prices(tmp_path):
    store = ScanTop10NextSessionV2JsonStore(tmp_path / "out.json")
    candidates = [SimpleNamespace(sembol=f"M{i}", kapanis=100 + i, analiz_tarihi="2026-10-26")
                  for i in range(12)]
    result = record_scan_top10_snapshot(run_date="2026-10-26", candidates=candidates, outcome_store=store)
    record = store.load()["records"][0]
    assert result["candidate_count"] == 5
    assert record["candidate_symbols"] == [f"M{i}" for i in range(5)]
    assert record["candidates"][0]["reference_price"] == 100
    assert record["candidates"][0]["reference_date"] == "2026-10-26"


def test_v2_missing_next_session_remains_pending(tmp_path):
    source = EodCandidateOutputJsonStore(tmp_path / "source.json")
    source.save_record({"run_date": "2026-10-26", "phase": "CANONICAL_CLOSE", "candidate_symbols": ["AAA"]})
    frames = {"AAA": pd.DataFrame({"High": [11], "Low": [9], "Close": [10]},
                                   index=pd.to_datetime(["2026-10-26"]))}
    store = ScanTop10NextSessionV2JsonStore(tmp_path / "out.json")
    settle_scan_top10_next_session(current_date="2026-10-27", source_store=source,
        outcome_store=store, market_data_fetcher=lambda *args, **kwargs: SimpleNamespace(veriler=frames))
    record = store.load()["records"][0]
    assert record["status"] == "PENDING_DATA"
    assert record["summary"]["pending_count"] == 1

