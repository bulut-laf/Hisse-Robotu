from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from backend.app.funds.contracts import DataQualityState
from backend.app.funds.portfolio_tracking import (
    FundPortfolioPosition,
    FundPortfolioSnapshot,
    FundPortfolioSnapshotJsonStore,
    PortfolioSnapshotStoreError,
    PositionChangeConfidence,
    PositionChangeKind,
    WeightChangeDirection,
    aggregate_stock_fund_activity,
    compare_portfolio_snapshots,
)

UTC = timezone.utc


def position(fund: str, day: date, symbol: str, *, shares=None, weight=None, value=None):
    return FundPortfolioPosition(
        canonical_fund_id=fund,
        portfolio_date=day,
        symbol=symbol,
        asset_type="EQUITY",
        shares_held=None if shares is None else Decimal(str(shares)),
        market_value=None if value is None else Decimal(str(value)),
        portfolio_weight=None if weight is None else Decimal(str(weight)),
    )


def snapshot(fund: str, day: date, *positions, quality=DataQualityState.VALID):
    return FundPortfolioSnapshot(
        canonical_fund_id=fund,
        portfolio_date=day,
        publication_date=day,
        ingested_at=datetime(day.year, day.month, day.day, 12, tzinfo=UTC),
        provider="TEFAS",
        positions=tuple(positions),
        data_quality_state=quality,
    )


def test_snapshot_store_is_append_only_and_idempotent(tmp_path):
    day = date(2026, 8, 31)
    item = snapshot("fund:tefas:AAA", day, position("fund:tefas:AAA", day, "THYAO", shares=100))
    store = FundPortfolioSnapshotJsonStore(tmp_path / "snapshots.json")
    assert store.append((item,)).inserted == 1
    assert store.append((item,)).unchanged == 1

    changed = snapshot("fund:tefas:AAA", day, position("fund:tefas:AAA", day, "THYAO", shares=101))
    with pytest.raises(PortfolioSnapshotStoreError, match="PORTFOLIO_SNAPSHOT_CONFLICT"):
        store.append((changed,))


def test_change_engine_uses_share_counts_for_confirmed_increase_and_reduction():
    first_day = date(2026, 7, 31)
    second_day = date(2026, 8, 31)
    fund = "fund:tefas:AAA"
    previous = snapshot(
        fund,
        first_day,
        position(fund, first_day, "THYAO", shares=100, weight="0.10"),
        position(fund, first_day, "ASELS", shares=200, weight="0.20"),
    )
    current = snapshot(
        fund,
        second_day,
        position(fund, second_day, "THYAO", shares=130, weight="0.12"),
        position(fund, second_day, "ASELS", shares=150, weight="0.15"),
    )
    changes = {item.symbol: item for item in compare_portfolio_snapshots(previous, current).changes}
    assert changes["THYAO"].kind is PositionChangeKind.INCREASED
    assert changes["THYAO"].confidence is PositionChangeConfidence.HIGH
    assert changes["THYAO"].share_change == Decimal("30")
    assert changes["ASELS"].kind is PositionChangeKind.REDUCED


def test_weight_change_alone_is_not_mislabeled_as_confirmed_trade():
    first_day = date(2026, 7, 31)
    second_day = date(2026, 8, 31)
    fund = "fund:tefas:AAA"
    previous = snapshot(fund, first_day, position(fund, first_day, "THYAO", weight="0.05", value=1000))
    current = snapshot(fund, second_day, position(fund, second_day, "THYAO", weight="0.08", value=1500))
    change = compare_portfolio_snapshots(previous, current).changes[0]
    assert change.kind is PositionChangeKind.UNKNOWN
    assert change.weight_direction is WeightChangeDirection.INCREASED
    assert change.reason == "WEIGHT_OR_VALUE_CHANGE_ONLY_NOT_CONFIRMED_TRADE"


def test_partial_snapshot_cannot_prove_full_exit():
    first_day = date(2026, 7, 31)
    second_day = date(2026, 8, 31)
    fund = "fund:tefas:AAA"
    previous = snapshot(fund, first_day, position(fund, first_day, "THYAO", shares=100))
    current = snapshot(fund, second_day, quality=DataQualityState.PARTIAL)
    change = compare_portfolio_snapshots(previous, current).changes[0]
    assert change.kind is PositionChangeKind.UNKNOWN
    assert "PARTIAL" in change.reason


def test_new_entry_and_full_exit_feed_stock_breadth():
    first_day = date(2026, 7, 31)
    second_day = date(2026, 8, 31)
    a = "fund:tefas:AAA"
    b = "fund:tefas:BBB"
    set_a = compare_portfolio_snapshots(
        snapshot(a, first_day),
        snapshot(a, second_day, position(a, second_day, "THYAO", shares=100)),
    )
    set_b = compare_portfolio_snapshots(
        snapshot(b, first_day, position(b, first_day, "THYAO", shares=100)),
        snapshot(b, second_day),
    )
    activity = aggregate_stock_fund_activity((set_a, set_b))[0]
    assert activity.symbol == "THYAO"
    assert activity.new_fund_count == 1
    assert activity.exited_fund_count == 1
    assert activity.accumulation_breadth == Decimal("0.5")
    assert activity.distribution_breadth == Decimal("0.5")


def test_snapshot_store_typed_read_model_roundtrip(tmp_path):
    day = date(2026, 8, 31)
    original = snapshot(
        "fund:tefas:AAA",
        day,
        position("fund:tefas:AAA", day, "THYAO", shares=123, weight="0.12", value=4567),
    )
    store = FundPortfolioSnapshotJsonStore(tmp_path / "snapshots.json")
    store.append((original,))

    loaded = store.list_snapshots()
    assert loaded == (original,)
    assert store.list_records()[0]["snapshot_id"] == original.snapshot_id
