from __future__ import annotations
from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from .short_term_investability import calculate_short_term_investability
from .long_term_investability import calculate_long_term_investability
from .financial_intelligence_panel import build_financial_intelligence_panel
from ..models.investability_models import MarketContextInput, LongTermContextInput

class InvestabilityAcceptanceError(ValueError): pass

def _d(v): return None if v is None else (v if isinstance(v, Decimal) else Decimal(str(v)))
def _i(v): return None if v is None else int(v)

def _ser(v):
    if isinstance(v, Decimal): return str(v)
    if isinstance(v, (date, datetime)): return v.isoformat()
    if hasattr(v, "__dataclass_fields__"): return _ser(asdict(v))
    if isinstance(v, dict): return {str(k): _ser(x) for k,x in v.items()}
    if isinstance(v, (tuple,list)): return [_ser(x) for x in v]
    return v

def _market(raw):
    raw = raw or {}
    return MarketContextInput(
        technical_trend=_d(raw.get("technical_trend")),
        relative_strength=_d(raw.get("relative_strength")),
        volume_liquidity=_d(raw.get("volume_liquidity")),
        catalyst=_d(raw.get("catalyst")),
        entry_risk=_d(raw.get("entry_risk")),
        earnings_surprise=_d(raw.get("earnings_surprise")),
    )

def _long(raw):
    raw = raw or {}
    return LongTermContextInput(
        business_quality=_d(raw.get("business_quality")),
        growth_durability=_d(raw.get("growth_durability")),
        governance=_d(raw.get("governance")),
        sector_risk=_d(raw.get("sector_risk")),
    )

def run_investability_acceptance(config: dict[str, Any]) -> dict[str, Any]:
    symbol = str(config.get("symbol","")).strip().upper()
    if not symbol: raise InvestabilityAcceptanceError("symbol is required")
    as_of_date = date.fromisoformat(str(config["as_of_date"]))
    as_of = datetime.fromisoformat(str(config.get("as_of", as_of_date.isoformat()+"T23:59:59")))
    sraw = config.get("short_term") or {}
    lraw = config.get("long_term") or {}
    mctx = _market(sraw.get("market"))
    lctx = _long(lraw.get("context"))

    short = calculate_short_term_investability(
        symbol, as_of_date,
        financial_health_score=_i(config.get("financial_health_score")),
        risk_score=_i(sraw.get("risk_score")),
        financial_momentum=_d(sraw.get("financial_momentum")),
        valuation_stretch=_d(sraw.get("valuation_stretch")),
        market=mctx,
    )
    long = calculate_long_term_investability(
        symbol, as_of_date,
        financial_health_score=_i(config.get("financial_health_score")),
        financial_risk_score=_i(lraw.get("financial_risk_score")),
        cash_quality_score=_d(lraw.get("cash_quality_score")),
        capital_efficiency_score=_d(lraw.get("capital_efficiency_score")),
        valuation_score=_d(lraw.get("valuation_score")),
        margin_of_safety_score=_d(lraw.get("margin_of_safety_score")),
        context=lctx,
    )
    v = config.get("valuation") or {}
    panel = build_financial_intelligence_panel(
        symbol=symbol, as_of=as_of,
        financial_health_score=_i(config.get("financial_health_score")),
        financial_health_grade=str(config.get("financial_health_grade","UNKNOWN")),
        financial_risk=str(config.get("financial_risk","UNKNOWN")),
        short_term=short, long_term=long,
        current_price=_d(v.get("current_price")),
        bear_value=_d(v.get("bear_value")),
        base_value=_d(v.get("base_value")),
        bull_value=_d(v.get("bull_value")),
        valuation_status=v.get("valuation_status"),
        margin_of_safety_status=v.get("margin_of_safety_status"),
        confidence=str(config.get("confidence","LOW")).upper(),
        extra_strengths=tuple(config.get("extra_strengths") or ()),
        extra_risks=tuple(config.get("extra_risks") or ()),
        what_to_watch_next=tuple(config.get("what_to_watch_next") or ()),
    )
    return _ser({
        "status":"PASS",
        "mode":"READ_ONLY_PRODUCTION_ACCEPTANCE",
        "symbol":symbol,
        "as_of_date":as_of_date,
        "short_term":short,
        "long_term":long,
        "panel":panel,
        "input_transparency":{
            "short_term_market_context_supplied": any(x is not None for x in (
                mctx.technical_trend,mctx.relative_strength,mctx.volume_liquidity,
                mctx.catalyst,mctx.entry_risk,mctx.earnings_surprise)),
            "long_term_context_supplied": any(x is not None for x in (
                lctx.business_quality,lctx.growth_durability,lctx.governance,lctx.sector_risk)),
        },
        "production_rules":[
            "Short-term and long-term investability are separate outputs.",
            "Missing inputs remain missing; they are not converted to zero.",
            "LOCKED is valid when required context is insufficient.",
            "Read-only: no AL/SAT, scanner, ranking, portfolio or score mutation."
        ]
    })
