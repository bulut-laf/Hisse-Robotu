from backend.app.market_context.v1_health_check import (
    validate_context_bundle,
)


def test_all_v1_context_types_are_accepted():
    bundle = {
        "documents": [
            {"report_type": "market_commentary"},
            {"report_type": "global_market_commentary"},
            {"report_type": "fund_etf_commentary"},
            {"report_type": "weekly_recommendation"},
        ]
    }

    assert validate_context_bundle(bundle)


def test_unknown_context_type_is_rejected():
    bundle = {
        "documents": [
            {"report_type": "unknown_type"}
        ]
    }

    assert not validate_context_bundle(bundle)
