from backend.app.funds.free_float_store import FreeFloatJsonStore
from datetime import date, datetime, timezone
from decimal import Decimal

import pandas as pd

from backend.app.funds.contracts import DataQualityState
from backend.app.funds.portfolio_tracking import (
    FundPortfolioPosition,
    FundPortfolioSnapshot,
    FundPortfolioSnapshotJsonStore,
)
from backend.app.funds.pressure_read_model import build_fund_pressure_read_model


def _position(fund, day, symbol, shares, value):
    return FundPortfolioPosition(
        canonical_fund_id=fund,
        portfolio_date=day,
        symbol=symbol,
        asset_type="EQUITY",
        shares_held=Decimal(shares),
        market_value=Decimal(value),
        portfolio_weight=Decimal("0.5"),
    )


def _snapshot(fund, day, *positions):
    return FundPortfolioSnapshot(
        canonical_fund_id=fund,
        portfolio_date=day,
        publication_date=day,
        ingested_at=datetime(day.year, day.month, day.day, 12, tzinfo=timezone.utc),
        provider="KAP",
        positions=tuple(positions),
        data_quality_state=DataQualityState.VALID,
    )


def _market(_symbol):
    close = [100 + index for index in range(20)]
    close[5] = 99
    volume = [1000 + index * 10 for index in range(20)]
    return pd.DataFrame({"Close": close, "Volume": volume})


def test_read_model_aggregates_latest_fund_positions_and_market_liquidity(tmp_path):
    store = FundPortfolioSnapshotJsonStore(tmp_path / "portfolio.json")
    may = date(2026, 5, 31)
    june = date(2026, 6, 30)
    store.append((
        _snapshot("fund:tefas:A", may, _position("fund:tefas:A", may, "THYAO", "100", "10000")),
        _snapshot("fund:tefas:A", june, _position("fund:tefas:A", june, "THYAO", "80", "8000")),
        _snapshot("fund:tefas:B", june, _position("fund:tefas:B", june, "THYAO", "20", "2000")),
    ))

    model = build_fund_pressure_read_model(
        store,
        free_float_shares_by_symbol={"THYAO": Decimal("400")},
        market_data_loader=_market,
        min_universe_size=1,
    )
    raw = model.inputs["THYAO"]
    assert raw.ownership.fund_owned_shares == Decimal("100")
    assert raw.ownership.fund_free_float_ratio == Decimal("0.25")
    assert raw.liquidity.total_fund_position_value == Decimal("10000")
    assert raw.liquidity.adv20_value is not None
    assert raw.liquidity.liquidation_days_normal is not None
    assert raw.distribution_breadth_20d == Decimal("1")
    assert raw.return_20d is not None
    assert raw.down_volume_ratio_20d is not None
    assert raw.data_quality_state is DataQualityState.VALID
    assert model.profiles["THYAO"].automatic_trade_authority == "NONE"


def test_missing_free_float_is_fail_open_for_other_observational_metrics_but_not_guessed(tmp_path):
    store = FundPortfolioSnapshotJsonStore(tmp_path / "portfolio.json")
    day = date(2026, 6, 30)
    store.append((_snapshot(
        "fund:tefas:A", day, _position("fund:tefas:A", day, "ASELS", "50", "5000")
    ),))

    free_float_store = FreeFloatJsonStore(tmp_path / "free_float.json")
    model = build_fund_pressure_read_model(
        store,
        free_float_store=free_float_store,
        market_data_loader=_market,
        min_universe_size=1,
    )
    raw = model.inputs["ASELS"]
    assert raw.ownership.free_float_shares is None
    assert raw.ownership.fund_free_float_ratio is None
    assert raw.liquidity.adv20_value is not None
    assert raw.data_quality_state is DataQualityState.PARTIAL
    assert model.free_float_source_state == "UNAVAILABLE"


def test_market_failure_is_isolated_per_symbol(tmp_path):
    store = FundPortfolioSnapshotJsonStore(tmp_path / "portfolio.json")
    day = date(2026, 6, 30)
    store.append((
        _snapshot("fund:tefas:A", day, _position("fund:tefas:A", day, "AAA", "10", "1000")),
        _snapshot("fund:tefas:B", day, _position("fund:tefas:B", day, "BBB", "10", "1000")),
    ))

    def loader(symbol):
        if symbol.startswith("AAA"):
            raise ValueError("offline")
        return _market(symbol)

    model = build_fund_pressure_read_model(
        store,
        market_data_loader=loader,
        min_universe_size=1,
    )
    assert model.inputs["AAA"].liquidity.adv20_value is None
    assert model.inputs["BBB"].liquidity.adv20_value is not None
    assert any(
    warning.startswith("AAA:MARKET_DATA_UNAVAILABLE")
    for warning in model.warnings
)
