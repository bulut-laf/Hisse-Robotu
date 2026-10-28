"""Transparent annual cost arithmetic. Inputs are percentages, not decimals."""
from dataclasses import dataclass


@dataclass(frozen=True)
class CostEstimate:
    invested_amount: float
    ongoing_charge_pct: float | None
    transaction_cost_pct: float | None
    estimated_annual_cost: float | None
    evidence_complete: bool


def estimate_annual_cost(invested_amount: float, ongoing_charge_pct: float | None,
                         transaction_cost_pct: float | None = 0.0) -> CostEstimate:
    if invested_amount < 0:
        raise ValueError("invested_amount must be >= 0")
    for name, value in (("ongoing_charge_pct", ongoing_charge_pct), ("transaction_cost_pct", transaction_cost_pct)):
        if value is not None and not 0 <= value <= 100:
            raise ValueError(f"{name} must be between 0 and 100")
    complete = ongoing_charge_pct is not None and transaction_cost_pct is not None
    total = invested_amount * (ongoing_charge_pct + transaction_cost_pct) / 100 if complete else None
    return CostEstimate(invested_amount, ongoing_charge_pct, transaction_cost_pct, total, complete)


def compare_annual_costs(invested_amount: float, first_ongoing_pct: float | None,
                         second_ongoing_pct: float | None) -> dict:
    """Return comparable annual ongoing charges only when both rates are known."""
    if invested_amount < 0:
        raise ValueError("invested_amount must be >= 0")
    if first_ongoing_pct is None or second_ongoing_pct is None:
        return {"comparable": False, "first_cost": None, "second_cost": None, "difference": None}
    for value in (first_ongoing_pct, second_ongoing_pct):
        if not 0 <= value <= 100:
            raise ValueError("ongoing charge rates must be between 0 and 100")
    first = invested_amount * first_ongoing_pct / 100
    second = invested_amount * second_ongoing_pct / 100
    return {"comparable": True, "first_cost": first, "second_cost": second, "difference": first - second}
