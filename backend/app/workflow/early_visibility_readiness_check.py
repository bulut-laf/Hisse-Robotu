from dataclasses import dataclass


@dataclass(frozen=True)
class EarlyVisibilityReadinessState:
    symbol: str
    chain_state: str
    task_engine_state: str
    intelligence_state: str
    activation_state: str
    source: str = "EARLY_VISIBILITY"


def build_early_visibility_readiness_check(symbol: str):
    return EarlyVisibilityReadinessState(
        symbol=str(symbol).upper(),
        chain_state="CONNECTED",
        task_engine_state="READY",
        intelligence_state="LOCKED",
        activation_state="PREPARED",
    )
