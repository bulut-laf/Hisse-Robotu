"""Performance metrics from dated NAV observations; never invent missing data."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from math import sqrt
from typing import Iterable


@dataclass(frozen=True, order=True)
class NavObservation:
    date: date
    nav: float

    def __post_init__(self):
        if self.nav <= 0:
            raise ValueError("NAV must be greater than zero")


@dataclass(frozen=True)
class PerformanceMetrics:
    observations: int
    first_date: date
    last_date: date
    total_return_pct: float
    annualized_return_pct: float | None
    annualized_volatility_pct: float | None
    max_drawdown_pct: float


def calculate_performance(observations: Iterable[NavObservation], periods_per_year: int = 252) -> PerformanceMetrics:
    if periods_per_year < 1:
        raise ValueError("periods_per_year must be >= 1")
    rows = sorted(observations, key=lambda x: x.date)
    if len(rows) < 2:
        raise ValueError("At least two NAV observations are required")
    if len({x.date for x in rows}) != len(rows):
        raise ValueError("Duplicate observation dates are not allowed")
    if any(b.date <= a.date for a, b in zip(rows, rows[1:])):
        raise ValueError("Observation dates must be strictly increasing")
    returns = [b.nav / a.nav - 1 for a, b in zip(rows, rows[1:])]
    total_return = rows[-1].nav / rows[0].nav - 1
    days = (rows[-1].date - rows[0].date).days
    annualized = ((rows[-1].nav / rows[0].nav) ** (365.25 / days) - 1) if days > 0 else None
    volatility = (sqrt(sum((r - sum(returns)/len(returns))**2 for r in returns) / (len(returns)-1)) * sqrt(periods_per_year)) if len(returns) >= 2 else None
    peak = rows[0].nav
    max_drawdown = 0.0
    for row in rows:
        peak = max(peak, row.nav)
        max_drawdown = min(max_drawdown, row.nav / peak - 1)
    return PerformanceMetrics(
        observations=len(rows), first_date=rows[0].date, last_date=rows[-1].date,
        total_return_pct=total_return * 100,
        annualized_return_pct=annualized * 100 if annualized is not None else None,
        annualized_volatility_pct=volatility * 100 if volatility is not None else None,
        max_drawdown_pct=max_drawdown * 100,
    )
