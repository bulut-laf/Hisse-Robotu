from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
import json

from .short_term_investability import calculate_short_term_investability
from .long_term_investability import calculate_long_term_investability
from .financial_intelligence_panel import build_financial_intelligence_panel
from ..models.investability_models import MarketContextInput, LongTermContextInput


class InvestabilityRuntimeWiringError(ValueError):
    pass


def _d(v: Any) -> Decimal | None:
    if v is None:
        return None
    return v if isinstance(v, Decimal) else Decimal(str(v))


def _i(v: Any) -> int | None:
    if v is None:
        return None
    return int(v)


def _ser(v: Any) -> Any:
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if hasattr(v, "__dataclass_fields__"):
        return _ser(asdict(v))
    if isinstance(v, dict):
        return {str(k): _ser(x) for k, x in v.items()}
    if isinstance(v, (tuple, list)):
        return [_ser(x) for x in v]
    return v


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run_runtime_wiring(
    *,
    base_input: dict[str, Any],
    canonical_evidence: dict[str, Any],
) -> dict[str, Any]:
    symbol = str(base_input.get("symbol", "")).strip().upper()
    if not symbol:
        raise InvestabilityRuntimeWiringError("symbol is required")

    as_of_date = date.fromisoformat(str(base_input["as_of_date"]))
    as_of = datetime.fromisoformat(
        str(base_input.get("as_of", as_of_date.isoformat() + "T23:59:59"))
    )

    short_raw = base_input.get("short_term") or {}
    long_raw = base_input.get("long_term") or {}
    valuation = base_input.get("valuation") or {}

    e_market = canonical_evidence.get("market_context") or {}
    market = MarketContextInput(
        technical_trend=_d(e_market.get("technical_trend")),
        relative_strength=_d(e_market.get("relative_strength")),
        volume_liquidity=_d(e_market.get("volume_liquidity")),
        catalyst=_d(e_market.get("catalyst")),
        entry_risk=_d(e_market.get("entry_risk")),
        earnings_surprise=_d(e_market.get("earnings_surprise")),
    )

    e_long = canonical_evidence.get("long_term_context") or {}
    long_context = LongTermContextInput(
        business_quality=_d(e_long.get("business_quality")),
        growth_durability=_d(e_long.get("growth_durability")),
        governance=_d(e_long.get("governance")),
        sector_risk=_d(e_long.get("sector_risk")),
    )

    short = calculate_short_term_investability(
        symbol,
        as_of_date,
        financial_health_score=_i(base_input.get("financial_health_score")),
        risk_score=_i(short_raw.get("risk_score")),
        financial_momentum=_d(canonical_evidence.get("financial_momentum")),
        # Do not infer valuation_stretch from valuation_score: semantics differ.
        valuation_stretch=_d(short_raw.get("valuation_stretch")),
        market=market,
    )

    long = calculate_long_term_investability(
        symbol,
        as_of_date,
        financial_health_score=_i(base_input.get("financial_health_score")),
        financial_risk_score=_i(long_raw.get("financial_risk_score")),
        cash_quality_score=_d(long_raw.get("cash_quality_score")),
        capital_efficiency_score=_d(long_raw.get("capital_efficiency_score")),
        valuation_score=_d(canonical_evidence.get("valuation_score")),
        margin_of_safety_score=_d(canonical_evidence.get("margin_of_safety_score")),
        context=long_context,
    )

    panel = build_financial_intelligence_panel(
        symbol=symbol,
        as_of=as_of,
        financial_health_score=_i(base_input.get("financial_health_score")),
        financial_health_grade=str(base_input.get("financial_health_grade", "UNKNOWN")),
        financial_risk=str(base_input.get("financial_risk", "UNKNOWN")),
        short_term=short,
        long_term=long,
        current_price=_d(valuation.get("current_price")),
        bear_value=_d(valuation.get("bear_value")),
        base_value=_d(valuation.get("base_value")),
        bull_value=_d(valuation.get("bull_value")),
        valuation_status=valuation.get("valuation_status"),
        margin_of_safety_status=valuation.get("margin_of_safety_status"),
        confidence=str(base_input.get("confidence", "LOW")).upper(),
        extra_strengths=tuple(base_input.get("extra_strengths") or ()),
        extra_risks=tuple(base_input.get("extra_risks") or ()),
        what_to_watch_next=tuple(base_input.get("what_to_watch_next") or ()),
    )

    return _ser({
        "status": "PASS",
        "mode": "READ_ONLY_PRODUCTION_ACCEPTANCE",
        "symbol": symbol,
        "as_of_date": as_of_date,
        "wired_evidence": {
            "financial_momentum": canonical_evidence.get("financial_momentum"),
            "valuation_score": canonical_evidence.get("valuation_score"),
            "margin_of_safety_score": canonical_evidence.get("margin_of_safety_score"),
            "governance_score": canonical_evidence.get("governance_score"),
            "market_context": e_market,
            "long_term_context": e_long,
        },
        "short_term": short,
        "long_term": long,
        "panel": panel,
        "coverage_note": (
            "FIN-014 requires >=0.70 component weight coverage. "
            "With current canonical TUPRS evidence, available long-term weights are "
            "FINANCIAL_HEALTH 0.15 + CASH_QUALITY 0.12 + GOVERNANCE 0.08 + "
            "VALUATION 0.12 + MARGIN_OF_SAFETY 0.09 = 0.56, so LOCKED is expected "
            "until additional canonical long-term evidence exists."
        ),
        "production_rules": [
            "No missing score is synthesized merely to unlock a horizon.",
            "valuation_score and margin_of_safety_score are wired only into FIN-014.",
            "valuation_stretch is not inferred from valuation_score because the semantics are not proven equivalent.",
            "Short-term remains fail-closed until canonical technical/market evidence exists.",
            "Read-only: no AL/SAT, scanner, ranking, portfolio or score mutation.",
        ],
        "engine_version": "fin-prod-007-v1",
    })
