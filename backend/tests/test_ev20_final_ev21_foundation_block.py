from backend.app.workflow.ev20_final_ev21_foundation_block import (
    build_ev20_final_ev21_foundation_state,
)


def test_ev20_final_ev21_foundation_block():
    result = build_ev20_final_ev21_foundation_state("tuprs")

    assert result.symbol == "TUPRS"
    assert result.maturity_state == "LOCKED"
    assert result.readiness_state == "READY"
    assert result.foundation_state == "PREPARED"
    assert result.source == "EARLY_VISIBILITY"
