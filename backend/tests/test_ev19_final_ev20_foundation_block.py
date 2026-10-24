from backend.app.workflow.ev19_final_ev20_foundation_block import (
    build_ev19_final_ev20_foundation_state,
)


def test_ev19_final_ev20_foundation_block():
    result = build_ev19_final_ev20_foundation_state("tuprs")

    assert result.symbol == "TUPRS"
    assert result.evolution_state == "LOCKED"
    assert result.lock_state == "READY"
    assert result.foundation_state == "PREPARED"
    assert result.source == "EARLY_VISIBILITY"
