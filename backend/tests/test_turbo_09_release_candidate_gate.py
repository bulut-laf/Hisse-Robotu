from backend.app.analysis.v1_release_candidate_gate import (
    build_v1_release_candidate_gate,
)


def test_turbo_09_release_candidate_gate():
    result = build_v1_release_candidate_gate(
        regression_passed=True,
        operation_ready=True,
        user_flow_ready=True,
    )

    assert result.regression_passed is True
    assert result.operation_ready is True
    assert result.user_flow_ready is True
    assert result.release_state == "V1 RELEASE CANDIDATE HAZIR"
