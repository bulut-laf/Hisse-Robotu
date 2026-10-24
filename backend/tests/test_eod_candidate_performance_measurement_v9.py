from __future__ import annotations

from types import SimpleNamespace
import pandas as pd

from backend.app.analysis.eod_candidate_performance_runtime import settle_eod_candidate_performance_history


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
        self.records = [item for item in self.records if not (
            item.get("run_date") == saved.get("run_date") and item.get("phase") == saved.get("phase")
        )]
        self.records.append(saved)
        return saved


def _candidate_frame():
    index = pd.to_datetime([
        "2026-08-28", "2026-08-31", "2026-09-01",
        "2026-09-02", "2026-09-03", "2026-09-04",
    ])
    return pd.DataFrame({
        "High": [101, 104, 106, 108, 107, 110],
        "Low": [99, 98, 99, 100, 101, 102],
        "Close": [100, 103, 105, 104, 106, 109],
    }, index=index)


def test_history_completes_t1_t3_t5_and_calculates_mfe_mae():
    source = FakeSourceStore([{
        "run_date": "2026-08-28",
        "buy_candidate_symbols": ["AAA.IS"],
        "created_at": "fixture",
    }])
    target = FakeOutcomeStore()

    def fetcher(symbols, **kwargs):
        assert tuple(symbols) == ("AAA",)
        assert kwargs["indirme_donemi"] == "3mo"
        return SimpleNamespace(veriler={"AAA.IS": _candidate_frame()})

    result = settle_eod_candidate_performance_history(
        current_date="2026-10-09", eod_store=source,
        outcome_store=target, market_data_fetcher=fetcher,
    )
    assert result["status"] == "SUCCESS"
    assert result["processed_count"] == 1
    assert len(target.records) == 1

    record = target.records[0]
    assert record["run_date"] == "2026-08-28"
    assert record["candidate_count"] == 1
    assert record["status"] == "SUCCESS"
    candidate = record["candidates"][0]
    assert candidate["symbol"] == "AAA"
    assert candidate["status"] == "COMPLETE"
    assert [item["horizon"] for item in candidate["horizons"]] == [1, 3, 5]

    t1, t3, t5 = candidate["horizons"]
    assert t1["target_date"] == "2026-08-31"
    assert t3["target_date"] == "2026-09-02"
    assert t5["target_date"] == "2026-09-04"
    assert round(t1["return"], 6) == 0.03
    assert round(t1["mfe"], 6) == 0.04
    assert round(t1["mae"], 6) == -0.02
    assert round(t3["return"], 6) == 0.04
    assert round(t3["mfe"], 6) == 0.08
    assert round(t3["mae"], 6) == -0.02
    assert round(t5["return"], 6) == 0.09
    assert round(t5["mfe"], 6) == 0.10
    assert round(t5["mae"], 6) == -0.02


def test_history_keeps_same_day_candidate_pending_without_fetching():
    source = FakeSourceStore([{"run_date": "2026-10-09", "buy_candidate_symbols": ["AAA"]}])
    target = FakeOutcomeStore()

    def forbidden_fetcher(*args, **kwargs):
        raise AssertionError("same-day records must not fetch data")

    result = settle_eod_candidate_performance_history(
        current_date="2026-10-09", eod_store=source,
        outcome_store=target, market_data_fetcher=forbidden_fetcher,
    )
    assert result["waiting_count"] == 1
    assert result["processed_count"] == 0
    assert target.records == []


def test_history_isolates_fetch_failure_and_continues_to_empty_candidate_record():
    source = FakeSourceStore([
        {"run_date": "2026-08-27", "buy_candidate_symbols": ["AAA"]},
        {"run_date": "2026-08-28", "buy_candidate_symbols": []},
    ])
    target = FakeOutcomeStore()

    def fetcher(*args, **kwargs):
        raise RuntimeError("temporary data issue")

    result = settle_eod_candidate_performance_history(
        current_date="2026-10-09", eod_store=source,
        outcome_store=target, market_data_fetcher=fetcher,
    )
    assert result["failure_count"] == 1
    assert any(item.get("run_date") == "2026-08-27" and item.get("status") == "DATA_UNAVAILABLE"
               for item in result["results"])
    assert any(item.get("run_date") == "2026-08-28" for item in target.records)
