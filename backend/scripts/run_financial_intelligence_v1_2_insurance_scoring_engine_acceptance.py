from app.analysis.financial_intelligence_insurance_scoring_engine import (
    score_insurance_model,
)


def main():
    strong = {
        "SOLVENCY_CAPITAL": {
            "solvency_ratio": 190.0,
            "equity_to_assets_ratio": 22.0,
        },
        "UNDERWRITING_QUALITY": {
            "loss_ratio": 50.0,
            "expense_ratio": 22.0,
            "combined_ratio": 88.0,
        },
        "RESERVE_ADEQUACY": {
            "technical_reserve_coverage": 145.0,
            "claims_reserve_growth": 15.0,
        },
        "PROFITABILITY": {
            "roe": 28.0,
            "roa": 3.2,
            "underwriting_margin": 18.0,
        },
        "LIQUIDITY_INVESTMENT": {
            "liquidity_ratio": 135.0,
            "investment_yield": 16.0,
        },
        "GROWTH_QUALITY": {
            "premium_growth": 25.0,
            "net_income_growth": 35.0,
        },
    }

    result = score_insurance_model(strong)

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
            "INSURANCE_SCORING_ENGINE_BLOCKED"
        )

    if result.total_score is None:
        raise SystemExit(
            "INSURANCE_SCORE_MISSING"
        )

    print(
        "FINANCIAL_INTELLIGENCE_V1_2_"
        "INSURANCE_SCORING_ENGINE_V1=PASS"
    )


if __name__ == "__main__":
    main()
