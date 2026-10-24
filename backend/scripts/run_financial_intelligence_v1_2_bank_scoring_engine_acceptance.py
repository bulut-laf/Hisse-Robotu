from app.analysis.financial_intelligence_bank_scoring_engine import (
    score_bank_model,
)


def main():
    strong = {
        "CAPITAL_ADEQUACY": {
            "capital_adequacy_ratio": 20.0,
            "tier1_capital_ratio": 16.0,
        },
        "ASSET_QUALITY": {
            "npl_ratio": 1.5,
            "npl_coverage_ratio": 110.0,
        },
        "PROFITABILITY": {
            "roe": 27.0,
            "roa": 3.2,
            "net_interest_margin": 6.2,
        },
        "FUNDING_LIQUIDITY": {
            "loan_to_deposit_ratio": 90.0,
            "liquidity_ratio": 135.0,
        },
        "EFFICIENCY": {
            "cost_to_income_ratio": 30.0,
        },
        "GROWTH_QUALITY": {
            "loan_growth": 18.0,
            "deposit_growth": 17.0,
            "net_income_growth": 28.0,
        },
    }

    result = score_bank_model(strong)

    print(f"STATUS={result.status}")
    print(f"TOTAL_SCORE={result.total_score}")
    print(
        f"COMPONENT_SCORES="
        f"{dict(result.component_scores)}"
    )
    print(
        f"MODEL_VERSION={result.model_version}"
    )

    if result.status != "PASS":
        raise SystemExit("BANK_SCORING_ENGINE_BLOCKED")

    if result.total_score is None:
        raise SystemExit("BANK_SCORE_MISSING")

    print(
        "FINANCIAL_INTELLIGENCE_V1_2_BANK_SCORING_ENGINE_V1=PASS"
    )


if __name__ == "__main__":
    main()
