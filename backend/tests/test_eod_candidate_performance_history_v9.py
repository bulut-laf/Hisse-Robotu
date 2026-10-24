from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pandas as pd

from backend.app.analysis.eod_candidate_performance_runtime import (
    settle_eod_candidate_performance_history,
)


class FakeSourceStore:
    def __init__(self, records):
        self.records = records

    def load(self):
        return {"records": self.records}


class FakeOutcomeStore:
    def __init__(self):
        self.path = "fake-performance.json"
        self.records = []

    def load(self):
        return {"records": list(self.records)}

    def save_record(self, record, *, recorded_at=None):
        saved = dict(record)
        saved["recorded_at"] = recorded_at.isoformat() if recorded_at else "test"
        self.records = [
            item for item in self.records
            if not (item.get("run_date") == saved.get("run_date")
                    and item.get("phase") == saved.get("phase"))
        ]
        self.records.append(saved)
        return saved


def _frame():
    idx = pd.to_datetime(["2026-08-28", "2026-08-31", "2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04"])
    return pd.DataFrame(
        {
            "High": [101, 103, 104, 105, 106, 107],
            "Low": [99, 100, 101, 102, 103, 104],
            "Close": [100, 102, 103, 104, 105, 106],
        },
        index=idx,
    )


def test_history_settles_old_record_and_leaves_same_day_pending():
    source = FakeSourceStore([
        {"run_date": "2026-08-28", "buy_candidate_symbols": ["AAA.IS"], "created_at": "x"},
        {"run_date": "2026-10-09", "buy_candidate_symbols": ["BBB.IS"], "created_at": "y"},
    ])
    target = FakeOutcomeStore()
    calls = []

    def fetcher(symbols, **kwargs):
        calls.append(tuple(symbols))
        return SimpleNamespace(veriler={"AAA.IS": _frame()})

    result = settle_eod_candidate_performance_history(
        current_date="2026-10-09",
        eod_store=source,
        outcome_store=target,
        market_data_fetcher=fetcher,
    )

    assert result["record_count"] == 2
    assert len(target.records) == 1
    assert target.records[0]["run_date"] == "2026-08-28"
    assert target.records[0]["candidate_count"] == 1
    assert calls == [("AAA",)]


def test_history_isolates_fetch_failure_and_continues():
    source = FakeSourceStore([
        {"run_date": "2026-08-27", "buy_candidate_symbols": ["AAA"]},
        {"run_date": "2026-08-28", "buy_candidate_symbols": []},
    ])
    target = FakeOutcomeStore()

    def fetcher(symbols, **kwargs):
        raise RuntimeError("temporary data issue")

    result = settle_eod_candidate_performance_history(
        current_date="2026-10-09",
        eod_store=source,
        outcome_store=target,
        market_data_fetcher=fetcher,
    )

    assert result["failure_count"] == 1
    assert any(item["run_date"] == "2026-08-27" and item["status"] == "DATA_UNAVAILABLE"
               for item in result["results"])
    assert any(item.get("run_date") == "2026-08-28" for item in target.records)


def test_history_empty_archive_returns_status():
    result = settle_eod_candidate_performance_history(
        current_date="2026-10-09",
        eod_store=FakeSourceStore([]),
        outcome_store=FakeOutcomeStore(),
        market_data_fetcher=lambda *args, **kwargs: None,
    )
    assert result == {"status": "NO_EOD_ARCHIVE", "processed_count": 0}
