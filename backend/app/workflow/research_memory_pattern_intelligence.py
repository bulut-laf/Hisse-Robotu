from dataclasses import dataclass


@dataclass(frozen=True)
class ResearchMemoryPatternState:
    symbol: str
    memory_state: str
    retrieval_state: str
    comparison_state: str
    source: str = "EARLY_VISIBILITY"


def build_research_memory_pattern_state(symbol: str):
    return ResearchMemoryPatternState(
        symbol=str(symbol).upper(),
        memory_state="FOUNDATION",
        retrieval_state="PREPARED",
        comparison_state="OBSERVED",
    )
