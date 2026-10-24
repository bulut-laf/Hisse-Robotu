from backend.app.workflow.ev21_final_ev22_foundation_block import (
    build_ev21_final_ev22_foundation_state,
)


def test_ev21_final_ev22_foundation_block():
    result = build_ev21_final_ev22_foundation_state("tuprs")

    assert result.symbol == "TUPRS"
    assert result.adaptation_state == "LOCKED"
    assert result.lock_state == "READY"
    assert result.foundation_state == "PREPARED"
    assert result.source == "EARLY_VISIBILITY"
