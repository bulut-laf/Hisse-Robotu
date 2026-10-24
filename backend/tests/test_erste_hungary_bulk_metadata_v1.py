from __future__ import annotations

from datetime import date
from decimal import Decimal
import json

from backend.app.funds.international.erste_hungary_bulk_metadata import (
    collect_bulk_metadata,
    fund_to_record,
    load_completed_isins,
)
from backend.app.funds.international.erste_hungary_comparison import (
    ErsteComparisonFund,
)


def _fund(isin: str) -> ErsteComparisonFund:
    return ErsteComparisonFund(
        isin=isin,
        name=f"Fund {isin}",
        fund_manager="Manager",
        inception_date=date(2020, 1, 2),
        currency="EUR",
        return_ytd=Decimal("0.10"),
        return_1y=Decimal("0.20"),
        return_5y=None,
        volatility_1y=Decimal("0.12"),
        volatility_3y=None,
        volatility_5y=None,
        max_drawdown_1y=Decimal("-0.08"),
        max_drawdown_5y=None,
        nav=Decimal("12.34"),
        nav_date=date(2026, 9, 24),
        net_asset_value=Decimal("123456"),
        category_raw="Category",
        risk_raw="Risk",
        source_url="https://example.invalid",
    )


def test_record_serialization_is_json_safe():
    record = fund_to_record(_fund("HU0000000001"))
    assert record["return_1y"] == "0.20"
    assert record["nav_date"] == "2026-09-24"
    assert record["nav"] == "12.34"


def test_completed_isins_ignore_invalid_json(tmp_path):
    path = tmp_path / "success.jsonl"
    path.write_text(
        '{"isin":"HU0000000001"}\nnot-json\n{"isin":"HU0000000002"}\n',
        encoding="utf-8",
    )
    assert load_completed_isins(path) == {
        "HU0000000001",
        "HU0000000002",
    }


def test_bulk_collection_is_resumable(tmp_path):
    success = tmp_path / "success.jsonl"
    failure = tmp_path / "failure.jsonl"

    calls = []

    def fake_fetcher(isin, **kwargs):
        calls.append(isin)
        return _fund(isin)

    first = collect_bulk_metadata(
        ["HU0000000001", "HU0000000002"],
        success_jsonl=success,
        failure_jsonl=failure,
        fetcher=fake_fetcher,
        request_delay_seconds=0,
    )

    assert first.success_count == 2
    assert first.completed_total_count == 2
    assert calls == ["HU0000000001", "HU0000000002"]

    calls.clear()

    second = collect_bulk_metadata(
        ["HU0000000001", "HU0000000002"],
        success_jsonl=success,
        failure_jsonl=failure,
        fetcher=fake_fetcher,
        request_delay_seconds=0,
    )

    assert second.attempted_count == 0
    assert second.already_completed_count == 2
    assert calls == []


def test_failures_do_not_count_as_completed(tmp_path):
    success = tmp_path / "success.jsonl"
    failure = tmp_path / "failure.jsonl"

    def fake_fetcher(isin, **kwargs):
        if isin.endswith("2"):
            raise ValueError("broken")
        return _fund(isin)

    result = collect_bulk_metadata(
        ["HU0000000001", "HU0000000002"],
        success_jsonl=success,
        failure_jsonl=failure,
        fetcher=fake_fetcher,
        request_delay_seconds=0,
    )

    assert result.success_count == 1
    assert result.failure_count == 1
    assert result.completed_total_count == 1

    failures = [
        json.loads(line)
        for line in failure.read_text(encoding="utf-8").splitlines()
    ]
    assert failures[0]["isin"] == "HU0000000002"
    assert failures[0]["error_type"] == "ValueError"