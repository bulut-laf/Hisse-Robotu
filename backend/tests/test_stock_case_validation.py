from backend.app.system.stock_case_validation import (
    validate_stock_case_analysis,
)


def test_stock_case_analysis():
    result = validate_stock_case_analysis(
        {
            "symbol": "AKBNK",
            "technical": True,
            "sector": True,
            "risk": True,
            "decision": True,
        }
    )

    assert result["ready"] is True


def test_stock_case_analysis_missing():
    result = validate_stock_case_analysis({})

    assert result["ready"] is False
