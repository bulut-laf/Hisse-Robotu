from dataclasses import dataclass


@dataclass(frozen=True)
class ContinuousIntelligenceOptimizationState:
    symbol: str
    observation_state: str
    improvement_state: str
    optimization_state: str
    source: str = "EARLY_VISIBILITY"


def build_continuous_intelligence_optimization_state(symbol: str):
    return ContinuousIntelligenceOptimizationState(
        symbol=str(symbol).upper(),
        observation_state="ACTIVE",
        improvement_state="TRACKING",
        optimization_state="FOUNDATION",
    )
