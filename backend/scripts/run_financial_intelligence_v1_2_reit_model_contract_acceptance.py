from app.analysis.financial_intelligence_reit_model_contract import (
    REIT_COMPONENTS,
    REIT_COMPONENT_WEIGHTS,
    REIT_REQUIRED_METRICS,
    validate_reit_model_input,
)


def _complete_payload():
    return {
        component: {
            metric: 1.0
            for metric in REIT_REQUIRED_METRICS[component]
        }
        for component in REIT_COMPONENTS
    }


def main():
    print(
        f"REIT_COMPONENTS="
        f"{list(REIT_COMPONENTS)}"
    )

    print(
        f"REIT_COMPONENT_WEIGHTS="
        f"{REIT_COMPONENT_WEIGHTS}"
    )

    complete = validate_reit_model_input(
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
        "PORTFOLIO_QUALITY"
    ]["occupancy_rate"] = None

    blocked = validate_reit_model_input(
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
            "COMPLETE_REIT_CONTRACT_BLOCKED"
        )

    if blocked.ready_for_scoring:
        raise SystemExit(
            "MISSING_REIT_DATA_DID_NOT_FAIL_CLOSED"
        )

    print(
        "FINANCIAL_INTELLIGENCE_V1_2_"
        "REIT_DEDICATED_MODEL_CONTRACT_V1=PASS"
    )


if __name__ == "__main__":
    main()
