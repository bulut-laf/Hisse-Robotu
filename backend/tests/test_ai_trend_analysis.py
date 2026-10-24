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


def test_ai_trend_classifies_new_persistent_and_resolved_factors():
    result = analyze_ai_history_trend(
        [
            {
                "risk_factors": ["Faiz", "Petrol"],
                "positive_factors": ["Asya"],
            },
            {
                "risk_factors": ["Faiz", "Kur"],
                "positive_factors": ["Asya", "ABD vadeli"],
            },
        ]
    )

    assert result["persistent_risks"] == ["Faiz"]
    assert result["new_risks"] == ["Kur"]
    assert result["resolved_risks"] == ["Petrol"]
    assert result["persistent_positive_factors"] == ["Asya"]
    assert result["new_positive_factors"] == ["ABD vadeli"]
    assert result["lost_positive_factors"] == []
    assert result["direction"] == "karisik"


def test_ai_trend_analysis_has_no_trade_logic():
    result = analyze_ai_history_trend([])

    assert "signal" not in result
    assert "technical_score" not in result


def test_ai_trend_single_day_is_baseline_not_directional():
    result = analyze_ai_history_trend(
        [
            {
                "risk_factors": [],
                "positive_factors": ["Asya", "ABD vadeli"],
            }
        ]
    )

    assert result["count"] == 1
    assert result["direction"] == "baslangic_verisi"
