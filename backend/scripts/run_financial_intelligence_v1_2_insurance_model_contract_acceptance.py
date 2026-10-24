from app.analysis.financial_intelligence_insurance_model_contract import (
    INSURANCE_COMPONENTS,
    INSURANCE_COMPONENT_WEIGHTS,
    INSURANCE_REQUIRED_METRICS,
    validate_insurance_model_input,
)


def _complete_payload():
    return {
        component: {
            metric: 1.0
            for metric in INSURANCE_REQUIRED_METRICS[
                component
            ]
        }
        for component in INSURANCE_COMPONENTS
    }


def main():
    print(
        f"INSURANCE_COMPONENTS="
        f"{list(INSURANCE_COMPONENTS)}"
    )

    print(
        f"INSURANCE_COMPONENT_WEIGHTS="
        f"{INSURANCE_COMPONENT_WEIGHTS}"
    )

    complete = validate_insurance_model_input(
        _complete_payload()
    )

    print(
        f"COMPLETE_STATUS="
        f"{complete.status}"
    )

    print(
        f"COMPLETE_READY_FOR_SCORING="
        f"{complete.ready_for_scoring}"
    )

    incomplete = _complete_payload()

    incomplete[
        "UNDERWRITING_QUALITY"
    ]["combined_ratio"] = None

    blocked = validate_insurance_model_input(
        incomplete
    )

    print(
        f"MISSING_STATUS="
        f"{blocked.status}"
    )

    print(
        f"MISSING_READY_FOR_SCORING="
        f"{blocked.ready_for_scoring}"
    )

    print(
        f"MISSING_BLOCKER="
        f"{blocked.blocker}"
    )

    if not complete.ready_for_scoring:
        raise SystemExit(
            "COMPLETE_INSURANCE_CONTRACT_BLOCKED"
        )

    if blocked.ready_for_scoring:
        raise SystemExit(
            "MISSING_INSURANCE_DATA_DID_NOT_FAIL_CLOSED"
        )

    print(
        "FINANCIAL_INTELLIGENCE_V1_2_"
        "INSURANCE_DEDICATED_MODEL_CONTRACT_V1=PASS"
    )


if __name__ == "__main__":
    main()
