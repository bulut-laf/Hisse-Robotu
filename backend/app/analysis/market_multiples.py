from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from ..data.historical_financial_series import HistoricalFinancialSeries
from ..models.valuation_foundation_models import MarketSnapshot, MultipleSnapshot, OwnershipSnapshot


class MarketMultiplesError(ValueError):
    pass


def _safe_div(a: Decimal | None, b: Decimal | None) -> Decimal | None:
    if a is None or b is None or b <= 0:
        return None
    return a / b


def _latest(series: HistoricalFinancialSeries, code: str, kind: str, as_of: datetime | None):
    p = series.latest_value(code, period_kind=kind, as_of=as_of)
    return p.value * p.currency_scale if p else None


def _duration_values(series: HistoricalFinancialSeries, code: str, as_of: datetime | None):
    return list(series.metric_series(code, period_kind="DURATION", as_of=as_of))


def _ttm(series: HistoricalFinancialSeries, code: str, as_of: datetime | None) -> Decimal | None:
    pts = _duration_values(series, code, as_of)
    if not pts:
        return None
    current = pts[-1]
    # If the latest disclosed duration is itself a full year, it is the TTM.
    if current.period_start and (current.period_end - current.period_start).days >= 330:
        return current.value * current.currency_scale

    # For interim reports, TTM = current YTD + prior FY - prior same period.
    if not current.period_start:
        return None
    current_days = (current.period_end - current.period_start).days
    if current_days >= 330:
        return current.value * current.currency_scale

    prior_same = None
    prior_full = None
    for p in reversed(pts[:-1]):
        if p.period_start is None:
            continue
        days = (p.period_end - p.period_start).days
        if prior_same is None and abs(days - current_days) <= 3 and p.period_end.year == current.period_end.year - 1:
            prior_same = p
        if prior_full is None and days >= 330 and p.period_end.year == current.period_end.year - 1:
            prior_full = p
    if prior_same and prior_full:
        return (current.value + prior_full.value - prior_same.value) * current.currency_scale
    return None


def calculate_market_multiples(
    series: HistoricalFinancialSeries,
    ownership: OwnershipSnapshot,
    market: MarketSnapshot,
    *,
    as_of: datetime | None = None,
    ebitda_ttm: Decimal | None = None,
    fcf_ttm: Decimal | None = None,
    dividends_ttm: Decimal | None = None,
) -> MultipleSnapshot:
    if series.symbol != ownership.symbol or series.symbol != market.symbol:
        raise MarketMultiplesError("symbol mismatch across financial/ownership/market inputs")
    if market.price <= 0:
        raise MarketMultiplesError("market price must be positive")
    if ownership.canonical_share_count <= 0:
        raise MarketMultiplesError("share count must be positive")
    if as_of is not None:
        if ownership.published_at is not None and ownership.published_at > as_of:
            raise MarketMultiplesError("ownership data not public as of requested time")
        if market.published_at is not None and market.published_at > as_of:
            raise MarketMultiplesError("market snapshot not public as of requested time")

    shares = ownership.canonical_share_count
    market_cap = market.price * shares
    parent_equity = _latest(series, "PARENT_EQUITY", "INSTANT", as_of) or _latest(series, "TOTAL_EQUITY", "INSTANT", as_of)
    earnings = _ttm(series, "PARENT_NET_INCOME", as_of) or _ttm(series, "NET_INCOME", as_of)
    revenue = _ttm(series, "REVENUE", as_of)

    cash = _latest(series, "CASH_EQUIVALENTS", "INSTANT", as_of) or Decimal("0")
    st = _latest(series, "SHORT_TERM_BORROWINGS", "INSTANT", as_of) or Decimal("0")
    cur_lt = _latest(series, "CURRENT_PORTION_LT_DEBT", "INSTANT", as_of) or Decimal("0")
    lt = _latest(series, "LONG_TERM_BORROWINGS", "INSTANT", as_of) or Decimal("0")
    total_financial_debt = st + cur_lt + lt
    enterprise_value = market_cap + total_financial_debt - cash

    flags: list[str] = []
    pe = _safe_div(market_cap, earnings)
    pb = _safe_div(market_cap, parent_equity)
    ps = _safe_div(market_cap, revenue)
    ev_sales = _safe_div(enterprise_value, revenue)
    ev_ebitda = _safe_div(enterprise_value, ebitda_ttm)
    p_fcf = _safe_div(market_cap, fcf_ttm)
    dividend_yield = _safe_div(dividends_ttm, market_cap)

    if earnings is None:
        flags.append("TTM_EARNINGS_UNAVAILABLE")
    elif earnings <= 0:
        flags.append("PE_NOT_MEANINGFUL_NEGATIVE_EARNINGS")
    if parent_equity is None:
        flags.append("EQUITY_UNAVAILABLE")
    elif parent_equity <= 0:
        flags.append("PB_NOT_MEANINGFUL_NONPOSITIVE_EQUITY")
    if ebitda_ttm is None:
        flags.append("EV_EBITDA_NOT_EVALUATED_WITHOUT_RELIABLE_EBITDA")
    if fcf_ttm is None:
        flags.append("P_FCF_NOT_EVALUATED_WITHOUT_TTM_FCF")

    return MultipleSnapshot(
        symbol=series.symbol,
        as_of_date=market.price_date,
        pe=pe,
        pb=pb,
        ev_ebitda=ev_ebitda,
        ev_sales=ev_sales,
        ps=ps,
        p_fcf=p_fcf,
        dividend_yield=dividend_yield,
        market_cap=market_cap,
        enterprise_value=enterprise_value,
        equity_value_basis=parent_equity,
        earnings_basis=earnings,
        ebitda_basis=ebitda_ttm,
        revenue_basis=revenue,
        fcf_basis=fcf_ttm,
        data_flags=tuple(flags),
    )
