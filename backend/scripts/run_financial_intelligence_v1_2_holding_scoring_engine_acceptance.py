from app.analysis.financial_intelligence_holding_scoring_engine import (
    score_holding_model,
)


def main():
    strong = {
        "NAV_QUALITY": {
            "nav_per_share": 1.2,
            "price_to_nav_ratio": 0.75,
        },
        "SUBSIDIARY_QUALITY": {
            "listed_subsidiary_value_share": 75.0,
            "subsidiary_dividend_coverage": 1.8,
        },
        "HOLDING_LEVERAGE": {
            "net_debt_to_nav": 5.0,
            "interest_coverage_ratio": 5.0,
        },
        "CASH_FLOW_QUALITY": {
            "holding_operating_cash_flow": 1.2,
            "dividend_income_to_financing_cost": 2.2,
        },
        "PROFITABILITY": {
            "roe": 22.0,
            "roa": 9.0,
        },
        "GROWTH_QUALITY": {
            "nav_growth": 25.0,
            "net_income_growth": 35.0,
            "dividend_income_growth": 30.0,
        },
    }

    result = score_holding_model(strong)

    print(f"STATUS={result.status}")
    print(f"TOTAL_SCORE={result.total_score}")
    print(
        f"COMPONENT_SCORES="
        f"{dict(result.component_scores)}"
    )
    print(
        f"MODEL_VERSION="
        f"{result.model_version}"
    )

    if result.status != "PASS":
        raise SystemExit(
            "HOLDING_SCORING_ENGINE_BLOCKED"
        )

    if result.total_score is None:
        raise SystemExit(
            "HOLDING_SCORE_MISSING"
        )

    print(
        "FINANCIAL_INTELLIGENCE_V1_2_"
        "HOLDING_SCORING_ENGINE_V1=PASS"
    )


if __name__ == "__main__":
    main()
