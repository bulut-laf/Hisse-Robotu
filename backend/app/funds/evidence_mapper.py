from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Mapping


class EvidenceState(str, Enum):
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    CAUTION = "CAUTION"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class FundEvidenceInput:
    canonical_fund_id: str
    category_id: str | None
    category_rank_percentile: Decimal | None
    category_rank_change: int | None
    return_1m: Decimal | None
    return_3m: Decimal | None
    return_6m: Decimal | None
    volatility_percentile: Decimal | None
    max_drawdown: Decimal | None
    fund_size_change: Decimal | None
    investor_change: Decimal | None
    net_flow_ratio: Decimal | None
    total_expense_ratio: Decimal | None
    regime_fit: Decimal | None
    allocation_known: bool


@dataclass(frozen=True, slots=True)
class FundEvidence:
    family: str
    state: EvidenceState
    facts: tuple[str, ...]
    missing_fields: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FundEvidenceMap:
    canonical_fund_id: str
    category_id: str | None
    category_mapping_state: str
    evidence: tuple[FundEvidence, ...]

    @property
    def available_family_count(self) -> int:
        return sum(item.state is not EvidenceState.UNAVAILABLE for item in self.evidence)


def _fmt(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _missing(family: str, *names: str) -> FundEvidence:
    return FundEvidence(family, EvidenceState.UNAVAILABLE, (), tuple(sorted(names)))


def _f1(value: FundEvidenceInput) -> FundEvidence:
    if value.category_id is None:
        return _missing("F1", "category_id")
    if value.category_rank_percentile is None or value.category_rank_change is None:
        missing = tuple(name for name, item in (
            ("category_rank_percentile", value.category_rank_percentile),
            ("category_rank_change", value.category_rank_change),
        ) if item is None)
        return _missing("F1", *missing)
    percentile = value.category_rank_percentile
    change = value.category_rank_change
    state = (
        EvidenceState.POSITIVE if percentile >= Decimal("0.70") and change > 0
        else EvidenceState.CAUTION if percentile < Decimal("0.30") or change < -2
        else EvidenceState.NEUTRAL
    )
    return FundEvidence("F1", state, (f"category_percentile={_fmt(percentile)}", f"rank_change={change}"))


def _f2(value: FundEvidenceInput) -> FundEvidence:
    returns = (value.return_1m, value.return_3m, value.return_6m)
    names = ("return_1m", "return_3m", "return_6m")
    if any(item is None for item in returns):
        return _missing("F2", *(name for name, item in zip(names, returns) if item is None))
    assert all(item is not None for item in returns)
    numeric = tuple(item for item in returns if item is not None)
    state = (
        EvidenceState.POSITIVE if all(item > 0 for item in numeric)
        else EvidenceState.CAUTION if sum(item < 0 for item in numeric) >= 2
        else EvidenceState.NEUTRAL
    )
    return FundEvidence("F2", state, tuple(f"{name}={_fmt(item)}" for name, item in zip(names, numeric)))


def _f3(value: FundEvidenceInput) -> FundEvidence:
    if value.volatility_percentile is None or value.max_drawdown is None:
        return _missing("F3", *(name for name, item in (
            ("volatility_percentile", value.volatility_percentile), ("max_drawdown", value.max_drawdown)
        ) if item is None))
    vol, drawdown = value.volatility_percentile, value.max_drawdown
    state = (
        EvidenceState.POSITIVE if vol <= Decimal("0.50") and drawdown >= Decimal("-0.10")
        else EvidenceState.CAUTION if vol >= Decimal("0.80") or drawdown <= Decimal("-0.20")
        else EvidenceState.NEUTRAL
    )
    return FundEvidence("F3", state, (f"volatility_percentile={_fmt(vol)}", f"max_drawdown={_fmt(drawdown)}"))


def _f4(value: FundEvidenceInput) -> FundEvidence:
    values = (value.fund_size_change, value.investor_change, value.net_flow_ratio)
    names = ("fund_size_change", "investor_change", "net_flow_ratio")
    available = [(name, item) for name, item in zip(names, values) if item is not None]
    if len(available) < 2:
        return _missing("F4", *(name for name, item in zip(names, values) if item is None))
    positives = sum(item > 0 for _, item in available)
    negatives = sum(item < 0 for _, item in available)
    state = EvidenceState.POSITIVE if positives >= 2 else EvidenceState.CAUTION if negatives >= 2 else EvidenceState.NEUTRAL
    return FundEvidence("F4", state, tuple(f"{name}={_fmt(item)}" for name, item in available),
                        tuple(name for name, item in zip(names, values) if item is None))


def _f5(value: FundEvidenceInput) -> FundEvidence:
    if value.total_expense_ratio is None or value.regime_fit is None or not value.allocation_known:
        missing = [name for name, item in (
            ("total_expense_ratio", value.total_expense_ratio), ("regime_fit", value.regime_fit)
        ) if item is None]
        if not value.allocation_known:
            missing.append("allocation")
        return _missing("F5", *missing)
    cost, fit = value.total_expense_ratio, value.regime_fit
    state = (
        EvidenceState.POSITIVE if cost <= Decimal("0.02") and fit >= Decimal("0.70")
        else EvidenceState.CAUTION if cost >= Decimal("0.04") or fit < Decimal("0.30")
        else EvidenceState.NEUTRAL
    )
    return FundEvidence("F5", state, (f"total_expense_ratio={_fmt(cost)}", f"regime_fit={_fmt(fit)}"))


def map_fund_evidence(value: FundEvidenceInput) -> FundEvidenceMap:
    if not value.canonical_fund_id.strip():
        raise ValueError("canonical_fund_id boş olamaz.")
    return FundEvidenceMap(
        canonical_fund_id=value.canonical_fund_id.strip(),
        category_id=value.category_id,
        category_mapping_state="MAPPED" if value.category_id else "UNMAPPED",
        evidence=(_f1(value), _f2(value), _f3(value), _f4(value), _f5(value)),
    )
