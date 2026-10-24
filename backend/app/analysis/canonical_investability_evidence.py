from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Any
import json

from ..models.investability_models import MarketContextInput, LongTermContextInput


class CanonicalInvestabilityEvidenceError(ValueError):
    pass


def _D(v: Any) -> Decimal | None:
    if v is None:
        return None
    return v if isinstance(v, Decimal) else Decimal(str(v))


def _clamp100(v: Decimal | None) -> Decimal | None:
    if v is None:
        return None
    return max(Decimal("0"), min(Decimal("100"), v))


def valuation_score_from_fair_value(*, current_price: Decimal | None, base_fair_value: Decimal | None) -> Decimal | None:
    """
    Deterministic price-vs-base score.
    100 at >=50% discount to base, 50 at fair value, 0 at >=50% premium.
    No peer/DCF confidence is invented here; this is only price stretch.
    """
    if current_price is None or base_fair_value is None or current_price <= 0 or base_fair_value <= 0:
        return None
    ratio = current_price / base_fair_value
    # score = 100 at ratio=.5, 50 at 1.0, 0 at 1.5
    return _clamp100(Decimal("150") - (ratio * Decimal("100")))


def margin_of_safety_score_from_result(*, current_margin_of_safety: Decimal | None) -> Decimal | None:
    """
    Maps current MOS to 0..100 without changing the underlying MOS result.
    0% MOS -> 50; +50% -> 100; -50% -> 0.
    """
    if current_margin_of_safety is None:
        return None
    return _clamp100(Decimal("50") + current_margin_of_safety * Decimal("100"))


def financial_momentum_from_acceptance(financial: dict[str, Any]) -> Decimal | None:
    """
    Uses only explicit positive/negative evidence counts when available.
    Does not infer momentum from health score.
    """
    eq = financial.get("earnings_cash_quality") or financial.get("earnings_quality") or {}
    yoy = eq.get("yoy_growth") or {}
    vals = []
    for k in ("revenue_yoy", "operating_profit_yoy", "net_income_yoy", "ocf_yoy"):
        if yoy.get(k) is not None:
            vals.append(_D(yoy[k]))
    if not vals:
        return None
    positive = sum(1 for x in vals if x is not None and x > 0)
    negative = sum(1 for x in vals if x is not None and x < 0)
    neutral = len(vals) - positive - negative
    raw = Decimal("50") + Decimal("12.5") * Decimal(positive - negative)
    return _clamp100(raw)


def governance_score_from_ownership(ownership: dict[str, Any]) -> Decimal | None:
    """
    Conservative categorical mapping from canonical ownership assessment only.
    """
    if not ownership:
        return None
    concentration = str(ownership.get("governance_concentration") or "").upper()
    dilution = str(ownership.get("dilution_risk") or "").upper()

    base = {
        "LOW": Decimal("80"),
        "MODERATE": Decimal("65"),
        "ELEVATED": Decimal("45"),
        "HIGH": Decimal("30"),
    }.get(concentration)
    if base is None:
        return None
    if dilution == "HIGH":
        base -= Decimal("15")
    elif dilution == "MODERATE":
        base -= Decimal("7")
    return _clamp100(base)


def build_canonical_evidence(
    *,
    financial_acceptance: dict[str, Any],
    fair_value_acceptance: dict[str, Any],
    market_ownership_acceptance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    fv = fair_value_acceptance.get("composite_fair_value") or {}
    mos = fair_value_acceptance.get("margin_of_safety") or {}
    price = _D(fair_value_acceptance.get("current_price") or mos.get("current_price"))
    base = _D(fv.get("base_value") or mos.get("base_fair_value"))
    current_mos = _D(mos.get("current_margin_of_safety"))

    ownership = {}
    if market_ownership_acceptance:
        ownership = (
            market_ownership_acceptance.get("ownership")
            or market_ownership_acceptance.get("ownership_assessment")
            or {}
        )

    return {
        "financial_momentum": financial_momentum_from_acceptance(financial_acceptance),
        "valuation_score": valuation_score_from_fair_value(
            current_price=price, base_fair_value=base
        ),
        "margin_of_safety_score": margin_of_safety_score_from_result(
            current_margin_of_safety=current_mos
        ),
        "governance_score": governance_score_from_ownership(ownership),
        "market_context": asdict(MarketContextInput()),
        "long_term_context": asdict(LongTermContextInput(
            governance=governance_score_from_ownership(ownership),
        )),
        "flags": [
            "TECHNICAL_MARKET_CONTEXT_NOT_SYNTHESIZED",
            "BUSINESS_QUALITY_NOT_SYNTHESIZED",
            "GROWTH_DURABILITY_NOT_SYNTHESIZED",
            "SECTOR_RISK_NOT_SYNTHESIZED",
            "CAPITAL_EFFICIENCY_NOT_SYNTHESIZED",
        ],
        "engine_version": "fin-prod-006-v1",
    }


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_json(path: str | Path, payload: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
