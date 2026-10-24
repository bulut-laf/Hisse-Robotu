from app.analysis.financial_intelligence_bank_model_contract import (
    BANK_COMPONENTS,
    BANK_REQUIRED_METRICS,
)
from app.analysis.financial_intelligence_bank_canonical_adapter import (
    adapt_bank_canonical_input,
)


def main():

    facts = {}

    for component in BANK_COMPONENTS:
        for metric in BANK_REQUIRED_METRICS[
            component
        ]:
            facts[
                f"{component}.{metric}"
            ] = 1.0

    record = {
        "symbol": "CONTRACT_BANK",
        "sector_model": "BANK",
        "as_of": "2026-08-31",
        "publication_date": "2026-08-15",
        "canonical_facts": facts,
    }

    result = adapt_bank_canonical_input(
        record
    )

    print(f"STATUS={result.status}")
    print(f"SYMBOL={result.symbol}")
    print(f"AS_OF={result.as_of}")
    print(
        f"PUBLICATION_DATE="
        f"{result.publication_date}"
    )
    print(f"BLOCKER={result.blocker}")
    print(
        f"PAYLOAD_READY="
        f"{result.payload is not None}"
    )
    print("PRODUCTION_EVIDENCE=False")

    if result.status != "PASS":
        raise SystemExit(
            "BANK_CANONICAL_ADAPTER_CONTRACT_BLOCKED"
        )

    print(
        "FINANCIAL_INTELLIGENCE_V1_2_"
        "BANK_CANONICAL_INPUT_PIT_BOUNDARY_V1=PASS"
    )


if __name__ == "__main__":
    main()
