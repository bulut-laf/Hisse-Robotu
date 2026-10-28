from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable

from backend.app.funds.evidence_mapper import EvidenceState
from backend.app.funds.international.erste_hungary_f4_bridge import (
    derive_f4_state,
    derive_fund_size_change,
)
from backend.app.funds.international.erste_hungary_f4_csv import CsvEvidence


@dataclass(frozen=True, slots=True)
class ErsteF4Observation:
    isin: str
    observation_date: date
    unit_price: Decimal | None
    fund_size: Decimal | None = None


@dataclass(frozen=True, slots=True)
class ErsteF4Result:
    canonical_fund_id: str
    previous_date: date | None
    latest_date: date | None
    fund_size_change: Decimal | None
    net_flow_ratio: Decimal | None
    state: EvidenceState
    reason: str


def observations_from_csv_evidence(
    evidence: CsvEvidence,
) -> tuple[ErsteF4Observation, ...]:
    """Map BAMOSZ Árfolyam to unit price and NEÉ to total fund net assets."""
    isin = evidence.isin.strip().upper()
    return tuple(
        ErsteF4Observation(
            isin=isin,
            observation_date=row.date,
            unit_price=row.price,
            fund_size=row.nav,
        )
        for row in evidence.rows
    )


def derive_erste_f4(
    *,
    isin: str,
    observations: Iterable[ErsteF4Observation],
    as_of_date: date,
    max_age_days: int,
    official_net_flow: Decimal | None = None,
    prior_fund_nav: Decimal | None = None,
) -> ErsteF4Result:
    normalized_isin = isin.strip().upper()
    canonical_id = f"fund:isin:{normalized_isin}"

    def unavailable(reason: str) -> ErsteF4Result:
        return ErsteF4Result(
            canonical_fund_id=canonical_id,
            previous_date=None,
            latest_date=None,
            fund_size_change=None,
            net_flow_ratio=None,
            state=EvidenceState.UNAVAILABLE,
            reason=reason,
        )

    if len(normalized_isin) != 12:
        return unavailable("INVALID_ISIN")

    if max_age_days < 0:
        return unavailable("INVALID_MAX_AGE")

    rows = tuple(observations)

    if any(row.isin.strip().upper() != normalized_isin for row in rows):
        return unavailable("ISIN_MISMATCH")

    if any(row.observation_date > as_of_date for row in rows):
        return unavailable("FUTURE_OBSERVATION")

    for row in rows:
        if row.unit_price is not None and (
            not row.unit_price.is_finite() or row.unit_price <= 0
        ):
            return unavailable("INVALID_UNIT_PRICE")
        if row.fund_size is not None and (
            not row.fund_size.is_finite() or row.fund_size <= 0
        ):
            return unavailable("INVALID_FUND_SIZE")

    ordered = sorted(rows, key=lambda row: row.observation_date)
    if len({row.observation_date for row in ordered}) != len(ordered):
        return unavailable("DUPLICATE_OBSERVATION_DATE")

    if len(ordered) < 2:
        return unavailable("INSUFFICIENT_HISTORY")

    previous, latest = ordered[-2], ordered[-1]

    if (as_of_date - latest.observation_date).days > max_age_days:
        return unavailable("STALE_OBSERVATION")

    size_change = (
        derive_fund_size_change(previous.fund_size, latest.fund_size)
        if previous.fund_size is not None and latest.fund_size is not None
        else None
    )

    flow_ratio = None
    if official_net_flow is not None and prior_fund_nav is not None:
        if (
            official_net_flow.is_finite()
            and prior_fund_nav.is_finite()
            and prior_fund_nav > 0
        ):
            flow_ratio = official_net_flow / prior_fund_nav

    state = derive_f4_state(
        fund_size_change=size_change,
        net_flow_ratio=flow_ratio,
    )

    if flow_ratio is not None:
        reason = (
            "OFFICIAL_FLOW_AND_FUND_SIZE_CHANGE_AVAILABLE"
            if size_change is not None
            else "OFFICIAL_FLOW_AVAILABLE_FUND_SIZE_CHANGE_UNAVAILABLE"
        )
    elif size_change is not None:
        reason = "FUND_SIZE_CHANGE_AVAILABLE_OFFICIAL_NET_FLOW_UNAVAILABLE"
    else:
        reason = "OFFICIAL_NET_FLOW_UNAVAILABLE"

    return ErsteF4Result(
        canonical_fund_id=canonical_id,
        previous_date=previous.observation_date,
        latest_date=latest.observation_date,
        fund_size_change=size_change,
        net_flow_ratio=flow_ratio,
        state=state,
        reason=reason,
    )
