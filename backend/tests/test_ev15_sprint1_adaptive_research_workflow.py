from backend.app.workflow.adaptive_research_workflow import (
    build_adaptive_research_workflow_state,
)


def test_ev15_sprint1_adaptive_research_workflow():
    result = build_adaptive_research_workflow_state("tuprs")

    assert result.symbol == "TUPRS"
    assert result.priority_state == "TRACKING"
    assert result.follow_up_state == "FOUNDATION"
    assert result.efficiency_state == "OBSERVED"
    assert result.source == "EARLY_VISIBILITY"
