from __future__ import annotations

from decimal import Decimal

from ..models.valuation_engine_models import DCFResult, ForecastScenario


class DCFValuationError(ValueError):
    pass


def _validate_rate(discount_rate: Decimal, terminal_growth: Decimal) -> None:
    if discount_rate <= Decimal("0") or discount_rate >= Decimal("0.60"):
        raise DCFValuationError("discount rate out of supported range")
    if terminal_growth < Decimal("-0.05") or terminal_growth >= discount_rate:
        raise DCFValuationError("terminal growth must be below discount rate")


def value_fcff(
    forecast: ForecastScenario,
    *,
    wacc: Decimal,
    terminal_growth: Decimal,
    net_debt: Decimal,
    diluted_shares: Decimal,
) -> DCFResult:
    _validate_rate(wacc, terminal_growth)
    if diluted_shares <= 0:
        raise DCFValuationError("diluted shares must be positive")
    if not forecast.years:
        raise DCFValuationError("forecast has no years")

    pv_explicit = Decimal("0")
    for i, row in enumerate(forecast.years, start=1):
        pv_explicit += row.fcff / ((Decimal("1") + wacc) ** i)

    last_fcff = forecast.years[-1].fcff
    warnings: list[str] = []
    if last_fcff <= 0:
        return DCFResult("FCFF", forecast.name, None, None, None, None, None, wacc, terminal_growth, ("NEGATIVE_TERMINAL_FCFF",))

    terminal_value = last_fcff * (Decimal("1") + terminal_growth) / (wacc - terminal_growth)
    pv_terminal = terminal_value / ((Decimal("1") + wacc) ** len(forecast.years))
    enterprise_value = pv_explicit + pv_terminal
    equity_value = enterprise_value - net_debt
    if equity_value <= 0:
        warnings.append("NONPOSITIVE_EQUITY_VALUE")
        fair_value = None
    else:
        fair_value = equity_value / diluted_shares
    terminal_share = pv_terminal / enterprise_value if enterprise_value > 0 else None
    if terminal_share is not None and terminal_share > Decimal("0.75"):
        warnings.append("TERMINAL_VALUE_DOMINANT")

    return DCFResult("FCFF", forecast.name, enterprise_value, equity_value, fair_value, terminal_value, terminal_share, wacc, terminal_growth, tuple(warnings))


def value_fcfe(
    cash_flows_to_equity: tuple[Decimal, ...],
    *,
    scenario: str,
    cost_of_equity: Decimal,
    terminal_growth: Decimal,
    diluted_shares: Decimal,
) -> DCFResult:
    _validate_rate(cost_of_equity, terminal_growth)
    if diluted_shares <= 0:
        raise DCFValuationError("diluted shares must be positive")
    if not cash_flows_to_equity:
        raise DCFValuationError("fcfe cash flows required")
    last = cash_flows_to_equity[-1]
    if last <= 0:
        return DCFResult("FCFE", scenario.upper(), None, None, None, None, None, cost_of_equity, terminal_growth, ("NEGATIVE_TERMINAL_FCFE",))

    pv_explicit = sum((cf / ((Decimal("1") + cost_of_equity) ** i) for i, cf in enumerate(cash_flows_to_equity, start=1)), Decimal("0"))
    terminal_value = last * (Decimal("1") + terminal_growth) / (cost_of_equity - terminal_growth)
    pv_terminal = terminal_value / ((Decimal("1") + cost_of_equity) ** len(cash_flows_to_equity))
    equity_value = pv_explicit + pv_terminal
    terminal_share = pv_terminal / equity_value if equity_value > 0 else None
    warnings: list[str] = []
    if terminal_share is not None and terminal_share > Decimal("0.75"):
        warnings.append("TERMINAL_VALUE_DOMINANT")
    return DCFResult("FCFE", scenario.upper(), None, equity_value, equity_value / diluted_shares, terminal_value, terminal_share, cost_of_equity, terminal_growth, tuple(warnings))
