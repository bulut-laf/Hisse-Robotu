from app.analysis.financial_intelligence_reit_scoring_engine import (
    score_reit_model,
)


def main():
    strong = {
        "PORTFOLIO_QUALITY": {
            "occupancy_rate": 97.0,
            "rental_income_margin": 70.0,
        },
        "LEVERAGE": {
            "net_debt_to_assets": 15.0,
            "interest_coverage_ratio": 5.0,
        },
        "NAV_VALUATION": {
            "nav_per_share": 1.2,
            "price_to_nav_ratio": 0.80,
        },
        "PROFITABILITY": {
            "roe": 20.0,
            "roa": 9.0,
            "ffo_margin": 50.0,
        },
        "CASH_DISTRIBUTION": {
            "ffo_payout_ratio": 60.0,
            "operating_cash_flow_to_dividend": 1.7,
        },
        "GROWTH_QUALITY": {
            "rental_income_growth": 20.0,
            "ffo_growth": 30.0,
            "nav_growth": 25.0,
        },
    }

    result = score_reit_model(strong)

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
            "REIT_SCORING_ENGINE_BLOCKED"
        )

    if result.total_score is None:
        raise SystemExit(
            "REIT_SCORE_MISSING"
        )

    print(
        "FINANCIAL_INTELLIGENCE_V1_2_"
        "REIT_SCORING_ENGINE_V1=PASS"
    )


if __name__ == "__main__":
    main()
