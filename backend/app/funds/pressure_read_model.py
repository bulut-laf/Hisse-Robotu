from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from statistics import median
from typing import Callable, Mapping

import pandas as pd

from .contracts import DataQualityState
from .portfolio_tracking import (
    FundPortfolioChangeSet,
    FundPortfolioSnapshot,
    FundPortfolioSnapshotJsonStore,
    PortfolioSnapshotStoreError,
    StockFundActivity,
    aggregate_stock_fund_activity,
    compare_portfolio_snapshots,
)
from .free_float_store import (
    FreeFloatJsonStore,
    FreeFloatSourceError,
    default_free_float_store,
    read_canonical_free_float,
)
from .pressure_risk import (
    StockFundPressureInput,
    StockFundPressureProfile,
    build_pressure_profiles,
    calculate_concentration,
    calculate_exit_liquidity,
)


MarketDataLoader = Callable[[str], pd.DataFrame]


@dataclass(frozen=True, slots=True)
class FundPressureReadModel:
    inputs: Mapping[str, StockFundPressureInput]
    profiles: Mapping[str, StockFundPressureProfile]
    warnings: tuple[str, ...] = ()
    free_float_source_state: str = "UNAVAILABLE"
    automatic_trade_authority: str = "NONE"


def _latest_and_changes(
    snapshots: tuple[FundPortfolioSnapshot, ...],
) -> tuple[dict[str, FundPortfolioSnapshot], tuple[FundPortfolioChangeSet, ...]]:
    grouped: dict[str, list[FundPortfolioSnapshot]] = {}
    for snapshot in snapshots:
        grouped.setdefault(snapshot.canonical_fund_id, []).append(snapshot)

    latest: dict[str, FundPortfolioSnapshot] = {}
    changes: list[FundPortfolioChangeSet] = []
    for fund_id, rows in sorted(grouped.items()):
        current = max(
            rows,
            key=lambda item: (
                item.portfolio_date,
                item.publication_date,
                item.ingested_at,
                item.provider,
            ),
        )
        latest[fund_id] = current
        comparable = sorted(
            (item for item in rows if item.provider == current.provider),
            key=lambda item: (item.portfolio_date, item.publication_date, item.ingested_at),
        )
        if len(comparable) >= 2:
            changes.append(compare_portfolio_snapshots(comparable[-2], comparable[-1]))
    return latest, tuple(changes)


def _market_symbol(symbol: str) -> str:
    clean = symbol.strip().upper()
    return clean if "." in clean else f"{clean}.IS"


def _decimal(value: object) -> Decimal:
    return Decimal(str(float(value)))


def _market_metrics(frame: pd.DataFrame) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    if frame is None or len(frame) < 20:
        raise ValueError("FUND_PRESSURE_MARKET_DATA_INSUFFICIENT")
    last20 = frame.tail(20).copy()
    close = pd.to_numeric(last20["Close"], errors="coerce")
    volume = pd.to_numeric(last20["Volume"], errors="coerce")
    traded_value = close * volume
    valid = pd.DataFrame({"close": close, "volume": volume, "value": traded_value}).dropna()
    valid = valid[(valid["close"] > 0) & (valid["volume"] >= 0)]
    if len(valid) < 20:
        raise ValueError("FUND_PRESSURE_MARKET_DATA_INSUFFICIENT")

    adv20 = _decimal(valid["value"].mean())
    median_value = _decimal(median(float(v) for v in valid["value"]))
    returns = valid["close"].pct_change()
    down_mask = returns < 0
    total_value = float(valid["value"].sum())
    down_value = float(valid.loc[down_mask, "value"].sum())
    down_ratio = Decimal("0") if total_value <= 0 else Decimal(str(down_value / total_value))
    first_close = float(valid["close"].iloc[0])
    last_close = float(valid["close"].iloc[-1])
    return20 = Decimal(str(last_close / first_close - 1.0))
    return adv20, median_value, down_ratio, return20


def build_fund_pressure_read_model(
    store: FundPortfolioSnapshotJsonStore,
    *,
    free_float_shares_by_symbol: Mapping[str, Decimal] | None = None,
    free_float_store: FreeFloatJsonStore | None = None,
    market_data_loader: MarketDataLoader | None = None,
    min_universe_size: int = 30,
) -> FundPressureReadModel:
    """Build observational stock-level fund-pressure inputs from persisted snapshots.

    The model reuses the current append-only fund snapshot store and canonical OHLCV
    loader. Free-float is accepted only from an explicit caller-provided canonical
    mapping; when none exists in the repository, Fon/FDO remains unavailable rather
    than being guessed from another provider.
    """
    try:
        snapshots = store.list_snapshots()
    except PortfolioSnapshotStoreError:
        raise

    latest_by_fund, change_sets = _latest_and_changes(snapshots)
    activity = {item.symbol: item for item in aggregate_stock_fund_activity(change_sets)}
    warnings: list[str] = []
    free_float_source_state = "UNAVAILABLE"
    if free_float_shares_by_symbol is not None:
        free_float = {
            str(symbol).strip().upper().removesuffix(".IS"): Decimal(str(value))
            for symbol, value in free_float_shares_by_symbol.items()
            if str(symbol).strip()
        }
        free_float_source_state = "READY" if free_float else "UNAVAILABLE"
    else:
        try:
            free_float_result = read_canonical_free_float(
                free_float_store or default_free_float_store()
            )
        except FreeFloatSourceError as exc:
            free_float = {}
            warnings.append(f"FREE_FLOAT_SOURCE_UNAVAILABLE:{exc}")
        else:
            free_float = dict(free_float_result.shares_by_symbol)
            free_float_source_state = free_float_result.source_state
            if free_float_result.stale_symbols:
                warnings.append(
                    "FREE_FLOAT_STALE:" + ",".join(free_float_result.stale_symbols[:20])
                )

    fund_shares: dict[str, dict[str, Decimal]] = {}
    fund_values: dict[str, Decimal] = {}
    observation_dates: dict[str, date] = {}
    snapshot_quality: dict[str, DataQualityState] = {}

    for fund_id, snapshot in latest_by_fund.items():
        for position in snapshot.positions:
            if position.asset_type != "EQUITY":
                continue
            symbol = position.symbol
            observation_dates[symbol] = max(
                observation_dates.get(symbol, snapshot.portfolio_date),
                snapshot.portfolio_date,
            )
            if position.shares_held is not None:
                fund_shares.setdefault(symbol, {})[fund_id] = position.shares_held
            if position.market_value is not None:
                fund_values[symbol] = fund_values.get(symbol, Decimal("0")) + position.market_value
            existing_quality = snapshot_quality.get(symbol, DataQualityState.VALID)
            if snapshot.data_quality_state is not DataQualityState.VALID:
                existing_quality = DataQualityState.PARTIAL
            snapshot_quality[symbol] = existing_quality

    # Relevant-universe FDO state:
    # a globally healthy canonical FDO store must not be reported as READY
    # when none of the symbols in this read-model universe has canonical FDO.
    relevant_symbols = set(fund_shares) | set(fund_values)
    if free_float_source_state == "READY":
        free_float_source_state = (
            "READY"
            if any(symbol in free_float for symbol in relevant_symbols)
            else "UNAVAILABLE"
        )

    if market_data_loader is None:
        def loader(symbol: str) -> pd.DataFrame:
            from backend.app.data.market_data import fiyat_verisi_getir
            return fiyat_verisi_getir(
                symbol,
                islem_gunu=20,
                indirme_donemi="3mo",
                yalnizca_tamamlanmis_gunler=True,
            )
    else:
        loader = market_data_loader

    inputs: dict[str, StockFundPressureInput] = {}
    for symbol in sorted(set(fund_shares) | set(fund_values)):
        ownership = calculate_concentration(
            fund_shares.get(symbol, {}),
            free_float_shares=free_float.get(symbol),
        )
        total_value = fund_values.get(symbol)
        market_ok = True
        try:
            adv20, median_value, down_ratio, return20 = _market_metrics(loader(_market_symbol(symbol)))
            stress_capacity = median_value * Decimal("0.05")
        except Exception as exc:
            market_ok = False
            adv20 = median_value = stress_capacity = down_ratio = return20 = None
            warnings.append(f"{symbol}:MARKET_DATA_UNAVAILABLE:{exc}")

        liquidity = calculate_exit_liquidity(
            total_value,
            adv20,
            median_daily_value_20=median_value,
            stressed_liquidity_capacity=stress_capacity,
        )
        activity_item: StockFundActivity | None = activity.get(symbol)
        quality = snapshot_quality.get(symbol, DataQualityState.PARTIAL)
        if (
            not market_ok
            or symbol not in free_float
            or activity_item is None
        ):
            quality = DataQualityState.PARTIAL

        inputs[symbol] = StockFundPressureInput(
            symbol=symbol,
            observation_date=observation_dates[symbol],
            ownership=ownership,
            liquidity=liquidity,
            ownership_change_20d=None,
            distribution_breadth_20d=(
                None if activity_item is None else activity_item.distribution_breadth
            ),
            down_volume_ratio_20d=down_ratio,
            return_20d=return20,
            data_quality_state=quality,
        )

    profiles = build_pressure_profiles(inputs, min_universe_size=min_universe_size)
    return FundPressureReadModel(
        inputs=inputs,
        profiles=profiles,
        warnings=tuple(warnings),
        free_float_source_state=free_float_source_state,
    )
