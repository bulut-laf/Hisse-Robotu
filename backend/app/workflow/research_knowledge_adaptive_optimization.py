from dataclasses import dataclass


@dataclass(frozen=True)
class ResearchKnowledgeAdaptiveState:
    symbol: str
    knowledge_state: str
    priority_state: str
    optimization_state: str
    source: str = "EARLY_VISIBILITY"


def build_research_knowledge_adaptive_state(symbol: str):
    return ResearchKnowledgeAdaptiveState(
        symbol=str(symbol).upper(),
        knowledge_state="FOUNDATION",
        priority_state="IMPROVING",
        optimization_state="PREPARED",
    )
