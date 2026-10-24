from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import Any

from backend.app.funds.evidence_mapper import FundEvidenceInput, EvidenceState

BRIDGE_VERSION = "erste-hungary-f4-evidence-bridge-v1"


def derive_f4_state(
    *,
    fund_size_change: Decimal | None,
    net_flow_ratio: Decimal | None,
) -> EvidenceState:
    values = [fund_size_change, net_flow_ratio]
    available = [v for v in values if v is not None]

    if len(available) < 2:
        return EvidenceState.UNAVAILABLE

    positive = sum(1 for value in available if value > 0)
    caution = sum(1 for value in available if value < 0)

    if positive >= 2:
        return EvidenceState.POSITIVE
    if caution >= 2:
        return EvidenceState.CAUTION
    return EvidenceState.NEUTRAL


def inject_f4_fields(
    base: FundEvidenceInput,
    *,
    fund_size_change: Decimal | None,
    net_flow_ratio: Decimal | None,
) -> FundEvidenceInput:
    return replace(
        base,
        fund_size_change=fund_size_change,
        investor_change=None,
        net_flow_ratio=net_flow_ratio,
    )


def derive_fund_size_change(
    previous_nav: Decimal | None,
    latest_nav: Decimal | None,
) -> Decimal | None:
    if previous_nav is None or latest_nav is None:
        return None
    if previous_nav <= 0 or latest_nav <= 0:
        return None
    return (latest_nav / previous_nav) - Decimal("1")