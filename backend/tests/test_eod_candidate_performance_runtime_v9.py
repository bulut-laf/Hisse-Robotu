from datetime import date
from types import SimpleNamespace

import pandas as pd

from app.analysis.eod_candidate_output_archive import EodCandidateOutputJsonStore
from app.analysis.eod_candidate_performance import EodCandidatePerformanceJsonStore
from app.analysis.eod_candidate_performance_runtime import settle_latest_eod_candidate_performance


def _frame():
    dates = pd.to_datetime([
        "2026-10-09", "2026-10-12", "2026-10-13",
        "2026-10-14", "2026-10-15", "2026-10-16",
    ])
    return pd.DataFrame(
        {
            "High": [101, 103, 106, 105, 108, 110],
            "Low": [99, 99, 98, 97, 100, 102],
            "Close": [100, 102, 104, 101, 107, 109],
        },
        index=dates,
    )


def test_runtime_reads_eod_candidates_and_writes_separate_archive(tmp_path):
    eod = EodCandidateOutputJsonStore(tmp_path / "eod.json")
    outcomes = EodCandidatePerformanceJsonStore(tmp_path / "performance.json")
    eod.save_record({
        "phase": "CANONICAL_CLOSE",
        "run_date": "2026-10-09",
        "created_at": "2026-10-09T18:30:00+03:00",
        "candidate_symbols": ["ABC", "XYZ"],
        "buy_candidate_symbols": ["ABC"],
        "buy_candidate_count": 1,
    })

    calls = []
    def fetcher(symbols, **kwargs):
        calls.append((symbols, kwargs))
        return SimpleNamespace(veriler={"ABC": _frame()})

    result = settle_latest_eod_candidate_performance(
        current_date="2026-10-16",
        eod_store=eod,
        outcome_store=outcomes,
        market_data_fetcher=fetcher,
    )

    assert result["status"] == "SUCCESS"
    assert result["candidate_count"] == 1
    assert calls[0][0] == ("ABC",)
    saved = outcomes.load()["records"][-1]
    assert saved["candidate_symbols"] == ["ABC"]
    assert [item["horizon"] for item in saved["candidates"][0]["horizons"]] == [1, 3, 5]


def test_runtime_waits_until_after_base_date(tmp_path):
    eod = EodCandidateOutputJsonStore(tmp_path / "eod.json")
    outcomes = EodCandidatePerformanceJsonStore(tmp_path / "performance.json")
    eod.save_record({
        "phase": "CANONICAL_CLOSE",
        "run_date": "2026-10-09",
        "candidate_symbols": ["ABC"],
        "buy_candidate_symbols": ["ABC"],
    })
    result = settle_latest_eod_candidate_performance(
        current_date="2026-10-09",
        eod_store=eod,
        outcome_store=outcomes,
        market_data_fetcher=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not fetch")),
    )
    assert result["status"] == "WAITING_FOR_FUTURE_SESSIONS"
    assert outcomes.load()["records"] == []


def test_runtime_handles_no_source_archive(tmp_path):
    eod = EodCandidateOutputJsonStore(tmp_path / "missing.json")
    outcomes = EodCandidatePerformanceJsonStore(tmp_path / "performance.json")
    result = settle_latest_eod_candidate_performance(
        current_date="2026-10-16",
        eod_store=eod,
        outcome_store=outcomes,
        market_data_fetcher=lambda *args, **kwargs: None,
    )
    assert result["status"] == "NO_EOD_ARCHIVE"
    assert outcomes.load()["records"] == []
