
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Iterable


@dataclass(frozen=True)
class FinancialIntelligencePanel:
    symbol: str
    as_of: datetime
    financial_health_score: int | None
    financial_health_grade: str
    financial_risk: str
    short_term_score: Decimal | None
    short_term_label: str | None
    short_term_locked: bool
    long_term_score: Decimal | None
    long_term_label: str | None
    long_term_locked: bool
    current_price: Decimal | None
    bear_value: Decimal | None
    base_value: Decimal | None
    bull_value: Decimal | None
    upside_downside_to_bear: Decimal | None
    upside_downside_to_base: Decimal | None
    upside_downside_to_bull: Decimal | None
    valuation_status: str | None
    margin_of_safety_status: str | None
    confidence: str
    strengths: tuple[str, ...]
    risks: tuple[str, ...]
    what_to_watch_next: tuple[str, ...]
    read_only: bool = True


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _upside(value: Decimal | None, current_price: Decimal | None) -> Decimal | None:
    if value is None or current_price is None or current_price == 0:
        return None
    return value / current_price - Decimal("1")


def _tuple_strings(values: Iterable[Any] | None) -> tuple[str, ...]:
    if values is None:
        return ()
    return tuple(str(value) for value in values if value is not None and str(value))


def _merge_unique(*groups: Iterable[Any] | None) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for group in groups:
        for value in _tuple_strings(group):
            if value not in seen:
                seen.add(value)
                result.append(value)
    return tuple(result)


def build_financial_intelligence_panel(
    *,
    symbol: str,
    as_of: datetime,
    financial_health_score: int | None,
    financial_health_grade: str,
    financial_risk: str,
    short_term: Any,
    long_term: Any,
    current_price: Decimal | None,
    bear_value: Decimal | None,
    base_value: Decimal | None,
    bull_value: Decimal | None,
    valuation_status: str | None,
    margin_of_safety_status: str | None,
    confidence: str,
    extra_strengths: Iterable[Any] | None = (),
    extra_risks: Iterable[Any] | None = (),
    what_to_watch_next: Iterable[Any] | None = (),
) -> FinancialIntelligencePanel:
    """Canonical FIN-015 read-only production panel builder.

    This is the public API consumed by FIN-013/014/015/016 production flows.
    It performs deterministic aggregation only and never mutates AL/SAT,
    scanner, ranking or portfolio state.
    """
    current_price_d = _decimal_or_none(current_price)
    bear_value_d = _decimal_or_none(bear_value)
    base_value_d = _decimal_or_none(base_value)
    bull_value_d = _decimal_or_none(bull_value)

    short_strengths = getattr(short_term, "strengths", ())
    short_risks = getattr(short_term, "risks", ())
    long_strengths = getattr(long_term, "strengths", ())
    long_risks = getattr(long_term, "risks", ())

    return FinancialIntelligencePanel(
        symbol=str(symbol).strip().upper(),
        as_of=as_of,
        financial_health_score=financial_health_score,
        financial_health_grade=str(financial_health_grade),
        financial_risk=str(financial_risk),
        short_term_score=getattr(short_term, "score", None),
        short_term_label=getattr(short_term, "label", None),
        short_term_locked=bool(getattr(short_term, "locked", False)),
        long_term_score=getattr(long_term, "score", None),
        long_term_label=getattr(long_term, "label", None),
        long_term_locked=bool(getattr(long_term, "locked", False)),
        current_price=current_price_d,
        bear_value=bear_value_d,
        base_value=base_value_d,
        bull_value=bull_value_d,
        upside_downside_to_bear=_upside(bear_value_d, current_price_d),
        upside_downside_to_base=_upside(base_value_d, current_price_d),
        upside_downside_to_bull=_upside(bull_value_d, current_price_d),
        valuation_status=valuation_status,
        margin_of_safety_status=margin_of_safety_status,
        confidence=str(confidence),
        strengths=_merge_unique(short_strengths, long_strengths, extra_strengths),
        risks=_merge_unique(short_risks, long_risks, extra_risks),
        what_to_watch_next=_tuple_strings(what_to_watch_next),
        read_only=True,
    )
