from dataclasses import dataclass


@dataclass(frozen=True)
class EarlyVisibilityProductionObservation:
    symbol: str
    mode_state: str
    observation_state: str
    feedback_state: str
    source: str = "EARLY_VISIBILITY"


def build_early_visibility_production_observation(symbol: str):
    return EarlyVisibilityProductionObservation(
        symbol=str(symbol).upper(),
        mode_state="PRODUCTION_OBSERVATION",
        observation_state="ACTIVE",
        feedback_state="COLLECTING",
    )
