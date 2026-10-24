from dataclasses import dataclass


@dataclass(frozen=True)
class AdaptiveResearchWorkflowState:
    symbol: str
    priority_state: str
    follow_up_state: str
    efficiency_state: str
    source: str = "EARLY_VISIBILITY"


def build_adaptive_research_workflow_state(symbol: str):
    return AdaptiveResearchWorkflowState(
        symbol=str(symbol).upper(),
        priority_state="TRACKING",
        follow_up_state="FOUNDATION",
        efficiency_state="OBSERVED",
    )
