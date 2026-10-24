from app.analysis.financial_intelligence_bank_model_contract import (
    BANK_COMPONENTS,
    BANK_REQUIRED_METRICS,
)
from app.analysis.financial_intelligence_bank_production_source_onboarding import (
    evaluate_bank_production_source,
)


def main():
    facts = {}

    for component in BANK_COMPONENTS:
        for metric in BANK_REQUIRED_METRICS[component]:
            facts[f"{component}.{metric}"] = 1.0

    contract_source = {
        "source_type": "CONTRACT",
        "source_uri": "contract://bank",
        "symbol": "CONTRACT_BANK",
        "sector_model": "BANK",
        "as_of": "2026-08-31",
        "publication_date": "2026-08-15",
        "canonical_facts": facts,
        "evidence_hash": "sha256:contract",
    }

    blocked = evaluate_bank_production_source(
        contract_source
    )

    print(f"CONTRACT_STATUS={blocked.status}")
    print(
        f"CONTRACT_PRODUCTION_EVIDENCE="
        f"{blocked.production_evidence}"
    )
    print(
        f"CONTRACT_ACTIVATION_READY="
        f"{blocked.activation_ready}"
    )
    print(
        f"CONTRACT_BLOCKER="
        f"{blocked.blocker}"
    )

    if blocked.status != "BLOCKED":
        raise SystemExit(
            "CONTRACT_SOURCE_MUST_NOT_ACTIVATE_BANK"
        )

    print("REAL_SOURCE_PRESENT=False")
    print("BANK_PRODUCTION_READY=False")
    print("BLOCKER=NO_REAL_BANK_SOURCE")
    print("AL_SAT_AUTHORITY=NONE")
    print("STORE_MUTATION=NO")
    print(
        "FINANCIAL_INTELLIGENCE_V1_3_"
        "BANK_PRODUCTION_SOURCE_ONBOARDING_CONTRACT_V1=PASS"
    )


if __name__ == "__main__":
    main()
