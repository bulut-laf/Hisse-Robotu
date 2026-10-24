from pathlib import Path

from app.ui.financial_intelligence_renderer_contract import (
    build_financial_intelligence_renderer_contract,
)


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    data = build_financial_intelligence_renderer_contract(root)

    print(f"STATUS={data['status']}")
    print(f"SYMBOL={data['symbol']}")
    print(f"ELIGIBLE_SYMBOLS={data['eligible_symbols']}")
    print(f"PANEL_ARTIFACT={data.get('panel_artifact')}")
    print("FINANCIAL_INTELLIGENCE_V1_1_RENDERER_CONTRACT_BRIDGE=PASS")


if __name__ == "__main__":
    main()
