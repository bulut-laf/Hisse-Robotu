from backend.app.workflow.final_intelligence_maturity_block import (
    build_final_intelligence_maturity_state,
)


def test_ev28_ev30_final_intelligence_maturity_block():
    result = build_final_intelligence_maturity_state("tuprs")

    assert result.symbol == "TUPRS"
    assert result.maturity_state == "ADVANCED"
    assert result.autonomy_state == "FOUNDATION"
    assert result.optimization_state == "ACTIVE"
    assert result.readiness_state == "PREPARED"
    assert result.source == "EARLY_VISIBILITY"
