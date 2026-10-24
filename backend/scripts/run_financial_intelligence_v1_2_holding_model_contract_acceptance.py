from app.analysis.financial_intelligence_holding_model_contract import (
    HOLDING_COMPONENTS,
    HOLDING_COMPONENT_WEIGHTS,
    HOLDING_REQUIRED_METRICS,
    validate_holding_model_input,
)


def _complete_payload():
    return {
        component: {
            metric: 1.0
            for metric in HOLDING_REQUIRED_METRICS[component]
        }
        for component in HOLDING_COMPONENTS
    }


def main():
    print(
        f"HOLDING_COMPONENTS="
        f"{list(HOLDING_COMPONENTS)}"
    )

    print(
        f"HOLDING_COMPONENT_WEIGHTS="
        f"{HOLDING_COMPONENT_WEIGHTS}"
    )

    complete = validate_holding_model_input(
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
        "NAV_QUALITY"
    ]["price_to_nav_ratio"] = None

    blocked = validate_holding_model_input(
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
            "COMPLETE_HOLDING_CONTRACT_BLOCKED"
        )

    if blocked.ready_for_scoring:
        raise SystemExit(
            "MISSING_HOLDING_DATA_DID_NOT_FAIL_CLOSED"
        )

    print(
        "FINANCIAL_INTELLIGENCE_V1_2_"
        "HOLDING_DEDICATED_MODEL_CONTRACT_V1=PASS"
    )


if __name__ == "__main__":
    main()
