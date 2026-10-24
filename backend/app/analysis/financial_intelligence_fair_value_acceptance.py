from __future__ import annotations

from dataclasses import asdict
from datetime import date
from decimal import Decimal
from typing import Any

from .forecast_engine import build_three_scenario_forecast
from .dcf_valuation import value_fcff
from .composite_fair_value import combine_fair_values
from .margin_of_safety import required_mos_for_confidence, assess_margin_of_safety
from ..models.valuation_engine_models import ForecastAssumptions, ValuationModelInput


class FairValueAcceptanceError(ValueError):
    pass


def _d(v: Any, name: str) -> Decimal:
    if v is None:
        raise FairValueAcceptanceError(f"{name} is required")
    try:
        return Decimal(str(v))
    except Exception as exc:
        raise FairValueAcceptanceError(f"{name} must be numeric") from exc


def _tuple_d(values: Any, name: str) -> tuple[Decimal, ...]:
    if not isinstance(values, list) or not values:
        raise FairValueAcceptanceError(f"{name} must be a non-empty list")
    return tuple(_d(v, name) for v in values)


def _forecast_assumptions(raw: dict[str, Any], label: str) -> ForecastAssumptions:
    required = (
        "revenue_growth",
        "ebit_margin",
        "tax_rate",
        "depreciation_to_revenue",
        "capex_to_revenue",
        "nwc_to_revenue",
    )
    missing = [k for k in required if k not in raw]
    if missing:
        raise FairValueAcceptanceError(f"{label} missing forecast fields: {', '.join(missing)}")
    return ForecastAssumptions(
        revenue_growth=_tuple_d(raw["revenue_growth"], f"{label}.revenue_growth"),
        ebit_margin=_tuple_d(raw["ebit_margin"], f"{label}.ebit_margin"),
        tax_rate=_d(raw["tax_rate"], f"{label}.tax_rate"),
        depreciation_to_revenue=_d(raw["depreciation_to_revenue"], f"{label}.depreciation_to_revenue"),
        capex_to_revenue=_d(raw["capex_to_revenue"], f"{label}.capex_to_revenue"),
        nwc_to_revenue=_d(raw["nwc_to_revenue"], f"{label}.nwc_to_revenue"),
    )


def _multiple_model(
    name: str,
    scenario_raw: dict[str, Any],
    *,
    net_debt: Decimal,
    shares: Decimal,
    weight: Decimal,
    confidence: str,
) -> ValuationModelInput:
    kind = str(scenario_raw.get("kind", "")).upper()
    if kind == "NORMALIZED_PE":
        eps = _d(scenario_raw.get("normalized_eps"), f"{name}.normalized_eps")
        multiple = _d(scenario_raw.get("target_multiple"), f"{name}.target_multiple")
        fair = eps * multiple
    elif kind == "EV_SALES":
        revenue = _d(scenario_raw.get("normalized_revenue"), f"{name}.normalized_revenue")
        multiple = _d(scenario_raw.get("target_multiple"), f"{name}.target_multiple")
        equity = revenue * multiple - net_debt
        fair = equity / shares if equity > 0 else None
    else:
        raise FairValueAcceptanceError(
            f"{name}.kind must be NORMALIZED_PE or EV_SALES"
        )
    return ValuationModelInput(name, fair, weight, confidence)


def _model_inputs(
    scenario_name: str,
    *,
    dcf_fair_value: Decimal | None,
    dcf_weight: Decimal,
    dcf_confidence: str,
    secondary: dict[str, Any],
    net_debt: Decimal,
    shares: Decimal,
) -> tuple[ValuationModelInput, ...]:
    models = [
        ValuationModelInput(
            f"FCFF_DCF_{scenario_name}",
            dcf_fair_value,
            dcf_weight,
            dcf_confidence,
        )
    ]

    secondary_weight = _d(secondary.get("weight"), f"{scenario_name}.secondary.weight")
    secondary_confidence = str(secondary.get("confidence", "MEDIUM")).upper()
    if secondary_confidence not in {"HIGH", "MEDIUM", "LOW"}:
        raise FairValueAcceptanceError(f"{scenario_name}.secondary.confidence invalid")

    models.append(
        _multiple_model(
            f"{secondary.get('kind', '').upper()}_{scenario_name}",
            secondary,
            net_debt=net_debt,
            shares=shares,
            weight=secondary_weight,
            confidence=secondary_confidence,
        )
    )
    return tuple(models)


def _serialize(v: Any) -> Any:
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, date):
        return v.isoformat()
    if hasattr(v, "__dataclass_fields__"):
        return _serialize(asdict(v))
    if isinstance(v, dict):
        return {str(k): _serialize(x) for k, x in v.items()}
    if isinstance(v, (tuple, list)):
        return [_serialize(x) for x in v]
    return v


def run_fair_value_acceptance(config: dict[str, Any]) -> dict[str, Any]:
    if config.get("example_only") is True:
        raise FairValueAcceptanceError(
            "example_only=true: replace the example assumptions with reviewed analyst assumptions before production acceptance"
        )

    symbol = str(config.get("symbol", "")).strip().upper()
    if not symbol:
        raise FairValueAcceptanceError("symbol is required")

    as_of_date = date.fromisoformat(str(config["as_of_date"]))
    current_price = _d(config.get("current_price"), "current_price")
    shares = _d(config.get("diluted_shares"), "diluted_shares")
    net_debt = _d(config.get("net_debt"), "net_debt")
    base_year = int(config["base_year"])
    base_revenue = _d(config.get("base_revenue"), "base_revenue")
    base_nwc = _d(config.get("base_nwc"), "base_nwc")
    cyclicality = str(config.get("cyclicality", "NORMAL")).upper()

    if current_price <= 0 or shares <= 0 or base_revenue <= 0:
        raise FairValueAcceptanceError("price, shares and base_revenue must be positive")

    scenarios_raw = config.get("scenarios")
    if not isinstance(scenarios_raw, dict):
        raise FairValueAcceptanceError("scenarios object is required")

    for s in ("bear", "base", "bull"):
        if s not in scenarios_raw:
            raise FairValueAcceptanceError(f"scenario {s} is required")

    bear_a = _forecast_assumptions(scenarios_raw["bear"]["forecast"], "bear")
    base_a = _forecast_assumptions(scenarios_raw["base"]["forecast"], "base")
    bull_a = _forecast_assumptions(scenarios_raw["bull"]["forecast"], "bull")

    bundle = build_three_scenario_forecast(
        symbol,
        as_of_date,
        base_year=base_year,
        base_revenue=base_revenue,
        base_nwc=base_nwc,
        bear=bear_a,
        base=base_a,
        bull=bull_a,
        confidence=str(config.get("forecast_confidence", "MEDIUM")).upper(),
    )

    dcf_results = {}
    model_sets = {}
    for key, forecast in (
        ("bear", bundle.bear),
        ("base", bundle.base),
        ("bull", bundle.bull),
    ):
        raw = scenarios_raw[key]
        dcf_raw = raw.get("dcf") or {}
        wacc = _d(dcf_raw.get("wacc"), f"{key}.dcf.wacc")
        terminal_growth = _d(dcf_raw.get("terminal_growth"), f"{key}.dcf.terminal_growth")
        dcf_weight = _d(dcf_raw.get("weight"), f"{key}.dcf.weight")
        dcf_conf = str(dcf_raw.get("confidence", "MEDIUM")).upper()

        dcf = value_fcff(
            forecast,
            wacc=wacc,
            terminal_growth=terminal_growth,
            net_debt=net_debt,
            diluted_shares=shares,
        )
        dcf_results[key] = dcf

        secondary = raw.get("secondary_model")
        if not isinstance(secondary, dict):
            raise FairValueAcceptanceError(f"{key}.secondary_model is required")

        model_sets[key] = _model_inputs(
            key.upper(),
            dcf_fair_value=dcf.fair_value_per_share,
            dcf_weight=dcf_weight,
            dcf_confidence=dcf_conf,
            secondary=secondary,
            net_debt=net_debt,
            shares=shares,
        )

    composite = combine_fair_values(
        symbol,
        as_of_date,
        bear_models=model_sets["bear"],
        base_models=model_sets["base"],
        bull_models=model_sets["bull"],
    )

    if composite.base_value is None:
        status = "DATA_INSUFFICIENT"
        mos = None
        required_mos = None
    else:
        required_mos = required_mos_for_confidence(
            composite.confidence,
            cyclicality=cyclicality,
        )
        mos = assess_margin_of_safety(
            symbol,
            as_of_date,
            current_price=current_price,
            base_fair_value=composite.base_value,
            required_margin_of_safety=required_mos,
        )
        status = "PASS"

    return _serialize({
        "status": status,
        "mode": "READ_ONLY_PRODUCTION_ACCEPTANCE",
        "symbol": symbol,
        "as_of_date": as_of_date,
        "current_price": current_price,
        "input_basis": {
            "base_year": base_year,
            "base_revenue": base_revenue,
            "base_nwc": base_nwc,
            "net_debt": net_debt,
            "diluted_shares": shares,
            "cyclicality": cyclicality,
            "assumption_source": config.get("assumption_source"),
            "assumption_notes": config.get("assumption_notes", []),
        },
        "forecast": bundle,
        "dcf": dcf_results,
        "model_inputs": model_sets,
        "composite_fair_value": composite,
        "margin_of_safety": mos,
        "required_margin_of_safety": required_mos,
        "production_rules": [
            "No forecast is invented by the engine; all forward assumptions are explicit inputs.",
            "At least two independent valuation models are required per scenario by the existing composite engine.",
            "Current price is not used to manufacture fair value.",
            "Cyclical companies should use normalized/mid-cycle assumptions rather than peak-period annualization.",
            "Terminal growth must remain below the discount rate.",
            "No AL/SAT, scanner, ranking, portfolio or existing score is mutated.",
        ],
    })
