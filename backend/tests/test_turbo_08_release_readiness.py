from backend.app.analysis.v1_release_readiness import (
    build_v1_release_readiness,
)


def test_turbo_08_release_readiness():
    result = build_v1_release_readiness(
        regression_passed=True,
        morning_flow_ready=True,
        operation_cycle_ready=True,
    )

    assert result.regression_passed is True
    assert result.morning_flow_ready is True
    assert result.operation_cycle_ready is True
    assert result.readiness_state == "V1 RELEASE HAZIR"
