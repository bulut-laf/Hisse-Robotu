from app.analysis.financial_intelligence_bank_model_contract import (
    BANK_COMPONENTS,
    BANK_COMPONENT_WEIGHTS,
    BANK_REQUIRED_METRICS,
    validate_bank_model_input,
)


def _complete_payload():
    return {
        component: {
            metric: 1.0
            for metric in BANK_REQUIRED_METRICS[component]
        }
        for component in BANK_COMPONENTS
    }


def main():
    print(f"BANK_COMPONENTS={list(BANK_COMPONENTS)}")
    print(f"BANK_COMPONENT_WEIGHTS={BANK_COMPONENT_WEIGHTS}")

    complete = validate_bank_model_input(
        _complete_payload()
    )

    print(f"COMPLETE_STATUS={complete.status}")
    print(
        f"COMPLETE_READY_FOR_SCORING="
        f"{complete.ready_for_scoring}"
    )

    incomplete = _complete_payload()
    incomplete["ASSET_QUALITY"]["npl_ratio"] = None

    blocked = validate_bank_model_input(
        incomplete
    )

    print(f"MISSING_STATUS={blocked.status}")
    print(
        f"MISSING_READY_FOR_SCORING="
        f"{blocked.ready_for_scoring}"
    )
    print(f"MISSING_BLOCKER={blocked.blocker}")

    if not complete.ready_for_scoring:
        raise SystemExit("COMPLETE_BANK_CONTRACT_BLOCKED")

    if blocked.ready_for_scoring:
        raise SystemExit("MISSING_BANK_DATA_DID_NOT_FAIL_CLOSED")

    print(
        "FINANCIAL_INTELLIGENCE_V1_2_BANK_DEDICATED_MODEL_CONTRACT_V1=PASS"
    )


if __name__ == "__main__":
    main()
