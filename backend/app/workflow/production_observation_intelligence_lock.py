from dataclasses import dataclass


@dataclass(frozen=True)
class ProductionObservationIntelligenceLock:
    symbol: str
    observation_state: str
    quality_state: str
    feedback_state: str
    readiness_state: str
    source: str = "EARLY_VISIBILITY"


def build_production_observation_intelligence_lock(symbol: str):
    return ProductionObservationIntelligenceLock(
        symbol=str(symbol).upper(),
        observation_state="LOCKED",
        quality_state="LOCKED",
        feedback_state="CONNECTED",
        readiness_state="READY",
    )
