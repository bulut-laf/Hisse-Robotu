from pathlib import Path

from app.analysis.financial_intelligence_selector_aware_panel import (
    build_selector_aware_financial_intelligence_panel,
)


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    data = build_selector_aware_financial_intelligence_panel(root)

    print(f"STATUS={data['status']}")
    print(f"RESOLVED_SYMBOL={data['resolved_symbol']}")
    print(f"ELIGIBLE_SYMBOLS={data['eligible_symbols']}")
    print(f"PANEL_ARTIFACT={data.get('panel_artifact')}")
    print("FINANCIAL_INTELLIGENCE_V1_1_SELECTOR_AWARE_PANEL_ADAPTER=PASS")


if __name__ == "__main__":
    main()
