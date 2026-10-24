from dataclasses import dataclass


@dataclass(frozen=True)
class AdaptiveResearchFinalLock:
    symbol: str
    workflow_state: str
    memory_state: str
    optimization_state: str
    readiness_state: str
    source: str = "EARLY_VISIBILITY"


def build_adaptive_research_final_lock(symbol: str):
    return AdaptiveResearchFinalLock(
        symbol=str(symbol).upper(),
        workflow_state="LOCKED",
        memory_state="CONNECTED",
        optimization_state="PREPARED",
        readiness_state="READY",
    )
