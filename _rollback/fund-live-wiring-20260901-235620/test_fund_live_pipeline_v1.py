from backend.app.funds.analysis_engine import FundAnalysisResult
from backend.app.funds.live_pipeline import analyze_tefas_rows


def test_verified_f2_only():
    results = analyze_tefas_rows(
        (
            {
                "fonkod": "ABC",
                "getiri1a": "10,00",
                "getiri3a": "20,00",
                "getiri6a": "30,00",
            },
        )
    )

    assert len(results) == 1

    result = results[0]

    assert isinstance(result, FundAnalysisResult)
    assert result.canonical_fund_id == "TEFAS:ABC"

    assert "F1" in result.unavailable_families
    assert "F3" in result.unavailable_families
    assert "F4" in result.unavailable_families
    assert "F5" in result.unavailable_families

    assert result.automatic_trade_authority == "NONE"
    assert result.forced_fill is False


def test_existing_analyze_funds_is_reused():
    results = analyze_tefas_rows(
        (
            {
                "fonkod": "BBB",
                "getiri1a": "1,00",
                "getiri3a": "2,00",
                "getiri6a": "3,00",
            },
            {
                "fonkod": "AAA",
                "getiri1a": "4,00",
                "getiri3a": "5,00",
                "getiri6a": "6,00",
            },
        )
    )

    assert tuple(
        item.canonical_fund_id
        for item in results
    ) == (
        "TEFAS:AAA",
        "TEFAS:BBB",
    )
