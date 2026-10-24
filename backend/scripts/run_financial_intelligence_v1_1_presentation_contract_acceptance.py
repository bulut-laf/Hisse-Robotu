from pathlib import Path

from app.ui.financial_intelligence_presentation_contract import (
    build_financial_intelligence_presentation_contract,
)


def main():

    root = Path(__file__).resolve().parents[2]

    data = (
        build_financial_intelligence_presentation_contract(
            root
        )
    )

    print(f"STATUS={data['status']}")
    print(f"SYMBOL={data['symbol']}")
    print(
        f"ELIGIBLE_SYMBOLS="
        f"{data['eligible_symbols']}"
    )

    cards = {
        row["key"]: row
        for row in data["cards"]
    }

    print(
        "FINANCIAL_HEALTH_DISPLAY="
        + cards[
            "financial_health"
        ]["display_value"]
    )

    print(
        "CASH_QUALITY_DISPLAY="
        + cards[
            "cash_quality"
        ]["display_value"]
    )

    print(
        "CAPITAL_EFFICIENCY_DISPLAY="
        + cards[
            "capital_efficiency"
        ]["display_value"]
    )

    print(
        "RISK_DISPLAY="
        + cards[
            "risk"
        ]["display_value"]
    )

    valuation = data["valuation"]

    print(
        "CURRENT_PRICE_DISPLAY="
        + valuation[
            "current_price"
        ]["display_value"]
    )

    print(
        "ATTRACTIVE_ENTRY_PRICE_DISPLAY="
        + valuation[
            "attractive_entry_price"
        ]["display_value"]
    )

    print(
        "VALUATION_STATUS_DISPLAY="
        + valuation[
            "valuation_status"
        ]["display_value"]
    )

    print(
        "FINANCIAL_INTELLIGENCE_V1_1_PRESENTATION_CONTRACT=PASS"
    )


if __name__ == "__main__":
    main()
