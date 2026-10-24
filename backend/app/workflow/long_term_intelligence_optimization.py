from dataclasses import dataclass


@dataclass(frozen=True)
class LongTermIntelligenceOptimizationState:
    symbol: str
    learning_state: str
    improvement_state: str
    knowledge_state: str
    readiness_state: str
    source: str = "EARLY_VISIBILITY"


def build_long_term_intelligence_optimization_state(symbol: str):
    return LongTermIntelligenceOptimizationState(
        symbol=str(symbol).upper(),
        learning_state="FOUNDATION",
        improvement_state="TRACKING",
        knowledge_state="EVOLVING",
        readiness_state="PREPARED",
    )
