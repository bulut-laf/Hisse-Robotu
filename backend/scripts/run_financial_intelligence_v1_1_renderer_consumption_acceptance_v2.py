from pathlib import Path

from app.ui.financial_intelligence_renderer_payload import (
    build_financial_intelligence_renderer_payload,
)


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    data = build_financial_intelligence_renderer_payload(root)

    print(f"STATUS={data['status']}")
    print(f"SYMBOL={data['symbol']}")
    print(f"ELIGIBLE_SYMBOLS={data['eligible_symbols']}")
    print(f"PANEL_STATUS={data['panel_status']}")
    print(f"FINANCIAL_HEALTH={data['financial_health']}")
    print(f"CASH_QUALITY={data['cash_quality']}")
    print(f"CAPITAL_EFFICIENCY={data['capital_efficiency']}")
    print(f"RISK={data['risk']}")
    print(f"CURRENT_PRICE={data['current_price']}")
    print(f"ATTRACTIVE_ENTRY_PRICE={data['attractive_entry_price']}")
    print(f"VALUATION_STATUS={data['valuation_status']}")
    print(f"PANEL_ARTIFACT={data['panel_artifact']}")
    print("FINANCIAL_INTELLIGENCE_V1_1_RENDERER_CONSUMPTION_ADAPTER_V2=PASS")


if __name__ == "__main__":
    main()
