from backend.app.market_context.ai_trend_analysis import (
    analyze_ai_history_trend,
)


def test_ai_trend_analysis_counts_factors():
    result = analyze_ai_history_trend(
        [
            {
                "risk_factors": ["Faiz"],
                "positive_factors": ["Global destek"],
            },
            {
                "risk_factors": ["Faiz"],
                "positive_factors": ["Likidite"],
            },
        ]
    )

    assert result["count"] == 2
    assert result["risk_frequency"]["Faiz"] == 2
    assert result["positive_frequency"]["Global destek"] == 1


def test_ai_trend_analysis_has_no_trade_logic():
    result = analyze_ai_history_trend([])

    assert "signal" not in result
    assert "technical_score" not in result
