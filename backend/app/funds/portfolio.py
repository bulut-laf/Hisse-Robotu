"""Rule-based fund allocation validation and transparent scenario stress tests."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class Allocation:
    fund_isin: str
    weight_pct: float

    def __post_init__(self):
        if not self.fund_isin.strip():
            raise ValueError("fund_isin must not be blank")
        if not 0 <= self.weight_pct <= 100:
            raise ValueError("weight_pct must be between 0 and 100")


def validate_allocations(allocations: list[Allocation], tolerance_pct: float = 0.01) -> dict:
    if tolerance_pct < 0:
        raise ValueError("tolerance_pct must be >= 0")
    if not allocations:
        return {"valid": False, "total_weight_pct": 0.0, "issues": ["empty_portfolio"]}
    duplicates = sorted({x.fund_isin for x in allocations if sum(y.fund_isin == x.fund_isin for y in allocations) > 1})
    total = sum(x.weight_pct for x in allocations)
    issues = []
    if duplicates:
        issues.append("duplicate_fund_isin:" + ",".join(duplicates))
    if abs(total - 100.0) > tolerance_pct:
        issues.append("weights_do_not_sum_to_100")
    return {"valid": not issues, "total_weight_pct": total, "issues": issues}


def allocation_amounts(investment_amount: float, allocations: list[Allocation]) -> dict:
    if investment_amount < 0:
        raise ValueError("investment_amount must be >= 0")
    validation = validate_allocations(allocations)
    if not validation["valid"]:
        raise ValueError("Invalid allocations: " + ";".join(validation["issues"]))
    return {x.fund_isin: investment_amount * x.weight_pct / 100 for x in allocations}


def stress_test(allocations: list[Allocation], scenario_returns_pct: Mapping[str, float]) -> dict:
    """Scenario return inputs are percentages keyed by fund ISIN; no return is imputed."""
    validation = validate_allocations(allocations)
    if not validation["valid"]:
        raise ValueError("Invalid allocations: " + ";".join(validation["issues"]))
    missing = sorted({x.fund_isin for x in allocations} - set(scenario_returns_pct))
    if missing:
        return {
            "comparable": False,
            "portfolio_return_pct": None,
            "missing_funds": missing,
            "contributions_pct": {},
        }
    contributions = {
        x.fund_isin: x.weight_pct * scenario_returns_pct[x.fund_isin] / 100
        for x in allocations
    }
    return {
        "comparable": True,
        "portfolio_return_pct": sum(contributions.values()),
        "missing_funds": [],
        "contributions_pct": contributions,
    }
