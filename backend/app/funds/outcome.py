from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum
from typing import Iterable

from .analysis_engine import FundAnalysisResult


class OutcomeHorizon(str, Enum):
    ONE_WEEK = "1H"
    ONE_MONTH = "1A"
    THREE_MONTHS = "3A"


HORIZON_DAYS = {OutcomeHorizon.ONE_WEEK: 7, OutcomeHorizon.ONE_MONTH: 30, OutcomeHorizon.THREE_MONTHS: 90}


@dataclass(frozen=True, slots=True)
class FundPricePoint:
    canonical_fund_id: str
    observation_date: date
    unit_price: Decimal


@dataclass(frozen=True, slots=True)
class FundForwardOutcome:
    evaluation_identity: str
    canonical_fund_id: str
    classification: str
    selection_date: date
    horizon: OutcomeHorizon
    target_date: date
    evaluation_date: date | None
    start_price: Decimal
    end_price: Decimal | None
    absolute_return: Decimal | None
    status: str
    tuning_authority: str = "NONE"


def evaluate_forward_outcomes(
    analysis: FundAnalysisResult, *, selection_date: date, start_price: Decimal,
    prices: Iterable[FundPricePoint], as_of: date,
) -> tuple[FundForwardOutcome, ...]:
    matching = sorted((p for p in prices if p.canonical_fund_id == analysis.canonical_fund_id), key=lambda p: p.observation_date)
    output = []
    for horizon in OutcomeHorizon:
        target = selection_date + timedelta(days=HORIZON_DAYS[horizon])
        point = next((p for p in matching if p.observation_date >= target), None)
        if point is not None and point.observation_date <= as_of:
            end, evaluated, status = point.unit_price, point.observation_date, "OBSERVED"
            performance = (end / start_price) - Decimal("1") if start_price > 0 else None
        elif as_of < target:
            end = evaluated = performance = None; status = "PENDING"
        else:
            end = evaluated = performance = None; status = "MISSING"
        output.append(FundForwardOutcome(
            evaluation_identity=f"{analysis.canonical_fund_id}|{selection_date.isoformat()}|{horizon.value}",
            canonical_fund_id=analysis.canonical_fund_id, classification=analysis.classification.value,
            selection_date=selection_date, horizon=horizon, target_date=target,
            evaluation_date=evaluated, start_price=start_price, end_price=end,
            absolute_return=performance, status=status,
        ))
    return tuple(output)
