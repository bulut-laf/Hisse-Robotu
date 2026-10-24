from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Mapping

from .portfolio_tracking import (
    FundPortfolioSnapshot,
    FundPortfolioSnapshotJsonStore,
)
from .store import FundObservationJsonStore


@dataclass(frozen=True, slots=True)
class FundProfileReadModel:
    canonical_fund_id: str
    fund_code: str
    observation_date: date | None
    unit_price: Decimal | None
    daily_return: Decimal | None
    fund_size: Decimal | None
    investor_count: int | None
    shares_outstanding: Decimal | None
    returns: Mapping[str, Decimal | None]
    latest_portfolio: FundPortfolioSnapshot | None
    observation_count: int
    price_history: tuple[tuple[date, Decimal], ...]
    fund_size_history: tuple[tuple[date, Decimal], ...]
    investor_history: tuple[tuple[date, int], ...]


def _decimal(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _history(
    store: FundObservationJsonStore,
    canonical_fund_id: str,
) -> tuple[tuple[date, Decimal, dict[str, object]], ...]:
    rows: list[tuple[date, Decimal, dict[str, object]]] = []
    for raw in store.list_records():
        if raw.get("record_type") != "FundDailyObservation":
            continue
        if str(raw.get("canonical_fund_id") or "") != canonical_fund_id:
            continue
        if str(raw.get("provider") or "").upper() != "TEFAS":
            continue
        price = _decimal(raw.get("unit_price"))
        if price is None or price <= 0:
            continue
        try:
            observed = date.fromisoformat(str(raw.get("observation_date")))
        except Exception:
            continue
        rows.append((observed, price, dict(raw)))
    rows.sort(key=lambda item: item[0])
    return tuple(rows)


def _return_from_target(
    history: tuple[tuple[date, Decimal, dict[str, object]], ...],
    *,
    latest_date: date,
    latest_price: Decimal,
    target_date: date,
    allow_forward_fallback: bool = False,
) -> Decimal | None:
    candidates = [item for item in history if item[0] <= target_date]
    if candidates:
        _, base_price, _ = candidates[-1]
    else:
        if not allow_forward_fallback:
            return None
        # TEFAS 12M history can begin on the first trading day after the
        # 1Y calendar target (for example, target Sunday -> first row Monday).
        # This fallback is intentionally opt-in and used only for 1Y.
        forward_candidates = [
            item
            for item in history
            if target_date < item[0] <= target_date + timedelta(days=7)
        ]
        if not forward_candidates:
            return None
        _, base_price, _ = forward_candidates[0]
    if base_price <= 0:
        return None
    return latest_price / base_price - Decimal("1")


def _latest_portfolio(
    store: FundPortfolioSnapshotJsonStore,
    canonical_fund_id: str,
) -> FundPortfolioSnapshot | None:
    candidates = [
        item for item in store.list_snapshots()
        if item.canonical_fund_id == canonical_fund_id
    ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: (
            item.portfolio_date,
            item.publication_date,
            item.ingested_at,
        ),
    )


def build_fund_profile_read_model(
    canonical_fund_id: str,
    *,
    observation_store: FundObservationJsonStore,
    portfolio_store: FundPortfolioSnapshotJsonStore,
) -> FundProfileReadModel:
    fund_id = str(canonical_fund_id or "").strip()
    if not fund_id.startswith("fund:tefas:"):
        raise ValueError("FUND_PROFILE_CANONICAL_ID_INVALID")

    history = _history(observation_store, fund_id)
    latest_date = None
    latest_price = None
    latest_row: dict[str, object] = {}
    if history:
        latest_date, latest_price, latest_row = history[-1]

    returns: dict[str, Decimal | None] = {
        "1H": None, "1A": None, "3A": None, "6A": None, "YTD": None, "1Y": None
    }
    if latest_date is not None and latest_price is not None:
        targets = {
            "1H": latest_date - timedelta(days=7),
            "1A": latest_date - timedelta(days=30),
            "3A": latest_date - timedelta(days=90),
            "6A": latest_date - timedelta(days=180),
            "YTD": date(latest_date.year, 1, 1),
            "1Y": latest_date - timedelta(days=365),
        }
        returns = {
            key: _return_from_target(
                history,
                latest_date=latest_date,
                latest_price=latest_price,
                target_date=target,
                allow_forward_fallback=(key == "1Y"),
            )
            for key, target in targets.items()
        }

    investor_raw = latest_row.get("investor_count")
    investor_count = None
    if investor_raw not in (None, ""):
        try:
            investor_count = int(Decimal(str(investor_raw)))
        except (InvalidOperation, ValueError):
            investor_count = None

    price_history = tuple((observed, price) for observed, price, _ in history)

    daily_return = _decimal(latest_row.get("daily_return"))
    if daily_return is None and len(price_history) >= 2:
        previous_price = None
        for observed, price in reversed(price_history[:-1]):
            if observed < latest_date:
                previous_price = price
                break
        if previous_price is not None and previous_price > 0:
            daily_return = latest_price / previous_price - Decimal("1")
    fund_size_history: list[tuple[date, Decimal]] = []
    investor_history: list[tuple[date, int]] = []
    for observed, _price, raw in history:
        size = _decimal(raw.get("fund_size"))
        if size is not None and size >= 0:
            fund_size_history.append((observed, size))
        raw_investors = raw.get("investor_count")
        if raw_investors not in (None, ""):
            try:
                count = int(Decimal(str(raw_investors)))
            except (InvalidOperation, ValueError):
                count = -1
            if count >= 0:
                investor_history.append((observed, count))

    return FundProfileReadModel(
        canonical_fund_id=fund_id,
        fund_code=fund_id.rsplit(":", 1)[-1],
        observation_date=latest_date,
        unit_price=latest_price,
        daily_return=daily_return,
        fund_size=_decimal(latest_row.get("fund_size")),
        investor_count=investor_count,
        shares_outstanding=_decimal(latest_row.get("shares_outstanding")),
        returns=returns,
        latest_portfolio=_latest_portfolio(portfolio_store, fund_id),
        observation_count=len(history),
        price_history=price_history,
        fund_size_history=tuple(fund_size_history),
        investor_history=tuple(investor_history),
    )
