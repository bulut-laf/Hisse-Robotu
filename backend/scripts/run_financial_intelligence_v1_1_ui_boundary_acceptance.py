from pathlib import Path

from app.ui.financial_intelligence_ui_boundary import (
    build_financial_intelligence_ui_boundary,
)


def main():

    root = Path(__file__).resolve().parents[2]

    data = build_financial_intelligence_ui_boundary(root)

    print(f"STATUS={data['status']}")
    print(f"SYMBOL={data['symbol']}")
    print(f"PANEL_STATUS={data['panel_status']}")

    cards = {
        row["key"]: row
        for row in data["metric_cards"]
    }

    print(
        "FINANCIAL_HEALTH_UI="
        + cards["financial_health"]["value"]
    )

    print(
        "CASH_QUALITY_UI="
        + cards["cash_quality"]["value"]
    )

    print(
        "CAPITAL_EFFICIENCY_UI="
        + cards["capital_efficiency"]["value"]
    )

    print(
        "RISK_UI="
        + cards["risk"]["value"]
    )

    valuation = {
        row["key"]: row
        for row in data["valuation_rows"]
    }

    print(
        "CURRENT_PRICE_UI="
        + valuation["current_price"]["value"]
    )

    print(
        "ATTRACTIVE_ENTRY_PRICE_UI="
        + valuation["attractive_entry_price"]["value"]
    )

    print(
        "VALUATION_STATUS_UI="
        + valuation["valuation_status"]["value"]
    )

    print(
        "FINANCIAL_INTELLIGENCE_V1_1_UI_CONSUMPTION_BOUNDARY=PASS"
    )


if __name__ == "__main__":
    main()
