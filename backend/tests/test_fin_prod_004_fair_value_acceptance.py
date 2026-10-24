from decimal import Decimal

import pytest

from app.analysis.financial_intelligence_fair_value_acceptance import (
    FairValueAcceptanceError,
    run_fair_value_acceptance,
)


def _config():
    return {
        "symbol": "TEST",
        "as_of_date": "2026-08-04",
        "current_price": "100",
        "diluted_shares": "1000000",
        "net_debt": "10000000",
        "base_year": 2026,
        "base_revenue": "200000000",
        "base_nwc": "20000000",
        "cyclicality": "NORMAL",
        "forecast_confidence": "MEDIUM",
        "assumption_source": "UNIT_TEST",
        "scenarios": {
            "bear": {
                "forecast": {
                    "revenue_growth": ["0.00", "0.02", "0.02", "0.02", "0.02"],
                    "ebit_margin": ["0.08", "0.08", "0.08", "0.08", "0.08"],
                    "tax_rate": "0.25",
                    "depreciation_to_revenue": "0.04",
                    "capex_to_revenue": "0.05",
                    "nwc_to_revenue": "0.10"
                },
                "dcf": {"wacc": "0.16", "terminal_growth": "0.03", "weight": "0.60", "confidence": "MEDIUM"},
                "secondary_model": {"kind": "NORMALIZED_PE", "normalized_eps": "7", "target_multiple": "10", "weight": "0.40", "confidence": "MEDIUM"}
            },
            "base": {
                "forecast": {
                    "revenue_growth": ["0.04", "0.04", "0.04", "0.04", "0.04"],
                    "ebit_margin": ["0.10", "0.10", "0.10", "0.10", "0.10"],
                    "tax_rate": "0.25",
                    "depreciation_to_revenue": "0.04",
                    "capex_to_revenue": "0.045",
                    "nwc_to_revenue": "0.10"
                },
                "dcf": {"wacc": "0.14", "terminal_growth": "0.04", "weight": "0.60", "confidence": "MEDIUM"},
                "secondary_model": {"kind": "NORMALIZED_PE", "normalized_eps": "9", "target_multiple": "11", "weight": "0.40", "confidence": "MEDIUM"}
            },
            "bull": {
                "forecast": {
                    "revenue_growth": ["0.07", "0.06", "0.05", "0.05", "0.05"],
                    "ebit_margin": ["0.12", "0.12", "0.12", "0.12", "0.12"],
                    "tax_rate": "0.25",
                    "depreciation_to_revenue": "0.04",
                    "capex_to_revenue": "0.04",
                    "nwc_to_revenue": "0.10"
                },
                "dcf": {"wacc": "0.12", "terminal_growth": "0.045", "weight": "0.60", "confidence": "MEDIUM"},
                "secondary_model": {"kind": "NORMALIZED_PE", "normalized_eps": "11", "target_multiple": "12", "weight": "0.40", "confidence": "MEDIUM"}
            }
        }
    }


def test_fin_prod_004_happy_path():
    r = run_fair_value_acceptance(_config())
    assert r["status"] == "PASS"
    assert r["composite_fair_value"]["base_value"] is not None
    assert r["margin_of_safety"] is not None


def test_example_only_is_fail_closed():
    c = _config()
    c["example_only"] = True
    with pytest.raises(FairValueAcceptanceError):
        run_fair_value_acceptance(c)


def test_terminal_growth_guard_is_preserved():
    c = _config()
    c["scenarios"]["base"]["dcf"]["wacc"] = "0.04"
    c["scenarios"]["base"]["dcf"]["terminal_growth"] = "0.04"
    with pytest.raises(Exception):
        run_fair_value_acceptance(c)
