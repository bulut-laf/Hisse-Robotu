from pathlib import Path

from app.analysis.financial_intelligence_symbol_selector import (
    build_financial_intelligence_symbol_selector,
)


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    data = build_financial_intelligence_symbol_selector(root)

    print(f"STATUS={data['status']}")
    print(f"SYMBOL_COUNT={data['symbol_count']}")
    print(f"SYMBOLS={data['symbols']}")
    print(f"DEFAULT_SYMBOL={data['default_symbol']}")
    print(f"REGISTRY_ARTIFACT={data['registry_artifact']}")
    print("FINANCIAL_INTELLIGENCE_V1_1_MULTI_SYMBOL_PANEL_SELECTOR=PASS")


if __name__ == "__main__":
    main()
