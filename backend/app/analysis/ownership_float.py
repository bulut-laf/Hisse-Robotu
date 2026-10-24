from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from ..models.valuation_foundation_models import OwnershipSnapshot


class OwnershipFloatError(ValueError):
    pass


@dataclass(frozen=True)
class OwnershipFloatAssessment:
    symbol: str
    free_float_ratio: Decimal | None
    effective_free_float_ratio: Decimal | None
    free_float_shares: Decimal | None
    float_liquidity_risk: str
    ownership_concentration: str
    dilution_risk: str
    governance_concentration: str
    evidence: tuple[str, ...]
    warnings: tuple[str, ...]


def _pct_valid(value: Decimal | None, name: str) -> None:
    if value is not None and not (Decimal("0") <= value <= Decimal("1")):
        raise OwnershipFloatError(f"{name} must be between 0 and 1")


def assess_ownership_float(snapshot: OwnershipSnapshot, *, as_of: datetime | None = None) -> OwnershipFloatAssessment:
    if snapshot.total_shares <= 0:
        raise OwnershipFloatError("total_shares must be positive")
    if snapshot.treasury_shares < 0 or snapshot.treasury_shares > snapshot.total_shares:
        raise OwnershipFloatError("treasury_shares out of range")
    if snapshot.diluted_shares is not None and snapshot.diluted_shares <= 0:
        raise OwnershipFloatError("diluted_shares must be positive")
    _pct_valid(snapshot.free_float_ratio, "free_float_ratio")
    _pct_valid(snapshot.effective_free_float_ratio, "effective_free_float_ratio")
    _pct_valid(snapshot.major_shareholder_ratio, "major_shareholder_ratio")

    if as_of is not None and snapshot.published_at is not None and snapshot.published_at > as_of:
        raise OwnershipFloatError("ownership snapshot was not public as of requested time")

    ratio = snapshot.effective_free_float_ratio
    if ratio is None:
        ratio = snapshot.free_float_ratio

    evidence: list[str] = []
    warnings: list[str] = []

    if ratio is None:
        float_risk = "NOT_EVALUATED"
        warnings.append("FREE_FLOAT_RATIO_MISSING")
    elif ratio < Decimal("0.10"):
        float_risk = "HIGH"
        evidence.append("VERY_LOW_FREE_FLOAT")
    elif ratio < Decimal("0.25"):
        float_risk = "ELEVATED"
        evidence.append("LOW_FREE_FLOAT")
    elif ratio < Decimal("0.50"):
        float_risk = "MODERATE"
        evidence.append("MID_FREE_FLOAT")
    else:
        float_risk = "LOW"
        evidence.append("BROAD_FREE_FLOAT")

    major = snapshot.major_shareholder_ratio
    if major is None:
        concentration = "NOT_EVALUATED"
        governance = "NOT_EVALUATED"
    elif major >= Decimal("0.75"):
        concentration = "VERY_HIGH"
        governance = "HIGH"
        evidence.append("DOMINANT_SHAREHOLDER")
    elif major >= Decimal("0.50"):
        concentration = "HIGH"
        governance = "ELEVATED"
        evidence.append("CONTROLLING_SHAREHOLDER")
    elif major >= Decimal("0.25"):
        concentration = "MODERATE"
        governance = "MODERATE"
    else:
        concentration = "LOW"
        governance = "LOW"

    dilution = "LOW"
    if snapshot.diluted_shares is not None and snapshot.diluted_shares > snapshot.total_shares * Decimal("1.05"):
        dilution = "ELEVATED"
        evidence.append("DILUTED_SHARE_COUNT_ABOVE_BASIC")

    if snapshot.privileged_share_flag is True:
        governance = "ELEVATED" if governance in {"LOW", "MODERATE"} else governance
        evidence.append("PRIVILEGED_SHARES_PRESENT")

    return OwnershipFloatAssessment(
        symbol=snapshot.symbol,
        free_float_ratio=snapshot.free_float_ratio,
        effective_free_float_ratio=snapshot.effective_free_float_ratio,
        free_float_shares=snapshot.free_float_shares,
        float_liquidity_risk=float_risk,
        ownership_concentration=concentration,
        dilution_risk=dilution,
        governance_concentration=governance,
        evidence=tuple(evidence),
        warnings=tuple(warnings),
    )
