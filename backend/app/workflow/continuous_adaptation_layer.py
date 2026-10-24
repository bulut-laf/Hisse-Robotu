from dataclasses import dataclass


@dataclass(frozen=True)
class ContinuousAdaptationState:
    symbol: str
    adaptation_state: str
    refinement_state: str
    optimization_bridge_state: str
    source: str = "EARLY_VISIBILITY"


def build_continuous_adaptation_state(symbol: str):
    return ContinuousAdaptationState(
        symbol=str(symbol).upper(),
        adaptation_state="TRACKING",
        refinement_state="ACTIVE",
        optimization_bridge_state="PREPARED",
    )
