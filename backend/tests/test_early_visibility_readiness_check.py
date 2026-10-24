from backend.app.workflow.early_visibility_readiness_check import (
    build_early_visibility_readiness_check,
)


def test_early_visibility_readiness_check():
    result = build_early_visibility_readiness_check("tuprs")

    assert result.symbol == "TUPRS"
    assert result.chain_state == "CONNECTED"
    assert result.task_engine_state == "READY"
    assert result.intelligence_state == "LOCKED"
    assert result.activation_state == "PREPARED"
    assert result.source == "EARLY_VISIBILITY"
