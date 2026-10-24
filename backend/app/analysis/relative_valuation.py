from __future__ import annotations

from decimal import Decimal
from statistics import median
from typing import Iterable

from ..models.valuation_foundation_models import MultipleSnapshot, RelativeValuationResult


_METRICS = ("pe", "pb", "ev_ebitda", "ev_sales", "ps", "p_fcf")


def _median_decimal(values: Iterable[Decimal | None]) -> Decimal | None:
    clean = [v for v in values if v is not None and v > 0]
    if not clean:
        return None
    return Decimal(str(median(clean)))


def _discount(current: Decimal | None, reference: Decimal | None) -> Decimal | None:
    if current is None or reference is None or reference <= 0:
        return None
    # Negative = discount, positive = premium.
    return (current / reference) - Decimal("1")


def assess_relative_valuation(
    current: MultipleSnapshot,
    *,
    history: Iterable[MultipleSnapshot] = (),
    peers: Iterable[MultipleSnapshot] = (),
) -> RelativeValuationResult:
    hist = tuple(x for x in history if x.symbol == current.symbol and x.as_of_date < current.as_of_date)
    peer = tuple(x for x in peers if x.symbol != current.symbol and x.as_of_date <= current.as_of_date)

    historical_medians: dict[str, Decimal | None] = {}
    peer_medians: dict[str, Decimal | None] = {}
    historical_dp: dict[str, Decimal | None] = {}
    peer_dp: dict[str, Decimal | None] = {}

    for metric in _METRICS:
        cur = getattr(current, metric)
        hm = _median_decimal(getattr(x, metric) for x in hist)
        pm = _median_decimal(getattr(x, metric) for x in peer)
        historical_medians[metric] = hm
        peer_medians[metric] = pm
        historical_dp[metric] = _discount(cur, hm)
        peer_dp[metric] = _discount(cur, pm)

    usable_hist = sum(v is not None for v in historical_dp.values())
    usable_peer = sum(v is not None for v in peer_dp.values())
    warnings: list[str] = []
    reasons: list[str] = []

    if not hist:
        warnings.append("HISTORICAL_MULTIPLE_HISTORY_UNAVAILABLE")
    if not peer:
        warnings.append("PEER_SET_UNAVAILABLE")

    for metric in _METRICS:
        hd = historical_dp[metric]
        pd = peer_dp[metric]
        if hd is not None:
            reasons.append(f"{metric.upper()}_VS_HISTORY={hd:+.2%}")
        if pd is not None:
            reasons.append(f"{metric.upper()}_VS_PEERS={pd:+.2%}")

    evidence_axes = usable_hist + usable_peer
    if evidence_axes >= 6:
        confidence = "HIGH"
    elif evidence_axes >= 3:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    return RelativeValuationResult(
        symbol=current.symbol,
        as_of_date=current.as_of_date,
        current=current,
        historical_medians=historical_medians,
        historical_discount_premium=historical_dp,
        peer_medians=peer_medians,
        peer_discount_premium=peer_dp,
        confidence=confidence,
        reasons=tuple(reasons),
        warnings=tuple(warnings),
    )
