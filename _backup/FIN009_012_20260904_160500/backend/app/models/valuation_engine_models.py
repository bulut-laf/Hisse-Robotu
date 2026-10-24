from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class ForecastAssumptions:
    revenue_growth: tuple[Decimal, ...]
    ebit_margin: tuple[Decimal, ...]
    tax_rate: Decimal
    depreciation_to_revenue: Decimal
    capex_to_revenue: Decimal
    nwc_to_revenue: Decimal


@dataclass(frozen=True)
class ForecastYear:
    year: int
    revenue: Decimal
    ebit: Decimal
    nopat: Decimal
    depreciation: Decimal
    capex: Decimal
    nwc: Decimal
    delta_nwc: Decimal
    fcff: Decimal


@dataclass(frozen=True)
class ForecastScenario:
    name: str
    base_year: int
    base_revenue: Decimal
    years: tuple[ForecastYear, ...]
    assumptions: ForecastAssumptions


@dataclass(frozen=True)
class ForecastBundle:
    symbol: str
    as_of_date: date
    bear: ForecastScenario
    base: ForecastScenario
    bull: ForecastScenario
    confidence: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class DCFResult:
    method: str
    scenario: str
    enterprise_value: Decimal | None
    equity_value: Decimal | None
    fair_value_per_share: Decimal | None
    terminal_value: Decimal | None
    terminal_value_share: Decimal | None
    discount_rate: Decimal
    terminal_growth: Decimal
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ValuationModelInput:
    name: str
    fair_value_per_share: Decimal | None
    weight: Decimal
    confidence: str = "MEDIUM"


@dataclass(frozen=True)
class CompositeFairValueResult:
    symbol: str
    as_of_date: date
    bear_value: Decimal | None
    base_value: Decimal | None
    bull_value: Decimal | None
    weighted_models: tuple[tuple[str, Decimal, Decimal], ...]
    confidence: str
    dispersion: Decimal | None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class MarginOfSafetyResult:
    symbol: str
    as_of_date: date
    current_price: Decimal
    base_fair_value: Decimal
    required_margin_of_safety: Decimal
    attractive_entry_price: Decimal
    upside_downside_to_base: Decimal
    current_margin_of_safety: Decimal
    status: str
