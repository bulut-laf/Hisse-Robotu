from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Iterable


class ProfileState(str, Enum):
    MATCH = "MATCH"
    WATCH = "WATCH"
    BLOCKED = "BLOCKED"
    INSUFFICIENT = "INSUFFICIENT"


class FundamentalDirection(str, Enum):
    POSITIVE = "POSITIVE"
    MIXED = "MIXED"
    NEGATIVE = "NEGATIVE"
    INSUFFICIENT = "INSUFFICIENT"


class ResearchProfileName(str, Enum):
    BABY_QUALITY_CAPEX = "BABY_QUALITY_CAPEX"
    CAPEX_TO_EARNINGS = "CAPEX_TO_EARNINGS"
    EARNINGS_INFLECTION = "EARNINGS_INFLECTION"


class CapexEvidenceStatus(str, Enum):
    VERIFIED = "VERIFIED"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class CapexStage(str, Enum):
    PLANNED_AND_FUNDED = "PLANNED_AND_FUNDED"
    UNDER_CONSTRUCTION = "UNDER_CONSTRUCTION"
    EQUIPMENT_INSTALLATION = "EQUIPMENT_INSTALLATION"
    COMMISSIONING = "COMMISSIONING"
    RECENTLY_COMMISSIONED = "RECENTLY_COMMISSIONED"


ACTIVE_CAPEX_STAGES = frozenset({
    CapexStage.PLANNED_AND_FUNDED,
    CapexStage.UNDER_CONSTRUCTION,
    CapexStage.EQUIPMENT_INSTALLATION,
    CapexStage.COMMISSIONING,
    CapexStage.RECENTLY_COMMISSIONED,
})


@dataclass(frozen=True)
class CapexEvidence:
    source_type: str
    source_date: date
    source_id: str
    investment_type: str
    stage: CapexStage
    evidence_status: CapexEvidenceStatus
    expected_completion_date: date | None = None
    commissioned_date: date | None = None
    investment_amount: float | None = None
    currency: str | None = None
    capacity_before: float | None = None
    capacity_after: float | None = None
    expected_revenue_impact: float | None = None
    expected_margin_impact: float | None = None
    expected_cost_impact: float | None = None
    new_product: bool = False
    new_geography: bool = False
    new_customer_segment: bool = False

    @property
    def has_economic_effect(self) -> bool:
        return any((
            self.capacity_before is not None and self.capacity_after is not None and self.capacity_after > self.capacity_before,
            self.expected_revenue_impact is not None,
            self.expected_margin_impact is not None,
            self.expected_cost_impact is not None,
            self.new_product,
            self.new_geography,
            self.new_customer_segment,
        ))


@dataclass(frozen=True)
class FundamentalSnapshot:
    symbol: str
    market_cap_try: float | None = None
    free_float_shares: float | None = None
    ttm_cfo: float | None = None
    ttm_operating_profit: float | None = None
    latest_ebitda: float | None = None
    latest_operating_profit: float | None = None
    net_cash: float | None = None
    net_debt_ebitda: float | None = None
    debt_equity: float | None = None
    revenue_yoy_pct: float | None = None
    gross_margin_delta_pp: float | None = None
    ebitda_margin_delta_pp: float | None = None
    operating_profit_yoy_pct: float | None = None
    cfo_direction: str | None = None
    leverage_direction: str | None = None
    capex: CapexEvidence | None = None


@dataclass(frozen=True)
class DirectionEvaluation:
    direction: FundamentalDirection
    positive_count: int
    severe_negative_count: int
    observed_count: int
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ResearchProfileResult:
    symbol: str
    profile: ResearchProfileName
    state: ProfileState
    direction: FundamentalDirection
    reasons: tuple[str, ...]
    warnings: tuple[str, ...] = ()
    size_classification: str | None = None


def _norm(value: str | None) -> str | None:
    if value is None:
        return None
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")


def evaluate_fundamental_direction(snapshot: FundamentalSnapshot) -> DirectionEvaluation:
    positive = severe = observed = 0
    reasons: list[str] = []

    if snapshot.revenue_yoy_pct is not None:
        observed += 1
        if snapshot.revenue_yoy_pct > 0:
            positive += 1; reasons.append("MATCH_REVENUE_GROWTH")
        if snapshot.revenue_yoy_pct <= -10:
            severe += 1; reasons.append("SEVERE_REVENUE_DECLINE")

    if snapshot.gross_margin_delta_pp is not None:
        observed += 1
        if snapshot.gross_margin_delta_pp >= 1:
            positive += 1; reasons.append("MATCH_GROSS_MARGIN_IMPROVEMENT")
        if snapshot.gross_margin_delta_pp <= -3:
            severe += 1; reasons.append("SEVERE_GROSS_MARGIN_DETERIORATION")

    if snapshot.ebitda_margin_delta_pp is not None:
        observed += 1
        if snapshot.ebitda_margin_delta_pp >= 1:
            positive += 1; reasons.append("MATCH_EBITDA_MARGIN_IMPROVEMENT")
        if snapshot.ebitda_margin_delta_pp <= -3:
            severe += 1; reasons.append("SEVERE_EBITDA_MARGIN_DETERIORATION")

    if snapshot.ttm_cfo is not None:
        observed += 1
        cfo_dir = _norm(snapshot.cfo_direction)
        if snapshot.ttm_cfo > 0 and cfo_dir != "deteriorating":
            positive += 1; reasons.append("MATCH_POSITIVE_CFO")
        if snapshot.ttm_cfo < 0 and cfo_dir == "deteriorating":
            severe += 1; reasons.append("SEVERE_CFO_DETERIORATION")

    leverage_observed = snapshot.net_cash is not None or snapshot.net_debt_ebitda is not None or snapshot.leverage_direction is not None
    if leverage_observed:
        observed += 1
        lev_dir = _norm(snapshot.leverage_direction)
        if lev_dir in {"improving", "improved"}:
            positive += 1; reasons.append("MATCH_LEVERAGE_IMPROVEMENT")
        elif snapshot.net_cash is not None and snapshot.net_cash >= 0 and lev_dir != "deteriorating":
            positive += 1; reasons.append("MATCH_NET_CASH")
        if lev_dir == "deteriorating":
            severe += 1; reasons.append("SEVERE_LEVERAGE_DETERIORATION")

    if observed < 3:
        direction = FundamentalDirection.INSUFFICIENT
    elif severe >= 2:
        direction = FundamentalDirection.NEGATIVE
    elif positive >= 3:
        direction = FundamentalDirection.POSITIVE
    else:
        direction = FundamentalDirection.MIXED

    return DirectionEvaluation(direction, positive, severe, observed, tuple(reasons))


def _months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + (end.month - start.month)


def _capex_window_ok(capex: CapexEvidence, as_of: date) -> bool:
    if capex.stage is CapexStage.RECENTLY_COMMISSIONED:
        return capex.commissioned_date is not None and 0 <= _months_between(capex.commissioned_date, as_of) <= 12
    return capex.expected_completion_date is not None and -1 <= _months_between(as_of, capex.expected_completion_date) <= 18


def _verified_capex(s: FundamentalSnapshot) -> bool:
    return s.capex is not None and s.capex.evidence_status is CapexEvidenceStatus.VERIFIED and s.capex.stage in ACTIVE_CAPEX_STAGES


def _baby_balance(s: FundamentalSnapshot) -> bool | None:
    if s.net_cash is not None and s.net_cash >= 0:
        return True
    if s.net_debt_ebitda is None or s.debt_equity is None:
        return None
    return s.net_debt_ebitda <= 0.50 and s.debt_equity <= 0.25


def _capex_balance(s: FundamentalSnapshot) -> bool | None:
    if s.net_cash is not None and s.net_cash >= 0:
        return True
    if s.net_debt_ebitda is None:
        return None
    return s.net_debt_ebitda <= 2.0


def _result(s, profile, state, d, reasons, warnings=(), size=None):
    return ResearchProfileResult(
        symbol=s.symbol.strip().upper(), profile=profile, state=state,
        direction=d, reasons=tuple(dict.fromkeys(reasons)),
        warnings=tuple(dict.fromkeys(warnings)), size_classification=size
    )


def evaluate_baby_quality_capex(snapshot: FundamentalSnapshot, *, as_of: date) -> ResearchProfileResult:
    profile = ResearchProfileName.BABY_QUALITY_CAPEX
    d = evaluate_fundamental_direction(snapshot)
    reasons, warnings = [], []

    required = {
        "MARKET_CAP_TRY": snapshot.market_cap_try,
        "FREE_FLOAT_SHARES": snapshot.free_float_shares,
        "TTM_CFO": snapshot.ttm_cfo,
        "TTM_OPERATING_PROFIT": snapshot.ttm_operating_profit,
    }
    missing = [k for k, v in required.items() if v is None]
    if missing:
        return _result(snapshot, profile, ProfileState.INSUFFICIENT, d.direction, ["MISSING_" + x for x in missing])

    if snapshot.capex is None:
        return _result(snapshot, profile, ProfileState.INSUFFICIENT, d.direction, ["MISSING_CAPEX_DATA"])
    if snapshot.capex.evidence_status is CapexEvidenceStatus.STALE:
        return _result(snapshot, profile, ProfileState.BLOCKED, d.direction, ["BLOCK_STALE_CAPEX"])
    if not _verified_capex(snapshot):
        return _result(snapshot, profile, ProfileState.INSUFFICIENT, d.direction, ["MISSING_VERIFIED_CAPEX_DATA"])

    reasons.append("MATCH_LOW_MARKET_CAP" if snapshot.market_cap_try <= 20_000_000_000 else "BLOCK_MARKET_CAP_ABOVE_LIMIT")
    reasons.append("MATCH_LOW_FLOAT" if snapshot.free_float_shares <= 50_000_000 else "BLOCK_FREE_FLOAT_ABOVE_LIMIT")
    reasons.append("MATCH_POSITIVE_CFO" if snapshot.ttm_cfo > 0 else "BLOCK_NEGATIVE_CFO")
    if snapshot.ttm_operating_profit <= 0:
        reasons.append("BLOCK_NEGATIVE_OPERATING_PROFIT")

    balance = _baby_balance(snapshot)
    if balance is None:
        return _result(snapshot, profile, ProfileState.INSUFFICIENT, d.direction, reasons + ["MISSING_BALANCE_SHEET_SAFETY_DATA"])
    reasons.append(("MATCH_NET_CASH" if snapshot.net_cash is not None and snapshot.net_cash >= 0 else "MATCH_LOW_LEVERAGE") if balance else "BLOCK_HIGH_LEVERAGE")
    reasons.append("MATCH_ACTIVE_CAPEX")
    if not _capex_window_ok(snapshot.capex, as_of):
        warnings.append("WATCH_CAPEX_TIMING_OUTSIDE_PREFERRED_WINDOW")

    if any(x.startswith("BLOCK_") for x in reasons):
        return _result(snapshot, profile, ProfileState.BLOCKED, d.direction, reasons, warnings)
    if d.direction is FundamentalDirection.INSUFFICIENT:
        return _result(snapshot, profile, ProfileState.INSUFFICIENT, d.direction, reasons + ["MISSING_DIRECTION_DATA"], warnings)
    if d.direction is FundamentalDirection.NEGATIVE:
        return _result(snapshot, profile, ProfileState.BLOCKED, d.direction, reasons + ["BLOCK_DIRECTION_NEGATIVE"], warnings)
    if d.direction is FundamentalDirection.MIXED:
        return _result(snapshot, profile, ProfileState.WATCH, d.direction, reasons, warnings + ["WATCH_DIRECTION_MIXED"])
    size = "PRIMARY" if snapshot.market_cap_try <= 10_000_000_000 else "SECONDARY"
    return _result(snapshot, profile, ProfileState.MATCH, d.direction, reasons, warnings, size)


def evaluate_capex_to_earnings(snapshot: FundamentalSnapshot, *, as_of: date) -> ResearchProfileResult:
    profile = ResearchProfileName.CAPEX_TO_EARNINGS
    d = evaluate_fundamental_direction(snapshot)
    reasons = []

    if snapshot.capex is None:
        return _result(snapshot, profile, ProfileState.INSUFFICIENT, d.direction, ["MISSING_CAPEX_DATA"])
    if snapshot.capex.evidence_status is CapexEvidenceStatus.STALE:
        return _result(snapshot, profile, ProfileState.BLOCKED, d.direction, ["BLOCK_STALE_CAPEX"])
    if not _verified_capex(snapshot):
        return _result(snapshot, profile, ProfileState.INSUFFICIENT, d.direction, ["MISSING_VERIFIED_CAPEX_DATA"])
    reasons.append("MATCH_ACTIVE_CAPEX")
    if not snapshot.capex.has_economic_effect:
        return _result(snapshot, profile, ProfileState.INSUFFICIENT, d.direction, reasons + ["MISSING_CAPEX_ECONOMIC_EFFECT"])
    reasons.append("MATCH_CAPEX_ECONOMIC_EFFECT")
    if not _capex_window_ok(snapshot.capex, as_of):
        return _result(snapshot, profile, ProfileState.WATCH, d.direction, reasons, ["WATCH_CAPEX_TIMING_OUTSIDE_PREFERRED_WINDOW"])

    balance = _capex_balance(snapshot)
    if balance is None:
        return _result(snapshot, profile, ProfileState.INSUFFICIENT, d.direction, reasons + ["MISSING_BALANCE_SHEET_SAFETY_DATA"])
    if not balance:
        return _result(snapshot, profile, ProfileState.BLOCKED, d.direction, reasons + ["BLOCK_HIGH_LEVERAGE"])
    if d.direction is FundamentalDirection.INSUFFICIENT:
        return _result(snapshot, profile, ProfileState.INSUFFICIENT, d.direction, reasons + ["MISSING_DIRECTION_DATA"])
    if d.direction is FundamentalDirection.NEGATIVE:
        return _result(snapshot, profile, ProfileState.BLOCKED, d.direction, reasons + ["BLOCK_DIRECTION_NEGATIVE"])
    if d.direction is FundamentalDirection.MIXED:
        return _result(snapshot, profile, ProfileState.WATCH, d.direction, reasons, ["WATCH_DIRECTION_MIXED"])
    return _result(snapshot, profile, ProfileState.MATCH, d.direction, reasons)


def evaluate_earnings_inflection(snapshot: FundamentalSnapshot, *, as_of: date) -> ResearchProfileResult:
    del as_of
    profile = ResearchProfileName.EARNINGS_INFLECTION
    d = evaluate_fundamental_direction(snapshot)

    if snapshot.latest_ebitda is None or snapshot.latest_operating_profit is None:
        return _result(snapshot, profile, ProfileState.INSUFFICIENT, d.direction, ["MISSING_OPERATING_PROFIT_DATA"])
    if snapshot.latest_ebitda <= 0 or snapshot.latest_operating_profit <= 0:
        return _result(snapshot, profile, ProfileState.BLOCKED, d.direction, ["BLOCK_NEGATIVE_OPERATING_PROFIT"])

    growth_known = snapshot.revenue_yoy_pct is not None or snapshot.gross_margin_delta_pp is not None
    acceleration_known = snapshot.ebitda_margin_delta_pp is not None or snapshot.operating_profit_yoy_pct is not None
    if not growth_known or not acceleration_known:
        return _result(snapshot, profile, ProfileState.INSUFFICIENT, d.direction, ["MISSING_INFLECTION_DATA"])

    growth = (snapshot.revenue_yoy_pct is not None and snapshot.revenue_yoy_pct > 0) or (snapshot.gross_margin_delta_pp is not None and snapshot.gross_margin_delta_pp >= 1)
    acceleration = (snapshot.ebitda_margin_delta_pp is not None and snapshot.ebitda_margin_delta_pp >= 2) or (snapshot.operating_profit_yoy_pct is not None and snapshot.operating_profit_yoy_pct >= 30)

    reasons = [
        "MATCH_MARGIN_OR_REVENUE_INFLECTION" if growth else "BLOCK_NO_REVENUE_OR_GROSS_MARGIN_INFLECTION",
        "MATCH_EBITDA_ACCELERATION" if acceleration else "BLOCK_NO_EBITDA_OR_OPERATING_PROFIT_ACCELERATION",
    ]
    if not growth or not acceleration:
        return _result(snapshot, profile, ProfileState.BLOCKED, d.direction, reasons)
    if d.direction is FundamentalDirection.INSUFFICIENT:
        return _result(snapshot, profile, ProfileState.INSUFFICIENT, d.direction, reasons + ["MISSING_DIRECTION_DATA"])
    if d.direction is not FundamentalDirection.POSITIVE:
        return _result(snapshot, profile, ProfileState.BLOCKED, d.direction, reasons + ["BLOCK_DIRECTION_NOT_POSITIVE"])

    warnings = ["WATCH_CFO_NEGATIVE"] if snapshot.ttm_cfo is not None and snapshot.ttm_cfo < 0 else []
    return _result(snapshot, profile, ProfileState.MATCH, d.direction, reasons, warnings)


def evaluate_research_profiles(snapshot: FundamentalSnapshot, *, as_of: date) -> tuple[ResearchProfileResult, ...]:
    """Read-only: no ranking, scoring, signal, order or AL/SAT authority."""
    return (
        evaluate_baby_quality_capex(snapshot, as_of=as_of),
        evaluate_capex_to_earnings(snapshot, as_of=as_of),
        evaluate_earnings_inflection(snapshot, as_of=as_of),
    )
